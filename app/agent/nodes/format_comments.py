from app.core.logging import get_logger
from app.agent.state import ReviewState

logger = get_logger(__name__)


def format_comments(state: ReviewState) -> dict:
    formatted = []
    for file_analysis in state["llm_analysis"]:
        file_path = file_analysis["file"]
        for comment in file_analysis["comments"]:
            formatted.append({
                "path": file_path,
                "line": comment.get("line", 1),
                "body": f"[{comment.get('severity', 'warning').upper()}] {comment['message']}",
                "severity": comment.get("severity", "warning"),
            })
    logger.info(f"Formatted {len(formatted)} review comments")
    return {"formatted_comments": formatted}
