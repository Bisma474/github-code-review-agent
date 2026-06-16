from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.db.models.enums import CommentCategory, CommentSeverity

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    from sqlalchemy import String
    UUID_TYPE = String


class ReviewComment(Base):
    """Review comment model - stores individual inline comments on code."""

    __tablename__ = "review_comments"

    id = Column(UUID_TYPE, primary_key=True, server_default=func.gen_random_uuid())
    review_id = Column(UUID_TYPE, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    github_comment_id = Column(Integer, nullable=True, index=True)
    file_path = Column(String(1024), nullable=False)
    line_number = Column(Integer, nullable=False)
    category = Column(Enum(CommentCategory, native_enum=True), nullable=False, index=True)
    severity = Column(Enum(CommentSeverity, native_enum=True), nullable=False, index=True)
    body = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    was_dismissed = Column(Boolean, default=False, nullable=False, index=True)
    was_resolved = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    review = relationship("Review", back_populates="comments")
    feedback = relationship("Feedback", back_populates="comment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReviewComment(id={self.id}, category='{self.category}', severity='{self.severity}')>"