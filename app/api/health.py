from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    status = "ok"
    db_status = "ok"

    try:
        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = "error"
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "db": db_status,
    }
