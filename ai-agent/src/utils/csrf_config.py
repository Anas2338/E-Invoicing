"""CSRF configuration for AI-agent."""

from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel
import secrets


class CsrfSettings(BaseModel):
    secret_key: str = secrets.token_urlsafe(32)
    cookie_name: str = "csrf_token"
    header_name: str = "X-CSRF-Token"
    cookie_samesite: str = "lax"
    cookie_secure: bool = True
    cookie_httponly: bool = False
    cookie_domain: str = None


csrf_settings = CsrfSettings()


@CsrfProtect.load_config
def get_csrf_config():
    return csrf_settings


CSRF_EXEMPT_PATHS = {
    "/api/v1/automation/health",
    "/api/v1/automation/agent/status",
    "/api/v1/docs",
    "/api/v1/openapi.json",
    "/health",
    "/",
}


def is_csrf_exempt(path: str) -> bool:
    return path in CSRF_EXEMPT_PATHS or path.startswith("/api/v1/docs") or path.startswith("/api/v1/openapi")
