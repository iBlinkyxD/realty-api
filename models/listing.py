import uuid
from sqlalchemy import Column, Text, Numeric, Integer, Boolean, Enum as SAEnum, TIMESTAMP, ARRAY, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

listing_status = SAEnum("draft", "pending_approval", "active", "rejected", "archived", name="listing_status", create_type=True)
listing_type = SAEnum("villa", "apartment", "condo", "land", "commercial", name="listing_type", create_type=True)
transaction_type = SAEnum("sale", "rent", "both", name="transaction_type", create_type=True)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text)
    type = Column(listing_type, nullable=False)
    transaction = Column(transaction_type, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    location = Column(Text, nullable=False)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    area_sqft = Column(Integer)
    lot_size_sqft = Column(Integer)
    roi = Column(Numeric(5, 2))
    seller_financing = Column(Boolean, nullable=False, server_default="false")
    hoa = Column(Boolean, nullable=False, server_default="false")
    hoa_fee = Column(Numeric(10, 2))
    tax_exempt = Column(Boolean, nullable=False, server_default="false")
    gated_community = Column(Boolean, nullable=False, server_default="false")
    construction_status = Column(Text)
    year_built = Column(Integer)
    features = Column(ARRAY(Text), server_default="{}")
    maps_url = Column(Text)
    tag = Column(Text)
    images = Column(ARRAY(Text), server_default="{}")
    status = Column(listing_status, nullable=False, server_default="pending_approval")
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(TIMESTAMP(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
