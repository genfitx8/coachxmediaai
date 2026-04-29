import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class JobCreate(BaseModel):
    media_id: Optional[uuid.UUID] = None
    job_type: str


class JobRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    owner_id: uuid.UUID
    media_id: Optional[uuid.UUID] = None
    job_type: str
    status: str
    celery_task_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
