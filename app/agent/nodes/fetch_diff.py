from app.core.logging import get_logger
from app.github.client import get_github_client
from app.agent.state import ReviewState

logger = get_logger(__name__)


async def fetch_pr_diff(state: ReviewState) -> dict:
    logger.info(f"Fetching diff for {state['github_owner']}/{state['github_repo']}#{state['github_pr_number']}")
    client = get_github_client()
    diff = client.get_pr_diff(state["github_owner"], state["github_repo"], state["github_pr_number"])
    return {"diff_raw": diff}
