"""
Security Headers Middleware

Adds security-related HTTP headers to all responses to protect against
common web vulnerabilities:
- Clickjacking (X-Frame-Options)
- MIME sniffing (X-Content-Type-Options)
- XSS attacks (X-XSS-Protection, Content-Security-Policy)
- Man-in-the-middle attacks (Strict-Transport-Security)
- Information leakage (Referrer-Policy)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add security headers to the response.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Prevent clickjacking attacks
        # DENY: Page cannot be displayed in a frame, regardless of the site attempting to do so
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        # Browsers should not try to guess the MIME type, reducing exposure to drive-by download attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection in older browsers
        # Modern browsers use CSP instead, but this provides defense-in-depth
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS (HTTP Strict Transport Security)
        # Tells browsers to only access this site over HTTPS for the next year
        # includeSubDomains: Apply to all subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        # Restricts sources from which content can be loaded
        # This is a strict policy that only allows resources from the same origin
        csp_directives = [
            "default-src 'self'",  # Only allow resources from same origin by default
            "script-src 'self'",  # Only allow scripts from same origin
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles (needed for some frameworks)
            "img-src 'self' data: https:",  # Allow images from same origin, data URIs, and HTTPS
            "font-src 'self'",  # Only allow fonts from same origin
            "connect-src 'self'",  # Only allow AJAX/WebSocket connections to same origin
            "frame-ancestors 'none'",  # Don't allow this page to be framed (redundant with X-Frame-Options)
            "base-uri 'self'",  # Restrict base tag URLs
            "form-action 'self'",  # Only allow form submissions to same origin
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer Policy
        # Control how much referrer information is sent with requests
        # strict-origin-when-cross-origin: Send full URL for same-origin, only origin for cross-origin HTTPS
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        # Disable potentially dangerous browser features
        permissions_directives = [
            "geolocation=()",  # Disable geolocation
            "microphone=()",  # Disable microphone
            "camera=()",  # Disable camera
            "payment=()",  # Disable payment API
            "usb=()",  # Disable USB API
            "magnetometer=()",  # Disable magnetometer
            "gyroscope=()",  # Disable gyroscope
            "accelerometer=()",  # Disable accelerometer
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        return response
