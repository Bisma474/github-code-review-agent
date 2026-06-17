from fastapi import APIRouter, Request, HTTPException, status
from app.core.logging import get_logger
from app.github.webhook import validate_webhook_signature

logger = get_logger(__name__)
router = APIRouter()


@router.post("/webhook/github")
async def github_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")

    raw_body = await request.body()

    from app.core.config import get_settings
    settings = get_settings()

    is_valid = validate_webhook_signature(raw_body, signature, settings.GITHUB_WEBHOOK_SECRET)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    import json
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid JSON payload")

    action = payload.get("action")
    pr_data = payload.get("pull_request")
    repo_data = payload.get("repository")

    if not action or not pr_data or not repo_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Missing required fields: action, pull_request, repository",
        )

    if action != "opened":
        logger.debug(f"Ignoring webhook action: {action}")
        return {"status": "ignored", "reason": f"action '{action}' not handled"}

    full_name = repo_data.get("full_name")
    pr_number = pr_data.get("number")

    from app.db.session import get_async_session
    from app.db.crud.repository import get_repo_by_full_name
    from app.db.crud.pull_request import create_pr
    from app.db.models.enums import PullRequestStatus

    async with get_async_session() as session:
        repo = await get_repo_by_full_name(session, full_name)
        if not repo or not repo.is_active:
            logger.info(f"Repo {full_name} not active or not found - ignoring")
            return {"status": "ignored", "reason": "repo not active"}

        pr_record = await create_pr(
            session,
            repository_id=repo.id,
            github_pr_id=pr_data.get("id"),
            github_pr_number=pr_number,
            title=pr_data.get("title", ""),
            author=pr_data.get("user", {}).get("login", "unknown"),
            base_branch=pr_data.get("base", {}).get("ref", ""),
            head_branch=pr_data.get("head", {}).get("ref", ""),
            github_pr_url=pr_data.get("html_url", ""),
            status=PullRequestStatus.PENDING,
        )

        pr_id = pr_record.id
        logger.info(f"PR #{pr_number} in {full_name} queued for review (id={pr_id})")

    try:
        from app.celery_app import app as celery_app
        from app.tasks.review import review_pr
        review_pr.delay(str(pr_id))
        logger.info(f"PR #{pr_number} dispatched to Celery")
    except Exception as e:
        logger.warning(f"Failed to dispatch Celery task for PR #{pr_number}: {e}")

    return {"status": "queued", "pr_number": pr_number}
