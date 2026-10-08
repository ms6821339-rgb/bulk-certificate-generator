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

> On Windows PowerShell, use `curl.exe` instead of `curl` and put each command on one line, or simply use the interactive docs at `/docs`.

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

Failed recipients have no file, so requesting their certificate returns `404`. Download only after the job reaches a final status (`COMPLETED`, `COMPLETED_WITH_ERRORS` or `FAILED`), because the ZIP contains whatever has succeeded so far.

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

## Design decisions

### Why FastAPI
FastAPI validates requests automatically using Pydantic, generates interactive API docs at `/docs`, and keeps endpoint code short. This made the request validation and the API contract explicit and easy to test.

### Why background processing
A single request can contain thousands of recipients. Generating thousands of PDFs inside one HTTP request would keep the client waiting, risk timeouts, and tie up the server.

So `POST /jobs` only validates the request, saves the job and its recipients, and returns `202 Accepted` with a job ID. The certificates are generated afterwards by a background task (FastAPI `BackgroundTasks`). The client polls `GET /jobs/{id}` to follow progress.

**Trade-off:** `BackgroundTasks` needs no extra infrastructure, which keeps the project easy to run. But the work runs inside the web server process, so a job that is mid-run when the server restarts is not resumed. See "Limitations" below for the production alternative.

### Two layers of validation
1. **Request-level (Pydantic schema):** problems with the request as a whole, such as a missing `event_name`, an empty recipient list, or more than the allowed number of recipients, are rejected with `422` and nothing is saved.
2. **Recipient-level (processor):** problems with a single recipient, such as a blank name, an invalid email, or a duplicate email, do **not** reject the request. The job is accepted, and that recipient is marked `FAILED` with a clear reason.

The recipient schema is deliberately permissive. If it were strict, one bad row in a list of thousands would reject the entire request, which goes against the requirement that one invalid recipient must not block the others.

### Failure isolation
The processor handles recipients one at a time:
- Invalid recipients are recorded as `FAILED` with a reason, and the loop continues.
- Certificate generation for each recipient is wrapped in its own `try/except`, so a rendering error on one certificate is recorded on that recipient and the rest are still generated.
- An outer `try/except` marks the whole job `FAILED` if an unexpected error breaks the run, so an exception never leaves a job stuck in `PROCESSING`. (A server restart mid-job is the exception; see Limitations.)

Progress is committed after every recipient, so `GET /jobs/{id}` shows live counts while a large job is running.

### Database design
Two tables:
- `jobs`: the shared details (event name, issuer, date), the status, and the counters (`total`, `succeeded`, `failed`).
- `certificates`: one row per recipient, linked to its job, holding that recipient's status, file path and error message.

The shared details are stored once on the job rather than repeated for each recipient. The counters are stored on the job so the status endpoint can report progress without counting rows each time. Recipients with invalid data are still stored (their name and email columns are unrestricted text and allow empty values) so the failure can be recorded and reported.

SQLAlchemy is used as the ORM, so the same models run on SQLite (default, zero setup) or PostgreSQL by setting `DATABASE_URL`.

### Models vs schemas
SQLAlchemy models describe how data is stored. Pydantic schemas describe what the API accepts and returns. They are kept separate so the API can change without changing storage, and so internal fields such as file paths are never exposed to clients.

### Certificate generation
Certificates are PDFs drawn with ReportLab from a single fixed layout. ReportLab installs with `pip` alone, so there are no system libraries to set up. Each job's files are stored in their own folder (`generated/job_<id>/`).

### Filename safety
The recipient's name is part of the output filename. Names are sanitised (only letters, digits, `-` and `_` are kept) and each file name is prefixed with the certificate ID. This prevents a name like `../../secret` from writing outside the output folder, and prevents two people with the same name from overwriting each other's file.

### Testability
The processor calls the generator through its module, so tests can replace it with a fake that fails for one chosen recipient. This is how the "one failure does not stop the others" behaviour is tested. Tests run against a temporary database and output folder.

## Limitations and what I would do next

These are known trade-offs of the current design:

- **Jobs are not resumed after a restart.** Background tasks run inside the web server process. If the server stops mid-job, that job stays in `PROCESSING` and the remaining recipients are not generated. Fix: on startup, find jobs left in `PROCESSING` and re-run them, with `process_job` changed to skip recipients that are not `PENDING` and to recompute the counters from the stored statuses.
- **No separate worker.** A very large job uses the same process that serves requests. Production fix: a task queue such as Celery or RQ with Redis, with workers that scale independently of the API.
- **No retry for failed certificates.** A failed recipient stays failed. A `POST /jobs/{id}/retry` endpoint that re-processes only `FAILED` rows would be a small addition.
- **Simple email validation.** The check is a basic pattern (something@something.something), not full RFC validation or a deliverability check.
- **No text wrapping on the certificate.** Very long names or event names can run off the page.
- **Non-Latin names.** The certificate uses a standard PDF font (Helvetica), which cannot draw characters such as Devanagari or Japanese. Such names would not render correctly. A Unicode TTF font would fix this.
- **Downloads during processing.** The ZIP endpoint returns whatever has succeeded so far, so download after the job reaches a final status.
- **Local file storage.** PDFs are saved on the server's disk. A production system would use object storage such as S3.
- **No authentication, rate limiting or pagination.** These were outside the scope of the brief.
- **No database migrations.** Tables are created at startup with `create_all`. A production system would use Alembic.

## Test results

All six required areas are covered: job creation, input validation, certificate generation, job status/progress, handling an individual certificate failure, and retrieving generated certificates.

```text
collected 16 items

tests/test_jobs.py::test_create_job_returns_202_and_job_id PASSED
tests/test_jobs.py::test_missing_event_name_is_rejected PASSED
tests/test_jobs.py::test_empty_recipient_list_is_rejected PASSED
tests/test_jobs.py::test_too_many_recipients_is_rejected PASSED
tests/test_jobs.py::test_invalid_recipients_are_marked_failed_with_reason PASSED
tests/test_jobs.py::test_certificate_pdf_is_generated PASSED
tests/test_jobs.py::test_job_status_all_successful PASSED
tests/test_jobs.py::test_job_status_with_some_failures PASSED
tests/test_jobs.py::test_job_status_all_failed PASSED
tests/test_jobs.py::test_unknown_job_returns_404 PASSED
tests/test_jobs.py::test_one_certificate_failure_does_not_stop_the_others PASSED
tests/test_jobs.py::test_download_single_certificate PASSED
tests/test_jobs.py::test_download_all_as_zip PASSED
tests/test_jobs.py::test_failed_certificate_has_no_file PASSED
tests/test_jobs.py::test_zip_contains_only_successful_certificates PASSED
tests/test_jobs.py::test_download_unknown_ids_return_404 PASSED

16 passed
```