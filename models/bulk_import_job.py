import uuid
from sqlalchemy import Column, Text, Integer, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base


class BulkImportJob(Base):
    __tablename__ = "bulk_import_jobs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status          = Column(Text, nullable=False, server_default="pending")  # pending | running | completed | failed
    total_rows      = Column(Integer, nullable=False, server_default="0")
    processed_rows  = Column(Integer, nullable=False, server_default="0")
    succeeded_count = Column(Integer, nullable=False, server_default="0")
    skipped_count   = Column(Integer, nullable=False, server_default="0")
    failed_count    = Column(Integer, nullable=False, server_default="0")
    results         = Column(JSONB, nullable=False, server_default="[]")
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at    = Column(TIMESTAMP(timezone=True), nullable=True)
