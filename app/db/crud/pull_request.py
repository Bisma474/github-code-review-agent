from typing import Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pull_request import PullRequest
from app.db.models.enums import PullRequestStatus


async def create_pr(
    db: AsyncSession,
    repository_id: UUID,
    github_pr_id: int,
    github_pr_number: int,
    title: str,
    author: str,
    base_branch: str,
    head_branch: str,
    github_pr_url: str,
    status: PullRequestStatus = PullRequestStatus.PENDING,
) -> PullRequest:
    pr = PullRequest(
        repository_id=repository_id,
        github_pr_id=github_pr_id,
        github_pr_number=github_pr_number,
        title=title,
        author=author,
        base_branch=base_branch,
        head_branch=head_branch,
        github_pr_url=github_pr_url,
        status=status,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)
    return pr


async def get_pr_by_id(
    db: AsyncSession,
    pr_id: UUID,
) -> Optional[PullRequest]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(PullRequest)
        .options(selectinload(PullRequest.repository))
        .where(PullRequest.id == pr_id)
    )
    return result.scalar_one_or_none()


async def get_pr_by_github_number(
    db: AsyncSession,
    repository_id: UUID,
    github_pr_number: int,
) -> Optional[PullRequest]:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repository_id == repository_id,
            PullRequest.github_pr_number == github_pr_number,
        )
    )
    return result.scalar_one_or_none()


async def update_pr_status(
    db: AsyncSession,
    pr_id: UUID,
    status: PullRequestStatus,
) -> Optional[PullRequest]:
    await db.execute(
        update(PullRequest)
        .where(PullRequest.id == pr_id)
        .values(status=status)
    )
    await db.commit()
    return await get_pr_by_id(db, pr_id)


async def get_pending_prs(
    db: AsyncSession,
) -> list[PullRequest]:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.status == PullRequestStatus.PENDING
        )
    )
    return list(result.scalars().all())
