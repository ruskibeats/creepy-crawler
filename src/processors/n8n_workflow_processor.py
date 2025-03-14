#!/usr/bin/env python3
"""
N8N Workflow Processor

This script fetches n8n workflows, extracts metadata, and performs LLM analysis
while keeping the workflow JSON and metadata separate.
"""

import json
import os
import sys
import argparse
import uuid
import traceback
import re
import shutil
import asyncio
import string
# Import from shared modules
from src.utils.common import call_openrouter, fix_json_with_llm
from src.utils.config import get_settings

def extract_and_clean_n8n_json(html_string):
    """Extracts, decodes, and cleans n8n JSON from dynamic HTML"""
    try:
        # Use BeautifulSoup to parse the HTML
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("❌ ERROR: BeautifulSoup not installed. Please install it with 'pip install beautifulsoup4'")
            return None
            
        soup = BeautifulSoup(html_string, 'html.parser')

        # Locate the <n8n-demo> tag
        n8n_demo_tag = soup.find('n8n-demo')

        if n8n_demo_tag:
            # Explicitly extract and print raw JSON
            raw_json = n8n_demo_tag['workflow']
            print(f"Raw JSON: {raw_json}")
            
            # Count nodes in raw JSON using regex to get a baseline
            node_matches = re.findall(r'"name"\s*:\s*"[^"]+"\s*,\s*"type"\s*:', raw_json)
            expected_node_count = len(node_matches)
            print(f"⚠️ Expected node count from raw JSON: {expected_node_count}")

            # Directly pass raw JSON to LLM for processing
            fixed_json = fix_json_with_llm(raw_json)
            
            # Print the fixed JSON for debugging
            print(f"Fixed JSON: {fixed_json[:200]}...")
            
            # Convert LLM output to dictionary
            try:
                response_data = json.loads(fixed_json)
            except json.JSONDecodeError as e:
                print(f"❌ ERROR: Failed to parse fixed JSON: {e}")
                # Try one more time with a more aggressive approach
                fixed_json = fix_json_with_llm(raw_json, model="openai/gpt-4-turbo")
                response_data = json.loads(fixed_json)
            
            # Check if the response has a cleaned_workflow field (from the LLM response format)
            if "cleaned_workflow" in response_data:
                print("Found cleaned_workflow field in response")
                workflow_data = response_data["cleaned_workflow"]
            elif "status" in response_data and response_data["status"] == "success":
                print("Found success status in response")
                if "cleaned_workflow" in response_data:
                    workflow_data = response_data["cleaned_workflow"]
                else:
                    print("⚠️ Success status but no cleaned_workflow field")
                    workflow_data = response_data
            else:
                print("Using response data directly")
                workflow_data = response_data
                
            # Print the workflow data structure
            print(f"Workflow data keys: {list(workflow_data.keys())}")
            
            # Ensure we have the basic structure if LLM didn't provide it
            required_keys = ["id", "name", "nodes", "connections", "settings", "active"]
            for key in required_keys:
                if key not in workflow_data:
                    workflow_data[key] = {} if key == "connections" else ([] if key == "nodes" else False)

            # Safely get node count
            nodes = workflow_data.get('nodes', [])
            node_count = len(nodes) if isinstance(nodes, list) else 0
            print(f"✅ Successfully processed workflow with {node_count} nodes")
            
            # Validate node count against expected count
            if node_count < expected_node_count:
                print(f"❌ WARNING: Node count mismatch! Expected {expected_node_count}, got {node_count}")
                print("⚠️ Attempting to recover missing nodes...")
                
                # Try to extract nodes directly from raw JSON as a fallback
                try:
                    # Use regex to extract node objects
                    node_pattern = r'{"id":"[^}]+","name":"[^}]+","type":"[^}]+"[^}]+}'
                    node_matches = re.findall(node_pattern, raw_json)
                    
                    if node_matches and len(node_matches) > node_count:
                        print(f"✅ Found {len(node_matches)} nodes with regex")
                        
                        # Parse each node and add to workflow_data
                        recovered_nodes = []
                        for node_str in node_matches:
                            try:
                                # Fix the node JSON if needed
                                fixed_node_str = node_str.replace('""', '","').replace('}{', '},{')
                                node = json.loads(fixed_node_str)
                                recovered_nodes.append(node)
                            except:
                                pass
                        
                        if recovered_nodes:
                            print(f"✅ Recovered {len(recovered_nodes)} nodes")
                            workflow_data['nodes'] = recovered_nodes
                            node_count = len(recovered_nodes)
                except Exception as e:
                    print(f"❌ Failed to recover nodes: {e}")
            
            # Final validation
            if node_count == 0:
                print("❌ ERROR: No nodes found in the workflow")
                return None
                
            return workflow_data
        else:
            print("❌ ERROR: n8n-demo tag not found")
            return None

    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON format - {e}")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        return None

