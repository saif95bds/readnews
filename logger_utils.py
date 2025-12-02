"""
Logger utility module for news fetcher application.
Handles all logging configuration and error handling.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class NewsLogger:
    """Centralized logging class for the news fetcher application."""
    
    def __init__(self, log_file: str = "news_fetcher.log", 
                 level: str = "INFO",
                 max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 5):
        """
        Initialize the logger.
        
        Args:
            log_file: Path to the log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
        """
        self.log_file = log_file
        self.logger = logging.getLogger("NewsFetcher")
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info)


class FeedError(Exception):
    """Base exception for feed-related errors."""
    pass


class NetworkError(FeedError):
    """Exception raised for network-related errors."""
    pass


class ParseError(FeedError):
    """Exception raised for parsing errors."""
    pass


class ConfigError(FeedError):
    """Exception raised for configuration errors."""
    pass
