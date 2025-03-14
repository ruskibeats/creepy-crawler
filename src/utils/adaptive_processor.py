"""
Adaptive Processor for URL Processing

This module provides an adaptive processor that dynamically adjusts
concurrency based on system performance.
"""

import asyncio
import time
import logging
import os
import psutil
from datetime import datetime, timedelta
import traceback
import json

logger = logging.getLogger("adaptive_processor")

class AdaptiveProcessor:
    """
    A processor that dynamically adjusts concurrency based on system performance.
    """
    
    def __init__(self, 
                initial_concurrency=2, 
                max_concurrency=10,
                adjustment_interval=60,
                cpu_threshold_high=80,
                cpu_threshold_low=50,
                memory_threshold_high=80,
                memory_threshold_low=60,
                checkpoint_interval=300):
        """
        Initialize the AdaptiveProcessor.
        
        Args:
            initial_concurrency: Initial number of concurrent workers
            max_concurrency: Maximum number of concurrent workers
            adjustment_interval: Interval in seconds between concurrency adjustments
            cpu_threshold_high: CPU usage percentage above which concurrency is reduced
            cpu_threshold_low: CPU usage percentage below which concurrency is increased
            memory_threshold_high: Memory usage percentage above which concurrency is reduced
            memory_threshold_low: Memory usage percentage below which concurrency is increased
            checkpoint_interval: Interval in seconds between checkpoints
        """
        self.current_concurrency = initial_concurrency
        self.max_concurrency = max_concurrency
        self.adjustment_interval = adjustment_interval
        self.cpu_threshold_high = cpu_threshold_high
        self.cpu_threshold_low = cpu_threshold_low
        self.memory_threshold_high = memory_threshold_high
        self.memory_threshold_low = memory_threshold_low
        self.checkpoint_interval = checkpoint_interval
        
        self.semaphore = asyncio.Semaphore(initial_concurrency)
        self.active_tasks = 0
        self.performance_metrics = []
        self.last_adjustment = time.time()
        self.last_checkpoint = time.time()
        self.running = False
        self.paused = False
        
        # Statistics
        self.stats = {
            "started_at": None,
            "urls_processed": 0,
            "urls_succeeded": 0,
            "urls_failed": 0,
            "avg_processing_time": 0,
            "concurrency_adjustments": [],
        }
        
        # Ensure checkpoint directory exists
        os.makedirs("db/checkpoints", exist_ok=True)
    
    async def process_queue(self, queue, url_processor):
        """
        Process URLs from the queue with adaptive concurrency.
        
        Args:
            queue: SmartQueue instance
            url_processor: Async function that processes a URL
        """
        self.running = True
        self.stats["started_at"] = datetime.now().isoformat()
        
        # Create worker tasks
        workers = [self._worker(i, queue, url_processor) for i in range(self.max_concurrency)]
        
        try:
            # Start workers
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            logger.info("Processing cancelled")
            self.running = False
        except Exception as e:
            logger.error(f"Error in process_queue: {e}")
            self.running = False
            raise
    
    async def _worker(self, worker_id, queue, url_processor):
        """
        Worker that pulls tasks when ready.
        
        Args:
            worker_id: Worker ID
            queue: SmartQueue instance
            url_processor: Async function that processes a URL
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            # Check if we should be active based on current concurrency
            if worker_id >= self.current_concurrency:
                await asyncio.sleep(5)
                continue
            
            # Check if processing is paused
            if self.paused:
                await asyncio.sleep(5)
                continue
            
            # Get next URL when ready
            url = await queue.get_next()
            if not url:
                # No URLs available, sleep and try again
                await asyncio.sleep(5)
                continue
            
            # Process URL
            start_time = time.time()
            try:
                async with self.semaphore:
                    self.active_tasks += 1
                    logger.info(f"Processing URL: {url}")
                    
                    # Process the URL
                    result = await url_processor(url)
                    
                    # Mark as completed
                    await queue.mark_completed(url)
                    
                    # Update statistics
                    self.stats["urls_processed"] += 1
                    self.stats["urls_succeeded"] += 1
                    
                    # Record performance metrics
                    processing_time = time.time() - start_time
                    self.performance_metrics.append(processing_time)
                    
                    # Update average processing time
                    if self.stats["avg_processing_time"] == 0:
                        self.stats["avg_processing_time"] = processing_time
                    else:
                        self.stats["avg_processing_time"] = (
                            self.stats["avg_processing_time"] * 0.9 + processing_time * 0.1
                        )
                    
                    logger.info(f"Processed URL in {processing_time:.2f}s: {url}")
            except Exception as e:
                self.stats["urls_failed"] += 1
                error_msg = f"Error processing {url}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                await queue.mark_failed(url, error_msg)
            finally:
                self.active_tasks -= 1
            
            # Adjust concurrency periodically
            current_time = time.time()
            if current_time - self.last_adjustment > self.adjustment_interval:
                await self._adjust_concurrency()
                self.last_adjustment = current_time
            
            # Create checkpoint periodically
            if current_time - self.last_checkpoint > self.checkpoint_interval:
                await self._create_checkpoint(queue)
                self.last_checkpoint = current_time
    
    async def _adjust_concurrency(self):
        """Dynamically adjust concurrency based on performance."""
        if not self.performance_metrics:
            return
        
        # Calculate average processing time
        avg_time = sum(self.performance_metrics) / len(self.performance_metrics)
        self.performance_metrics = []  # Reset for next interval
        
        # Check system load
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        
        logger.info(f"Performance metrics: avg_time={avg_time:.2f}s, CPU={cpu_usage}%, MEM={memory_usage}%")
        
        old_concurrency = self.current_concurrency
        
        # Adjust concurrency based on metrics
        if cpu_usage > self.cpu_threshold_high or memory_usage > self.memory_threshold_high:
            # System under heavy load, reduce concurrency
            self.current_concurrency = max(1, self.current_concurrency - 1)
            if self.current_concurrency != old_concurrency:
                logger.info(f"Reducing concurrency to {self.current_concurrency} due to high system load")
        elif (cpu_usage < self.cpu_threshold_low and 
              memory_usage < self.memory_threshold_low and 
              avg_time < 10.0):  # Only increase if processing time is reasonable
            # System has capacity, increase concurrency
            self.current_concurrency = min(self.max_concurrency, self.current_concurrency + 1)
            if self.current_concurrency != old_concurrency:
                logger.info(f"Increasing concurrency to {self.current_concurrency}")
        
        # Record adjustment if changed
        if self.current_concurrency != old_concurrency:
            self.stats["concurrency_adjustments"].append({
                "timestamp": datetime.now().isoformat(),
                "old_value": old_concurrency,
                "new_value": self.current_concurrency,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "avg_processing_time": avg_time
            })
        
        # Update semaphore if changed
        if self.current_concurrency != old_concurrency:
            self.semaphore = asyncio.Semaphore(self.current_concurrency)
    
    async def _create_checkpoint(self, queue):
        """Create a checkpoint for recovery."""
        try:
            checkpoint_file = f"db/checkpoints/checkpoint_{int(time.time())}.json"
            
            # Get queue stats
            queue_stats = await queue.get_stats()
            
            # Create checkpoint data
            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "processor_stats": self.stats,
                "queue_stats": queue_stats,
                "current_concurrency": self.current_concurrency,
            }
            
            # Save checkpoint
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
            
            logger.info(f"Created checkpoint: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Error creating checkpoint: {e}")
    
    def pause(self):
        """Pause processing."""
        if not self.paused:
            self.paused = True
            logger.info("Processing paused")
    
    def resume(self):
        """Resume processing."""
        if self.paused:
            self.paused = False
            logger.info("Processing resumed")
    
    def stop(self):
        """Stop processing."""
        self.running = False
        logger.info("Processing stopped")
    
    async def get_stats(self):
        """
        Get statistics about the processor.
        
        Returns:
            dict: Processor statistics
        """
        # Calculate ETA
        eta = None
        if (self.stats["urls_processed"] > 0 and 
            self.stats["avg_processing_time"] > 0 and 
            self.active_tasks > 0):
            # Calculate remaining time based on average processing time and current concurrency
            queue_stats = await self.queue.get_stats() if hasattr(self, 'queue') else {"queued": 0}
            remaining_urls = queue_stats.get("queued", 0)
            if remaining_urls > 0:
                # Estimate time to complete remaining URLs
                seconds_per_url = self.stats["avg_processing_time"] / self.current_concurrency
                remaining_seconds = remaining_urls * seconds_per_url
                eta = (datetime.now() + timedelta(seconds=remaining_seconds)).isoformat()
        
        return {
            **self.stats,
            "current_concurrency": self.current_concurrency,
            "max_concurrency": self.max_concurrency,
            "active_tasks": self.active_tasks,
            "paused": self.paused,
            "running": self.running,
            "eta": eta,
            "system": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        }
