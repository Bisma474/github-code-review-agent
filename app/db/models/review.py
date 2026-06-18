import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Review(Base):
    """Review model - stores completed agent reviews."""

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pull_request_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
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
    feedback = relationship("Feedback", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Review(id={self.id}, score={self.quality_score}, model='{self.model_used}')>"