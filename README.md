# Bulk Certificate Generator

A backend API that accepts one request containing many recipients, generates a PDF certificate for each valid recipient from a single predefined template, and lets the client track progress and download the results.

**Tech stack:** Python, FastAPI, SQLAlchemy, SQLite (PostgreSQL-ready), ReportLab, pytest.

## Setup

Requires Python 3.10 or newer.

```bash
# 1. Create and activate a virtual environment
python -m venv aero

# Windows (PowerShell)
aero\Scripts\Activate.ps1
# macOS / Linux
source aero/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

No database installation is needed. SQLite is used by default and the database file is created automatically on first run.

## Run the application

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs (try every endpoint here): http://127.0.0.1:8000/docs

## Run the tests

```bash
pytest -v
```

Tests use a temporary database and a temporary output folder, so they never touch real data.

## Configuration (optional)

Settings are read from environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file in the project folder | Set to a PostgreSQL URL to use PostgreSQL |
| `OUTPUT_DIR` | `generated/` | Where PDFs are stored |
| `MAX_RECIPIENTS_PER_JOB` | `5000` | Maximum recipients in one request |