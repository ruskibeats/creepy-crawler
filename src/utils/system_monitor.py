"""
System Monitor for URL Processing

This module provides a system monitor that tracks system resources
and controls the processor accordingly.
"""

import asyncio
import time
import logging
import psutil
import json
import os
from datetime import datetime

logger = logging.getLogger("system_monitor")

class SystemMonitor:
    """
    A monitor that tracks system resources and controls the processor accordingly.
    """
    
    def __init__(self, 
                processor, 
                queue, 
                check_interval=30,
                cpu_critical=90,
                memory_critical=90,
                disk_critical=95):
        """
        Initialize the SystemMonitor.
        
        Args:
            processor: AdaptiveProcessor instance
            queue: SmartQueue instance
            check_interval: Interval in seconds between resource checks
            cpu_critical: CPU usage percentage above which processing is paused
            memory_critical: Memory usage percentage above which processing is paused
            disk_critical: Disk usage percentage above which processing is paused
        """
        self.processor = processor
        self.queue = queue
        self.check_interval = check_interval
        self.cpu_critical = cpu_critical
        self.memory_critical = memory_critical
        self.disk_critical = disk_critical
        
        self.running = False
        self.resource_history = []
        self.max_history_size = 100  # Keep last 100 resource checks
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
    
    async def start_monitoring(self):
        """Start monitoring system resources."""
        self.running = True
        logger.info("System monitoring started")
        
        try:
            while self.running:
                await self._check_resources()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("System monitoring cancelled")
            self.running = False
        except Exception as e:
            logger.error(f"Error in system monitoring: {e}")
            self.running = False
            raise
    
    async def _check_resources(self):
        """Check system resources and adjust processing."""
        try:
            # Get system resource usage
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Get processor and queue stats
            processor_stats = await self.processor.get_stats() if hasattr(self.processor, 'get_stats') else {}
            queue_stats = await self.queue.get_stats() if hasattr(self.queue, 'get_stats') else {}
            
            # Log resource usage
            logger.info(f"System resources: CPU={cpu}%, Memory={memory}%, Disk={disk}%")
            
            # Record resource usage
            resource_data = {
                "timestamp": datetime.now().isoformat(),
                "cpu": cpu,
                "memory": memory,
                "disk": disk,
                "processor": {
                    "concurrency": self.processor.current_concurrency,
                    "active_tasks": self.processor.active_tasks,
                    "paused": self.processor.paused,
                },
                "queue": queue_stats
            }
            
            # Add to history and trim if needed
            self.resource_history.append(resource_data)
            if len(self.resource_history) > self.max_history_size:
                self.resource_history = self.resource_history[-self.max_history_size:]
            
            # Save resource history periodically
            if len(self.resource_history) % 10 == 0:
                self._save_resource_history()
            
            # Implement throttling logic
            if cpu > self.cpu_critical or memory > self.memory_critical or disk > self.disk_critical:
                if not self.processor.paused:
                    logger.warning(f"System resources critical: CPU={cpu}%, Memory={memory}%, Disk={disk}%")
                    logger.warning("Pausing processing")
                    self.processor.pause()
            elif cpu < self.cpu_critical * 0.8 and memory < self.memory_critical * 0.8 and disk < self.disk_critical * 0.8:
                if self.processor.paused:
                    logger.info("System resources normal, resuming processing")
                    self.processor.resume()
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _save_resource_history(self):
        """Save resource history to file."""
        try:
            history_file = f"logs/resource_history_{datetime.now().strftime('%Y%m%d')}.json"
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.resource_history, f, indent=2)
            
            logger.debug(f"Saved resource history to {history_file}")
        except Exception as e:
            logger.error(f"Error saving resource history: {e}")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("System monitoring stopped")
        
        # Save final resource history
        self._save_resource_history()
    
    async def get_stats(self):
        """
        Get statistics about the system.
        
        Returns:
            dict: System statistics
        """
        return {
            "current": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": psutil.net_io_counters()._asdict(),
            },
            "thresholds": {
                "cpu_critical": self.cpu_critical,
                "memory_critical": self.memory_critical,
                "disk_critical": self.disk_critical,
            },
            "processor_paused": self.processor.paused if hasattr(self.processor, 'paused') else False,
            "history_size": len(self.resource_history),
        }
