import uuid
from sqlalchemy import Column, Text, TIMESTAMP, Numeric, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    check_in = Column(Text, nullable=False)
    check_out = Column(Text, nullable=False)
    guests = Column(Integer, default=1)
    total_price = Column(Numeric(12, 2))
    notes = Column(Text)
    status = Column(Text, nullable=False, default="pending")  # pending / confirmed / cancelled
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
