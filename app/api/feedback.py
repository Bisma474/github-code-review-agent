from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.db.crud.feedback import (
    create_feedback as create_feedback_crud,
    get_feedback_by_review_id,
)

logger = get_logger(__name__)
router = APIRouter()


class FeedbackCreate(BaseModel):
    review_id: str
    comment_id: str | None = None
    rating: int
    category: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    review_id: str
    rating: int
    category: str | None = None
    notes: str | None = None


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackCreate):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Rating must be 1-5")

    import uuid
    async with get_async_session() as session:
        fb = await create_feedback_crud(
            session,
            review_id=uuid.UUID(body.review_id),
            comment_id=uuid.UUID(body.comment_id) if body.comment_id else None,
            rating=body.rating,
            category=body.category,
            notes=body.notes,
        )

    return FeedbackResponse(id=str(fb.id), review_id=str(fb.review_id), rating=fb.rating, category=fb.category, notes=fb.notes)


@router.get("/feedback/{review_id}", response_model=list[FeedbackResponse])
async def get_feedback(review_id: str):
    import uuid
    async with get_async_session() as session:
        items = await get_feedback_by_review_id(session, uuid.UUID(review_id))
    return [
        FeedbackResponse(id=str(fb.id), review_id=str(fb.review_id), rating=fb.rating, category=fb.category, notes=fb.notes)
        for fb in items
    ]
