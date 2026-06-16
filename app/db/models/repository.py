from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.db.models.enums import PullRequestStatus

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    from sqlalchemy import String
    UUID_TYPE = String


class Repository(Base):
    """Repository model - stores GitHub repos connected to the agent."""

    __tablename__ = "repositories"

    id = Column(UUID_TYPE, primary_key=True, server_default=func.gen_random_uuid())
    github_repo_id = Column(Integer, unique=True, nullable=False, index=True)
    owner = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    full_name = Column(String(511), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    webhook_secret = Column(String(511), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pull_requests = relationship("PullRequest", back_populates="repository")

    def __repr__(self):
        return f"<Repository(id={self.id}, full_name='{self.full_name}', active={self.is_active})>"