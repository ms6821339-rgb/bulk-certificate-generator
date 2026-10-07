from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


from app.config import MAX_RECIPIENTS_PER_JOB

class RecipientIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import MAX_RECIPIENTS_PER_JOB


class RecipientIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class JobCreate(BaseModel):# the below data is given by user 
    event_name: str = Field(min_length=1, max_length=200)
    issued_by: str = Field(min_length=1, max_length=200)
    issue_date: str = Field(min_length=1, max_length=50)
    recipients: List[RecipientIn] = Field(min_length=1, max_length=MAX_RECIPIENTS_PER_JOB)    

class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    status: str
    error_message: Optional[str] = None

class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_name: str
    issued_by: str
    issue_date: str
    status: str
    total: int
    succeeded: int
    failed: int
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    certificates: List[CertificateOut] = []
