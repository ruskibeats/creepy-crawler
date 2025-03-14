import os
from dotenv import load_dotenv

load_dotenv()

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_WORKERS = int(os.getenv("API_WORKERS", 4))

# Crawler Settings
DEFAULT_MAX_DEPTH = int(os.getenv("CRAWL_DEPTH", 3))
DEFAULT_MAX_PAGES = int(os.getenv("MAX_PAGES", 100))
SAVE_SCREENSHOTS = os.getenv("SAVE_SCREENSHOTS", "true").lower() == "true"
SAVE_HTML = os.getenv("SAVE_HTML", "true").lower() == "true"
SAVE_MARKDOWN = os.getenv("SAVE_MARKDOWN", "true").lower() == "true"
EXTRACT_TEXT = os.getenv("EXTRACT_TEXT", "true").lower() == "true"

# Storage Settings
DB_PATH = os.getenv("DB_PATH", "crawl4ai.db")
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
MODELS_DIR = os.getenv("MODELS_DIR", "models")
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "screenshots")
HTML_CONTENT_DIR = os.getenv("HTML_CONTENT_DIR", "html_content")
MARKDOWN_CONTENT_DIR = os.getenv("MARKDOWN_CONTENT_DIR", "markdown_content")
EXTRACTED_CONTENT_DIR = os.getenv("EXTRACTED_CONTENT_DIR", "extracted_content")

# Logging Settings
LOG_FILE = os.getenv("LOG_FILE", "crawler.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") 