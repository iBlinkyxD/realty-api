import uuid
from sqlalchemy import Column, Text, Numeric, Enum as SAEnum, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base

deal_request_status = SAEnum("pending", "approved", "rejected", name="deal_request_status", create_type=True)


class DealRequest(Base):
    __tablename__ = "deal_requests"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id   = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    discount_value = Column(Numeric(12, 2), nullable=False)
    discount_type  = Column(Text, nullable=False, server_default="pct")
    message      = Column(Text)
    status       = Column(deal_request_status, nullable=False, server_default="pending")
    rejection_reason = Column(Text)
    reviewed_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at  = Column(TIMESTAMP(timezone=True))
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
