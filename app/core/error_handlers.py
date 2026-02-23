# Standard library
import logging

# Third-party
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Internal — core
from app.core.config import settings
from app.core.exceptions import AppException
from app.constants.messages import INTERNAL_SERVER_ERROR, VALIDATION_ERROR

logger = logging.getLogger(__name__)


def _error_response(
    code: str,
    message: str,
    http_status: int,
    detail=None,
) -> JSONResponse:
    """
    Build a standard error response envelope.
    detail is only included in development mode.
    """
    return JSONResponse(
        status_code=http_status,
        content={
            "success": False,
            "message": message,
            "error": {
                "code": code,
                "detail": detail if settings.is_development else None,
            },
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom AppException subclasses."""
    logger.warning(
        "AppException: code=%s status=%s path=%s",
        exc.code,
        exc.http_status,
        request.url.path,
    )
    return _error_response(
        code=exc.code,
        message=exc.message,
        http_status=exc.http_status,
        detail=exc.detail,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors — return field-level detail."""
    field_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        field_errors.append({"field": field, "message": error["msg"]})

    logger.warning("ValidationError: path=%s errors=%s", request.url.path, field_errors)
    return _error_response(
        code=VALIDATION_ERROR,
        message="Invalid request data",
        http_status=422,
        detail=field_errors,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Pass through Starlette HTTPExceptions wrapped in standard envelope."""
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"

    return _error_response(
        code=code,
        message=str(exc.detail),
        http_status=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any unhandled exception — log full traceback, return 500."""
    logger.exception(
        "Unhandled exception: path=%s method=%s",
        request.url.path,
        request.method,
    )
    return _error_response(
        code=INTERNAL_SERVER_ERROR,
        message="Something went wrong, please try again",
        http_status=500,
        detail=str(exc) if settings.is_development else None,
    )