def fetch_workflow_from_api(workflow_id, output_dir="."):
    """Fetch workflow from n8n.io website directly and save consolidated files."""
    url = f"https://n8n.io/workflows/{workflow_id}"
    print(f"Fetching workflow from: {url}")
    
    try:
        # Try to use urllib if requests is not available
        try:
            # Use requests with custom SSL verification
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch workflow: HTTP {response.status_code}")
                return None
                
            html_response_text = response.text
        except ImportError:
            print("⚠️ Requests module not available, using urllib")
            import urllib.request
            import ssl
            
            # Create a context that doesn't verify SSL certificates
            context = ssl._create_unverified_context()
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=context, timeout=30) as response:
                html_response_text = response.read().decode('utf-8')
        
        # Parse HTML with BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_response_text, 'html.parser')
            
            # Extract and clean n8n JSON using the Python function
            workflow_data = extract_and_clean_n8n_json(html_response_text)
            
            # Prepare result data
            data = {
                'scraped_data': {
                    'workflow': {
                        'metadata': {
                            'title': soup.find('h1', {'class': 'workflow-title'}).text.strip() if soup.find('h1', {'class': 'workflow-title'}) else "Unknown Workflow",
                            'description': soup.find('div', {'class': 'workflow-description'}).text.strip() if soup.find('div', {'class': 'workflow-description'}) else "",
                            'url': url
                        },
                        'nodes': [],
                        'raw_html': str(soup.find('div', {'class': 'workflow-container'})),
                        'full_description': str(soup.find('div', {'class': 'workflow-description'}))
                    }
                }
            }
        except ImportError:
            print("❌ ERROR: BeautifulSoup not installed. Using minimal data structure.")
            # Create a minimal data structure
            workflow_data = None
            data = {
                'scraped_data': {
                    'workflow': {
                        'metadata': {
                            'title': "Unknown Workflow",
                            'description': "No description available (BeautifulSoup not installed)",
                            'url': url
                        },
                        'nodes': [],
                        'raw_html': "",
                        'full_description': ""
                    }
                }
            }
        
        # If we found workflow JSON, add it to the result and save files
        if workflow_data:
            data['scraped_data']['workflow']['json'] = workflow_data
            
            # Create output directory if it doesn't exist
            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"✅ Created or verified output directory: {os.path.abspath(output_dir)}")
            except Exception as e:
                print(f"❌ ERROR: Failed to create output directory: {e}")
                traceback.print_exc()
                return data, url
            
            try:
                # 1. Save the workflow JSON to a separate file
                workflow_json_file = os.path.join(output_dir, f"{workflow_id}.json")
                with open(workflow_json_file, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, indent=2)
                print(f"✅ Workflow JSON saved to: {os.path.abspath(workflow_json_file)}")
                
                # 2. Save the consolidated data (metadata + workflow info) to a JSON file
                consolidated_json_file = os.path.join(output_dir, f"{workflow_id}_consolidated.json")
                with open(consolidated_json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"✅ Consolidated data saved to: {os.path.abspath(consolidated_json_file)}")
                
                # 3. Generate a text file with workflow analysis
                analysis_text = f"""# {data['scraped_data']['workflow']['metadata']['title']}

## Workflow Information
- URL: {url}
- ID: {workflow_id}
- Node Count: {len(workflow_data.get('nodes', []))}

## Description
{data['scraped_data']['workflow']['metadata']['description']}

## Nodes
"""
                # Add node information
                for i, node in enumerate(workflow_data.get('nodes', []), 1):
                    if 'name' in node and 'type' in node:
                        analysis_text += f"{i}. **{node['name']}** ({node['type']})\n"
                        if 'parameters' in node and 'toolDescription' in node['parameters']:
                            analysis_text += f"   - Description: {node['parameters']['toolDescription']}\n"
                
                # Save the analysis text file
                analysis_file = os.path.join(output_dir, f"{workflow_id}_analysis.txt")
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(analysis_text)
                print(f"✅ Analysis saved to: {os.path.abspath(analysis_file)}")
                
                # Create a directory with the workflow ID and copy all files there
                workflow_dir = os.path.join(output_dir, workflow_id)
                os.makedirs(workflow_dir, exist_ok=True)
                print(f"✅ Created workflow directory: {os.path.abspath(workflow_dir)}")
                
                # Copy files to the workflow directory
                import shutil
                shutil.copy2(workflow_json_file, os.path.join(workflow_dir, f"{workflow_id}.json"))
                shutil.copy2(consolidated_json_file, os.path.join(workflow_dir, f"{workflow_id}_consolidated.json"))
                shutil.copy2(analysis_file, os.path.join(workflow_dir, f"{workflow_id}_analysis.txt"))
                print(f"✅ Files copied to workflow directory: {os.path.abspath(workflow_dir)}")
                
                # Create a README.md file in the workflow directory
                readme_file = os.path.join(workflow_dir, "README.md")
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(analysis_text)
                print(f"✅ README.md created in workflow directory: {os.path.abspath(readme_file)}")
                
            except Exception as e:
                print(f"❌ ERROR: Failed to save files: {e}")
                traceback.print_exc()
            
        else:
            print("❌ WARNING: No workflow JSON found using any extraction method")
            # Create a marker file to indicate no JSON was found
            with open(os.path.join(output_dir, f"{workflow_id}_❌_no_json_found"), "w") as marker_file:
                marker_file.write(f"No JSON found for workflow: {url}")
        
        return data, url
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch workflow - {e}")
        traceback.print_exc()
        return None, url

