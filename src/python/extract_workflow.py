import json
import sys

def extract_workflow_json():
    # Read the response from stdin or a file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            response_text = f.read()
    else:
        response_text = sys.stdin.read()
    
    print("Response text:", response_text[:100] + "...")
    
    # Parse the JSON response
    response = json.loads(response_text)
    
    print("Response keys:", list(response.keys()))
    
    # Extract the workflow JSON
    url = response.get('url', '')
    
    # Check if workflow_json is directly in the response
    if 'workflow_json' in response:
        workflow_json = response['workflow_json']
        print(json.dumps(json.loads(workflow_json), indent=2))
        return
    
    # Check if it's in the data
    if 'data' in response and url in response['data']:
        data = response['data'][url]
        print("Data keys:", list(data.keys()))
        if 'n8n_workflow_json' in data:
            workflow_json = data['n8n_workflow_json']
            # If it's already a string, parse it to JSON
            if isinstance(workflow_json, str):
                try:
                    workflow_json_obj = json.loads(workflow_json)
                    print(json.dumps(workflow_json_obj, indent=2))
                    return
                except json.JSONDecodeError:
                    print("Error: workflow_json is not valid JSON")
                    print(workflow_json)
                    return
            # If it's already a JSON object, print it
            else:
                print(json.dumps(workflow_json, indent=2))
                return
    
    print("Error: Could not find workflow_json in the response")
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    extract_workflow_json()
