"""Custom error handlers for AI-agent. All responses include CORS headers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


def _cors_response(status_code: int, content: dict, request: Request) -> JSONResponse:
    """Return a JSONResponse with CORS headers matching CORSMiddleware."""
    origin = request.headers.get("origin", "")
    allowed_origins = settings.allowed_origins
    headers = {}
    if origin in allowed_origins or "*" in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin if origin in allowed_origins else "*"
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(
        f"HTTP {exc.status_code} error: {exc.detail}. "
        f"Path: {request.url.path}, Method: {request.method}"
    )
    if settings.app_env == "production" and exc.status_code >= 500:
        return _cors_response(
            exc.status_code,
            {"detail": "An internal server error occurred.", "status_code": exc.status_code},
            request,
        )
    return _cors_response(
        exc.status_code,
        {"detail": exc.detail, "status_code": exc.status_code},
        request,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    if settings.app_env == "production":
        simplified_errors = []
        for error in exc.errors():
            simplified_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
            })
        return _cors_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"detail": "Validation error", "errors": simplified_errors},
            request,
        )
    return _cors_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        {"detail": exc.errors()},
        request,
    )


async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unexpected error on {request.url.path}: {str(exc)}")
    if settings.app_env == "production":
        return _cors_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"detail": "An unexpected error occurred.", "status_code": 500},
            request,
        )
    return _cors_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        {
            "detail": f"Internal server error: {type(exc).__name__}",
            "message": str(exc),
            "status_code": 500,
        },
        request,
    )
