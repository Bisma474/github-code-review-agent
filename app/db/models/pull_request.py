import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import PullRequestStatus


class PullRequest(Base):
    """Pull request model - tracks PRs through the review lifecycle."""

    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    github_pr_id = Column(BigInteger, nullable=False, index=True)
    github_pr_number = Column(Integer, nullable=False, index=True)
    title = Column(String(1000), nullable=False)
    author = Column(String(255), nullable=False, index=True)
    base_branch = Column(String(255), nullable=False)
    head_branch = Column(String(255), nullable=False)
    status = Column(Enum(PullRequestStatus, native_enum=True), default=PullRequestStatus.PENDING, nullable=False, index=True)
    github_pr_url = Column(String(2047), nullable=False)
    diff_fetched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="pull_requests")
    review = relationship("Review", uselist=False, back_populates="pull_request", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_pull_requests_repo_pr', 'repository_id', 'github_pr_number', unique=True),
    )

    def __repr__(self):
        return f"<PullRequest(id={self.id}, pr_number={self.github_pr_number}, status='{self.status}', repo='{self.repository.full_name}')>"