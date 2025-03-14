#!/usr/bin/env python3
import subprocess
import time
import sys
import signal
import psutil
from datetime import datetime
import requests
from typing import Optional, Tuple
from logging_config import get_logger

# Get structured logger
logger = get_logger("server_manager")

class ServerManager:
    def __init__(self, server_script: str, check_endpoint: str = "http://localhost:8000/health"):
        self.server_script = server_script
        self.check_endpoint = check_endpoint
        self.process: Optional[subprocess.Popen] = None
        self.start_time = None
        self.restart_count = 0
        self.max_memory_percent = 90  # Restart if memory usage exceeds 90%
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def start_server(self) -> None:
        """Start the API server as a subprocess"""
        try:
            # Kill any existing process using port 8000
            try:
                subprocess.run(['fuser', '-k', '8000/tcp'], check=False)
            except:
                pass  # Ignore if fuser is not available
                
            # Start the server
            self.process = subprocess.Popen([sys.executable, self.server_script])
            self.start_time = datetime.now()
            self.restart_count += 1
            logger.info("server_started", pid=self.process.pid, script=self.server_script)
            
            # Wait for server to initialize with retries
            logger.info("waiting_for_server_startup")
            max_retries = 5
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    logger.info("startup_check_attempt", attempt=attempt + 1)
                    time.sleep(retry_delay)
                    
                    response = requests.get(self.check_endpoint, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            logger.info("server_startup_successful", 
                                      attempt=attempt + 1,
                                      pid=data.get("pid"))
                            return
                        else:
                            logger.warning("server_startup_check_failed", 
                                         attempt=attempt + 1,
                                         status=data.get("status"))
                    else:
                        logger.warning("server_startup_check_failed", 
                                     attempt=attempt + 1,
                                     status_code=response.status_code)
                except Exception as e:
                    logger.warning("server_startup_check_error",
                                 attempt=attempt + 1,
                                 error=str(e))
            
            # If we get here, all retries failed
            logger.error("server_startup_failed_all_retries",
                        max_retries=max_retries,
                        check_endpoint=self.check_endpoint)
            raise RuntimeError("Server failed to start after multiple retries")
        except Exception as e:
            logger.error("server_start_failed", error=str(e))
            raise

    def check_server_health(self) -> bool:
        """Check if the server is responding to health checks"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info("checking_server_health",
                          attempt=attempt + 1,
                          endpoint=self.check_endpoint)
                
                response = requests.get(self.check_endpoint, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    is_healthy = data.get("status") == "healthy"
                    
                    if is_healthy:
                        logger.info("server_health_check_passed",
                                  attempt=attempt + 1,
                                  pid=data.get("pid"))
                        return True
                    else:
                        logger.warning("server_health_check_failed",
                                     attempt=attempt + 1,
                                     status=data.get("status"))
                else:
                    logger.warning("server_health_check_failed",
                                 attempt=attempt + 1,
                                 status_code=response.status_code)
                    
            except requests.RequestException as e:
                logger.warning("server_health_check_error",
                             attempt=attempt + 1,
                             error=str(e))
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        logger.error("server_health_check_failed_all_retries",
                    max_retries=max_retries)
        return False

    def check_resource_usage(self) -> Tuple[float, bool]:
        """Check if server resource usage is within acceptable limits
        
        Returns:
            Tuple[float, bool]: (memory_percent, is_within_limits)
        """
        if not self.process:
            return 0.0, False
            
        try:
            process = psutil.Process(self.process.pid)
            memory_percent = process.memory_percent()
            
            # Log resource usage
            logger.info("resource_usage", memory_percent=f"{memory_percent:.1f}%", pid=self.process.pid)
            
            # Return memory percent and whether it's within limits
            return memory_percent, memory_percent < self.max_memory_percent
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0, False

    def restart_server(self) -> None:
        """Restart the server process"""
        logger.info("server_restarting")
        self.stop_server()
        time.sleep(5)  # Wait for cleanup
        self.start_server()

    def stop_server(self) -> None:
        """Stop the server process"""
        if self.process:
            try:
                process = psutil.Process(self.process.pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
                process.wait(timeout=10)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                logger.warning("force_killing_server", pid=self.process.pid)
                if self.process.poll() is None:
                    self.process.kill()
            self.process = None

    def handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully"""
        logger.info("shutdown_signal_received")
        self.stop_server()
        sys.exit(0)

    def run(self) -> None:
        """Main run loop"""
        logger.info("manager_starting")
        self.start_server()

        while True:
            try:
                # Wait between health checks
                time.sleep(30)  # Increased from 10 to 30 seconds

                # Check server health
                if not self.check_server_health():
                    logger.error("health_check_failed")
                    self.restart_server()
                    continue

                # Check resource usage
                memory_percent, is_ok = self.check_resource_usage()
                if not is_ok:
                    logger.warning("resource_usage_exceeded", memory_percent=f"{memory_percent:.1f}%")
                    self.restart_server()
                    continue

                # Log uptime and restart count every hour
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    if uptime.total_seconds() % 3600 < 60:  # Log near the hour mark
                        logger.info("server_status", uptime=str(uptime), restart_count=self.restart_count)

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error("manager_loop_error", error=str(e))
                time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server_manager.py <path_to_server_script>")
        sys.exit(1)

    manager = ServerManager(sys.argv[1])
    manager.run()
