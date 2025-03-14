#!/usr/bin/env python3
"""
Test script for the template-based workflow analysis.
"""

import os
import sys
import json
import argparse
from src.processors.n8n_workflow_processor import analyze_workflow, load_analysis_template, render_template
from src.utils.config import get_settings

def test_template_rendering():
    """Test the template rendering functionality."""
    print("Testing template rendering...")
    
    # Load the template
    template_path = os.path.join("cline_docs", "prompt_templates", "combined_analysis.md")
    template_content = load_analysis_template(template_path)
    
    # Create sample data
    sample_data = {
        "workflow_json": json.dumps({"name": "Test Workflow", "nodes": [{"name": "Node1", "type": "TestType"}]}),
        "nodes": [{"name": "Node1", "type": "TestType"}]
    }
    
    # Render the template
    rendered = render_template(template_content, **sample_data)
    
    # Verify the rendering
    if "Test Workflow" in rendered and "Node1" in rendered and "TestType" in rendered:
        print("✅ Template rendering successful!")
    else:
        print("❌ Template rendering failed!")
        print("Rendered content:")
        print(rendered)
    
    return rendered

def test_workflow_analysis(workflow_file, model=get_settings().default_model):
    """Test the workflow analysis with a template."""
    print(f"Testing workflow analysis with file: {workflow_file}")
    
    # Analyze the workflow
    template_path = os.path.join("cline_docs", "prompt_templates", "combined_analysis.md")
    analysis_file = analyze_workflow(workflow_file, model, template_path)
    
    if analysis_file and os.path.exists(analysis_file):
        print(f"✅ Analysis successful! Output saved to: {analysis_file}")
        
        # Print the first few lines of the analysis
        with open(analysis_file, 'r', encoding='utf-8') as file:
            content = file.read()
            print("\nAnalysis preview:")
            print("=" * 80)
            print("\n".join(content.split("\n")[:20]))
            print("...")
            print("=" * 80)
    else:
        print("❌ Analysis failed!")
    
    return analysis_file

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the template-based workflow analysis")
    parser.add_argument("--workflow", help="Path to workflow JSON file to analyze", default=None)
    parser.add_argument("--model", help=f"OpenRouter model to use (default: {get_settings().default_model})", 
                        default=get_settings().default_model)
    args = parser.parse_args()
    
    # Test template rendering
    rendered = test_template_rendering()
    
    # Test workflow analysis if a file is provided
    if args.workflow:
        if os.path.exists(args.workflow):
            analysis_file = test_workflow_analysis(args.workflow, args.model)
        else:
            print(f"❌ Workflow file not found: {args.workflow}")
    else:
        print("ℹ️ No workflow file provided. Skipping workflow analysis test.")
        print("To test workflow analysis, run: python test_template.py --workflow path/to/workflow.json")

if __name__ == "__main__":
    main()
