# Creepy Crawler for n8n Workflows

A web crawling and scraping system designed to extract structured data from websites, with special support for n8n workflows.

## Overview

Creepy Crawler is built on top of the Crawl4AI framework and specializes in:

1. Extracting n8n workflows from websites
2. Validating and analyzing workflow JSON files
3. Generating comprehensive documentation for workflows
4. Processing workflows in batch mode

## Features

- **Workflow Extraction**: Extract n8n workflows from websites
- **Validation & Analysis**: Automatically validate, fix, and analyze workflow JSON
- **LLM Integration**: Use advanced language models to analyze and improve workflows
- **Batch Processing**: Process multiple workflows in batch mode
- **Comprehensive Documentation**: Generate detailed README files for each workflow

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ruskibeats/creepy-crawler.git
cd creepy-crawler
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Process a Single Workflow

```bash
source venv/bin/activate
python -m src.processors.n8n_workflow_processor [workflow_id]
```

### Process Multiple Workflows

```bash
source venv/bin/activate
python -m src.processors.batch_workflow_processor --urls-file [path_to_urls_file]
```

### Analyze a Local Workflow File

```bash
source venv/bin/activate
python test_template.py --workflow [path_to_workflow_file]
```

## Outputs

The system generates the following outputs for each workflow:
- Workflow JSON file
- Metadata JSON file
- Analysis file
- README.md with comprehensive documentation

## License

MIT
