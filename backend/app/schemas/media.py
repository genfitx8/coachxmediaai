import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class MediaRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    project_id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    status: str
    metadata_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    project_id: uuid.UUID


class PresignedUrlResponse(BaseModel):
    upload_url: str
    storage_key: str


class ConfirmUploadRequest(BaseModel):
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int
    project_id: uuid.UUID
