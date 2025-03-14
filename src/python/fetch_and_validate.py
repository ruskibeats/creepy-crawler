import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import subprocess
from urllib.parse import unquote

def fetch_workflow(workflow_id):
    """Fetch workflow from n8n website"""
    url = f"https://n8n.io/workflows/{workflow_id}"
    print(f"Fetching workflow from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        demo_element = soup.select_one('#__layout > div > section > div.grid-container_WGQB2 > div.template-column_G3Q-B > div.workflow-preview_6f4BW > div > n8n-demo')
        
        if not demo_element:
            print("❌ ERROR: Could not find n8n-demo element")
            return None
            
        # Extract and decode workflow JSON from attributes
        encoded_workflow = demo_element.attrs.get('workflow', '{}')
        workflow_json = unquote(encoded_workflow)
        
        # Save the raw workflow JSON
        raw_file = f"{workflow_id}_raw.json"
        with open(raw_file, "w", encoding="utf-8") as file:
            file.write(workflow_json)
        print(f"✅ Raw workflow saved as: {raw_file}")
        
        return raw_file
        
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch workflow - {e}")
        return None

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python fetch_and_validate.py <workflow_id>")
        return
        
    workflow_id = sys.argv[1]
    
    # Fetch workflow
    raw_file = fetch_workflow(workflow_id)
    if not raw_file:
        return
    
    # Validate workflow
    print("\nValidating workflow...")
    subprocess.run(["python", "validate_n8n_json_llm.py", raw_file])

if __name__ == "__main__":
    main()
