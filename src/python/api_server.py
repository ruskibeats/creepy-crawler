from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
import uvicorn
import time
import os
from datetime import datetime, timedelta
from crawler_script import AsyncWebCrawler
import asyncio
import json
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
from urllib.parse import unquote, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import sys
import traceback
from contextlib import asynccontextmanager
import uuid

# Setup structured logging
import structlog
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_jobs())
    logger.info("server_startup", task="cleanup_task_created")
    yield
    # Shutdown: Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("server_shutdown", task="cleanup_task_cancelled")

app = FastAPI(
    title="Crawl4AI API",
    description="REST API for the Crawl4AI web crawler",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

from rate_limiter import BatchProcessor, RateLimitConfig

# Initialize rate limiter and batch processor
rate_limit_config = RateLimitConfig(
    requests_per_minute=100,
    batch_size=50,
    max_concurrent_requests=10,
    cooldown_period=1.0
)
batch_processor = BatchProcessor(rate_limit_config)

# Store active crawlers and grid scrape jobs
active_crawlers: Dict[str, AsyncWebCrawler] = {}
grid_scrape_jobs: Dict[str, Dict[str, Any]] = {}
JOB_CLEANUP_THRESHOLD = timedelta(hours=24)  # Clean up jobs older than 24 hours

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        logger.info("health_check_called")
        response = {
            "status": "healthy",
            "time": datetime.now().isoformat(),
            "pid": os.getpid()
        }
        logger.info("health_check_success", response=response)
        return response
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint that returns server status"""
    try:
        logger.info("root_endpoint_called")
        response = {
            "message": "Server is running",
            "status": "healthy",
            "time": datetime.now().isoformat(),
            "active_crawlers": len(active_crawlers),
            "grid_scrape_jobs": len(grid_scrape_jobs)
        }
        logger.info("root_endpoint_success", response=response)
        return response
    except Exception as e:
        logger.error("root_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-minimal")
async def test_minimal():
    """Minimal test endpoint that returns a small JSON object"""
    try:
        logger.info("test_minimal_called")
        response = {
            "status": "success",
            "data": "This is a minimal test response",
            "time": datetime.now().isoformat()
        }
        logger.info("test_minimal_success", response=response)
        return JSONResponse(
            content=response,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.error("test_minimal_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-grid-scrape")
async def test_grid_scrape(url: str):
    """Test endpoint for grid scraping"""
    try:
        logger.info("grid_scrape_called", url=url)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        logger.info("job_id_generated", job_id=job_id)
        
        # Create crawler instance
        crawler = AsyncWebCrawler(job_id)
        logger.info("crawler_created", job_id=job_id)
        
        try:
            # Crawl the URL
            logger.info("starting_crawl", job_id=job_id, url=url)
            await crawler.crawl(url)
            logger.info("crawl_completed", job_id=job_id, url=url)
            
            # Get the scraped data
            data = crawler.page_data
            logger.info("data_retrieved", 
                       job_id=job_id, 
                       url=url, 
                       data_size=len(str(data)),
                       urls_scraped=len(data) if isinstance(data, dict) else 0)
            
            # Parse and structure workflow data
            structured_workflow = {}
            workflow_json = None
            
            if url in data:
                try:
                    # Use the n8n_extract.js script to extract workflow JSON
                    import subprocess
                    import tempfile
                    
                    # Create a temporary file with the HTML content
                    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
                        temp_file_path = temp_file.name
                        # Get the page source from the crawler
                        page_source = crawler.driver.page_source if hasattr(crawler, 'driver') and crawler.driver else ""
                        if not page_source and 'page_source' in data[url]:
                            page_source = data[url]['page_source']
                        
                        # Write the page source to the temp file
                        temp_file.write(page_source.encode('utf-8'))
                    
                    try:
                        # Run the n8n_extract.js script on the temp file
                        result = subprocess.run(
                            ['node', 'n8n_extract.js', temp_file_path],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        
                        # Check if the script was successful
                        if result.returncode == 0 and result.stdout.strip():
                            # Parse the JSON output - skip the first line which is a log message
                            stdout_lines = result.stdout.strip().split('\n')
                            json_output = stdout_lines[-1]  # Get the last line which should be the JSON
                            
                            try:
                                workflow_json = json.loads(json_output)
                            except json.JSONDecodeError:
                                # If the last line isn't valid JSON, try to find a valid JSON object in the output
                                import re
                                json_pattern = r'(\{.*\})'
                                match = re.search(json_pattern, result.stdout, re.DOTALL)
                                if match:
                                    workflow_json = json.loads(match.group(1))
                                else:
                                    workflow_json = None
                            
                            # Create simplified response with just the workflow JSON
                            response = {
                                "workflow": workflow_json
                            }
                            
                            logger.info("extracted_workflow_json_with_js_script", url=url)
                            return JSONResponse(content=response)
                        else:
                            # If script failed, fall back to text parsing
                            if 'n8n_workflow_json' in data[url] and isinstance(data[url]['n8n_workflow_json'], str):
                                workflow_content = data[url]['n8n_workflow_json']
                                
                                # Parse pipe-separated sections into structured data
                                sections = [s.strip() for s in workflow_content.split('|') if s.strip()]
                                structured_workflow = {
                                    "metadata": {
                                        "title": sections[0] if len(sections) > 0 else "",
                                        "description": sections[1] if len(sections) > 1 else "",
                                        "version": "1.1"
                                    },
                                    "nodes": [],
                                    "connections": [],
                                }
                                
                                # Parse node details from subsequent sections
                                for section in sections[2:]:
                                    if ':' in section:
                                        key, value = section.split(':', 1)
                                        structured_workflow["nodes"].append({
                                            "type": key.strip(),
                                            "description": value.strip()
                                        })
                                logger.info("extracted_workflow_text", url=url)
                                
                                # Return simplified response with structured workflow
                                return JSONResponse(content={"workflow": structured_workflow})
                            
                            # Log the error
                            if result.stderr:
                                logger.warning("js_script_error", url=url, error=result.stderr)
                                
                            # Return error response
                            return JSONResponse(
                                content={"error": "Failed to extract workflow JSON"},
                                status_code=500
                            )
                    finally:
                        # Clean up the temp file
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            logger.warning("temp_file_cleanup_failed", url=url, error=str(e))
                except Exception as e:
                    logger.error("workflow_parsing_failed", url=url, error=str(e))
                    return JSONResponse(
                        content={"error": f"Workflow parsing failed: {str(e)}"},
                        status_code=500
                    )
            
            # If we get here, we couldn't extract a workflow
            return JSONResponse(
                content={"error": "No workflow found in the provided URL"},
                status_code=404
            )
            
        except Exception as e:
            logger.error("crawl_execution_failed",
                        job_id=job_id,
                        url=url,
                        error=str(e),
                        error_type=type(e).__name__)
            
            # Store error information
            grid_scrape_jobs[job_id] = {
                "status": "failed",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__,
                "is_running": False
            }
            
            raise
        finally:
            logger.info("closing_crawler", job_id=job_id)
            crawler.close()
            
    except Exception as e:
        logger.error("grid_scrape_failed", 
                    url=url, 
                    error=str(e),
                    error_type=type(e).__name__,
                    stack_trace=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a grid scrape job"""
    try:
        if job_id not in grid_scrape_jobs:
            logger.error("job_not_found", job_id=job_id)
            raise HTTPException(status_code=404, detail="Job not found")
            
        job = grid_scrape_jobs[job_id]
        crawler = active_crawlers.get(job_id)
        
        response = {
            "job_id": job_id,
            "status": job["status"],
            "url": job["url"],
            "timestamp": job["timestamp"],
            "is_running": crawler.is_running if crawler else job.get("is_running", False),
            "scraped_data": {
                "metadata": {
                    "source_url": job["url"],
                    "extracted_at": job.get("timestamp", ""),
                    "schema_version": "1.1"
                },
                "workflow": json.loads(job["workflow_json"]) if job.get("workflow_json") else None,
                "raw_html": job.get("data", {}).get("n8n_template_details", ""),
                "description": job.get("data", {}).get("n8n_template_description", "")
            }
        }
        
        logger.info("job_status_checked", job_id=job_id, status=job["status"])
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("job_status_check_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def list_jobs():
    """List all grid scrape jobs"""
    try:
        jobs_list = []
        for job_id, job in grid_scrape_jobs.items():
            jobs_list.append({
                "job_id": job_id,
                "status": job["status"],
                "url": job["url"],
                "timestamp": job["timestamp"],
                "is_running": job.get("is_running", False)
            })
        
        logger.info("jobs_listed", count=len(jobs_list))
        return {"jobs": jobs_list}
    except Exception as e:
        logger.error("jobs_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Periodic cleanup task
async def cleanup_old_jobs():
    while True:
        try:
            current_time = datetime.now()
            # Clean up old grid scrape jobs
            for job_id, job in list(grid_scrape_jobs.items()):
                job_time = datetime.fromisoformat(job["timestamp"])
                if current_time - job_time > JOB_CLEANUP_THRESHOLD:
                    del grid_scrape_jobs[job_id]
                    logger.info("cleaned_up_job", job_id=job_id)
            
            # Clean up inactive crawlers
            for job_id, crawler in list(active_crawlers.items()):
                if not crawler.is_running and crawler.completion_time:
                    completion_time = datetime.fromisoformat(crawler.completion_time)
                    if current_time - completion_time > JOB_CLEANUP_THRESHOLD:
                        crawler.close()
                        del active_crawlers[job_id]
                        logger.info("cleaned_up_crawler", job_id=job_id)
        except Exception as e:
            logger.error("cleanup_error", error=str(e))
        
        await asyncio.sleep(3600)  # Run every hour

if __name__ == "__main__":
    import argparse
    import socket
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Crawl4AI API Server")
    parser.add_argument("--port", type=int, default=8001, help="Starting port to try (will try 8000-8005 if specified port is in use)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    args = parser.parse_args()
    
    # Use fixed port 8000
    port = 8000
    try:
        print(f"Starting server on {args.host}:{port}")
        uvicorn.run(
            "api_server:app",
            host=args.host,
            port=port,
            reload=False,  # Disable auto-reload
            log_level="info",
            access_log=True,  # Enable access logging
            timeout_keep_alive=30  # Increase keep-alive timeout
        )
    except OSError as e:
        print(f"Error: Port {port} is already in use. Please free up port {port} and try again.")
        sys.exit(1)