def load_analysis_template(template_path=None):
    """Load the analysis template from file."""
    if template_path is None:
        template_path = os.path.join("cline_docs", "prompt_templates", "combined_analysis.md")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
            print(f"✅ Loaded template from: {template_path}")
            return template_content
    except FileNotFoundError:
        print(f"⚠️ Template file not found: {template_path}")
        print("⚠️ Using fallback template")
        return """
        # Comprehensive Workflow Analysis for "{{workflow_name}}"
        
        Analyze the following n8n workflow JSON in detail:
        
        ```json
        {{workflow_json}}
        ```
        
        Provide a comprehensive analysis including:
        1. Node Analysis: Detailed examination of each node's purpose, configuration, and role in the workflow. Ensure you analyze ALL nodes present in the workflow.
        2. Flow Analysis: How data flows through the workflow, including connections and dependencies between nodes.
        3. Business Vertical: Identify at least 3-5 potential industry verticals where this workflow could be applied, with specific use cases for each.
        4. Use Cases: Primary intended use case, business problems solved, target users, and potential adaptations.
        5. Technical Details: API endpoints, data structures, integration points, technical specifications, and security considerations.
        6. Vector Database Enrichment: Technical keywords, concepts, patterns, and technologies used.
        
        Format your response as a structured report with clear sections and bullet points. Ensure your analysis is comprehensive and covers ALL nodes in the workflow.
        """
    except Exception as e:
        print(f"⚠️ Error loading template: {e}")
        print("⚠️ Using fallback template")
        return """
        # Comprehensive Workflow Analysis for "{{workflow_name}}"
        
        Analyze the following n8n workflow JSON in detail:
        
        ```json
        {{workflow_json}}
        ```
        
        Provide a comprehensive analysis including:
        1. Node Analysis: Detailed examination of each node's purpose, configuration, and role in the workflow. Ensure you analyze ALL nodes present in the workflow.
        2. Flow Analysis: How data flows through the workflow, including connections and dependencies between nodes.
        3. Business Vertical: Identify at least 3-5 potential industry verticals where this workflow could be applied, with specific use cases for each.
        4. Use Cases: Primary intended use case, business problems solved, target users, and potential adaptations.
        5. Technical Details: API endpoints, data structures, integration points, technical specifications, and security considerations.
        6. Vector Database Enrichment: Technical keywords, concepts, patterns, and technologies used.
        
        Format your response as a structured report with clear sections and bullet points. Ensure your analysis is comprehensive and covers ALL nodes in the workflow.
        """

