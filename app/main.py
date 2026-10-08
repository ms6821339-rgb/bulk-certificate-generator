import io
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app import models
from app.database import Base, engine, get_db
from app.schemas import JobCreate, JobOut
from app.services.processor import process_job

# Create the tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not payload.event_name.strip():
        raise HTTPException(status_code=422, detail="event_name cannot be blank")

    job = models.Job(
        event_name=payload.event_name.strip(),
        issued_by=payload.issued_by.strip(),
        issue_date=payload.issue_date.strip(),
        status="PENDING",
        total=len(payload.recipients),
    )
    job.certificates = [
        models.Certificate(
            recipient_name=r.name,
            recipient_email=r.email,
            status="PENDING",
        )
        for r in payload.recipients
    ]
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_job, job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "status_url": f"/jobs/{job.id}",
    }


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = (
        db.query(models.Job)
        .options(selectinload(models.Job.certificates))
        .filter(models.Job.id == job_id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs/{job_id}/certificates/{cert_id}")
def download_certificate(job_id: int, cert_id: int, db: Session = Depends(get_db)):
    cert = (
        db.query(models.Certificate)
        .filter(models.Certificate.id == cert_id, models.Certificate.job_id == job_id)
        .first()
    )
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if cert.status != "SUCCESS" or not cert.file_path or not Path(cert.file_path).exists():
        raise HTTPException(status_code=404, detail="Certificate file is not available")

    return FileResponse(
        cert.file_path,
        media_type="application/pdf",
        filename=Path(cert.file_path).name,
    )


@app.get("/jobs/{job_id}/download")
def download_all(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    certs = (
        db.query(models.Certificate)
        .filter(models.Certificate.job_id == job_id, models.Certificate.status == "SUCCESS")
        .all()
    )
    files = [c.file_path for c in certs if c.file_path and Path(c.file_path).exists()]
    if not files:
        raise HTTPException(status_code=404, detail="No certificates available to download")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, arcname=Path(path).name)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}_certificates.zip"'},
    )