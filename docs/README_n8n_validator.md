# N8N Workflow Validator with LLM Analysis and Metadata Extraction

This tool validates, fixes, analyzes, and extracts metadata from n8n workflow JSON files using OpenRouter's LLM capabilities. It helps identify issues, improve workflow quality, and ensure compliance with n8n's schema requirements.

## Features

- ✅ **JSON Validation**: Validates workflow structure against n8n schema requirements
- 🔧 **Automatic Fixes**: Fixes common issues like missing fields and misplaced properties
- 🧠 **LLM Analysis**: Uses OpenRouter's LLM to analyze workflows for improvements
- 🔄 **JSON Repair**: Fixes malformed JSON using LLM capabilities
- 💾 **Cleaned Output**: Saves a cleaned version of the workflow
- 🌐 **Workflow Fetching**: Fetches workflows directly from n8n.io by ID
- 📊 **Metadata Extraction**: Extracts and saves workflow metadata

## Requirements

- Python 3.6+
- Required packages:
  - `requests`
  - `python-dotenv`
  - `openai` (for OpenRouter API)
  - `beautifulsoup4` (for fetching workflows from n8n.io)

## Installation

1. Clone this repository or download the script
2. Install required packages:

```bash
pip install requests python-dotenv openai beautifulsoup4
```

3. Create a `.env` file with your OpenRouter API key:

```
OPENROUTER_API_KEY=your_api_key_here
```

## Usage

### Validating Local Workflow Files

```bash
python n8n_validator.py --validate your_workflow.json
```

With metadata:

```bash
python n8n_validator.py --validate your_workflow.json --metadata your_metadata.json
```

### Fetching and Validating Workflows from n8n.io

Using BeautifulSoup (default):

```bash
python n8n_validator.py --fetch 2859-chat-with-postgresql-database
```

Using the test-grid-scrape API:

```bash
python n8n_validator.py --fetch 2859-chat-with-postgresql-database --api
```

This will:
1. Fetch the workflow JSON from n8n.io
2. Extract metadata (title, description, version, etc.)
3. Save the raw workflow JSON and metadata to separate files
4. Validate the workflow structure
5. Fix common issues
6. Provide detailed analysis using OpenRouter's LLM
7. Save a cleaned version of the workflow

## What It Validates

The validator checks for:

1. **Required Keys**: Ensures the workflow has all required top-level keys
2. **Node Structure**: Validates each node has required fields
3. **Connections**: Checks that connections are properly structured
4. **Type Placement**: Fixes misplaced typeVersion properties
5. **JSON Syntax**: Repairs malformed JSON using LLM

## Metadata Extraction

The tool extracts and saves the following metadata:

- **Title**: Workflow title
- **Description**: Workflow description
- **Version**: Workflow version
- **Nodes**: Node descriptions and details
- **Template Details**: Raw HTML template details
- **Template Description**: Full workflow description

## LLM Analysis

The LLM analysis provides insights on:

1. **Structural Issues**: Missing or misconfigured fields
2. **Logical Errors**: Inefficiencies or potential bugs
3. **Security Concerns**: Potential security vulnerabilities
4. **Optimization Suggestions**: Ways to improve the workflow
5. **Reliability Recommendations**: How to make the workflow more robust

## Example Output

```
================================================================================
🚀 N8N Workflow Validator with LLM Analysis
================================================================================
Fetching workflow from: https://n8n.io/workflows/2859-chat-with-postgresql-database
✅ Raw workflow saved as: 2859-chat-with-postgresql-database_raw.json
✅ Metadata saved as: 2859-chat-with-postgresql-database_metadata.json

Validating workflow...
✅ Loaded metadata from: 2859-chat-with-postgresql-database_metadata.json
✅ Basic JSON structure is valid.

🧠 Calling LLM for workflow analysis...

📝 LLM Analysis Report:
================================================================================
[Detailed analysis from LLM]
================================================================================

✅ Cleaned workflow saved as: 2859-chat-with-postgresql-database_raw_cleaned.json
```

## Customization

You can customize the validator by:

1. Modifying the `OPENROUTER_MODEL` variable to use a different LLM model
2. Adjusting the LLM prompts for different analysis focuses
3. Adding additional validation checks for specific n8n node types
4. Implementing more automatic fixes for common issues

## Batch Processing

You can easily extend this solution to batch process multiple workflows:

```python
# Example batch processing script
import os
import subprocess

# List of workflow IDs to process
workflow_ids = [
    "2529-automatic-background-removal-for-images-in-google-drive",
    "2859-chat-with-postgresql-database",
    "1980-use-an-open-source-llm-via-huggingface"
]

# Process each workflow
for workflow_id in workflow_ids:
    print(f"Processing workflow: {workflow_id}")
    subprocess.run(["python", "n8n_validator.py", "--fetch", workflow_id, "--api"])
    print("-" * 80)
```

## License

MIT
