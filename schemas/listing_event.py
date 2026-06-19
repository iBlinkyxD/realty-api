from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import uuid


class ListingEventResponse(BaseModel):
    id:              uuid.UUID
    listing_id:      uuid.UUID
    event_type:      str
    actor_name:      Optional[str]
    actor_email:     Optional[str]
    note:            Optional[str]
    snapshot_before: Optional[dict[str, Any]]
    snapshot_after:  Optional[dict[str, Any]]
    created_at:      datetime

    class Config:
        from_attributes = True
