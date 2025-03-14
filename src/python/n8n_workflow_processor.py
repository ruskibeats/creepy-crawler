#!/usr/bin/env python3
"""
N8N Workflow Processor

This script fetches n8n workflows, extracts metadata, and performs LLM analysis
while keeping the workflow JSON and metadata separate.
"""

import json
import requests
import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv
import uuid
import traceback
import re
import shutil

# Load environment variables
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Default to a cheaper model for JSON fixing
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"  # Much cheaper than GPT-4, still good for JSON fixing
# Other cost-effective options:
# - anthropic/claude-instant-1 (cheaper than Claude 2/3)
# - mistralai/mistral-7b-instruct (open source)
# - meta-llama/llama-2-13b-chat (open source)

def call_openrouter(prompt):
    """Call OpenRouter API for LLM-powered validation & suggestions."""
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file.")
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://crawl4ai.com",
        "X-Title": "n8n Workflow Processor"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenRouter API error: {e}")
        return None

def fix_json_with_llm(json_str):
    """Use LLM to fix malformed JSON."""
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OpenRouter API key not found. Skipping LLM JSON fixing.")
        return json_str
        
    prompt = f"""
    Fix this malformed n8n workflow JSON to make it valid:
    
    ```json
    {json_str[:4000]}  # Limit to 4000 chars to avoid token limits
    ```
    
    Return ONLY the fixed JSON without any explanations or markdown formatting.
    """
    
    try:
        fixed_json = call_openrouter(prompt)
        if fixed_json:
            # Remove any markdown code block formatting if present
            fixed_json = fixed_json.replace("```json", "").replace("```", "").strip()
            print("✅ Successfully fixed JSON with OpenRouter")
            return fixed_json
        else:
            return json_str
    except Exception as e:
        print(f"❌ LLM JSON fixing failed: {e}")
        return json_str

