from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

# Import API routers
from src.api.v1.invoices import router as invoices_router
from src.api.v1.fbr_integration import router as fbr_integration_router
from src.api.v1.auth import router as auth_router
from src.api.v1.masterdata import router as masterdata_router
from src.api.v1.fbr_reference import router as fbr_reference_router
from src.api.v1.admin_users import router as admin_users_router
from src.api.v1.admin_sync import router as admin_sync_router
from src.api.v1.notifications import router as notifications_router
from src.api.v1.saved_products import router as saved_products_router
from src.api.v1.user_profile import router as user_profile_router
from src.api.v1.dashboard import router as dashboard_router

# Import middleware
from src.api.middleware.auth_middleware import AuthMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.middleware.csrf_middleware import CSRFMiddleware
from src.middleware.request_size_limit import RequestSizeLimitMiddleware
from src.middleware.session_timeout import SessionTimeoutMiddleware

# Import configuration
from src.config.settings import settings

# Import custom error handlers
from src.utils.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

# Import database session
from src.database.session import create_db_and_tables

# Import scheduler
from src.services.scheduler import start_scheduler, stop_scheduler

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app instance
app = FastAPI(
    title="FBR Invoice Integration Portal API",
    description="Backend service for FBR invoice processing with validation and posting capabilities",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# SECURITY: Add custom error handlers to prevent information disclosure
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add CORS middleware with security validation
# SECURITY: Validate allowed origins and prevent wildcard with credentials
allowed_origins = settings.allowed_origins

# CRITICAL SECURITY CHECK: Never allow "*" with credentials
if "*" in allowed_origins and len(allowed_origins) == 1:
    raise ValueError(
        "SECURITY ERROR: CORS cannot use wildcard '*' with allow_credentials=True. "
        "This creates a critical security vulnerability. "
        "Set ALLOWED_ORIGINS to specific domains in .env file."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],  # Explicit headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add request size limit middleware (10MB max)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)

# Add session timeout middleware (30 minutes of inactivity)
app.add_middleware(SessionTimeoutMiddleware, timeout_minutes=30)

# Add CSRF protection middleware
app.add_middleware(CSRFMiddleware)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Startup event to create database tables and start scheduler
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    start_scheduler()

# Shutdown event to stop scheduler
@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()

# Include API routers
app.include_router(invoices_router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(fbr_integration_router, prefix="/api/v1/fbr", tags=["fbr-integration"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(masterdata_router, prefix="/api/v1/masterdata", tags=["masterdata"])
app.include_router(fbr_reference_router, prefix="/api/v1/fbr-reference", tags=["fbr-reference"])
app.include_router(admin_users_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(admin_sync_router, prefix="/api/v1/admin", tags=["admin-sync"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(saved_products_router, prefix="/api/v1/profile", tags=["saved-products"])
app.include_router(user_profile_router, prefix="/api/v1", tags=["user-profile"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])

@app.get("/")
def read_root():
    return {"message": "FBR Invoice Integration Portal Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fbr-invoice-portal-backend"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )