from app.core.logging import get_logger
from app.github.client import get_pr_diff, get_pr_head_sha
from app.agent.state import ReviewState

logger = get_logger(__name__)


async def fetch_pr_diff(state: ReviewState) -> dict:
    repo = f"{state['github_owner']}/{state['github_repo']}"
    logger.info(f"Fetching diff and head SHA for {repo}#{state['github_pr_number']}")
    diff = get_pr_diff(repo, state["github_pr_number"])
    try:
        sha = get_pr_head_sha(repo, state["github_pr_number"])
    except Exception as e:
        logger.warning(f"Failed to fetch head commit SHA for {repo}#{state['github_pr_number']}: {e}. Defaulting to 'HEAD'")
        sha = "HEAD"
    return {"diff_raw": diff, "latest_commit_sha": sha}

