# Codebase Summary

## Project Structure

```
/root/.crawl4ai/
├── cline_docs/                      # Project documentation
│   ├── prompt_templates/            # LLM prompt templates
│   │   ├── combined_analysis.md     # Main template for workflow analysis
│   │   ├── technical_analysis.md    # Technical-focused template
│   │   └── business_vertical.md     # Business-focused template
│   ├── README.md                    # Documentation overview
│   ├── projectRoadmap.md            # Project goals and progress
│   ├── currentTask.md               # Current objectives and next steps
│   ├── techStack.md                 # Technology choices and decisions
│   ├── system_architecture.md       # System architecture documentation
│   └── codebaseSummary.md           # This file
│
├── src/                             # Source code
│   ├── __init__.py                  # Package initialization
│   ├── processors/                  # Workflow processors
│   │   ├── __init__.py              # Package initialization
│   │   ├── n8n_workflow_processor.py # Main workflow processor
│   │   └── batch_workflow_processor.py # Batch processing logic
│   │
│   └── utils/                       # Utility modules
│       ├── __init__.py              # Package initialization
│       ├── common.py                # Common utility functions
│       ├── config.py                # Configuration management
│       ├── smart_queue.py           # Queue and rate limiting
│       ├── system_monitor.py        # System monitoring
│       └── adaptive_processor.py    # Adaptive processing logic
│
├── scripts/                         # Helper scripts
│   ├── run_batch_processor.sh       # Script to run batch processor
│   └── generate_urls_file.py        # Script to generate URL list
│
├── test_template.py                 # Template testing script
└── requirements.txt                 # Project dependencies
```

## Key Components and Their Interactions

### Core Components

1. **Workflow Processor (`n8n_workflow_processor.py`)**
   - Fetches workflow data from n8n.io
   - Extracts metadata and workflow JSON
   - Uses templates to generate LLM prompts
   - Calls OpenRouter API for analysis
   - Saves results to output directory

2. **Batch Processor (`batch_workflow_processor.py`)**
   - Processes multiple workflows in batches
   - Implements rate limiting and cooldown
   - Handles errors and retries

3. **Smart Queue (`smart_queue.py`)**
   - Manages workflow processing queue
   - Implements token bucket rate limiter
   - Handles deduplication and priority

4. **System Monitor (`system_monitor.py`)**
   - Tracks processing metrics
   - Monitors system health
   - Implements alert thresholds

5. **Template System (`prompt_templates/`)**
   - Provides templates for LLM prompts
   - Supports different analysis types
   - Uses simple variable substitution

### Planned Components

1. **URL Manager (to be implemented)**
   - Will parse sitemap.xml for workflow URLs
   - Will handle URL deduplication and tracking
   - Will integrate with smart queue

2. **Output Manager (to be implemented)**
   - Will enforce directory structure
   - Will handle workflow saving and organization
   - Will implement error handling and logging

## Data Flow

1. **Input**: Workflow URLs from sitemap.xml or bulk import
2. **Queue**: URLs added to smart queue with deduplication
3. **Processing**: Batch processor fetches workflows in chunks
4. **Analysis**: LLM generates analysis using templates
5. **Output**: Results saved to structured directory

## External Dependencies

1. **OpenRouter API**
   - Used to access LLM models
   - Requires API key in configuration
   - Rate limited based on subscription

2. **Mistral AI Models**
   - Primary: `mistralai/ministral-8b`
   - Fallback: `mistralai/mistral-small`
   - Accessed through OpenRouter API

3. **n8n.io**
   - Source of workflow data
   - Accessed through web scraping
   - Provides sitemap-workflows.xml (https://n8n.io/sitemap-workflows.xml) for workflow discovery
   - Workflow URLs extracted from 'loc' parameter in the sitemap

## Recent Significant Changes

1. **Template System Implementation**
   - Added template-based workflow analysis
   - Created templates for different analysis types
   - Implemented template loading and rendering

2. **Mistral AI Integration**
   - Switched from OpenAI to Mistral models
   - Updated configuration to use model from settings
   - Modified code to support different models

3. **Enhanced Node Analysis**
   - Added explicit node type information
   - Improved node description quality
   - Ensured all nodes are covered in analysis

4. **Documentation Updates**
   - Created system architecture documentation
   - Updated project roadmap and task list
   - Documented technology stack and decisions

## User Feedback Integration

Recent user feedback has highlighted the need for:

1. **Scalability**: System needs to handle ~1500 workflow URLs
2. **Rate Limiting**: Need to avoid API restrictions
3. **Output Management**: Results must be saved to specific directory
4. **Monitoring**: Need visibility into processing status

These requirements have been incorporated into the current development plan, with specific tasks created to address each point.