def render_template(template, **kwargs):
    """Simple template rendering function."""
    # Replace {{variable}} with the corresponding value
    rendered = template
    for key, value in kwargs.items():
        placeholder = f"{{{{{key}}}}}"
        if isinstance(value, str):
            rendered = rendered.replace(placeholder, value)
        elif isinstance(value, dict) or isinstance(value, list):
            rendered = rendered.replace(placeholder, json.dumps(value, indent=2))
    
    return rendered

def analyze_workflow(workflow_file, model=get_settings().default_model, template_path=None):
    """Analyze workflow JSON with LLM using a template."""
    try:
        # Load workflow JSON
        with open(workflow_file, 'r', encoding='utf-8') as file:
            workflow_content = file.read()
            
        try:
            workflow_json = json.loads(workflow_content)
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Invalid JSON format - {e}")
            print("🔧 Attempting to fix JSON with LLM...")
            fixed_content = fix_json_with_llm(workflow_content, model)
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
        
        # Load the analysis template
        template_content = load_analysis_template(template_path)
        
        # Call OpenRouter API for workflow analysis
        print("\n🧠 Calling LLM for workflow analysis...")
        
        # Prepare node data for template
        nodes_data = []
        for node in workflow_json.get('nodes', []):
            nodes_data.append({
                'name': node.get('name', 'Unnamed Node'),
                'type': node.get('type', 'Unknown Type')
            })
        
        # Get workflow name
        workflow_name = workflow_json.get('name', 'Unknown Workflow')
        
        # Render the template with workflow data
        llm_prompt = render_template(
            template_content,
            workflow_json=json.dumps(workflow_json, indent=2),
            nodes=nodes_data,
            workflow_name=workflow_name
        )
        
        llm_response = call_openrouter(llm_prompt, model=model)
        
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
        
        # Get workflow name from the workflow JSON
        workflow_name = workflow_json.get('name', 'N8N Workflow')
        
        # Create README.md with metadata and analysis
        readme_content = f"""# {workflow_name}

## Metadata

- **Title**: {workflow_name}
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

async def process_workflow(workflow_id, model=get_settings().default_model, template_path=None):
    """
    Process a workflow by ID.
    
    Args:
        workflow_id: Workflow ID to process
        model: OpenRouter model to use
        
    Returns:
        dict: Processing result
    """
    print("=" * 80)
    print(f"🚀 Processing workflow: {workflow_id}")
    print("=" * 80)
    
    print(f"Using model: {model}")
    
    # Fetch workflow and metadata
    data, url = fetch_workflow_from_api(workflow_id)
    
    if not data:
        print("❌ ERROR: Failed to fetch workflow")
        return {"success": False, "error": "Failed to fetch workflow"}
        
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
    
    # Extract workflow JSON
    raw_workflow = None
    if data and "scraped_data" in data and "workflow" in data["scraped_data"]:
        workflow_data = data["scraped_data"]["workflow"]
        if "json" in workflow_data:
            raw_workflow = json.dumps(workflow_data["json"], indent=2)
    
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
    
    # Analyze workflow
    analysis_file = analyze_workflow(workflow_file, model, template_path)
    if not analysis_file:
        print("❌ ERROR: Failed to analyze workflow")
        return {"success": False, "error": "Failed to analyze workflow"}
    
    # Create output folder with workflow JSON and README.md
    output_folder = create_output_folder(workflow_id, workflow_file, metadata_file, analysis_file)
    
    print("\n✅ Processing completed successfully!")
    print(f"Workflow: {workflow_file}")
    print(f"Metadata: {metadata_file}")
    print(f"Analysis: {analysis_file}")
    print(f"Output Folder: {output_folder}")
    
    return {
        "success": True,
        "workflow_file": workflow_file,
        "metadata_file": metadata_file,
        "analysis_file": analysis_file,
        "output_folder": output_folder
    }

def main():
    """Main function to run the processor."""
    parser = argparse.ArgumentParser(description="N8N Workflow Processor")
    parser.add_argument("workflow_id", help="Workflow ID to process (e.g., 2859-chat-with-postgresql-database)")
    parser.add_argument("--model", help=f"OpenRouter model to use (default: {get_settings().default_model})", 
                        default=get_settings().default_model)
    parser.add_argument("--template", help="Path to analysis template file", 
                        default=None)
    args = parser.parse_args()
    
    # Process workflow
    result = asyncio.run(process_workflow(args.workflow_id, args.model, args.template))
    
    # Check result
    if not result["success"]:
        print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
