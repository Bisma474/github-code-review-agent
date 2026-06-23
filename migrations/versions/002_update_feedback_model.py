"""update feedback model

Revision ID: 002
Revises: 001
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=True, index=True))
    op.add_column("feedback", sa.Column("rating", sa.Integer(), nullable=True))
    op.add_column("feedback", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column("feedback", sa.Column("notes", sa.Text(), nullable=True))
    op.alter_column("feedback", "action", existing_type=sa.Enum("APPROVED", "REJECTED", "CHANGES_REQUESTED", "INFORMATIONAL", name="feedbackaction"), nullable=True)
    op.alter_column("feedback", "engineer", existing_type=sa.VARCHAR(length=255), nullable=True)
    op.alter_column("feedback", "comment_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.drop_column("feedback", "notes")
    op.drop_column("feedback", "category")
    op.drop_column("feedback", "rating")
    op.drop_column("feedback", "review_id")
    op.alter_column("feedback", "comment_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("feedback", "engineer", existing_type=sa.VARCHAR(length=255), nullable=False)
    op.alter_column("feedback", "action", existing_type=sa.Enum("APPROVED", "REJECTED", "CHANGES_REQUESTED", "INFORMATIONAL", name="feedbackaction"), nullable=False)
