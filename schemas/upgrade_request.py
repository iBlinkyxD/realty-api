from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class UpgradeRequestCreate(BaseModel):
    requested_role: str
    # Realtor questionnaire fields (ignored for owner requests)
    license_number: Optional[str] = None
    territory: Optional[str] = None
    years_experience: Optional[int] = None
    specialties: Optional[str] = None
    bio: Optional[str] = None


class UpgradeRequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    requested_role: str
    status: str
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}


class UpgradeRequestAdminResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_display_name: str
    requested_role: str
    status: str
    rejection_reason: Optional[str]
    created_at: datetime
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    # Realtor questionnaire
    license_number: Optional[str] = None
    territory: Optional[str] = None
    years_experience: Optional[int] = None
    specialties: Optional[str] = None
    bio: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminRejectBody(BaseModel):
    reason: str
