"""
Logging utility for title2ris
"""
import logging
from config import LOG_FORMAT, LOG_DATE_FORMAT, LOG_LEVEL, LOG_FILE

def setup_logger(name='title2ris'):
    """Setup and return a configured logger instance"""
    logger = logging.getLogger(name)
    
    # Set the logging level
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create handlers
    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create a global logger instance
logger = setup_logger() 