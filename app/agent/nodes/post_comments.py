from app.core.logging import get_logger
from app.github.client import get_github_client
from app.agent.state import ReviewState

logger = get_logger(__name__)


async def post_comments(state: ReviewState) -> dict:
    owner = state["github_owner"]
    repo = state["github_repo"]
    pr_number = state["github_pr_number"]
    client = get_github_client()
    posted_ids = []

    for comment in state["formatted_comments"]:
        try:
            comment_id = client.post_review_comment(
                owner, repo, pr_number,
                body=comment["body"],
                path=comment["path"],
                line=comment["line"],
            )
            posted_ids.append(comment_id)
        except Exception as e:
            logger.warning(f"Failed to post comment on {comment['path']}:{comment['line']}: {e}")

    logger.info(f"Posted {len(posted_ids)}/{len(state['formatted_comments'])} comments")
    return {"posted_comment_ids": posted_ids}
