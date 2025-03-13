# Crawl4AI Project

## Overview

Crawl4AI is a web crawling and scraping API designed to extract structured data from websites, with special support for n8n workflows. This project provides comprehensive tools for extracting, validating, and analyzing workflow data.

## Project Structure

The project has been reorganized into a more maintainable structure:

```
/
├── src/                    # Source code
│   ├── api/                # API server components
│   │   ├── api_server.py   # FastAPI-based REST API
│   │   └── rate_limiter.py # Request rate limiting
│   ├── crawler/            # Web crawling components
│   │   ├── crawler_script.py # Selenium-based crawler
│   │   └── extract_workflow.py # Workflow extraction
│   ├── processors/         # Data processing components
│   │   ├── n8n_workflow_processor.py # Workflow processing
│   │   └── get_workflow.py # Workflow fetching
│   ├── validators/         # Validation components
│   │   ├── n8n_validator.py # Workflow validation
│   │   └── validate_n8n_json_llm.py # LLM-based validation
│   └── utils/              # Shared utilities
│       ├── common.py       # Common functions
│       ├── config.py       # Centralized configuration
│       └── logging_config.py # Logging configuration
├── tests/                  # Test files
├── docs/                   # Documentation
├── scripts/                # Shell scripts
├── cline_docs/             # Project management documentation
├── api/                    # API-related files
├── config/                 # Configuration files
├── db/                     # Database files
├── logs/                   # Log files
├── workflows/              # Workflow JSON files
└── backups/                # Backup files
```

## Key Improvements

1. **Modular Design**: Code is now organized into logical modules with clear responsibilities
2. **Shared Utilities**: Common functionality has been extracted into shared modules
3. **Centralized Configuration**: All configuration is now managed through a hierarchical config class
4. **Clean Root Directory**: The root directory is now clean and organized

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the API server:
   ```bash
   ./scripts/start_server.sh
   ```

3. Process a single workflow:
   ```bash
   python -m src.processors.n8n_workflow_processor <workflow_id>
   ```

4. Process a batch of workflows with adaptive resource management:
   ```bash
   # Generate a test URLs file with 10 URLs
   ./scripts/generate_urls_file.py --output urls.txt --count 10
   
   # Process the URLs with adaptive concurrency
   ./scripts/run_batch_processor.sh --urls-file urls.txt --initial-concurrency 2 --max-concurrency 5
   
   # Enable API endpoint for monitoring and control
   ./scripts/run_batch_processor.sh --urls-file urls.txt --enable-api
   ```

## Batch Processing Features

The batch processing system includes:

1. **Adaptive Resource Management**
   - Dynamically adjusts concurrency based on system performance
   - Starts conservatively and scales up/down as needed
   - Monitors CPU, memory, and processing times

2. **Self-Healing Capabilities**
   - Automatically retries failed URLs
   - Creates checkpoints for recovery
   - Tracks completed URLs to avoid duplication

3. **Monitoring and Control**
   - Optional API endpoint for status monitoring
   - Pause/resume processing via API
   - Detailed statistics and progress tracking

## Documentation

See the `docs/` directory for detailed documentation on each component.

## Project Management

The `cline_docs/` directory contains project management documentation:
- `projectRoadmap.md`: High-level goals and features
- `currentTask.md`: Current objectives and next steps
- `techStack.md`: Key technology choices
- `codebaseSummary.md`: Overview of project structure and components
# creepy-crawler
