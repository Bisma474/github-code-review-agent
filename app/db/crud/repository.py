from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository


async def create_repo(
    db: AsyncSession,
    github_repo_id: int,
    owner: str,
    name: str,
    full_name: str,
    webhook_secret: str,
    is_active: bool = True,
) -> Repository:
    repo = Repository(
        github_repo_id=github_repo_id,
        owner=owner,
        name=name,
        full_name=full_name,
        webhook_secret=webhook_secret,
        is_active=is_active,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


async def get_repo_by_full_name(
    db: AsyncSession,
    full_name: str,
) -> Optional[Repository]:
    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name)
    )
    return result.scalar_one_or_none()


async def get_repo_by_id(
    db: AsyncSession,
    repo_id: str,
) -> Optional[Repository]:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    return result.scalar_one_or_none()


async def get_active_repos(
    db: AsyncSession,
) -> list[Repository]:
    result = await db.execute(
        select(Repository).where(Repository.is_active == True)
    )
    return list(result.scalars().all())


async def set_repo_active_status(
    db: AsyncSession,
    repo_id: str,
    is_active: bool,
) -> Optional[Repository]:
    await db.execute(
        update(Repository)
        .where(Repository.id == repo_id)
        .values(is_active=is_active)
    )
    await db.commit()
    return await get_repo_by_id(db, repo_id)
