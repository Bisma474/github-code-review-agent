from app.core.logging import get_logger
from app.github.client import post_pr_comment as gh_post_summary
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)


def post_summary(owner: str, repo: str, pr_number: int, body: str) -> dict:
    """
    Post a PR-level summary comment on the conversation timeline.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        body: Summary comment body in markdown

    Returns:
        dict with success status, comment_id, or error details
    """
    try:
        full_name = f"{owner}/{repo}"
        comment_id = gh_post_summary(
            repo_full_name=full_name,
            pr_number=pr_number,
            body=body,
        )
        return {"success": True, "comment_id": comment_id}
    except GitHubAPIError as e:
        logger.error(f"Failed to post summary on {owner}/{repo}#{pr_number}: {e}")
        return {"success": False, "error": str(e), "error_code": e.error_code}
    except Exception as e:
        logger.error(f"Unexpected error posting summary: {e}")
        return {"success": False, "error": str(e)}
