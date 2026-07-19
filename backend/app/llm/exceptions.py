class OpenRouterError(Exception):
    """Base exception for OpenRouter client errors."""
    pass

class OpenRouterRateLimitError(OpenRouterError):
    """Raised when the API rate limit is exceeded (HTTP 429)."""
    pass

class OpenRouterTimeoutError(OpenRouterError):
    """Raised when the API request times out."""
    pass

class OpenRouterValidationError(OpenRouterError):
    """Raised when the API response fails Pydantic validation."""
    pass

class OpenRouterAPIError(OpenRouterError):
    """Raised for general API errors (e.g., 5xx, invalid payload)."""
    def __init__(self, message: str, status_code: int, error_detail: str = ""):
        self.status_code = status_code
        self.error_detail = error_detail
        super().__init__(f"API Error {status_code}: {message} - {error_detail}")