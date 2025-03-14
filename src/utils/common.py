"""
Common utilities shared across multiple modules.
"""

import json
try:
    import requests
except ImportError:
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import os
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None
import traceback
import html
import re
try:
    from .config import get_settings  # Import settings
except ImportError:
    # Fallback settings
    class Settings:
        def __init__(self):
            self.openrouter_api_key = None
            self.default_model = "openai/gpt-3.5-turbo"
    
    def get_settings():
        return Settings()

# Load environment variables
load_dotenv()

# OpenRouter API Configuration
settings = get_settings()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or settings.openrouter_api_key

def call_openrouter(prompt, model="openai/gpt-3.5-turbo", temperature=0.1, max_tokens=1000):
    """Call OpenRouter API for LLM-powered validation & suggestions."""
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file.")
        return None
    
    # Check if requests is available
    if requests is None:
        print("❌ ERROR: requests module not available. Using fallback response.")
        return f"Analysis for {model} (FALLBACK - requests module not available)"
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://crawl4ai.com",
        "X-Title": "Crawl4AI LLM Integration",
        "X-OpenRouter-Version": "1.3.0"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        if "choices" in response_data:
            content = response_data["choices"][0]["message"]["content"]
        elif "content" in response_data:
            content = response_data["content"]
        else:
            raise ValueError("Unexpected API response format")
        return content
    except Exception as e:
        print(f"❌ OpenRouter API error: {e}")
        return f"Error calling OpenRouter API: {str(e)[:100]}... (FALLBACK RESPONSE)"

def fix_json_with_llm(json_str, model="openai/gpt-3.5-turbo"):
    """Fix malformed JSON using regex patterns for common issues."""
    try:
        # Try to parse as-is first
        try:
            parsed_json = json.loads(json_str)
            # Verify that nodes exist and are not empty
            if "nodes" in parsed_json and len(parsed_json["nodes"]) > 0:
                print(f"✅ JSON is already valid with {len(parsed_json['nodes'])} nodes")
                return json_str  # Already valid JSON with nodes
            else:
                print("⚠️ JSON is valid but missing nodes, attempting to fix")
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON format, attempting to fix")
        
        # Fix missing commas between properties
        fixed = re.sub(r'(["\d])\s*"', r'\1,"', json_str)
        
        # Fix missing commas between array items
        fixed = re.sub(r'}\s*{', r'},{', fixed)
        
        # Fix position arrays without commas
        fixed = re.sub(r'\[(-?\d+)(-?\d+)\]', r'[\1,\2]', fixed)
        
        # Try to parse the fixed JSON
        try:
            parsed_fixed = json.loads(fixed)
            # Verify that nodes exist and are not empty
            if "nodes" in parsed_fixed and len(parsed_fixed["nodes"]) > 0:
                print(f"✅ Successfully fixed JSON with regex - found {len(parsed_fixed['nodes'])} nodes")
                return fixed
            else:
                print("⚠️ Fixed JSON is missing nodes, trying LLM")
        except json.JSONDecodeError:
            print("⚠️ Regex fixing failed, trying LLM")
        
        # If regex fixing failed or nodes are missing, try with LLM
        if OPENROUTER_API_KEY:
            prompt = f"""
You are a JSON repair expert. Fix the following n8n workflow JSON to make it valid:

```json
{json_str}
```

IMPORTANT: 
1. Return ONLY the fixed JSON without any explanations or markdown formatting.
2. Add missing commas between properties and array items.
3. Ensure all strings are properly quoted.
4. DO NOT REMOVE ANY NODES OR PROPERTIES from the original JSON.
5. Ensure the 'nodes' array contains ALL nodes from the original JSON.
6. The output must be valid JSON that can be parsed with json.loads().

Your task is to fix the JSON syntax while preserving ALL content, especially the nodes array.
"""
            try:
                fixed_json = call_openrouter(prompt, model=model)
                if fixed_json:
                    # Remove any markdown code block formatting if present
                    fixed_json = fixed_json.replace("```json", "").replace("```", "").strip()
                    
                    # Verify the fixed JSON
                    try:
                        parsed_llm = json.loads(fixed_json)
                        if "nodes" in parsed_llm and len(parsed_llm["nodes"]) > 0:
                            print(f"✅ Successfully fixed JSON with OpenRouter - found {len(parsed_llm['nodes'])} nodes")
                            return fixed_json
                        else:
                            print("❌ LLM-fixed JSON is missing nodes")
                    except json.JSONDecodeError:
                        print("❌ LLM-fixed JSON is still invalid")
            except Exception as e:
                print(f"❌ LLM JSON fixing failed: {e}")
        
        # If all else fails, try a more aggressive regex approach
        print("⚠️ Attempting aggressive regex fixing")
        
        # Add commas between all property-value pairs
        aggressive_fixed = re.sub(r'(["\d}])\s*"', r'\1,"', json_str)
        
        # Add commas between all array items
        aggressive_fixed = re.sub(r'([\]}])\s*([\[{])', r'\1,\2', aggressive_fixed)
        
        # Fix position arrays
        aggressive_fixed = re.sub(r'\[(-?\d+)(-?\d+)\]', r'[\1,\2]', aggressive_fixed)
        
        # Try to parse the aggressively fixed JSON
        try:
            parsed_aggressive = json.loads(aggressive_fixed)
            if "nodes" in parsed_aggressive and len(parsed_aggressive["nodes"]) > 0:
                print(f"✅ Successfully fixed JSON with aggressive regex - found {len(parsed_aggressive['nodes'])} nodes")
                return aggressive_fixed
        except:
            pass
        
        # If all else fails, return a minimal valid JSON structure
        print("⚠️ Using fallback minimal JSON structure")
        return '{"id":"unknown","name":"Unknown Workflow","nodes":[],"connections":{},"active":false,"settings":{}}'
    except Exception as e:
        print(f"❌ JSON fixing failed: {e}")
        return '{"id":"unknown","name":"Unknown Workflow","nodes":[],"connections":{},"active":false,"settings":{}}'

def extract_and_clean_n8n_json(html_string):
    """Extracts, decodes, and cleans n8n JSON from dynamic HTML"""
    try:
        # Use BeautifulSoup to parse the HTML
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
        # Check if requests is available
        if requests is None:
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
        else:
            # Fetch the webpage using requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # Get the HTML content
            html_response_text = response.text
        
        # Parse HTML with BeautifulSoup
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
