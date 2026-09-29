import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DB = DATA_DIR / "sample.db"
UPLOAD_DB = DATA_DIR / "uploaded.db"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5")
MAX_ROWS = 1000
QUERY_TIMEOUT_SEC = 10
