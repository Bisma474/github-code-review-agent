from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    from sqlalchemy import String
    UUID_TYPE = String


class Review(Base):
    """Review model - stores completed agent reviews."""

    __tablename__ = "reviews"

    id = Column(UUID_TYPE, primary_key=True, server_default=func.gen_random_uuid())
    pull_request_id = Column(UUID_TYPE, ForeignKey("pull_requests.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    quality_score = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    top_concerns = Column(JSON, nullable=True)
    files_reviewed = Column(Integer, nullable=True)
    total_comments = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pull_request = relationship("PullRequest", back_populates="review")
    comments = relationship("ReviewComment", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Review(id={self.id}, score={self.quality_score}, model='{self.model_used}')>"