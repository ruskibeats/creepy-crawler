#!/usr/bin/env python3
"""
N8N Workflow Validator with LLM Analysis

This script combines workflow fetching, validation, and LLM analysis for n8n workflows.
It can fetch workflows from n8n.io, validate their structure, fix common issues,
and provide detailed analysis using OpenRouter's LLM capabilities.
"""

import json
import requests
import os
import sys
import subprocess
import argparse
from bs4 import BeautifulSoup
from urllib.parse import unquote
from dotenv import load_dotenv
import uuid
import traceback

# Load environment variables
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-4-turbo"

def call_openrouter(prompt):
    """Call OpenRouter API for LLM-powered validation & suggestions."""
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file.")
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://crawl4ai.com",  # Replace with your actual domain
        "X-Title": "n8n Workflow Validator"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # Low temperature for more deterministic responses
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
            if "metadata" in workflow_data:
                metadata = workflow_data["metadata"]
            
            # Extract nodes
            if "nodes" in workflow_data:
                metadata["nodes"] = workflow_data["nodes"]
                
            # Extract raw HTML and descriptions
            if "raw_html" in workflow_data:
                metadata["n8n_template_details"] = workflow_data["raw_html"]
                
            if "full_description" in workflow_data:
                metadata["n8n_template_description"] = workflow_data["full_description"]
        
        # Extract raw workflow JSON
        raw_workflow = None
        if "scraped_data" in data and "workflow" in data["scraped_data"]:
            # Try to get the actual workflow JSON
            if "nodes" in data["scraped_data"]["workflow"]:
                # Create a proper workflow JSON structure
                raw_workflow = {
                    "nodes": data["scraped_data"]["workflow"].get("nodes", []),
                    "connections": {},
                    "meta": {
                        "instanceId": str(uuid.uuid4()),
                        "templateCredsSetupCompleted": True
                    },
                    "name": data["scraped_data"]["workflow"].get("metadata", {}).get("title", "Unnamed Workflow"),
                    "id": str(uuid.uuid4()),
                    "active": False,
                    "settings": {
                        "executionOrder": "v1"
                    }
                }
                raw_workflow = json.dumps(raw_workflow, indent=2)
            # Fallback to raw_data if available
            elif "raw_data" in data["scraped_data"]:
                raw_data = data["scraped_data"]["raw_data"]
                if url in raw_data and "n8n_workflow_json" in raw_data[url]:
                    raw_workflow = raw_data[url]["n8n_workflow_json"]
        
        # Save the raw workflow JSON
        raw_file = f"{workflow_id}_raw.json"
        with open(raw_file, "w", encoding="utf-8") as file:
            file.write(raw_workflow if raw_workflow else "{}")
        print(f"✅ Raw workflow saved as: {raw_file}")
        
        # Save the metadata
        metadata_file = f"{workflow_id}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
        print(f"✅ Metadata saved as: {metadata_file}")
        
        return raw_file, metadata_file
        
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch workflow - {e}")
        traceback.print_exc()
        return None, None

