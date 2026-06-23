import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force test database before any imports
os.environ.setdefault("GITHUB_TOKEN", "ghp_test")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test_secret")
os.environ.setdefault("APP_SECRET_KEY", "test_app_key")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./.pytest_test.db",
)

# Force Celery eager mode for tests
os.environ["CELERY_ALWAYS_EAGER"] = "true"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Clean up any leftover test database file from previous runs
try:
    Path(".pytest_test.db").unlink(missing_ok=True)
except Exception:
    pass



# ---------------------------------------------------------------------------
# Session-level event loop for all async fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database fixtures (session-scoped to share engine)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create tables once per session."""
    from app.db.session import engine, create_tables

    await create_tables()
    yield engine


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Fresh session per test."""
    from app.db.session import get_async_session

    async with get_async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_engine):
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Mock GitHub client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_github():
    with patch("app.github.client.Github") as mock_cls:
        gh = MagicMock()
        mock_cls.return_value = gh
        repo = MagicMock()
        pull = MagicMock()
        gh.get_repo.return_value = repo
        repo.get_pull.return_value = pull
        pull.get_files.return_value = []
        pull.create_review_comment.return_value = MagicMock(id=123)
        pull.create_issue_comment.return_value = MagicMock(id=456)
        yield gh


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_invoke():
    """Patch llm_invoke to return controlled JSON."""
    from app.agent.llm import LLMResponse

    async def fake(*args, **kwargs):
        return LLMResponse(
            content='[{"file":"test.py","comments":[{"severity":"warning","line":1,"message":"test"}]}]',
            model="test-model",
            tokens_used=10,
        )

    with patch("app.agent.llm.llm_invoke", side_effect=fake):
        yield


# ---------------------------------------------------------------------------
# Mock ChromaDB
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_chroma():
    mock_collection = MagicMock()
    mock_collection.name = "test-patterns"
    mock_collection.count.return_value = 3
    mock_collection.add.return_value = None
    mock_collection.query.return_value = {
        "ids": [["pat1"]],
        "distances": [[0.15]],
        "metadatas": [[{"issue_type": "bug", "severity": "error"}]],
        "documents": [["def foo(): pass"]],
    }
    mock_collection.delete.return_value = None

    with patch("app.rag.chroma.get_chroma_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.heartbeat.return_value = 1
        client.get_collection.return_value = mock_collection
        client.create_collection.return_value = mock_collection
        yield mock_collection
