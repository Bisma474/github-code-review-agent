import uuid
from app.db.session import get_async_session
from app.db.crud.feedback import create_feedback as create_feedback_crud
from app.core.logging import get_logger

logger = get_logger(__name__)


async def store_feedback(
    review_id: str,
    rating: int,
    comment_id: str | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    if rating < 1 or rating > 5:
        return {"success": False, "error": "rating must be between 1 and 5"}

    async with get_async_session() as session:
        fb = await create_feedback_crud(
            session,
            review_id=uuid.UUID(review_id),
            comment_id=uuid.UUID(comment_id) if comment_id else None,
            rating=rating,
            category=category,
            notes=notes,
        )

    logger.info(f"Feedback {fb.id} stored for review {review_id}")
    return {"success": True, "feedback_id": str(fb.id), "rating": rating}
