"""Initial schema - create all 5 tables

Revision ID: 001
Revises: 
Create Date: 2026-06-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table 1: repositories
    op.create_table(
        "repositories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("github_repo_id", sa.BigInteger(), unique=True, nullable=False, index=True),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=511), unique=True, nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("webhook_secret", sa.String(length=511), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Table 2: pull_requests
    op.create_table(
        "pull_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("github_pr_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("github_pr_number", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False, index=True),
        sa.Column("base_branch", sa.String(length=255), nullable=False),
        sa.Column("head_branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("pending", "reviewing", "completed", "failed", name="pullrequeststatus"), nullable=False, index=True),
        sa.Column("github_pr_url", sa.String(length=2047), nullable=False),
        sa.Column("diff_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository_id", "github_pr_number", name="uq_repo_pr_number"),
    )

    # Table 3: reviews
    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pull_request_id", UUID(as_uuid=True), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("top_concerns", JSONB(), nullable=True),
        sa.Column("files_reviewed", sa.Integer(), nullable=True),
        sa.Column("total_comments", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Table 4: review_comments
    op.create_table(
        "review_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("github_comment_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.Enum("bug", "security", "performance", "style", "suggestion", name="commentcategory"), nullable=False),
        sa.Column("severity", sa.Enum("blocking", "warning", "suggestion", name="commentseverity"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("was_dismissed", sa.Boolean(), default=False, nullable=False),
        sa.Column("was_resolved", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    # Table 5: feedback
    op.create_table(
        "feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comment_id", UUID(as_uuid=True), sa.ForeignKey("review_comments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.Enum("dismissed", "resolved", "thumbs_up", "thumbs_down", name="feedbackaction"), nullable=False),
        sa.Column("engineer", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("review_comments")
    op.drop_table("reviews")
    op.drop_table("pull_requests")
    op.drop_table("repositories")

    sa.Enum(name="pullrequeststatus").drop(op.get_bind())
    sa.Enum(name="commentcategory").drop(op.get_bind())
    sa.Enum(name="commentseverity").drop(op.get_bind())
    sa.Enum(name="feedbackaction").drop(op.get_bind())
