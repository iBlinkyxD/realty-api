from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SavedHomeResponse(BaseModel):
    id: str
    listing_id: str
    listing_title: str
    listing_location: str
    listing_price: float
    listing_transaction: str
    listing_images: list[str]
    listing_bedrooms: Optional[int] = None
    listing_bathrooms: Optional[float] = None
    saved_at: datetime

    model_config = {"from_attributes": True}
