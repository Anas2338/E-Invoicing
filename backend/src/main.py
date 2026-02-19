from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import API routers
from src.api.v1.invoices import router as invoices_router
from src.api.v1.fbr_integration import router as fbr_integration_router
from src.api.v1.auth import router as auth_router
from src.api.v1.masterdata import router as masterdata_router
from src.api.v1.fbr_reference import router as fbr_reference_router
from src.api.v1.password_reset import router as password_reset_router

# Import middleware
from src.api.middleware.auth_middleware import AuthMiddleware

# Import configuration
from src.config.settings import settings

# Import database session
from src.database.session import create_db_and_tables

# Create FastAPI app instance
app = FastAPI(
    title="FBR Invoice Integration Portal API",
    description="Backend service for FBR invoice processing with validation and posting capabilities",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Startup event to create database tables
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Include API routers
app.include_router(invoices_router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(fbr_integration_router, prefix="/api/v1/fbr", tags=["fbr-integration"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(masterdata_router, prefix="/api/v1/masterdata", tags=["masterdata"])
app.include_router(fbr_reference_router, prefix="/api/v1/fbr-reference", tags=["fbr-reference"])
app.include_router(password_reset_router, prefix="/api/v1/password-reset", tags=["password-reset"])

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