# N8N Workflow Validator with LLM Analysis

This tool validates, fixes, and analyzes n8n workflow JSON files using OpenRouter's LLM capabilities. It helps identify issues, improve workflow quality, and ensure compliance with n8n's schema requirements.

## Features

- ✅ **JSON Validation**: Validates workflow structure against n8n schema requirements
- 🔧 **Automatic Fixes**: Fixes common issues like missing fields and misplaced properties
- 🧠 **LLM Analysis**: Uses OpenRouter's LLM to analyze workflows for improvements
- 🔄 **JSON Repair**: Fixes malformed JSON using LLM capabilities
- 💾 **Cleaned Output**: Saves a cleaned version of the workflow
- 🌐 **Workflow Fetching**: Fetches workflows directly from n8n.io by ID

## Requirements

- Python 3.6+
- Required packages:
  - `requests`
  - `python-dotenv`
  - `openai` (for OpenRouter API)
  - `beautifulsoup4` (for fetching workflows from n8n.io)

## Installation

1. Clone this repository or download the scripts
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

Run the validator script with a workflow JSON file as an argument:

```bash
python validate_n8n_json_llm.py your_workflow.json
```

Or run the script without arguments to be prompted for a file path:

```bash
python validate_n8n_json_llm.py
```

### Fetching and Validating Workflows from n8n.io

Use the fetch_and_validate.py script to fetch a workflow from n8n.io by its ID and validate it:

```bash
python fetch_and_validate.py 2529-automatic-background-removal-for-images-in-google-drive
```

This will:
1. Fetch the workflow JSON from n8n.io
2. Save it as a raw JSON file
3. Run the validator on the raw JSON
4. Provide a detailed analysis of the workflow

You can find workflow IDs in n8n.io URLs, for example:
- https://n8n.io/workflows/2529-automatic-background-removal-for-images-in-google-drive
- The ID is: 2529-automatic-background-removal-for-images-in-google-drive

## What It Validates

The validator checks for:

1. **Required Keys**: Ensures the workflow has all required top-level keys
2. **Node Structure**: Validates each node has required fields
3. **Connections**: Checks that connections are properly structured
4. **Type Placement**: Fixes misplaced typeVersion properties
5. **JSON Syntax**: Repairs malformed JSON using LLM

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
❌ ERROR: Invalid JSON format - Expecting '' delimiter: line 3 column 3 (char 27)
🔧 Attempting to fix JSON with LLM...
✅ Successfully fixed JSON with OpenRouter
✅ JSON successfully fixed and parsed!
⚠️ WARNING: Missing recommended keys: settings active
🔧 Added missing 'settings' field with default values
🔧 Added missing 'active' field (default: false)
✅ Basic JSON structure is valid.
🔧 Fixing misplaced 'typeVersion' in node: Webhook
🔧 Added default 'typeVersion' to node: HTTP Request

🧠 Calling LLM for workflow analysis...

📝 LLM Analysis Report:
================================================================================
[Detailed analysis from LLM]
================================================================================

✅ Cleaned workflow saved as: workflow_cleaned.json
```

## Customization

You can customize the validator by:

1. Modifying the `OPENROUTER_MODEL` variable to use a different LLM model
2. Adjusting the LLM prompts for different analysis focuses
3. Adding additional validation checks for specific n8n node types
4. Implementing more automatic fixes for common issues

## Scripts

### validate_n8n_json_llm.py

The main validator script that:
- Validates n8n workflow JSON structure
- Fixes common issues automatically
- Uses OpenRouter's LLM to fix malformed JSON
- Provides detailed analysis of workflows
- Saves cleaned versions of workflows

### fetch_and_validate.py

A helper script that:
- Fetches workflow JSON from n8n.io using a workflow ID
- Extracts the workflow JSON from the n8n-demo element
- Saves the raw JSON to a file
- Runs the validator on the raw JSON
- Provides a detailed analysis of the workflow

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
    subprocess.run(["python", "fetch_and_validate.py", workflow_id])
    print("-" * 80)
```

## License

MIT
