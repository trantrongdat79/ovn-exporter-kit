"""
JSON structured logging setup with rotation.

Configures Python logging with JSON formatting, file rotation,
and customizable log levels.
"""

import os
import logging
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

class MyLogger():
    
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(
        self, 
        name: str, 
        log_file: str, 
        level: str = "INFO", 
        max_bytes: int = 500 * 1024 * 1024, 
        backup_count: int = 1
    ):
        
        """
        Set up logger with JSON formatting and file rotation.
        
        Args:
            name: Logger name (usually component name)
            log_file: Path to log file
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            max_bytes: Maximum file size before rotation (default 500MB)
            backup_count: Number of backup files to keep (default 1)
        """

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Set up rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)
        
        # Store component name on logger for use in formatter
        self.logger.component_name = name

    def add_context(self, **kwargs):
        """
        Add contextual information to logger for structured logging.
        
        Args:
            **kwargs: Context key-value pairs
        """
        # Store context in logger's extra dictionary for use in log calls
        if not hasattr(self.logger, 'default_context'):
            self.logger.default_context = {}
        self.logger.default_context.update(kwargs)

    def log_with_context(self, level: int, message: str, **context):
        """
        Log a message with contextual information.
        
        Args:
            level: Log level (logging.INFO, logging.ERROR, etc.)
            message: Log message
            **context: Additional context key-value pairs
        """
        # Merge default context with provided context
        log_context = {}
        if hasattr(self.logger, 'default_context'):
            log_context.update(self.logger.default_context)
        log_context.update(context)
        
        # Create extra dictionary for log record
        extra = {
            'component': getattr(self.logger, 'component_name', 'unknown'),
            'context': log_context if log_context else None
        }
        
        # Log the message at the specified level
        self.logger.log(level, message, extra=extra)
    

class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "component": getattr(record, 'component', 'unknown'),
            "message": record.getMessage(),
        }
        
        # Add context if available
        if hasattr(record, 'context') and record.context:
            log_data["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)