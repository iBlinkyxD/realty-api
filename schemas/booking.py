from pydantic import BaseModel, model_validator, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class BookingCreate(BaseModel):
    listing_id: UUID
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=20)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if self.check_in < date.today():
            raise ValueError("check_in cannot be in the past")
        return self


class BookingResponse(BaseModel):
    id: str
    listing_id: str
    listing_title: Optional[str] = None
    listing_location: Optional[str] = None
    listing_images: list[str] = []
    check_in: str
    check_out: str
    guests: int
    total_price: Optional[float] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
