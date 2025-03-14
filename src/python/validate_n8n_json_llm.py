import json
import requests
import os
import sys
from dotenv import load_dotenv

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

def validate_n8n_workflow(file_path):
    """Load, validate, fix, and analyze an n8n workflow JSON."""
    try:
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
                    import uuid
                    data[key] = str(uuid.uuid4())
                    print(f"🔧 Added missing 'id' field with UUID: {data[key]}")
                elif key == "name":
                    data[key] = "Unnamed Workflow"
                    print(f"🔧 Added missing 'name' field with default value: {data[key]}")
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
                import uuid
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
        llm_prompt = f"""
        The following is an n8n workflow JSON file. Analyze it for errors, inefficiencies, and improvements:
        
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
    print("=" * 80)
    print("🚀 N8N Workflow Validator with LLM Analysis")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("Enter the path to the n8n workflow JSON file: ")
    
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        return
        
    validate_n8n_workflow(file_path)

# Run the validator
if __name__ == "__main__":
    main()
