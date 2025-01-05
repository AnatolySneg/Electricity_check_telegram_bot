from dotenv import load_dotenv
import os

load_dotenv()


# Configs

DEVICE_IP = os.getenv("DEVICE_IP")  # Device IP
CHECK_INTERVAL = 10  # Checking timeout
TOKEN = os.getenv('TOKEN')  # Bot token
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID chanel
MAX_FAIL_COUNT = 3  # Max failed request checks


ROOT_DIR = os.path.dirname(__file__)



