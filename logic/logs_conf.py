"""
Logging Configuration Module

This module sets up and configures logging for the Electricity Check Bot.
It creates a logging directory if it doesn't exist and configures
the logging format and handlers.
"""

import logging
import os
from settings import ROOT_DIR

# Constants
LOGS_DIR = "logs"
ERROR_LOGFILE = "error.log"

def setup_logging():
    """
    Configure and initialize the logging system.
    
    Creates the logs directory if it doesn't exist and sets up logging with
    the following configuration:
    - Log level: INFO
    - Format: timestamp [level] message
    - Output: File handler writing to error.log
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logs_path = os.path.join(ROOT_DIR, LOGS_DIR)
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(logs_path, ERROR_LOGFILE)),
        ]
    )
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()