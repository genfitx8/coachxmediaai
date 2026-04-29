import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscriptionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    stripe_customer_id: str
    stripe_subscription_id: Optional[str] = None
    plan: str
    status: str
    current_period_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
