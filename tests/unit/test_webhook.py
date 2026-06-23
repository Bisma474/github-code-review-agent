"""Tests for GitHub webhook signature validation."""

import hmac
import hashlib

import pytest

from app.github.webhook import validate_webhook_signature


class TestWebhookSignature:
    def test_valid_signature(self):
        secret = "mysecret"
        body = b'{"action":"opened"}'
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert validate_webhook_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        secret = "mysecret"
        body = b'{"action":"opened"}'
        assert validate_webhook_signature(body, "sha256=bad", secret) is False

    def test_bad_signing_secret(self):
        secret = "mysecret"
        body = b'{"action":"opened"}'
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert validate_webhook_signature(body, sig, "wrongsecret") is False

    def test_missing_header_raises(self):
        from app.core.exceptions import WebhookValidationError
        with pytest.raises(WebhookValidationError, match="Missing"):
            validate_webhook_signature(b"body", None, "secret")

    def test_empty_secret(self):
        body = b"test"
        sig = "sha256=" + hmac.new(b"", body, hashlib.sha256).hexdigest()
        assert validate_webhook_signature(body, sig, "") is True
