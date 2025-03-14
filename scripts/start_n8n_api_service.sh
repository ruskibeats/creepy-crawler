#!/bin/bash

# Log file
LOG_DIR="/var/log/n8n_api"
LOG_FILE="$LOG_DIR/n8n_api.log"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Function to check if a port is in use
is_port_in_use() {
    netstat -tuln | grep ":$1 " > /dev/null
    return $?
}

# Function to kill processes using a specific port
kill_processes_on_port() {
    local port=$1
    log "Checking for processes on port $port"
    
    # Find PIDs using the port
    local pids=$(lsof -t -i:$port)
    
    if [ -n "$pids" ]; then
        log "Found processes using port $port: $pids"
        log "Killing processes: $pids"
        
        # Try graceful termination first
        kill $pids 2>/dev/null
        
        # Wait a bit
        sleep 2
        
        # Check if processes are still running
        local remaining_pids=$(lsof -t -i:$port)
        if [ -n "$remaining_pids" ]; then
            log "Processes still running, using force kill: $remaining_pids"
            kill -9 $remaining_pids 2>/dev/null
        fi
        
        # Final check
        if is_port_in_use $port; then
            log "ERROR: Failed to free port $port"
            return 1
        else
            log "Successfully freed port $port"
            return 0
        fi
    else
        log "No processes found using port $port"
        return 0
    fi
}

# This script is now used as a pre-start script for the systemd service
# It only kills existing processes and doesn't start the server itself

log "Starting n8n API service pre-start script"

# Kill any existing processes on port 8000
log "Checking for processes on port 8000"
kill_processes_on_port 8000

# Try additional methods to ensure port is free
log "Using additional methods to free port 8000"
fuser -k 8000/tcp 2>/dev/null || true

# Make sure all previous uvicorn processes are killed
log "Killing all previous uvicorn processes"
pkill -f "uvicorn api_server:app" || true

# Wait to ensure processes are terminated
log "Waiting for processes to terminate"
sleep 2

# Final check to ensure port is free
if is_port_in_use 8000; then
    log "ERROR: Failed to free port 8000 after multiple attempts"
    exit 1
else
    log "Port 8000 is free and ready for use"
fi

# Activate virtual environment (not needed anymore as systemd service uses full path)
log "Pre-start script completed successfully"

# Exit with success
exit 0
