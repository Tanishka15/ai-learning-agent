"""
Logging Setup and Configuration

Provides centralized logging configuration for the AI learning agent system.
"""

import logging
import logging.handlers
import os
from typing import Optional


def setup_logger(name: str, level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting and handling.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Rotating file handler to manage log file size
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=5
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_global_log_level(level: str) -> None:
    """
    Set the logging level for all existing loggers.
    
    Args:
        level: Logging level to set
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Set root logger level
    logging.getLogger().setLevel(numeric_level)
    
    # Set level for all existing loggers
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(numeric_level)
        
        # Update handler levels
        for handler in logger.handlers:
            handler.setLevel(numeric_level)


def configure_logging_from_config(config) -> None:
    """
    Configure logging based on configuration object.
    
    Args:
        config: Configuration object with logging settings
    """
    try:
        # Set up main application logger
        logger = setup_logger(
            name="ai_learning_agent",
            level=config.logging.level,
            log_file=config.logging.file
        )
        
        # Set up component loggers
        component_loggers = [
            "agent",
            "reasoning_engine", 
            "memory_system",
            "web_scraper",
            "api_client",
            "text_processor",
            "knowledge_graph",
            "tutor",
            "curriculum_generator"
        ]
        
        for component in component_loggers:
            setup_logger(
                name=component,
                level=config.logging.level,
                log_file=config.logging.file
            )
        
        logger.info("Logging configuration completed")
        
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.getLogger().error(f"Failed to configure logging from config: {e}")


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.
    
    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                super().__init__()
                self.logger.info("MyClass initialized")
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)


class ContextLogger:
    """
    Context manager for temporary logger configuration.
    
    Usage:
        with ContextLogger("debug_session", "DEBUG"):
            # All logging in this block will use DEBUG level
            logger.debug("This will be shown")
    """
    
    def __init__(self, name: str, level: str, log_file: Optional[str] = None):
        self.name = name
        self.level = level
        self.log_file = log_file
        self.original_level = None
        self.logger = None
    
    def __enter__(self):
        self.logger = setup_logger(self.name, self.level, self.log_file)
        self.original_level = self.logger.level
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_level is not None:
            self.logger.setLevel(self.original_level)


# Pre-configured loggers for common use cases
def get_performance_logger() -> logging.Logger:
    """Get a logger specifically for performance monitoring."""
    return setup_logger("performance", "INFO", "logs/performance.log")


def get_error_logger() -> logging.Logger:
    """Get a logger specifically for error tracking."""
    return setup_logger("errors", "ERROR", "logs/errors.log")


def get_debug_logger() -> logging.Logger:
    """Get a logger for debug information."""
    return setup_logger("debug", "DEBUG", "logs/debug.log")


# Function to log method calls (decorator)
def log_method_calls(logger_name: str = None):
    """
    Decorator to log method entry and exit.
    
    Args:
        logger_name: Optional logger name, defaults to class name
        
    Usage:
        @log_method_calls()
        def my_method(self):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get logger
            if logger_name:
                logger = logging.getLogger(logger_name)
            else:
                logger = logging.getLogger(func.__qualname__)
            
            # Log entry
            logger.debug(f"Entering {func.__name__} with args={args[1:]} kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting {func.__name__} successfully")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator


# Function to log execution time
def log_execution_time(logger_name: str = None):
    """
    Decorator to log method execution time.
    
    Args:
        logger_name: Optional logger name
        
    Usage:
        @log_execution_time()
        def slow_method(self):
            pass
    """
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get logger
            if logger_name:
                logger = logging.getLogger(logger_name)
            else:
                logger = logging.getLogger(func.__qualname__)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func.__name__} failed after {execution_time:.3f} seconds: {e}")
                raise
        
        return wrapper
    return decorator