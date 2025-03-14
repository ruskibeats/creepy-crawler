import structlog
import logging
import sys
from typing import Any, Dict

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger with the given name"""
    
    # Configure standard logging
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
        stream=sys.stdout
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # Filter by log level
            structlog.stdlib.add_logger_name,  # Add logger name
            structlog.stdlib.add_log_level,    # Add log level
            structlog.processors.TimeStamper(fmt="iso"),  # Add timestamp
            structlog.processors.StackInfoRenderer(),  # Add stack info for errors
            structlog.processors.format_exc_info,  # Format exception info
            structlog.processors.JSONRenderer()  # Output as JSON
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Create and return logger
    logger = structlog.get_logger(name)
    logger = logger.bind()
    
    return logger

def log_dict(data: Dict[str, Any], exclude_keys: list = None) -> Dict[str, Any]:
    """
    Safely convert a dictionary to a loggable format, excluding sensitive keys
    """
    if exclude_keys is None:
        exclude_keys = ['password', 'token', 'secret', 'key']
        
    safe_dict = {}
    for key, value in data.items():
        if key in exclude_keys:
            safe_dict[key] = '***REDACTED***'
        elif isinstance(value, dict):
            safe_dict[key] = log_dict(value, exclude_keys)
        elif isinstance(value, (list, tuple)):
            safe_dict[key] = [
                log_dict(item, exclude_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            safe_dict[key] = value
            
    return safe_dict
