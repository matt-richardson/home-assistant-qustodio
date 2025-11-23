"""Exceptions for Qustodio integration."""


class QustodioException(Exception):
    """Base exception for Qustodio integration."""


class QustodioAuthenticationError(QustodioException):
    """Exception raised when authentication fails due to invalid credentials."""


class QustodioTokenExpiredError(QustodioException):
    """Exception raised when the access token has expired."""


class QustodioConnectionError(QustodioException):
    """Exception raised when connection to Qustodio API fails."""


class QustodioRateLimitError(QustodioException):
    """Exception raised when API rate limit is exceeded."""


class QustodioAPIError(QustodioException):
    """Exception raised when API returns an unexpected error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code


class QustodioDataError(QustodioException):
    """Exception raised when data returned by API is invalid or incomplete."""
