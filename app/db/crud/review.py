from typing import Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.review import Review


async def create_review(
    db: AsyncSession,
    pull_request_id: UUID,
) -> Review:
    review = Review(pull_request_id=pull_request_id)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review_by_pr_id(
    db: AsyncSession,
    pull_request_id: UUID,
) -> Optional[Review]:
    result = await db.execute(
        select(Review).where(Review.pull_request_id == pull_request_id)
    )
    return result.scalar_one_or_none()


async def update_review(
    db: AsyncSession,
    review_id: UUID,
    updates: dict,
) -> Optional[Review]:
    await db.execute(
        update(Review).where(Review.id == review_id).values(**updates)
    )
    await db.commit()
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    return result.scalar_one_or_none()
