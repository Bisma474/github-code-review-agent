from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feedback import Feedback


async def create_feedback(
    db: AsyncSession,
    review_id: UUID,
    rating: int,
    comment_id: Optional[UUID] = None,
    category: Optional[str] = None,
    notes: Optional[str] = None,
) -> Feedback:
    fb = Feedback(
        review_id=review_id,
        comment_id=comment_id,
        rating=rating,
        category=category,
        notes=notes,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def get_feedback_by_review_id(db: AsyncSession, review_id: UUID) -> list[Feedback]:
    result = await db.execute(
        select(Feedback).where(Feedback.review_id == review_id)
    )
    return list(result.scalars().all())
