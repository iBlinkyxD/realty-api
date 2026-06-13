import uuid
from sqlalchemy import Column, Text, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class PendingUser(Base):
    __tablename__ = "pending_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    display_name = Column(Text, nullable=False)
    phone = Column(Text, nullable=True)
    verification_code = Column(Text, nullable=True)
    verification_code_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    verification_attempts = Column(Integer, nullable=False, server_default="0")
    last_code_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # Row-level TTL: pending rows older than this are garbage-collected by the cleanup task
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
