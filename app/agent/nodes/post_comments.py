from app.core.logging import get_logger
from app.github.client import post_review_comment
from app.agent.state import ReviewState

logger = get_logger(__name__)


async def post_comments(state: ReviewState) -> dict:
    repo_full = f"{state['github_owner']}/{state['github_repo']}"
    pr_number = state["github_pr_number"]
    posted_ids = []

    for comment in state["formatted_comments"]:
        try:
            comment_id = post_review_comment(
                repo_full_name=repo_full,
                pr_number=pr_number,
                body=comment["body"],
                path=comment["path"],
                line=comment["line"],
                commit_id=comment.get("commit_id", state.get("latest_commit_sha", "HEAD")),
            )
            posted_ids.append(comment_id)
        except Exception as e:
            logger.warning(f"Failed to post comment on {comment['path']}:{comment['line']}: {e}")

    logger.info(f"Posted {len(posted_ids)}/{len(state['formatted_comments'])} comments")
    return {"posted_comment_ids": posted_ids}
