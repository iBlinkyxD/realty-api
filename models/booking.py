import uuid
from sqlalchemy import Column, Text, TIMESTAMP, Numeric, Integer, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    guest_name = Column(Text, nullable=True)
    guest_email = Column(Text, nullable=True)
    lead_id = Column(UUID(as_uuid=True), nullable=True)
    check_in = Column(Text, nullable=False)
    check_out = Column(Text, nullable=False)
    guests = Column(Integer, default=1)
    total_price = Column(Numeric(12, 2))
    notes = Column(Text)
    status = Column(Text, nullable=False, default="pending")  # pending / confirmed / cancelled
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    # Payment fields (Phase 38)
    paypal_order_id = Column(Text, nullable=True)
    paypal_authorization_id = Column(Text, nullable=True)
    paypal_capture_id = Column(Text, nullable=True)
    payment_status = Column(Text, nullable=False, server_default="unpaid")  # unpaid | authorized | captured | voided | refunded
    payout_status = Column(Text, nullable=False, server_default="pending")  # pending | paid | failed
    booked_price_per_day = Column(Numeric(10, 2), nullable=True)
    needs_admin_review = Column(Boolean, nullable=False, server_default="false")
    platform_fee = Column(Numeric(12, 2), nullable=True)
    payout_amount = Column(Numeric(12, 2), nullable=True)
