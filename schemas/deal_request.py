from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class DealRequestCreate(BaseModel):
    discount_value: float = Field(gt=0)
    discount_type: str = 'pct'
    message: Optional[str] = None

    @model_validator(mode='after')
    def validate_discount(self):
        if self.discount_type not in ('pct', 'fixed'):
            raise ValueError("discount_type must be 'pct' or 'fixed'")
        if self.discount_type == 'pct' and self.discount_value >= 100:
            raise ValueError("Percentage discount must be less than 100")
        return self


class DealRequestResponse(BaseModel):
    id: UUID
    listing_id: UUID
    listing_title: str
    listing_location: str
    listing_thumbnail: Optional[str]
    requested_by_name: Optional[str]
    requested_by_email: str
    discount_value: float
    discount_type: str
    message: Optional[str]
    status: str
    rejection_reason: Optional[str]
    reviewed_by_name: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class DealRequestRejectBody(BaseModel):
    reason: str
