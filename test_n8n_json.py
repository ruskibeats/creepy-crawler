#!/usr/bin/env python3
"""
Test script for n8n JSON extraction and cleaning
"""

from src.utils.common import extract_and_clean_n8n_json
import json

# Create a simple test HTML with n8n-demo tag
test_html = '<n8n-demo workflow="{&quot;nodes&quot;:[{&quot;name&quot;:&quot;Test Node&quot;,&quot;type&quot;:&quot;test-node&quot;}],&quot;connections&quot;:{},&quot;id&quot;:&quot;test-id&quot;,&quot;name&quot;:&quot;Test Workflow&quot;,&quot;active&quot;:false,&quot;settings&quot;:{}}"></n8n-demo>'

# Process the HTML
result = extract_and_clean_n8n_json(test_html)

# Print the result
print("\nExtracted workflow data:")
print(json.dumps(result, indent=2))

print("\nTest completed successfully!")
