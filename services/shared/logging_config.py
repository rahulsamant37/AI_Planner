import logging
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger

def setup_structured_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured JSON logging for microservices"""
    
    # Create logs directory
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    log_file = os.path.join(LOGS_DIR, f"{service_name}_{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_service_logger(service_name: str):
    """Get a logger for a specific service"""
    return setup_structured_logging(service_name)
