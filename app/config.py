import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "db.sqlite3"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "gpt-4o-mini")
VALIDATION_MODEL = os.environ.get("VALIDATION_MODEL", "gpt-4o-mini")

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
