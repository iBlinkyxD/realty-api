import uuid
from sqlalchemy import Column, Text, Integer, Enum as SAEnum, TIMESTAMP, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

upgrade_status = SAEnum("pending", "approved", "rejected", name="upgrade_status", create_type=True)


class UpgradeRequest(Base):
    __tablename__ = "upgrade_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_role = Column(
        SAEnum("owner", "realtor", name="requested_role_check", create_type=False),
        nullable=False,
    )
    status = Column(upgrade_status, nullable=False, server_default="pending")
    notes = Column(Text)
    license_number = Column(Text)
    territory = Column(Text)
    years_experience = Column(Integer)
    specialties = Column(Text)
    bio = Column(Text)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(TIMESTAMP(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
