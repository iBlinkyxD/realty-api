import uuid
import sqlalchemy
from sqlalchemy import Column, Text, Boolean, Integer, Enum as SAEnum, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base

user_role = SAEnum("buyer", "owner", "realtor", "admin", name="user_role", create_type=True)
user_status = SAEnum("active", "suspended", name="user_status", create_type=True)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Human-readable sequential ID assigned by DB sequence on insert; never null after migration
    user_code = Column(Integer, nullable=True, unique=True)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=True)
    google_id = Column(Text, nullable=True, unique=True)
    avatar_url = Column(Text, nullable=True)
    role = Column(user_role, nullable=False, server_default="buyer")
    status = Column(user_status, nullable=False, server_default="active")
    display_name = Column(Text, nullable=False)
    phone = Column(Text)
    email_verified = Column(Boolean, nullable=False, default=False)
    verification_code = Column(Text, nullable=True)
    verification_code_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    verification_attempts = Column(sqlalchemy.Integer, nullable=False, server_default="0")
    last_code_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    deletion_requested_at = Column(TIMESTAMP(timezone=True), nullable=True)
    password_reset_token = Column(Text, nullable=True, index=True)
    password_reset_expires = Column(TIMESTAMP(timezone=True), nullable=True)
