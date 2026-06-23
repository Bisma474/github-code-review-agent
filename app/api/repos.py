from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/repos")


class RegisterRepoRequest(BaseModel):
    full_name: str
    github_repo_id: int


@router.post("/register")
async def register_repo(req: RegisterRepoRequest):
    from app.db.session import get_async_session
    from app.db.crud.repository import create_repo, get_repo_by_full_name

    async with get_async_session() as session:
        existing = await get_repo_by_full_name(session, req.full_name)
        if existing:
            if existing.is_active:
                return {"status": "already_registered", "repo_id": str(existing.id)}
            existing.is_active = True
            await session.commit()
            return {"status": "reactivated", "repo_id": str(existing.id)}

        import secrets

        owner, name = req.full_name.split("/", 1)
        repo = await create_repo(
            session,
            github_repo_id=req.github_repo_id,
            owner=owner,
            name=name,
            full_name=req.full_name,
            webhook_secret=secrets.token_hex(32),
            is_active=True,
        )
        logger.info(f"Registered repo {req.full_name} (id={repo.id})")
        return {"status": "registered", "repo_id": str(repo.id)}


@router.get("")
async def list_repos():
    from app.db.session import get_async_session
    from app.db.crud.repository import get_active_repos

    async with get_async_session() as session:
        repos = await get_active_repos(session)
        return {
            "repos": [
                {
                    "id": str(r.id),
                    "full_name": r.full_name,
                    "is_active": r.is_active,
                }
                for r in repos
            ]
        }
