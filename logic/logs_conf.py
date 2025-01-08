import logging
import os
from settings import ROOT_DIR

logs_dir = "logs"
error_logfile = "error.log"

logs_path = os.path.join(ROOT_DIR, logs_dir)
if not os.path.exists(logs_path):
    os.makedirs(logs_path)

logging.basicConfig(
    level=logging.INFO,  # Log level: INFO, DEBUG, WARNING, ERROR, CRITICAL
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_path, error_logfile)),  # Log to file
    ]
)

logger = logging.getLogger(__name__)