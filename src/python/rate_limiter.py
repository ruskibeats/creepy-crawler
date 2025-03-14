import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import structlog
from logging_config import get_logger

logger = get_logger("rate_limiter")

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 100
    batch_size: int = 50
    max_concurrent_requests: int = 10
    cooldown_period: float = 1.0

class BatchProcessor:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self.last_request_time = 0
        self.request_count = 0
        self.window_start = time.time()
        
    async def process_batch(self, items: List[Any], process_func: Callable) -> str:
        """Process a batch of items with rate limiting
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            
        Returns:
            str: Job ID for tracking progress
        """
        job_id = f"batch_{int(time.time())}"
        
        self.jobs[job_id] = {
            "total": len(items),
            "completed": 0,
            "results": [],
            "errors": [],
            "start_time": time.time(),
            "status": "running"
        }
        
        logger.info("batch_job_started",
                   job_id=job_id,
                   total_items=len(items))
        
        try:
            # Process items in batches
            for i in range(0, len(items), self.config.batch_size):
                batch = items[i:i + self.config.batch_size]
                
                # Create tasks for batch
                tasks = []
                for item in batch:
                    task = asyncio.create_task(self._process_item(
                        job_id=job_id,
                        item=item,
                        process_func=process_func
                    ))
                    tasks.append(task)
                
                # Wait for batch to complete
                await asyncio.gather(*tasks)
                
                # Apply cooldown between batches
                await asyncio.sleep(self.config.cooldown_period)
            
            self.jobs[job_id]["status"] = "completed"
            logger.info("batch_job_completed",
                       job_id=job_id,
                       total_processed=self.jobs[job_id]["completed"],
                       total_errors=len(self.jobs[job_id]["errors"]))
            
        except Exception as e:
            self.jobs[job_id]["status"] = "failed"
            logger.error("batch_job_failed",
                        job_id=job_id,
                        error=str(e))
            raise
            
        return job_id
    
    async def _process_item(self, job_id: str, item: Any, process_func: Callable) -> None:
        """Process a single item with rate limiting"""
        try:
            # Wait for semaphore (concurrency limit)
            async with self.semaphore:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Process item
                result = await process_func(item)
                
                # Update job status
                self.jobs[job_id]["results"].append(result)
                self.jobs[job_id]["completed"] += 1
                
                logger.debug("item_processed",
                           job_id=job_id,
                           completed=self.jobs[job_id]["completed"],
                           total=self.jobs[job_id]["total"])
                
        except Exception as e:
            self.jobs[job_id]["errors"].append({
                "item": item,
                "error": str(e)
            })
            logger.error("item_processing_failed",
                        job_id=job_id,
                        item=item,
                        error=str(e))
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting based on requests per minute"""
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.window_start >= 60:
            self.request_count = 0
            self.window_start = current_time
        
        # Check if we need to wait
        if self.request_count >= self.config.requests_per_minute:
            wait_time = 60 - (current_time - self.window_start)
            if wait_time > 0:
                logger.debug("rate_limit_wait",
                           wait_time=f"{wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.window_start = time.time()
        
        # Update request count
        self.request_count += 1
        self.last_request_time = current_time
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a batch job"""
        if job_id not in self.jobs:
            raise KeyError(f"Job {job_id} not found")
            
        job = self.jobs[job_id]
        return {
            "job_id": job_id,
            "status": job["status"],
            "total": job["total"],
            "completed": job["completed"],
            "errors": len(job["errors"]),
            "duration": time.time() - job["start_time"]
        }
    
    def get_job_results(self,
                       job_id: str,
                       include_failed: bool = True,
                       limit: int = 100,
                       offset: int = 0) -> Dict[str, Any]:
        """Get results of a batch job"""
        if job_id not in self.jobs:
            raise KeyError(f"Job {job_id} not found")
            
        job = self.jobs[job_id]
        results = job["results"][offset:offset + limit]
        
        if include_failed:
            failed = job["errors"][offset:offset + limit]
        else:
            failed = []
            
        return {
            "job_id": job_id,
            "status": job["status"],
            "total": job["total"],
            "completed": job["completed"],
            "results": results,
            "failed": failed,
            "has_more": (offset + limit) < job["total"]
        }
