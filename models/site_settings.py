from sqlalchemy import Column, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class SiteSettings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, default=1)
    data = Column(JSONB, nullable=False, server_default="{}")
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
