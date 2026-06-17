from typing import Optional
from app.core.logging import get_logger
from app.github.client import get_pr_files as gh_get_files
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)


def get_pr_files(owner: str, repo: str, pr_number: int) -> dict:
    """
    List all files changed in a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        dict with success status, files list, or error details
    """
    try:
        full_name = f"{owner}/{repo}"
        files = gh_get_files(full_name, pr_number)
        return {"success": True, "files": files}
    except GitHubAPIError as e:
        logger.error(f"Failed to fetch files for {owner}/{repo}#{pr_number}: {e}")
        return {"success": False, "error": str(e), "error_code": e.error_code}
    except Exception as e:
        logger.error(f"Unexpected error fetching files: {e}")
        return {"success": False, "error": str(e)}