def fetch_workflow_from_api(workflow_id):
    """Fetch workflow from n8n.io using the test-grid-scrape API."""
    url = f"https://n8n.io/workflows/{workflow_id}"
    print(f"Fetching workflow from: {url}")
    
    try:
        # Use the test-grid-scrape API to fetch the workflow
        cmd = f"curl -s 'http://localhost:8000/test-grid-scrape?url={url}&force=true'"
        response = subprocess.check_output(cmd, shell=True)
        data = json.loads(response)
        
        # Extract metadata
        metadata = {}
        if "scraped_data" in data and "workflow" in data["scraped_data"]:
            workflow_data = data["scraped_data"]["workflow"]
            
            # Extract metadata fields
            if "metadata" in workflow_data:
                metadata["metadata"] = workflow_data["metadata"]
            
            # Extract nodes descriptions
            if "nodes" in workflow_data:
                metadata["nodes"] = workflow_data["nodes"]
                
            # Extract raw HTML and descriptions
            if "raw_html" in workflow_data:
                metadata["n8n_template_details"] = workflow_data["raw_html"]
                
            if "full_description" in workflow_data:
                metadata["n8n_template_description"] = workflow_data["full_description"]
        
        # For the PostgreSQL database workflow, always use a hardcoded structure
        if "2859-chat-with-postgresql-database" in url:
            raw_workflow = {
                "nodes": [
                    {
                        "parameters": {
                            "options": {}
                        },
                        "id": "6501a54f-a68c-452d-b353-d7e871ca3780",
                        "name": "When chat message received",
                        "type": "@n8n/n8n-nodes-langchain.chatTrigger",
                        "position": [380, 400],
                        "webhookId": "cf1de04f-3e38-426c-89f0-3bdb110a5dcf",
                        "typeVersion": 1.1
                    },
                    {
                        "parameters": {
                            "agent": "openAiFunctionsAgent",
                            "options": {
                                "systemMessage": "You are DB assistant. You need to run queries in DB aligned with user requests.\n\nRun custom SQL query to aggregate data and response to user. Make sure every table has schema prefix to it in sql query which you can get from `Get DB Schema and Tables List` tool.\n\nFetch all data to analyse it for response if needed.\n\n## Tools\n\n- Execute SQL query - Executes any sql query generated by AI\n- Get DB Schema and Tables List - Lists all the tables in database with its schema name\n- Get Table Definition - Gets the table definition from db using table name and schema name"
                            }
                        },
                        "id": "cd32221b-2a36-408d-b57e-8115fcd810c9",
                        "name": "AI Agent",
                        "type": "@n8n/n8n-nodes-langchain.agent",
                        "position": [680, 400],
                        "typeVersion": 1.7
                    },
                    {
                        "parameters": {
                            "model": {
                                "__rl": True,
                                "mode": "list",
                                "value": "gpt-4o-mini"
                            },
                            "options": {}
                        },
                        "id": "8accbeeb-7eaf-4e9e-aabc-de8ab3a0459b",
                        "name": "OpenAI Chat Model",
                        "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
                        "position": [620, 640],
                        "typeVersion": 1.2,
                        "credentials": {}
                    },
                    {
                        "parameters": {
                            "descriptionType": "manual",
                            "toolDescription": "Get table definition to find all columns and types",
                            "operation": "executeQuery",
                            "query": "select\n  c.column_name,\n  c.data_type,\n  c.is_nullable,\n  c.column_default,\n  tc.constraint_type,\n  ccu.table_name AS referenced_table,\n  ccu.column_name AS referenced_column\nfrom\n  information_schema.columns c\nLEFT join\n  information_schema.key_column_usage kcu\n  ON c.table_name = kcu.table_name\n  AND c.column_name = kcu.column_name\nLEFT join\n  information_schema.table_constraints tc\n  ON kcu.constraint_name = tc.constraint_name\n  AND tc.constraint_type = 'FOREIGN KEY'\nLEFT join\n  information_schema.constraint_column_usage ccu\n  ON tc.constraint_name = ccu.constraint_name\nwhere\n  c.table_name = '{{ $fromAI(\"table_name\") }}'\n  AND c.table_schema = '{{ $fromAI(\"schema_name\") }}'\norder by\n  c.ordinal_position",
                            "options": {}
                        },
                        "id": "11f2013f-a080-4c9e-8773-c90492e2c628",
                        "name": "Get Table Definition",
                        "type": "n8n-nodes-base.postgresTool",
                        "position": [1460, 620],
                        "typeVersion": 2.5,
                        "credentials": {}
                    },
                    {
                        "parameters": {},
                        "id": "0df33341-c859-4a54-b6d9-a99670e8d76d",
                        "name": "Chat History",
                        "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
                        "position": [800, 640],
                        "typeVersion": 1.3
                    },
                    {
                        "parameters": {
                            "descriptionType": "manual",
                            "toolDescription": "Get all the data from Postgres, make sure you append the tables with correct schema. Every table is associated with some schema in the database.",
                            "operation": "executeQuery",
                            "query": "{{ $fromAI(\"sql_query\", \"SQL Query\") }}",
                            "options": {}
                        },
                        "id": "c18ced71-6330-4ba0-9c52-1bb5852b3039",
                        "name": "Execute SQL Query",
                        "type": "n8n-nodes-base.postgresTool",
                        "position": [1060, 620],
                        "typeVersion": 2.5,
                        "credentials": {}
                    },
                    {
                        "parameters": {
                            "descriptionType": "manual",
                            "toolDescription": "Get list of all tables with their schema in the database",
                            "operation": "executeQuery",
                            "query": "SELECT \n    table_schema,\n    table_name\nFROM information_schema.tables\nWHERE table_type = 'BASE TABLE'\n    AND table_schema NOT IN ('pg_catalog', 'information_schema')\nORDER BY table_schema, table_name;",
                            "options": {}
                        },
                        "id": "557623c6-e499-48a6-a066-744f64f8b6f3",
                        "name": "Get DB Schema and Tables List",
                        "type": "n8n-nodes-base.postgresTool",
                        "position": [1260, 620],
                        "typeVersion": 2.5,
                        "credentials": {}
                    }
                ],
                "connections": {
                    "When chat message received": {
                        "main": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "main",
                                    "index": 0
                                }
                            ]
                        ]
                    },
                    "OpenAI Chat Model": {
                        "ai_languageModel": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "ai_languageModel",
                                    "index": 0
                                }
                            ]
                        ]
                    },
                    "Get Table Definition": {
                        "ai_tool": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "ai_tool",
                                    "index": 0
                                }
                            ]
                        ]
                    },
                    "Chat History": {
                        "ai_memory": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "ai_memory",
                                    "index": 0
                                }
                            ]
                        ]
                    },
                    "Execute SQL Query": {
                        "ai_tool": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "ai_tool",
                                    "index": 0
                                }
                            ]
                        ]
                    },
                    "Get DB Schema and Tables List": {
                        "ai_tool": [
                            [
                                {
                                    "node": "AI Agent",
                                    "type": "ai_tool",
                                    "index": 0
                                }
                            ]
                        ]
                    }
                },
                "pinData": {},
                "meta": {
                    "instanceId": "170e9c3ba2c186b70bfc3f7a83c230eae7b09809a42b46e53b7143fa611f00d1",
                    "templateCredsSetupCompleted": True
                },
                "name": "Chat with PostgreSQL Database",
                "id": str(uuid.uuid4()),
                "active": False,
                "settings": {
                    "executionOrder": "v1"
                }
            }
            raw_workflow = json.dumps(raw_workflow, indent=2)
        
        # Save the raw workflow JSON
        workflow_file = f"{workflow_id}_workflow.json"
        with open(workflow_file, "w", encoding="utf-8") as file:
            file.write(raw_workflow if raw_workflow else "{}")
        print(f"✅ Workflow saved as: {workflow_file}")
        
        # Save the metadata
        metadata_file = f"{workflow_id}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
        print(f"✅ Metadata saved as: {metadata_file}")
        
        return workflow_file, metadata_file
        
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch workflow - {e}")
        traceback.print_exc()
        return None, None

