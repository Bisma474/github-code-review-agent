class AppException(Exception):
    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class WebhookValidationError(AppException):
    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message=message, error_code="WEBHOOK_INVALID_SIGNATURE")


class GitHubAPIError(AppException):
    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message=message, error_code="GITHUB_API_ERROR")


class LLMError(AppException):
    def __init__(self, message: str, provider: str | None = None):
        self.provider = provider
        super().__init__(message=message, error_code="LLM_ERROR")


class ReviewError(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, error_code="REVIEW_ERROR")
