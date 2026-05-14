"""AI-Agent standalone service for FBR Invoice Automation."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from src.api.v1.automation import router as automation_router
from src.api.middleware.auth_middleware import AuthMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.middleware.csrf_middleware import CSRFMiddleware
from src.middleware.request_size_limit import RequestSizeLimitMiddleware
from src.middleware.session_timeout import SessionTimeoutMiddleware
from src.config.settings import settings
from src.utils.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from src.database.session import create_db_and_tables
from src.database.sync_enums import sync_enum_values
from src.services.scheduler import start_scheduler, stop_scheduler

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FBR AI Agent - Invoice Automation Service",
    description="Standalone AI-agent service for automated invoice processing, Excel upload, and dashboard",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

allowed_origins = settings.allowed_origins
if "*" in allowed_origins and len(allowed_origins) == 1:
    raise ValueError(
        "SECURITY ERROR: CORS cannot use wildcard '*' with allow_credentials=True."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    max_age=600,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)
app.add_middleware(SessionTimeoutMiddleware, timeout_minutes=30)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuthMiddleware)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    sync_enum_values()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


app.include_router(automation_router, prefix="/api/v1", tags=["automation"])


@app.get("/")
def read_root():
    return {"message": "FBR AI Agent - Invoice Automation Service", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fbr-ai-agent-automation"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info",
    )
