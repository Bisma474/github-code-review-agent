import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import FeedbackAction


class Feedback(Base):
    """Feedback model - stores engineer feedback on review comments."""

    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("review_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Enum(FeedbackAction, native_enum=True), nullable=False)
    engineer = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    comment = relationship("ReviewComment", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, action='{self.action}', engineer='{self.engineer}')>"