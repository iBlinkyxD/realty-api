from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid


class ListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    transaction: str
    price: Decimal
    location: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    roi: Optional[Decimal] = None
    seller_financing: bool = False
    hoa: bool = False
    hoa_fee: Optional[Decimal] = None
    tax_exempt: bool = False
    gated_community: bool = False
    construction_status: Optional[str] = None
    year_built: Optional[int] = None
    features: Optional[List[str]] = None
    maps_url: Optional[str] = None
    tag: Optional[str] = None
    images: Optional[List[str]] = None


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    transaction: Optional[str] = None
    price: Optional[Decimal] = None
    location: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    roi: Optional[Decimal] = None
    seller_financing: Optional[bool] = None
    hoa: Optional[bool] = None
    hoa_fee: Optional[Decimal] = None
    tax_exempt: Optional[bool] = None
    gated_community: Optional[bool] = None
    construction_status: Optional[str] = None
    year_built: Optional[int] = None
    features: Optional[List[str]] = None
    maps_url: Optional[str] = None
    tag: Optional[str] = None
    images: Optional[List[str]] = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    type: str
    transaction: str
    price: Decimal
    location: str
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    area_sqft: Optional[int]
    lot_size_sqft: Optional[int]
    roi: Optional[Decimal]
    seller_financing: bool
    hoa: bool
    hoa_fee: Optional[Decimal]
    tax_exempt: bool
    gated_community: bool
    construction_status: Optional[str]
    year_built: Optional[int]
    features: List[str]
    maps_url: Optional[str]
    tag: Optional[str]
    images: List[str]
    status: str
    rejection_reason: Optional[str] = None
    submitted_by: uuid.UUID
    submitted_by_name: Optional[str] = None
    submitted_by_email: Optional[str] = None
    owner_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class AdminListingResponse(ListingResponse):
    submitted_by_name: Optional[str] = None
    submitted_by_email: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_by_email: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminRejectBody(BaseModel):
    reason: str
