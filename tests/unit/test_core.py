"""Tests for app/core/ — config, exceptions, logging."""

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppException,
    GitHubAPIError,
    WebhookValidationError,
    LLMError,
    ReviewError,
)
from app.core.logging import get_logger, ColorFormatter, JsonFormatter


class TestConfig:
    def test_settings_loads_defaults(self):
        s = Settings()
        assert s.GITHUB_TOKEN == "ghp_test"

    def test_get_settings_is_cached(self):
        assert get_settings() is get_settings()


class TestExceptions:
    def test_app_exception(self):
        e = AppException("msg", error_code="ERR")
        assert str(e) == "msg"
        assert e.error_code == "ERR"

    def test_webhook_validation_defaults(self):
        e = WebhookValidationError()
        assert "signature" in e.message

    def test_github_api_error_with_status(self):
        e = GitHubAPIError("API down", status_code=500)
        assert e.status_code == 500

    def test_llm_error_with_provider(self):
        e = LLMError("timeout", provider="ollama")
        assert e.provider == "ollama"

    def test_review_error(self):
        e = ReviewError("failed")
        assert "REVIEW_ERROR" in e.error_code

    def test_inheritance(self):
        assert issubclass(GitHubAPIError, AppException)
        assert issubclass(WebhookValidationError, AppException)
        assert issubclass(LLMError, AppException)
        assert issubclass(ReviewError, AppException)


class TestLogging:
    def test_get_logger(self):
        log = get_logger("test")
        assert log.name == "test"

    def test_color_formatter(self):
        fmt = ColorFormatter("%(message)s")
        record = logging.LogRecord("n", logging.INFO, "p", 1, "hello", (), None)
        out = fmt.format(record)
        assert out is not None

    def test_json_formatter(self):
        fmt = JsonFormatter()
        record = logging.LogRecord("n", logging.WARNING, "p", 1, "hi", (), None)
        out = fmt.format(record)
        assert '"message": "hi"' in out
        assert '"level": "WARNING"' in out


import logging
