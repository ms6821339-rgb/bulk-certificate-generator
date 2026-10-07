import re
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Certificate, Job
from app.services import generator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_recipient(name, email, seen_emails):
    if not name or not name.strip():
        return "Name is required"
    if len(name.strip()) > 200:
        return "Name is too long (max 200 characters)"
    if not email or not EMAIL_PATTERN.match(email.strip()):
        return "Invalid email address"
    if email.strip().lower() in seen_emails:
        return "Duplicate email in this job"
    return None


def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        job.status = "PROCESSING"
        job.succeeded = 0
        job.failed = 0
        db.commit()

        seen_emails = set()
        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .order_by(Certificate.id)
            .all()
        )

        for cert in certificates:
            problem = validate_recipient(
                cert.recipient_name, cert.recipient_email, seen_emails
            )

            if problem:
                cert.status = "FAILED"
                cert.error_message = problem
                job.failed += 1
            else:
                try:
                    cert.file_path = generator.generate_certificate(
                        job_id=job.id,
                        cert_id=cert.id,
                        name=cert.recipient_name.strip(),
                        event_name=job.event_name,
                        issued_by=job.issued_by,
                        issue_date=job.issue_date,
                    )
                    cert.status = "SUCCESS"
                    seen_emails.add(cert.recipient_email.strip().lower())
                    job.succeeded += 1
                except Exception as exc:
                    cert.status = "FAILED"
                    cert.error_message = f"Certificate generation failed: {exc}"
                    job.failed += 1

            db.commit()

        if job.failed == 0:
            job.status = "COMPLETED"
        elif job.succeeded == 0:
            job.status = "FAILED"
        else:
            job.status = "COMPLETED_WITH_ERRORS"

        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception:
        db.rollback()
        job = db.get(Job, job_id)
        if job is not None:
            job.status = "FAILED"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()