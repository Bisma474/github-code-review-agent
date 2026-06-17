from app.core.logging import get_logger
from app.github.client import post_review_comment as gh_post_comment
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)


def post_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    path: str,
    line: int,
    commit_id: str,
) -> dict:
    """
    Post an inline review comment on a specific line of a file.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        body: Comment body in markdown
        path: File path relative to repo root
        line: Line number in the diff
        commit_id: SHA of the latest commit

    Returns:
        dict with success status, comment_id, or error details
    """
    try:
        full_name = f"{owner}/{repo}"
        comment_id = gh_post_comment(
            repo_full_name=full_name,
            pr_number=pr_number,
            body=body,
            path=path,
            line=line,
            commit_id=commit_id,
        )
        return {"success": True, "comment_id": comment_id}
    except GitHubAPIError as e:
        logger.error(f"Failed to post comment on {owner}/{repo}#{pr_number}: {e}")
        return {"success": False, "error": str(e), "error_code": e.error_code}
    except Exception as e:
        logger.error(f"Unexpected error posting comment: {e}")
        return {"success": False, "error": str(e)}
