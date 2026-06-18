import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import FeedbackAction


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=True, index=True)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("review_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    action = Column(Enum(FeedbackAction, native_enum=True), nullable=True)
    rating = Column(Integer, nullable=True)
    category = Column(String(50), nullable=True)
    engineer = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    review = relationship("Review", back_populates="feedback")
    comment = relationship("ReviewComment", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, action='{self.action}', engineer='{self.engineer}')>"