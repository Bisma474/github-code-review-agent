from datetime import datetime, timezone
from celery import Task
from app.celery_app import app as celery_app
from app.core.logging import get_logger
from app.core.config import get_settings
from app.db.session import get_async_session
from app.db.crud.pull_request import get_pr_by_id, update_pr_status
from app.db.crud.review import create_review, update_review
from app.db.models.enums import PullRequestStatus

logger = get_logger(__name__)


class ReviewTask(Task):
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    max_retries = 2
    default_retry_delay = 30


@celery_app.task(
    bind=True,
    base=ReviewTask,
    name="review.review_pr",
    queue="review",
)
def review_pr(self, pull_request_id: str):
    """
    Celery task that orchestrates the full PR review pipeline.

    Args:
        pull_request_id: UUID string of the PullRequest record
    """
    import asyncio

    logger.info(f"Starting review for PR id={pull_request_id}")
    asyncio.run(_run_review(pull_request_id))


async def _run_review(pull_request_id: str):
    async with get_async_session() as db:
        pr = await get_pr_by_id(db, pull_request_id)
        if not pr:
            logger.error(f"PullRequest not found: {pull_request_id}")
            return

        await update_pr_status(db, pr.id, PullRequestStatus.REVIEWING)
        review = await create_review(db, pull_request_id=pr.id)
        start_time = datetime.now(timezone.utc)

        try:
            from app.agent.graph import review_graph
            initial_state = {
                "pull_request_id": str(pr.id),
                "repository_id": str(pr.repository_id),
                "github_owner": pr.repository.full_name.split("/")[0],
                "github_repo": pr.repository.full_name.split("/")[1],
                "github_pr_number": pr.github_pr_number,
                "diff_raw": "",
                "latest_commit_sha": "",
                "parsed_files": [],
                "llm_analysis": [],
                "formatted_comments": [],
                "posted_comment_ids": [],
                "summary": "",
                "quality_score": 0,
                "top_concerns": [],
                "errors": [],
            }


            result = await review_graph.ainvoke(initial_state)
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            await update_review(db, review.id, {
                "quality_score": result.get("quality_score"),
                "summary": result.get("summary"),
                "top_concerns": result.get("top_concerns"),
                "total_comments": len(result.get("formatted_comments", [])),
                "model_used": get_settings().LLM_MODEL,
                "tokens_used": 0,
                "duration_seconds": duration,
                "completed_at": datetime.now(timezone.utc),
            })

            await update_pr_status(db, pr.id, PullRequestStatus.COMPLETED)
            logger.info(f"Review completed for PR #{pr.github_pr_number} in {duration:.1f}s")

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Review failed for PR #{pr.github_pr_number}: {e}")

            await update_review(db, review.id, {
                "duration_seconds": duration,
                "completed_at": datetime.now(timezone.utc),
            })
            await update_pr_status(db, pr.id, PullRequestStatus.FAILED)
