import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
