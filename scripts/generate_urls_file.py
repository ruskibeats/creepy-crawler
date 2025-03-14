#!/usr/bin/env python3
"""
Generate URLs File

This script generates a file containing n8n workflow URLs for testing the batch processor.
It fetches URLs from the n8n.io sitemap-workflows.xml file.
"""

import argparse
import json
import os
import random
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

def fetch_urls_from_sitemap(sitemap_url="https://n8n.io/sitemap-workflows.xml", max_urls=None):
    """
    Fetch workflow URLs from the n8n.io sitemap.
    
    Args:
        sitemap_url: URL of the sitemap
        max_urls: Maximum number of URLs to fetch (None for all)
        
    Returns:
        list: List of workflow URLs
    """
    try:
        print(f"Fetching URLs from {sitemap_url}...")
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Extract URLs from <loc> tags
        # The namespace is typically in the format {http://www.sitemaps.org/schemas/sitemap/0.9}
        namespace = root.tag.split('}')[0] + '}'
        urls = []
        
        for url_element in root.findall(f'.//{namespace}url'):
            loc_element = url_element.find(f'{namespace}loc')
            if loc_element is not None and loc_element.text:
                # Ensure it's a workflow URL
                parsed_url = urlparse(loc_element.text)
                if '/workflows/' in parsed_url.path:
                    urls.append(loc_element.text)
                    
                    # Break if we've reached the maximum
                    if max_urls and len(urls) >= max_urls:
                        break
        
        print(f"Found {len(urls)} workflow URLs in sitemap")
        return urls
    
    except Exception as e:
        print(f"Error fetching URLs from sitemap: {e}")
        return []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate URLs File")
    parser.add_argument("--output", default="urls.txt", help="Output file")
    parser.add_argument("--count", type=int, default=10, help="Number of URLs to generate")
    parser.add_argument("--completed-urls", default="api/completed_urls.json", 
                       help="Path to completed URLs file")
    parser.add_argument("--include-completed", action="store_true",
                       help="Include URLs from completed URLs file")
    parser.add_argument("--sitemap", default="https://n8n.io/sitemap-workflows.xml",
                       help="URL of the sitemap to fetch URLs from")
    args = parser.parse_args()
    
    # Fetch URLs from sitemap
    sitemap_urls = fetch_urls_from_sitemap(args.sitemap)
    
    if not sitemap_urls:
        print("No URLs found in sitemap, using fallback URLs")
        # Fallback URLs in case sitemap fetch fails
        sitemap_urls = [
            "https://n8n.io/workflows/1-insert-excel-data-to-postgres/",
            "https://n8n.io/workflows/2-send-slack-notifications-for-new-gitlab-issues/",
            "https://n8n.io/workflows/3-write-http-query-string-on-image/",
            "https://n8n.io/workflows/4-send-selected-github-events-to-slack/",
            "https://n8n.io/workflows/6-sync-data-between-multiple-google-spreadsheets/",
            # Add more fallback URLs as needed
        ]
    
    # Load completed URLs if available
    completed_urls = []
    if os.path.exists(args.completed_urls):
        try:
            with open(args.completed_urls, 'r') as f:
                completed_urls = list(json.load(f).keys())
            print(f"Loaded {len(completed_urls)} completed URLs")
        except Exception as e:
            print(f"Error loading completed URLs: {e}")
    
    # Generate URLs
    urls = []
    
    # Add some completed URLs if requested
    if args.include_completed and completed_urls:
        # Add up to 20% completed URLs
        num_completed = min(int(args.count * 0.2), len(completed_urls))
        urls.extend(random.sample(completed_urls, num_completed))
        print(f"Added {len(urls)} completed URLs")
    
    # Add URLs from sitemap
    remaining_count = args.count - len(urls)
    if remaining_count > 0:
        # If we have more sitemap URLs than needed, sample randomly
        if len(sitemap_urls) > remaining_count:
            sampled_urls = random.sample(sitemap_urls, remaining_count)
        else:
            # Otherwise use all available sitemap URLs
            sampled_urls = sitemap_urls
            
        urls.extend(sampled_urls)
        print(f"Added {len(sampled_urls)} URLs from sitemap")
    
    # Shuffle URLs
    random.shuffle(urls)
    
    # Trim to requested count if we have more
    if len(urls) > args.count:
        urls = urls[:args.count]
    
    # Write URLs to file
    with open(args.output, 'w') as f:
        for url in urls:
            f.write(f"{url}\n")
    
    print(f"Generated {len(urls)} URLs in {args.output}")

if __name__ == "__main__":
    main()
