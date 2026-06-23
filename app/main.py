from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GitHub Code Review Agent")
    from app.db.session import engine, create_tables
    logger.info(f"Database engine created: {settings.DATABASE_URL}")
    await create_tables()
    yield
    logger.info("Shutting down GitHub Code Review Agent")
    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GitHub Code Review Agent",
        version="1.0.0",
        description="Autonomous AI-powered code review agent for GitHub pull requests",
        lifespan=lifespan,
    )

    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.health import router as health_router
    app.include_router(health_router)

    from app.api.webhook import router as webhook_router
    app.include_router(webhook_router)

    from app.api.feedback import router as feedback_router
    app.include_router(feedback_router)

    from app.api.repos import router as repos_router
    app.include_router(repos_router)

    return app


app = create_app()
