from typing import Optional
from app.core.logging import get_logger
from app.github.client import get_pr_diff as gh_get_diff
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)


def get_pr_diff(owner: str, repo: str, pr_number: int) -> dict:
    """
    Fetch the raw unified diff for a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        dict with success status, diff text, or error details
    """
    try:
        full_name = f"{owner}/{repo}"
        diff = gh_get_diff(full_name, pr_number)
        return {"success": True, "diff": diff}
    except GitHubAPIError as e:
        logger.error(f"Failed to fetch diff for {owner}/{repo}#{pr_number}: {e}")
        return {"success": False, "error": str(e), "error_code": e.error_code}
    except Exception as e:
        logger.error(f"Unexpected error fetching diff: {e}")
        return {"success": False, "error": str(e)}
