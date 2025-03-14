#!/usr/bin/env python3
"""
Test script to check node count in workflow JSON
"""

import json
import os

def check_node_count(file_path):
    """Check node count in workflow JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        node_count = len(nodes)
        
        print(f"File: {file_path}")
        print(f"Node count: {node_count}")
        
        if node_count > 0:
            print("\nNode names:")
            for i, node in enumerate(nodes, 1):
                print(f"{i}. {node.get('name', 'Unnamed')} ({node.get('type', 'Unknown')})")
        
        return node_count
    except Exception as e:
        print(f"Error: {e}")
        return 0

if __name__ == "__main__":
    workflow_file = "2859-chat-with-postgresql-database/2859-chat-with-postgresql-database.json"
    
    if os.path.exists(workflow_file):
        check_node_count(workflow_file)
    else:
        print(f"File not found: {workflow_file}")
