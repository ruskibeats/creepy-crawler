#!/usr/bin/env python3
"""
Batch Workflow Processor

This script processes a batch of n8n workflow URLs with adaptive resource management.
"""

import asyncio
import argparse
import logging
import os
import sys
import time
from datetime import datetime
import json
import traceback

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.smart_queue import SmartQueue
from src.utils.adaptive_processor import AdaptiveProcessor
from src.utils.system_monitor import SystemMonitor
from src.processors.n8n_workflow_processor import process_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/batch_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger("batch_processor")

async def process_workflow_url(url):
    """
    Process a single workflow URL.
    
    Args:
        url: URL to process
        
    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"Processing workflow URL: {url}")
        
        # Extract workflow ID from URL
        workflow_id = url.split('/')[-1]
        if not workflow_id:
            workflow_id = url.split('/')[-2]
        
        # Process workflow
        result = await process_workflow(workflow_id)
        
        return {
            "url": url,
            "workflow_id": workflow_id,
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error processing workflow URL {url}: {e}")
        logger.debug(traceback.format_exc())
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

async def setup_api_endpoint(processor, queue, monitor, host="0.0.0.0", port=8080):
    """
    Set up a simple API endpoint for monitoring and control.
    
    Args:
        processor: AdaptiveProcessor instance
        queue: SmartQueue instance
        monitor: SystemMonitor instance
        host: Host to bind to
        port: Port to bind to
    """
    from aiohttp import web
    
    app = web.Application()
    
    async def get_status(request):
        """Get status of batch processing."""
        processor_stats = await processor.get_stats()
        queue_stats = await queue.get_stats()
        system_stats = await monitor.get_stats()
        
        return web.json_response({
            "timestamp": datetime.now().isoformat(),
            "processor": processor_stats,
            "queue": queue_stats,
            "system": system_stats
        })
    
    async def pause_processing(request):
        """Pause processing."""
        processor.pause()
        return web.json_response({"status": "paused"})
    
    async def resume_processing(request):
        """Resume processing."""
        processor.resume()
        return web.json_response({"status": "resumed"})
    
    async def add_urls(request):
        """Add URLs to the queue."""
        data = await request.json()
        urls = data.get("urls", [])
        
        if not urls:
            return web.json_response({"error": "No URLs provided"}, status=400)
        
        added = await queue.add_jobs(urls)
        return web.json_response({"added": added})
    
    # Set up routes
    app.router.add_get("/status", get_status)
    app.router.add_post("/pause", pause_processing)
    app.router.add_post("/resume", resume_processing)
    app.router.add_post("/add-urls", add_urls)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"API endpoint available at http://{host}:{port}")
    
    return runner

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Batch Workflow Processor")
    parser.add_argument("--urls-file", help="File containing URLs to process")
    parser.add_argument("--initial-concurrency", type=int, default=2,
                       help="Initial number of concurrent workers")
    parser.add_argument("--max-concurrency", type=int, default=5,
                       help="Maximum number of concurrent workers")
    parser.add_argument("--api-port", type=int, default=8080,
                       help="Port for API endpoint")
    parser.add_argument("--api-host", default="0.0.0.0",
                       help="Host for API endpoint")
    parser.add_argument("--enable-api", action="store_true",
                       help="Enable API endpoint")
    args = parser.parse_args()
    
    # Ensure required directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("db", exist_ok=True)
    
    # Initialize queue
    queue = SmartQueue()
    
    # Load URLs if provided
    if args.urls_file:
        try:
            with open(args.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            logger.info(f"Loaded {len(urls)} URLs from {args.urls_file}")
            
            # Add URLs to queue
            added = await queue.add_jobs(urls)
            logger.info(f"Added {added} new URLs to queue")
        except Exception as e:
            logger.error(f"Error loading URLs from {args.urls_file}: {e}")
            return
    
    # Initialize processor with conservative settings
    processor = AdaptiveProcessor(
        initial_concurrency=args.initial_concurrency,
        max_concurrency=args.max_concurrency
    )
    
    # Initialize system monitor
    monitor = SystemMonitor(processor, queue)
    
    # Start API endpoint if enabled
    api_runner = None
    if args.enable_api:
        try:
            api_runner = await setup_api_endpoint(
                processor, queue, monitor,
                host=args.api_host, port=args.api_port
            )
        except Exception as e:
            logger.error(f"Error setting up API endpoint: {e}")
    
    # Start monitoring
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    try:
        # Start processing
        logger.info("Starting batch processing")
        await processor.process_queue(queue, process_workflow_url)
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        logger.debug(traceback.format_exc())
    finally:
        # Stop monitoring
        monitor_task.cancel()
        
        # Stop processor
        processor.stop()
        
        # Clean up API endpoint
        if api_runner:
            await api_runner.cleanup()
        
        logger.info("Batch processing completed")

if __name__ == "__main__":
    asyncio.run(main())
