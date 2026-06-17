import hashlib
import hmac
from typing import Optional

from app.core.exceptions import WebhookValidationError


def validate_webhook_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    secret: str,
) -> bool:
    """
    Validate a GitHub webhook payload signature using HMAC-SHA256.

    Args:
        payload_body: Raw request body as bytes
        signature_header: Value of the X-Hub-Signature-256 header
        secret: The webhook secret configured in GitHub

    Returns:
        True if the signature matches

    Raises:
        WebhookValidationError: If the signature header is missing or invalid
    """
    if not signature_header:
        raise WebhookValidationError("Missing X-Hub-Signature-256 header")

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    header_signature = signature_header

    if header_signature.startswith("sha256="):
        header_signature = header_signature[7:]

    if not hmac.compare_digest(expected_signature, header_signature):
        return False

    return True