def fetch_workflow_from_html(workflow_id):
    """Fetch workflow from n8n.io using BeautifulSoup (fallback method)."""
    url = f"https://n8n.io/workflows/{workflow_id}"
    print(f"Fetching workflow from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        demo_element = soup.select_one('#__layout > div > section > div.grid-container_WGQB2 > div.template-column_G3Q-B > div.workflow-preview_6f4BW > div > n8n-demo')
        
        if not demo_element:
            print("❌ ERROR: Could not find n8n-demo element")
            return None, None
            
        # Extract and decode workflow JSON from attributes
        encoded_workflow = demo_element.attrs.get('workflow', '{}')
        workflow_json = unquote(encoded_workflow)
        
        # Extract metadata
        metadata = {}
        
        # Extract title
        title_element = soup.select_one('h1')
        if title_element:
            metadata["title"] = title_element.text.strip()
        
        # Extract description
        desc_element = soup.select_one('.template-description')
        if desc_element:
            metadata["description"] = desc_element.text.strip()
        
        # Extract version (if available)
        version_element = soup.select_one('.version')
        if version_element:
            metadata["version"] = version_element.text.strip()
        else:
            metadata["version"] = "1.0"
        
        # Save the raw workflow JSON
        raw_file = f"{workflow_id}_raw.json"
        with open(raw_file, "w", encoding="utf-8") as file:
            file.write(workflow_json)
        print(f"✅ Raw workflow saved as: {raw_file}")
        
        # Save the metadata
        metadata_file = f"{workflow_id}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
        print(f"✅ Metadata saved as: {metadata_file}")
        
        return raw_file, metadata_file
        
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch workflow - {e}")
        return None, None

def validate_n8n_workflow(file_path, metadata_path=None):
    """Load, validate, fix, and analyze an n8n workflow JSON."""
    try:
        # Load metadata if available
        metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as file:
                    metadata = json.load(file)
                print(f"✅ Loaded metadata from: {metadata_path}")
            except Exception as e:
                print(f"⚠️ WARNING: Could not load metadata - {e}")
        
        # Load JSON file
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
                
            try:
                data = json.loads(file_content)
            except json.JSONDecodeError as e:
                print(f"❌ ERROR: Invalid JSON format - {e}")
                print("🔧 Attempting to fix JSON with LLM...")
                fixed_content = fix_json_with_llm(file_content)
                try:
                    data = json.loads(fixed_content)
                    print("✅ JSON successfully fixed and parsed!")
                except json.JSONDecodeError as e2:
                    print(f"❌ ERROR: Could not fix JSON - {e2}")
                    return False
        except Exception as e:
            print(f"❌ ERROR: Could not read file - {e}")
            return False

        # Basic structure validation
        required_keys = ["nodes", "connections"]
        recommended_keys = ["id", "name", "settings", "active"]
        
        # Check required keys
        missing_required = [key for key in required_keys if key not in data]
        if missing_required:
            print(f"❌ ERROR: Missing required keys: {', '.join(missing_required)}")
            return False
            
        # Check recommended keys
        missing_recommended = [key for key in recommended_keys if key not in data]
        if missing_recommended:
            print(f"⚠️ WARNING: Missing recommended keys: {', '.join(missing_recommended)}")
            
            # Add missing recommended keys with default values
            for key in missing_recommended:
                if key == "id":
                    data[key] = str(uuid.uuid4())
                    print(f"🔧 Added missing 'id' field with UUID: {data[key]}")
                elif key == "name":
                    if "title" in metadata:
                        data[key] = metadata["title"]
                    else:
                        data[key] = "Unnamed Workflow"
                    print(f"🔧 Added missing 'name' field with value: {data[key]}")
                elif key == "settings":
                    data[key] = {"executionOrder": "v1"}
                    print(f"🔧 Added missing 'settings' field with default values")
                elif key == "active":
                    data[key] = False
                    print(f"🔧 Added missing 'active' field (default: false)")

        # Validate nodes
        if not isinstance(data["nodes"], list):
            print("❌ ERROR: 'nodes' must be a list.")
            return False
            
        if len(data["nodes"]) == 0:
            print("⚠️ WARNING: 'nodes' list is empty.")

        # Validate connections
        if not isinstance(data["connections"], dict):
            print("❌ ERROR: 'connections' must be a dictionary.")
            return False

        print("✅ Basic JSON structure is valid.")

        # Auto-fix common issues in nodes
        for node in data["nodes"]:
            # Ensure node has required fields
            if "id" not in node:
                node["id"] = str(uuid.uuid4())
                print(f"🔧 Added missing 'id' to node: {node.get('name', 'Unnamed')}")
                
            if "name" not in node:
                node["name"] = f"Unnamed Node ({node.get('id', 'unknown')})"
                print(f"🔧 Added missing 'name' to node: {node['id']}")
                
            if "type" not in node:
                node["type"] = "n8n-nodes-base.unknown"
                print(f"⚠️ WARNING: Added placeholder 'type' to node: {node['name']}")
                
            if "parameters" not in node:
                node["parameters"] = {}
                print(f"🔧 Added missing 'parameters' to node: {node['name']}")
                
            if "position" not in node:
                node["position"] = [0, 0]
                print(f"🔧 Added default 'position' to node: {node['name']}")
                
            # Fix misplaced typeVersion inside parameters
            if "parameters" in node and "typeVersion" in node["parameters"]:
                print(f"🔧 Fixing misplaced 'typeVersion' in node: {node['name']}")
                node["typeVersion"] = node["parameters"].pop("typeVersion")
            elif "typeVersion" not in node:
                node["typeVersion"] = 1
                print(f"🔧 Added default 'typeVersion' to node: {node['name']}")

        # Call OpenRouter API for workflow analysis
        print("\n🧠 Calling LLM for workflow analysis...")
        
        # Include metadata in the prompt if available
        metadata_info = ""
        if metadata:
            if "title" in metadata:
                metadata_info += f"Title: {metadata['title']}\n"
            if "description" in metadata:
                metadata_info += f"Description: {metadata['description']}\n"
            if "version" in metadata:
                metadata_info += f"Version: {metadata['version']}\n"
            if "nodes" in metadata and isinstance(metadata["nodes"], list):
                metadata_info += f"Node Count: {len(metadata['nodes'])}\n"
                for i, node in enumerate(metadata["nodes"]):
                    if i < 3:  # Show first 3 nodes
                        metadata_info += f"- Node {i+1}: {node.get('description', 'No description')}\n"
        
        llm_prompt = f"""
        The following is an n8n workflow JSON file. Analyze it for errors, inefficiencies, and improvements:
        
        {metadata_info}
        
        ```json
        {json.dumps(data, indent=2)}
        ```

        Provide a detailed analysis including:
        1. Structural issues or missing required fields
        2. Logical errors or inefficiencies in the workflow
        3. Security concerns or best practices violations
        4. Optimization suggestions
        5. Recommendations for improving reliability

        Format your response as a structured report with clear sections and bullet points.
        """
        
        llm_response = call_openrouter(llm_prompt)
        
        if llm_response:
            print("\n📝 LLM Analysis Report:")
            print("=" * 80)
            print(llm_response)
            print("=" * 80)

        # Save the cleaned JSON file
        cleaned_file = file_path.replace(".json", "_cleaned.json")
        with open(cleaned_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        print(f"\n✅ Cleaned workflow saved as: {cleaned_file}")
        return True

    except Exception as e:
        print(f"❌ ERROR: Unexpected error - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the validator."""
    parser = argparse.ArgumentParser(description="N8N Workflow Validator with LLM Analysis")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fetch", help="Fetch workflow from n8n.io by ID")
    group.add_argument("--validate", help="Validate local workflow JSON file")
    parser.add_argument("--metadata", help="Path to metadata JSON file (optional)")
    parser.add_argument("--api", action="store_true", help="Use test-grid-scrape API for fetching")
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 N8N Workflow Validator with LLM Analysis")
    print("=" * 80)
    
    if args.fetch:
        # Fetch workflow from n8n.io
        if args.api:
            workflow_file, metadata_file = fetch_workflow_from_api(args.fetch)
        else:
            workflow_file, metadata_file = fetch_workflow_from_html(args.fetch)
            
        if not workflow_file:
            print("❌ ERROR: Failed to fetch workflow")
            return
            
        # Validate the fetched workflow
        print("\nValidating workflow...")
        validate_n8n_workflow(workflow_file, metadata_file)
    
    elif args.validate:
        # Validate local workflow file
        if not os.path.exists(args.validate):
            print(f"❌ ERROR: File not found: {args.validate}")
            return
            
        validate_n8n_workflow(args.validate, args.metadata)

# Run the validator
if __name__ == "__main__":
    main()
