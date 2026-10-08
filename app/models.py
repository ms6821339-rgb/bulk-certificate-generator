from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(200), nullable=False)
    issued_by = Column(String(200), nullable=False)
    issue_date = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    total = Column(Integer, nullable=False, default=0)
    succeeded = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    
    certificates = relationship("Certificate", back_populates="job", cascade="all, delete-orphan")

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    recipient_name = Column(Text, nullable=True)
    recipient_email = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    job = relationship("Job", back_populates="certificates")