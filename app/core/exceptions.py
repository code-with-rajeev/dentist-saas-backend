# Standard library
from typing import Any


class AppException(Exception):
    """
    Base class for all custom application exceptions.
    All custom exceptions must inherit from this class.

    Usage:
        raise NotFoundException(
            code=PATIENT_NOT_FOUND,
            message="Patient not found"
        )
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        detail: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.detail = detail
        super().__init__(message)


class AuthException(AppException):
    """401 family — authentication failures."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=401,
            detail=detail,
        )


class ForbiddenException(AppException):
    """403 family — authorization failures."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=403,
            detail=detail,
        )


class NotFoundException(AppException):
    """404 family — resource not found."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=404,
            detail=detail,
        )


class ConflictException(AppException):
    """409 family — duplicate resource / conflict."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=409,
            detail=detail,
        )


class ValidationException(AppException):
    """400 family — business rule violations, invalid input."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=400,
            detail=detail,
        )


class ServerException(AppException):
    """500 family — unhandled server errors."""

    def __init__(
        self,
        code: str = "INTERNAL_SERVER_ERROR",
        message: str = "Something went wrong, please try again",
        detail: Any = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=500,
            detail=detail,
        )
