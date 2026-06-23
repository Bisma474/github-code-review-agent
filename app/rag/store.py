import uuid
from typing import Optional
from app.rag.repository import get_pattern_repo, PatternRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


def store_review_feedback(
    file_path: str,
    code_snippet: str,
    issue_type: str,
    severity: str,
    message: str,
    suggestion: str,
    repo_full_name: str,
    repo: Optional[PatternRepository] = None,
):
    repo = repo or get_pattern_repo()
    pattern_id = str(uuid.uuid4())
    repo.add_pattern(
        pattern_id=pattern_id,
        code_snippet=code_snippet,
        issue_type=issue_type,
        severity=severity,
        message=message,
        suggestion=suggestion,
        repo_full_name=repo_full_name,
        file_path=file_path,
    )
    logger.info(f"Stored pattern {pattern_id} for {file_path} in {repo_full_name}")
    return pattern_id
