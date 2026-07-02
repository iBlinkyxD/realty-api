from pydantic import BaseModel, model_validator, Field, EmailStr
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class BookingCreate(BaseModel):
    listing_id: UUID
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=20)
    notes: Optional[str] = Field(default=None, max_length=1000)
    # Guest contact fields — required when not authenticated
    name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    # Payment — set after buyer approves on PayPal
    paypal_order_id: Optional[str] = Field(default=None, max_length=64)

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
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    ghl_contact_url: Optional[str] = None
    # Payment fields
    payment_status: Optional[str] = None
    payout_status: Optional[str] = None
    booked_price_per_day: Optional[float] = None
    platform_fee: Optional[float] = None
    payout_amount: Optional[float] = None
    owner_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CreatePaymentAuthRequest(BaseModel):
    listing_id: UUID
    check_in: date
    check_out: date

    @model_validator(mode='after')
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class CreatePaymentAuthResponse(BaseModel):
    paypal_order_id: str
    amount_usd: float