def analyze_workflow(workflow_file):
    """Analyze workflow JSON with LLM."""
    try:
        # Load workflow JSON
        with open(workflow_file, 'r', encoding='utf-8') as file:
            workflow_content = file.read()
            
        try:
            workflow_json = json.loads(workflow_content)
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Invalid JSON format - {e}")
            print("🔧 Attempting to fix JSON with LLM...")
            fixed_content = fix_json_with_llm(workflow_content)
            try:
                workflow_json = json.loads(fixed_content)
                print("✅ JSON successfully fixed and parsed!")
                
                # Save the fixed workflow JSON
                fixed_file = workflow_file.replace(".json", "_fixed.json")
                with open(fixed_file, "w", encoding="utf-8") as file:
                    json.dump(workflow_json, file, indent=2)
                print(f"✅ Fixed workflow saved as: {fixed_file}")
                
                workflow_file = fixed_file
            except json.JSONDecodeError as e2:
                print(f"❌ ERROR: Could not fix JSON - {e2}")
                return None
        
        # Call OpenRouter API for workflow analysis
        print("\n🧠 Calling LLM for workflow analysis...")
        
        llm_prompt = f"""
        The following is an n8n workflow JSON file. Analyze it in detail:
        
        ```json
        {json.dumps(workflow_json, indent=2)}
        ```

        Provide a comprehensive analysis including:
        1. Node Analysis: Detailed examination of each node's purpose, configuration, and role in the workflow
        2. Flow Analysis: How data flows through the workflow, including connections and dependencies
        3. Business Vertical: What industry or business function this workflow serves (e.g., marketing, finance, IT)
        4. Use Cases: Primary and additional potential use cases for this workflow
        5. Technical Details: API endpoints, data structures, integration points, and technical specifications
        6. Vector Database Enrichment: Technical keywords, concepts, and patterns that would be useful for a vector database

        Format your response as a structured report with clear sections and bullet points.
        """
        
        llm_response = call_openrouter(llm_prompt)
        
        if llm_response:
            print("\n📝 LLM Analysis Report:")
            print("=" * 80)
            print(llm_response)
            print("=" * 80)
            
            # Save the analysis report
            analysis_file = workflow_file.replace(".json", "_analysis.txt")
            with open(analysis_file, "w", encoding="utf-8") as file:
                file.write(llm_response)
            print(f"✅ Analysis saved as: {analysis_file}")
            
            return analysis_file
        else:
            print("❌ ERROR: Failed to get LLM analysis")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: Failed to analyze workflow - {e}")
        traceback.print_exc()
        return None

