import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite by default; set DATABASE_URL to use PostgreSQL, e.g.
# postgresql://user:password@localhost:5432/certs
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'certificates.db'}")

# Where generated PDFs are stored
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "generated"))

# Safety limit for one request
MAX_RECIPIENTS_PER_JOB = int(os.getenv("MAX_RECIPIENTS_PER_JOB", "5000"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)