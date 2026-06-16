from typing import Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.comment import ReviewComment


async def create_comment(
    db: AsyncSession,
    review_id: UUID,
    file_path: str,
    line_number: int,
    category: str,
    severity: str,
    body: str,
    code_snippet: Optional[str] = None,
    suggestion: Optional[str] = None,
    github_comment_id: Optional[int] = None,
) -> ReviewComment:
    comment = ReviewComment(
        review_id=review_id,
        file_path=file_path,
        line_number=line_number,
        category=category,
        severity=severity,
        body=body,
        code_snippet=code_snippet,
        suggestion=suggestion,
        github_comment_id=github_comment_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_comments_by_review_id(
    db: AsyncSession,
    review_id: UUID,
) -> list[ReviewComment]:
    result = await db.execute(
        select(ReviewComment)
        .where(ReviewComment.review_id == review_id)
        .order_by(ReviewComment.file_path, ReviewComment.line_number)
    )
    return list(result.scalars().all())


async def update_comment_github_id(
    db: AsyncSession,
    comment_id: UUID,
    github_comment_id: int,
) -> Optional[ReviewComment]:
    await db.execute(
        update(ReviewComment)
        .where(ReviewComment.id == comment_id)
        .values(github_comment_id=github_comment_id)
    )
    await db.commit()
    result = await db.execute(
        select(ReviewComment).where(ReviewComment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def get_dismissed_patterns(
    db: AsyncSession,
    repository_id: UUID,
) -> list[ReviewComment]:
    from app.db.models.review import Review
    from app.db.models.pull_request import PullRequest

    result = await db.execute(
        select(ReviewComment)
        .join(Review, ReviewComment.review_id == Review.id)
        .join(PullRequest, Review.pull_request_id == PullRequest.id)
        .where(
            PullRequest.repository_id == repository_id,
            ReviewComment.was_dismissed == True,
        )
    )
    return list(result.scalars().all())
