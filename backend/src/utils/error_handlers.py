"""
Custom Error Handlers

Prevents information disclosure via stack traces and detailed error messages.
Returns generic error messages to clients while logging details server-side.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions.

    SECURITY: In production, returns generic error messages to prevent
    information disclosure. Detailed errors are logged server-side.

    Args:
        request: The request that caused the exception
        exc: The HTTP exception

    Returns:
        JSON response with appropriate error message
    """
    # Log the error with full details
    logger.error(
        f"HTTP {exc.status_code} error: {exc.detail}. "
        f"Path: {request.url.path}, Method: {request.method}"
    )

    # In production, return generic messages for server errors
    if settings.app_env == "production" and exc.status_code >= 500:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "status_code": exc.status_code
            }
        )

    # Return the actual error message for client errors (4xx) and development
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.

    SECURITY: Sanitizes validation errors to prevent information disclosure
    while providing useful feedback to clients.

    Args:
        request: The request that caused the exception
        exc: The validation exception

    Returns:
        JSON response with validation errors
    """
    # Log validation errors
    logger.warning(
        f"Validation error on {request.url.path}: {exc.errors()}"
    )

    # In production, simplify error messages
    if settings.app_env == "production":
        # Return simplified validation errors
        simplified_errors = []
        for error in exc.errors():
            simplified_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"]
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": simplified_errors
            }
        )

    # In development, return full validation errors
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.

    SECURITY: Prevents stack trace exposure. Returns generic error message
    to client while logging full details server-side.

    Args:
        request: The request that caused the exception
        exc: The exception

    Returns:
        JSON response with generic error message
    """
    # Log the full exception with stack trace
    logger.exception(
        f"Unexpected error on {request.url.path}: {str(exc)}"
    )

    # SECURITY: Never expose internal error details in production
    if settings.app_env == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred. Please try again later.",
                "status_code": 500
            }
        )

    # In development, return more details (but not full stack trace)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Internal server error: {type(exc).__name__}",
            "message": str(exc),
            "status_code": 500
        }
    )
