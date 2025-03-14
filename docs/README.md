# Crawl4AI Integration Guide

## Overview

Crawl4AI is a web crawling and scraping API designed to extract structured data from websites, with special support for n8n workflows. This guide provides comprehensive information for AI coding bots to integrate with the Crawl4AI system.

## System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Client App  │────▶│  API Server │────▶│ Web Crawler │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │Rate Limiter │     │ n8n Workflow│
                    └─────────────┘     │  Extraction │
                                        └─────────────┘
```

The system consists of the following components:

- **API Server**: FastAPI-based REST API (api_server.py)
- **Web Crawler**: Selenium-based crawler for extracting data from websites
- **Rate Limiter**: Controls request frequency to prevent overloading (rate_limiter.py)
- **Server Manager**: Monitors and manages the API server (server_manager.py)
- **n8n Integration**: Extracts and validates n8n workflows (n8n_workflow_validator.js)

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/` | GET | Root endpoint with server status |
| `/test-minimal` | GET | Minimal test endpoint |
| `/test-grid-scrape` | GET | Main scraping endpoint |
| `/jobs/{job_id}` | GET | Get status of a specific job |
| `/jobs` | GET | List all grid scrape jobs |
| `/completed-urls` | GET | List all completed URLs |
| `/completed-urls/{url}` | GET | Check if a URL has been completed |
| `/completed-urls/{url}` | DELETE | Remove a URL from completed URLs |

### Main Scraping Endpoint

```
GET /test-grid-scrape?url={url}&force={force}&clean={clean}
```

Parameters:
- `url` (required): The URL to scrape
- `force` (optional): Boolean to force re-scraping even if URL was previously scraped (default: false)
- `clean` (optional): Boolean to clean and structure the HTML data (default: false)

Response:
```json
{
  "job_id": "uuid-string",
  "status": "success",
  "message": "Grid scrape completed",
  "url": "https://example.com",
  "workflow_json": {}, // n8n workflow JSON if available
  "data": {} // Scraped data
}
```

## Authentication

> **Note**: The current implementation does not include authentication. It is recommended to implement API key authentication for production use.

## Rate Limiting

The system includes a rate limiter with the following default configuration:

```python
rate_limit_config = RateLimitConfig(
    requests_per_minute=100,
    batch_size=50,
    max_concurrent_requests=10,
    cooldown_period=1.0
)
```

- **Requests per minute**: Maximum 100 requests per minute
- **Batch size**: Process up to 50 items in a batch
- **Max concurrent requests**: Up to 10 concurrent requests
- **Cooldown period**: 1 second between batches

The rate limiter is implemented in `rate_limiter.py` and used by the API server to prevent overloading.

## n8n Workflow Integration

Crawl4AI has special support for extracting n8n workflows from websites. The system:

1. Extracts workflow JSON from HTML content
2. Validates and ensures the workflow is compliant with n8n requirements
3. Returns the workflow JSON in the API response

### n8n Workflow Validator

The `n8n_workflow_validator.js` script ensures that extracted workflow JSON is compliant with n8n's requirements by:

- Validating the structure
- Adding any missing required fields
- Ensuring each node has required properties

### n8n HTML Cleaner

The `n8n_html_cleaner.js` script cleans up the HTML content returned from the scraping API by:

- Extracting workflow details
- Extracting workflow description
- Extracting workflow demo JSON

## Job Management

The system maintains a record of all scraping jobs with the following information:

- **Job ID**: UUID for the job
- **Status**: success, failed, or running
- **URL**: The URL being scraped
- **Timestamp**: When the job was created
- **Data**: The scraped data
- **Error**: Error information if the job failed

Jobs are automatically cleaned up after 24 hours, except for the most recent successful job for each URL.

## Testing

The system includes a simple HTML interface for testing the API endpoints:

- `test_api.html`: Web interface for testing the API
- `test_urls.txt`: Sample URLs for testing

## Installation and Setup

### Prerequisites

- Python 3.8+
- Chrome/Chromium browser
- Node.js (for n8n integration)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   ./start_server.sh
   ```

### Starting the Server

```bash
./start_server.sh start
```

### Viewing Logs

```bash
./start_server.sh logs
```

## Integration Examples

### Example 1: Basic Scraping Request

```python
import requests

url = "https://example.com"
response = requests.get(f"http://localhost:8000/test-grid-scrape?url={url}")
data = response.json()

print(f"Job ID: {data['job_id']}")
print(f"Status: {data['status']}")
```

### Example 2: Checking Job Status

```python
import requests

job_id = "your-job-id"
response = requests.get(f"http://localhost:8000/jobs/{job_id}")
data = response.json()

print(f"Status: {data['status']}")
print(f"URL: {data['url']}")
```

### Example 3: Extracting n8n Workflow

```python
import requests

url = "https://n8n.io/workflows/2467-narrating-over-a-video-using-multimodal-ai/"
response = requests.get(f"http://localhost:8000/test-grid-scrape?url={url}&clean=true")
data = response.json()

if data.get('workflow_json'):
    print("Workflow extracted successfully")
    print(f"Nodes: {len(data['workflow_json'].get('nodes', []))}")
else:
    print("No workflow found")
```

## Error Handling

The API returns standard HTTP status codes:

- **200**: Success
- **404**: Resource not found
- **500**: Server error

Error responses include detailed information:

```json
{
  "detail": {
    "error": "Error message",
    "type": "ErrorType"
  }
}
```

## Logging

The system uses structured logging with the following configuration:

- JSON format
- ISO timestamp
- Log level, logger name, and other metadata
- Redaction of sensitive information

## Best Practices

1. **Check for cached results**: Use the `/completed-urls/{url}` endpoint to check if a URL has already been scraped.
2. **Handle rate limits**: Implement backoff and retry logic for rate limit errors.
3. **Monitor job status**: For long-running jobs, poll the `/jobs/{job_id}` endpoint to check status.
4. **Process workflow JSON**: Use the n8n workflow validator to ensure workflow JSON is compliant.
5. **Implement authentication**: Add API key authentication for production use.

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure the server is running on port 8000.
2. **Timeout errors**: Large pages may take longer to scrape, increase your client timeout.
3. **Missing workflow JSON**: Not all pages contain n8n workflows, check the response data.

### Debugging

Enable debug logging for more detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
