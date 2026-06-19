import uuid
from sqlalchemy import Column, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base


class ListingEvent(Base):
    __tablename__ = "listing_events"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id      = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type      = Column(Text, nullable=False)   # submitted | approved | rejected | archived | edit_submitted | edit_approved | edit_rejected
    actor_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note            = Column(Text, nullable=True)     # rejection reason, etc.
    snapshot_before = Column(JSONB, nullable=True)   # for edit events
    snapshot_after  = Column(JSONB, nullable=True)   # for edit events
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
