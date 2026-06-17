from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GitHub Code Review Agent",
        version="1.0.0",
        description="Autonomous AI-powered code review agent for GitHub pull requests",
    )

    @app.on_event("startup")
    async def startup():
        logger.info("Starting GitHub Code Review Agent")
        from app.db.session import engine
        logger.info(f"Database engine created: {settings.DATABASE_URL}")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Shutting down GitHub Code Review Agent")
        from app.db.session import engine
        await engine.dispose()
        logger.info("Database engine disposed")

    from app.api.health import router as health_router
    app.include_router(health_router)

    return app
