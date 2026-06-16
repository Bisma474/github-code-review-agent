from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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


class PullRequest(Base):
    """Pull request model - tracks PRs through the review lifecycle."""

    __tablename__ = "pull_requests"

    id = Column(UUID_TYPE, primary_key=True, server_default=func.gen_random_uuid())
    repository_id = Column(UUID_TYPE, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    github_pr_id = Column(Integer, nullable=False, index=True)
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