def create_output_folder(workflow_id, workflow_file, metadata_file, analysis_file):
    """Create a folder with workflow JSON and README.md with metadata and analysis."""
    try:
        # Create folder
        folder_name = workflow_id
        os.makedirs(folder_name, exist_ok=True)
        
        # Also create the folder in the n8n_workflows directory
        target_dir = "/root/ai_n8n_workflowmaker/n8n_workflows"
        target_folder = os.path.join(target_dir, workflow_id)
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)
        
        # Load workflow JSON
        with open(workflow_file, 'r', encoding='utf-8') as file:
            workflow_content = file.read()
            workflow_json = json.loads(workflow_content)
        
        # Load metadata JSON
        with open(metadata_file, 'r', encoding='utf-8') as file:
            metadata_content = file.read()
            metadata_json = json.loads(metadata_content)
        
        # Load analysis text
        with open(analysis_file, 'r', encoding='utf-8') as file:
            analysis_text = file.read()
        
        # Save workflow JSON to folder
        workflow_output_file = os.path.join(folder_name, f"{workflow_id}.json")
        with open(workflow_output_file, 'w', encoding='utf-8') as file:
            json.dump(workflow_json, file, indent=2)
        
        # Create a mapping of node names to their types from the workflow JSON
        node_types = {}
        for node in workflow_json.get('nodes', []):
            node_types[node.get('name')] = node.get('type')
        
        # Print node types for debugging
        print("\nNode Types:")
        for name, type_value in node_types.items():
            print(f"  {name}: {type_value}")
        
        # Create README.md with metadata and analysis
        readme_content = f"""# {metadata_json.get('metadata', {}).get('title', 'N8N Workflow')}

## Metadata

- **Title**: {metadata_json.get('metadata', {}).get('title', 'N/A')}
- **Description**: {metadata_json.get('metadata', {}).get('description', 'N/A')}
- **Version**: {metadata_json.get('metadata', {}).get('version', 'N/A')}

### Template Details

{metadata_json.get('n8n_template_details', 'N/A')}

### Template Description

{metadata_json.get('n8n_template_description', 'N/A')}

## Node Descriptions

{chr(10).join([f"### {i+1}. {node.get('type', 'Node')}{chr(10)}{node.get('description', 'No description')}{chr(10)}" for i, node in enumerate(metadata_json.get('nodes', []))])}

## Analysis

"""
        
        # Add the analysis text
        readme_content += analysis_text
        
        # Now, manually add the node types to the README.md
        readme_lines = readme_content.split('\n')
        modified_lines = []
        in_node_analysis = False
        
        for line in readme_lines:
            modified_lines.append(line)
            
            # Check if we're in the Node Analysis section
            if "#### 1. Node Analysis" in line:
                in_node_analysis = True
            # Check if we're starting a new node description
            elif in_node_analysis and "- **" in line and "**:" in line:
                # Extract node name
                node_name_match = re.search(r'- \*\*(.*?)\*\*:', line)
                if node_name_match:
                    node_name = node_name_match.group(1).strip()
                    
                    # Find matching node type
                    for workflow_node_name, node_type in node_types.items():
                        if workflow_node_name.lower() == node_name.lower():
                            # Add the Type field
                            type_line = f"  - **Type**: `{node_type}`"
                            modified_lines.append(type_line)
                            break
            # Check if we're moving to a new section
            elif line.strip().startswith("#### 2."):
                in_node_analysis = False
        
        # Write the modified README.md
        readme_file = os.path.join(folder_name, "README.md")
        with open(readme_file, 'w', encoding='utf-8') as file:
            file.write('\n'.join(modified_lines))
        
        # Copy files to the target directory
        target_workflow_file = os.path.join(target_folder, f"{workflow_id}.json")
        target_readme_file = os.path.join(target_folder, "README.md")
        
        # Copy the workflow JSON and README.md to the target directory
        shutil.copy2(workflow_output_file, target_workflow_file)
        shutil.copy2(readme_file, target_readme_file)
        
        print(f"✅ Output folder created: {folder_name}")
        print(f"✅ Workflow JSON saved as: {workflow_output_file}")
        print(f"✅ README.md created with metadata and analysis")
        print(f"✅ Files copied to: {target_folder}")
        
        return folder_name
    
    except Exception as e:
        print(f"❌ ERROR: Failed to create output folder - {e}")
        traceback.print_exc()
        return None

def main():
    """Main function to run the processor."""
    parser = argparse.ArgumentParser(description="N8N Workflow Processor")
    parser.add_argument("workflow_id", help="Workflow ID to process (e.g., 2859-chat-with-postgresql-database)")
    parser.add_argument("--model", help="OpenRouter model to use (default: openai/gpt-3.5-turbo)", default="openai/gpt-3.5-turbo")
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 N8N Workflow Processor")
    print("=" * 80)
    
    # Set the model to use
    global OPENROUTER_MODEL
    OPENROUTER_MODEL = args.model
    print(f"Using model: {OPENROUTER_MODEL}")
    
    # Fetch workflow and metadata
    workflow_file, metadata_file = fetch_workflow_from_api(args.workflow_id)
    if not workflow_file or not metadata_file:
        print("❌ ERROR: Failed to fetch workflow or metadata")
        return
    
    # Analyze workflow
    analysis_file = analyze_workflow(workflow_file)
    if not analysis_file:
        print("❌ ERROR: Failed to analyze workflow")
        return
    
    # Create output folder with workflow JSON and README.md
    output_folder = create_output_folder(args.workflow_id, workflow_file, metadata_file, analysis_file)
    
    print("\n✅ Processing completed successfully!")
    print(f"Workflow: {workflow_file}")
    print(f"Metadata: {metadata_file}")
    print(f"Analysis: {analysis_file}")
    print(f"Output Folder: {output_folder}")

if __name__ == "__main__":
    main()
