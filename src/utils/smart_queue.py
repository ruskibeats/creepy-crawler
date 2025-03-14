"""
Smart Queue for URL Processing

This module provides a queue implementation that tracks completed URLs
and provides efficient access to the next URL to process.
"""

import json
import os
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger("smart_queue")

class SmartQueue:
    """
    A queue implementation that tracks completed URLs and provides
    efficient access to the next URL to process.
    """
    
    def __init__(self, queue_file="db/job_queue.json", completed_file="api/completed_urls.json"):
        """
        Initialize the SmartQueue.
        
        Args:
            queue_file: Path to the file storing the queue
            completed_file: Path to the file storing completed URLs
        """
        self.queue_file = queue_file
        self.completed_file = completed_file
        self.queue = []
        self.completed = {}
        self.in_progress = set()
        self.lock = asyncio.Lock()
        self.failed = {}
        self.max_retries = 3
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
        
        # Load existing data
        self._load_queue()
        self._load_completed()
        
    def _load_queue(self):
        """Load the queue from file."""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    self.queue = json.load(f)
                logger.info(f"Loaded {len(self.queue)} URLs from queue")
            else:
                self.queue = []
                logger.info("No existing queue file, starting with empty queue")
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.queue = []
    
    def _save_queue(self):
        """Save the queue to file."""
        try:
            # Create a temporary file and then rename to avoid corruption
            temp_file = f"{self.queue_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.queue, f, indent=2)
            os.replace(temp_file, self.queue_file)
            logger.debug(f"Saved {len(self.queue)} URLs to queue")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
    
    def _load_completed(self):
        """Load completed URLs from file."""
        try:
            if os.path.exists(self.completed_file):
                with open(self.completed_file, 'r', encoding='utf-8') as f:
                    self.completed = json.load(f)
                logger.info(f"Loaded {len(self.completed)} completed URLs")
            else:
                self.completed = {}
                logger.info("No existing completed file, starting with empty set")
        except Exception as e:
            logger.error(f"Error loading completed URLs: {e}")
            self.completed = {}
    
    def _save_completed(self):
        """Save completed URLs to file."""
        try:
            # Create a temporary file and then rename to avoid corruption
            temp_file = f"{self.completed_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.completed, f, indent=2)
            os.replace(temp_file, self.completed_file)
            logger.debug(f"Saved {len(self.completed)} completed URLs")
        except Exception as e:
            logger.error(f"Error saving completed URLs: {e}")
    
    async def add_jobs(self, urls):
        """
        Add new URLs to the queue.
        
        Args:
            urls: List of URLs to add
        
        Returns:
            int: Number of new URLs added (excluding duplicates)
        """
        async with self.lock:
            # Filter out URLs that are already in the queue or completed
            new_urls = [url for url in urls 
                       if url not in self.queue 
                       and url not in self.completed
                       and url not in self.in_progress]
            
            # Add new URLs to the queue
            self.queue.extend(new_urls)
            self._save_queue()
            
            logger.info(f"Added {len(new_urls)} new URLs to queue")
            return len(new_urls)
    
    async def get_next(self):
        """
        Get the next URL to process.
        
        Returns:
            str: Next URL to process, or None if none available
        """
        async with self.lock:
            # Find a URL that's not completed or in progress
            for i, url in enumerate(self.queue):
                if url not in self.completed and url not in self.in_progress:
                    # Check if this URL has failed too many times
                    if url in self.failed and self.failed[url]["retries"] >= self.max_retries:
                        continue
                    
                    # Mark as in progress and return
                    self.in_progress.add(url)
                    return url
            
            # No URLs available
            return None
    
    async def mark_completed(self, url):
        """
        Mark a URL as completed.
        
        Args:
            url: URL to mark as completed
        """
        async with self.lock:
            # Add to completed set with timestamp
            self.completed[url] = datetime.now().isoformat()
            
            # Remove from in-progress set
            if url in self.in_progress:
                self.in_progress.remove(url)
            
            # Remove from queue
            if url in self.queue:
                self.queue.remove(url)
            
            # Remove from failed dict if present
            if url in self.failed:
                del self.failed[url]
            
            # Save changes
            self._save_completed()
            self._save_queue()
            
            logger.info(f"Marked URL as completed: {url}")
    
    async def mark_failed(self, url, error, retry=True):
        """
        Mark a URL as failed.
        
        Args:
            url: URL to mark as failed
            error: Error message
            retry: Whether to retry the URL
        """
        async with self.lock:
            # Remove from in-progress set
            if url in self.in_progress:
                self.in_progress.remove(url)
            
            # Update failed dict
            if url in self.failed:
                self.failed[url]["retries"] += 1
                self.failed[url]["last_error"] = error
                self.failed[url]["last_attempt"] = datetime.now().isoformat()
            else:
                self.failed[url] = {
                    "retries": 1,
                    "last_error": error,
                    "last_attempt": datetime.now().isoformat()
                }
            
            # If retry is enabled and we haven't exceeded max retries,
            # move the URL to the end of the queue for later retry
            if retry and self.failed[url]["retries"] < self.max_retries:
                if url in self.queue:
                    self.queue.remove(url)
                self.queue.append(url)
                logger.info(f"URL failed, scheduled for retry ({self.failed[url]['retries']}/{self.max_retries}): {url}")
            else:
                # If we've exceeded max retries, log it
                if url in self.queue:
                    self.queue.remove(url)
                logger.warning(f"URL failed permanently after {self.failed[url]['retries']} attempts: {url}")
            
            # Save changes
            self._save_queue()
    
    async def get_stats(self):
        """
        Get statistics about the queue.
        
        Returns:
            dict: Queue statistics
        """
        async with self.lock:
            return {
                "total": len(self.queue) + len(self.completed),
                "queued": len(self.queue),
                "in_progress": len(self.in_progress),
                "completed": len(self.completed),
                "failed": len(self.failed),
                "permanent_failures": sum(1 for url in self.failed 
                                         if self.failed[url]["retries"] >= self.max_retries)
            }
