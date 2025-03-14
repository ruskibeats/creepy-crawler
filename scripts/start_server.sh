#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to view logs
view_logs() {
    echo "Viewing logs (Ctrl+C to exit)..."
    tail -f server.log
}

# Function to show help
show_help() {
    echo "Usage: ./start_server.sh [command]"
    echo "Commands:"
    echo "  start    - Start the server (default)"
    echo "  logs     - View server logs"
    echo "  help     - Show this help message"
}

# Install dependencies
install_deps() {
    echo "Installing dependencies..."
    
    # Install system packages
    echo "Installing system packages..."
    apt-get update && apt-get install -y \
        python3-pip \
        python3-venv \
        chromium \
        chromium-driver \
        psutil \
        procps \
        net-tools \
        lsof
    
    # Remove existing venv if it exists
    if [ -d "venv" ]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
    fi

    # Create fresh virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv

    # Activate virtual environment and install dependencies
    echo "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    
    # Install dependencies with verbose output
    echo "Installing dependencies..."
    pip install -v --no-cache-dir -r requirements.txt || {
        echo "Error: Failed to install dependencies"
        return 1
    }
    
    # Verify all required modules are installed
    echo "Verifying dependencies..."
    python3 -c "import fastapi, uvicorn, pydantic, aiohttp, selenium, psutil, structlog, requests" || {
        echo "Error: Missing required Python modules"
        return 1
    }
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        return 1
    fi
}

# Start the server
start_server() {
    echo "Starting server..."
    
    # Ensure we're in the virtual environment
    source venv/bin/activate || {
        echo "Error: Failed to activate virtual environment"
        return 1
    }
    
    # Verify all required modules are installed
    echo "Verifying dependencies..."
    python3 -c "import fastapi, uvicorn, pydantic, aiohttp, selenium, psutil, structlog, requests" || {
        echo "Error: Missing required Python modules"
        return 1
    }
    
    echo "Starting server with manager..."
    
    # Kill any existing processes on port 8000
    echo "Checking for existing processes on port 8000..."
    if command -v fuser >/dev/null 2>&1; then
        fuser -k 8000/tcp 2>/dev/null || true
    elif command -v lsof >/dev/null 2>&1; then
        pid=$(lsof -t -i:8000 2>/dev/null)
        if [ ! -z "$pid" ]; then
            echo "Killing process $pid on port 8000"
            kill -9 $pid
        fi
    fi
    
    # Wait for port to be available
    echo "Waiting for port 8000 to be available..."
    for i in {1..10}; do
        if ! (command -v fuser >/dev/null 2>&1 && fuser 8000/tcp 2>/dev/null) && \
           ! (command -v lsof >/dev/null 2>&1 && lsof -i:8000 >/dev/null 2>&1); then
            break
        fi
        echo "Port 8000 still in use, waiting..."
        sleep 2
    done
    
    # Set environment variables for Chrome
    export CHROME_BIN=/usr/bin/chromium
    export CHROMEDRIVER_PATH=/usr/bin/chromedriver
    
    # Start the server directly
    echo "Launching server..."
    python3 api_server.py 2>&1 | tee -a server.log
}

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    if [ -d "venv" ]; then
        deactivate 2>/dev/null || true
    fi
    
    # Remove temporary files
    rm -f *.pyc
    rm -rf __pycache__
    
    echo "Cleanup complete"
}

# Register cleanup function
trap cleanup EXIT

# Main command handling
case "$1" in
    "logs")
        view_logs
        ;;
    "help")
        show_help
        ;;
    "start"|"")
        install_deps
        start_server
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
