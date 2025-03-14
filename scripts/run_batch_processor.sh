#!/bin/bash
# Run Batch Workflow Processor
# This script runs the batch workflow processor with different configurations.

# Default values
URLS_FILE="urls.txt"
INITIAL_CONCURRENCY=2
MAX_CONCURRENCY=5
ENABLE_API=false
API_PORT=8080
API_HOST="0.0.0.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --urls-file)
      URLS_FILE="$2"
      shift 2
      ;;
    --initial-concurrency)
      INITIAL_CONCURRENCY="$2"
      shift 2
      ;;
    --max-concurrency)
      MAX_CONCURRENCY="$2"
      shift 2
      ;;
    --enable-api)
      ENABLE_API=true
      shift
      ;;
    --api-port)
      API_PORT="$2"
      shift 2
      ;;
    --api-host)
      API_HOST="$2"
      shift 2
      ;;
    --generate)
      GENERATE=true
      shift
      ;;
    --count)
      COUNT="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --urls-file FILE          File containing URLs to process (default: urls.txt)"
      echo "  --initial-concurrency N   Initial number of concurrent workers (default: 2)"
      echo "  --max-concurrency N       Maximum number of concurrent workers (default: 5)"
      echo "  --enable-api              Enable API endpoint"
      echo "  --api-port PORT           Port for API endpoint (default: 8080)"
      echo "  --api-host HOST           Host for API endpoint (default: 0.0.0.0)"
      echo "  --generate                Generate URLs file before running"
      echo "  --count N                 Number of URLs to generate (default: 10)"
      echo "  --help                    Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Ensure required directories exist
mkdir -p logs db

# Generate URLs file if requested
if [ "$GENERATE" = true ]; then
  echo "Generating URLs file..."
  python scripts/generate_urls_file.py --output "$URLS_FILE" ${COUNT:+--count "$COUNT"}
fi

# Check if URLs file exists
if [ ! -f "$URLS_FILE" ]; then
  echo "Error: URLs file '$URLS_FILE' not found"
  exit 1
fi

# Count URLs in file
URL_COUNT=$(wc -l < "$URLS_FILE")
echo "Processing $URL_COUNT URLs from $URLS_FILE"

# Build command
CMD="python -m src.processors.batch_workflow_processor --urls-file $URLS_FILE --initial-concurrency $INITIAL_CONCURRENCY --max-concurrency $MAX_CONCURRENCY"

if [ "$ENABLE_API" = true ]; then
  CMD="$CMD --enable-api --api-port $API_PORT --api-host $API_HOST"
fi

# Run batch processor
echo "Running batch processor with command:"
echo "$CMD"
echo "----------------------------------------"

# Execute command
eval "$CMD"
