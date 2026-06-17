from typing import Optional
from github import Github, GithubException, RateLimitExceededException
from github.PullRequest import PullRequest as GithubPullRequest
from github.Repository import Repository as GithubRepository

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)
settings = get_settings()

_github_client: Optional[Github] = None


def get_github_client() -> Github:
    """
    Get or create a configured PyGithub Github instance.

    Uses GITHUB_TOKEN from settings for authentication.
    The client is cached as a singleton.
    """
    global _github_client
    if _github_client is None:
        logger.info("Initializing GitHub client")
        _github_client = Github(settings.GITHUB_TOKEN)
    return _github_client


def get_repo(full_name: str) -> GithubRepository:
    """
    Get a GitHub repository by its full name (owner/repo).

    Args:
        full_name: Repository full name, e.g. "acme-corp/backend-api"

    Returns:
        GithubRepository object

    Raises:
        GitHubAPIError: If the repo is not found or token lacks access
    """
    client = get_github_client()
    try:
        return client.get_repo(full_name)
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to get repo '{full_name}': {e.data.get('message', str(e))}",
            status_code=e.status,
        )


def get_pull_request(repo: GithubRepository, number: int) -> GithubPullRequest:
    """
    Get a pull request by its number.

    Args:
        repo: GithubRepository instance
        number: PR number

    Returns:
        GithubPullRequest object

    Raises:
        GitHubAPIError: If the PR is not found or token lacks access
    """
    try:
        return repo.get_pull(number)
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to get PR #{number}: {e.data.get('message', str(e))}",
            status_code=e.status,
        )


def get_pr_diff(repo_full_name: str, pr_number: int) -> str:
    """
    Fetch the raw unified diff for a pull request.

    Args:
        repo_full_name: Repository full name, e.g. "owner/repo"
        pr_number: Pull request number

    Returns:
        Raw diff text string

    Raises:
        GitHubAPIError: If the fetch fails
    """
    client = get_github_client()
    try:
        repo = client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        return pr.diff
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to fetch diff for {repo_full_name}#{pr_number}: {e.data.get('message', str(e))}",
            status_code=e.status,
        )
    except RateLimitExceededException:
        logger.warning("GitHub API rate limit exceeded when fetching diff")
        raise


def get_pr_files(repo_full_name: str, pr_number: int) -> list[dict]:
    """
    List all files changed in a pull request with metadata.

    Args:
        repo_full_name: Repository full name, e.g. "owner/repo"
        pr_number: Pull request number

    Returns:
        List of dicts with keys: filename, status, additions, deletions, changes

    Raises:
        GitHubAPIError: If the fetch fails
    """
    client = get_github_client()
    try:
        repo = client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = pr.get_files()
        return [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
            }
            for f in files
        ]
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to fetch files for {repo_full_name}#{pr_number}: {e.data.get('message', str(e))}",
            status_code=e.status,
        )
    except RateLimitExceededException:
        logger.warning("GitHub API rate limit exceeded when fetching files")
        raise


def post_review_comment(
    repo_full_name: str,
    pr_number: int,
    body: str,
    path: str,
    line: int,
    commit_id: str,
) -> int:
    """
    Post an inline review comment on a specific line of a file in a PR.

    Args:
        repo_full_name: Repository full name
        pr_number: Pull request number
        body: Comment body (markdown)
        path: File path relative to repo root
        line: Line number in the diff
        commit_id: SHA of the latest commit on the PR head branch

    Returns:
        The created comment's GitHub ID

    Raises:
        GitHubAPIError: If posting fails
    """
    client = get_github_client()
    try:
        repo = client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        comment = pr.create_review_comment(body=body, commit_id=commit_id, path=path, line=line)
        return comment.id
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to post review comment on {repo_full_name}#{pr_number}: {e.data.get('message', str(e))}",
            status_code=e.status,
        )
    except RateLimitExceededException:
        logger.warning("GitHub API rate limit exceeded when posting comment")
        raise


def post_pr_comment(
    repo_full_name: str,
    pr_number: int,
    body: str,
) -> int:
    """
    Post a PR-level comment on the conversation timeline.

    Uses the Issues API endpoint (GitHub treats PR comments as issue comments).

    Args:
        repo_full_name: Repository full name
        pr_number: Pull request number
        body: Comment body (markdown)

    Returns:
        The created comment's GitHub ID

    Raises:
        GitHubAPIError: If posting fails
    """
    client = get_github_client()
    try:
        repo = client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        comment = pr.create_issue_comment(body)
        return comment.id
    except GithubException as e:
        raise GitHubAPIError(
            message=f"Failed to post PR comment on {repo_full_name}#{pr_number}: {e.data.get('message', str(e))}",
            status_code=e.status,
        )
    except RateLimitExceededException:
        logger.warning("GitHub API rate limit exceeded when posting PR comment")
        raise
