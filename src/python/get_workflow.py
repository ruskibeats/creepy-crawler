import requests
import json
import sys

def get_workflow():
    # Default URL
    url = "https://n8n.io/workflows/1-insert-excel-data-to-postgres/"
    
    # Use command line argument if provided
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Make the request
    print(f"Making request to: http://localhost:8003/test-grid-scrape?url={url}")
    response = requests.get(f"http://localhost:8003/test-grid-scrape?url={url}")
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Get the workflow JSON
        workflow_json = data.get('workflow_json')
        
        if workflow_json:
            # If it's a string, parse it to JSON
            if isinstance(workflow_json, str):
                try:
                    workflow_json = json.loads(workflow_json)
                except json.JSONDecodeError:
                    print("Error: workflow_json is not valid JSON")
                    return
            
            # Print the workflow JSON
            print(json.dumps(workflow_json, indent=2))
            
            # Save the workflow JSON to a file
            with open("workflow.json", "w") as f:
                json.dump(workflow_json, f, indent=2)
            print("\nWorkflow JSON saved to workflow.json")
        else:
            print("Error: workflow_json not found in response")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    get_workflow()
