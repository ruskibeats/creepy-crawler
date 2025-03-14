"""
OpenRouter API Integration Module

This module provides functions for interacting with the OpenRouter API for LLM-powered
validation, suggestions, and JSON fixing.
"""

import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def call_openrouter(prompt, model="openai/gpt-3.5-turbo", temperature=0.1, max_tokens=1000):
    """
    Call OpenRouter API for LLM-powered validation & suggestions.
    
    Args:
        prompt (str): The prompt to send to the LLM
        model (str): The model to use (default: "openai/gpt-3.5-turbo")
        temperature (float): The temperature parameter (default: 0.1)
        max_tokens (int): The maximum number of tokens to generate (default: 1000)
        
    Returns:
        str or None: The LLM response content, or None if the API call failed
    """
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file.")
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://crawl4ai.com",
        "X-Title": "Crawl4AI LLM Integration"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenRouter API error: {e}")
        return None
