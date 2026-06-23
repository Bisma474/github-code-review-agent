from typing import Optional
from app.rag.repository import get_pattern_repo, PatternRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


def retrieve_similar_patterns(
    code_snippet: str,
    n_results: int = 5,
    repo: Optional[PatternRepository] = None,
) -> list[dict]:
    repo = repo or get_pattern_repo()
    results = repo.search_similar(code_snippet, n_results=n_results)
    logger.debug(f"Retrieved {len(results)} similar patterns")
    return results
