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


## Usage

### 1. Submit a generation request

`POST /jobs` accepts one request containing the event details and the full list of recipients. It returns immediately with a job ID, and the certificates are generated in the background.

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Python Workshop 2026",
    "issued_by": "Tech Club",
    "issue_date": "7 October 2026",
    "recipients": [
      {"name": "Asha Rao", "email": "asha@example.com"},
      {"name": "Ravi Kumar", "email": "ravi@example.com"},
      {"name": "", "email": "not-an-email"}
    ]
  }'
```

Response (`202 Accepted`):

```json
{
  "job_id": 1,
  "status": "PENDING",
  "total": 3,
  "status_url": "/jobs/1"
}
```

### 2. Check progress

```bash
curl http://127.0.0.1:8000/jobs/1
```

Response:

```json
{
  "id": 1,
  "event_name": "Python Workshop 2026",
  "issued_by": "Tech Club",
  "issue_date": "7 October 2026",
  "status": "COMPLETED_WITH_ERRORS",
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "created_at": "2026-10-08T10:15:00",
  "finished_at": "2026-10-08T10:15:01",
  "certificates": [
    {"id": 1, "recipient_name": "Asha Rao", "recipient_email": "asha@example.com", "status": "SUCCESS", "error_message": null},
    {"id": 2, "recipient_name": "Ravi Kumar", "recipient_email": "ravi@example.com", "status": "SUCCESS", "error_message": null},
    {"id": 3, "recipient_name": "", "recipient_email": "not-an-email", "status": "FAILED", "error_message": "Name is required"}
  ]
}
```

**Job statuses**

| Status | Meaning |
|---|---|
| `PENDING` | Saved, waiting to be processed |
| `PROCESSING` | Certificates are being generated |
| `COMPLETED` | Every certificate succeeded |
| `COMPLETED_WITH_ERRORS` | Some succeeded, some failed |
| `FAILED` | No certificate succeeded |

Each recipient has its own status (`PENDING`, `SUCCESS`, `FAILED`) and, if it failed, an `error_message`.

### 3. Retrieve certificates

Download one certificate (PDF):

```bash
curl -o asha.pdf http://127.0.0.1:8000/jobs/1/certificates/1
```

Download all successful certificates as a ZIP:

```bash
curl -o job_1_certificates.zip http://127.0.0.1:8000/jobs/1/download
```

Failed recipients have no file, so requesting their certificate returns `404`.

### Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| POST | `/jobs` | Submit a bulk request (returns `202`) |
| GET | `/jobs/{job_id}` | Job progress and per-recipient results |
| GET | `/jobs/{job_id}/certificates/{cert_id}` | Download one PDF |
| GET | `/jobs/{job_id}/download` | Download all successful PDFs as a ZIP |
| GET | `/health` | Health check |

### Validation rules

- **Rejected with `422` (nothing saved):** missing `event_name`, `issued_by` or `issue_date`; an empty recipient list; more than 5000 recipients.
- **Accepted, but that recipient is marked `FAILED` with a reason:** blank name, name over 200 characters, invalid email, or a duplicate email in the same job.


