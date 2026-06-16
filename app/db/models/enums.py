from enum import Enum
from sqlalchemy import Enum as SQLEnum


class PullRequestStatus(str, Enum):
    """Status of a pull request review."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class CommentCategory(str, Enum):
    """Category of a review comment."""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    SUGGESTION = "suggestion"


class CommentSeverity(str, Enum):
    """Severity level of a review comment."""
    BLOCKING = "blocking"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class FeedbackAction(str, Enum):
    """Action taken on a review comment."""
    DISMISSED = "dismissed"
    RESOLVED = "resolved"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"