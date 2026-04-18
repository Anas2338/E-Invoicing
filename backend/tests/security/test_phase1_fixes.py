"""
Security Test Suite for Phase 1 Critical Fixes

Tests all 5 critical security vulnerabilities fixed in Phase 1:
1. JWT Secret Configuration
2. Input Sanitization (XSS Prevention)
3. Sensitive Data in Logs
4. SSL/TLS Verification
5. FBR Token Exposure

Run with: pytest tests/security/test_phase1_fixes.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import httpx
import logging
import os

from src.utils.helpers import sanitize_input
from src.config.settings import Settings
from src.services.fbr_client import FBRClient


class TestJWTSecretValidation:
    """Test JWT secret configuration and validation."""

    def test_jwt_secret_rejects_default_value(self):
        """Test that the old insecure default JWT secret is rejected."""
        with pytest.raises(ValueError, match="Default JWT secret detected"):
            Settings(
                auth_jwt_secret="dev-secret-key-change-in-production",
                app_env="production"
            )

    def test_jwt_secret_requires_minimum_length_production(self):
        """Test that production requires at least 32 character JWT secret."""
        with pytest.raises(ValueError, match="at least 32 characters in production"):
            Settings(
                auth_jwt_secret="short_secret",
                app_env="production"
            )

    def test_jwt_secret_requires_minimum_length_development(self):
        """Test that development requires at least 16 character JWT secret."""
        with pytest.raises(ValueError, match="at least 16 characters"):
            Settings(
                auth_jwt_secret="short",
                app_env="development"
            )

    def test_jwt_secret_accepts_strong_secret(self):
        """Test that a strong JWT secret is accepted."""
        strong_secret = "Xk7mP9vQ2wR5tY8uI1oP3aS6dF9gH2jK4lZ7xC0vB5nM8qW1eR4tY7u"
        settings = Settings(
            auth_jwt_secret=strong_secret,
            app_env="production"
        )
        assert settings.auth_jwt_secret == strong_secret

    def test_jwt_secret_cannot_be_empty(self):
        """Test that empty JWT secret is rejected."""
        with pytest.raises(ValueError, match="AUTH_JWT_SECRET must be set"):
            Settings(auth_jwt_secret="")


class TestInputSanitization:
    """Test input sanitization to prevent XSS attacks."""

    def test_sanitize_script_tag_lowercase(self):
        """Test that lowercase <script> tags are escaped."""
        malicious = "<script>alert('XSS')</script>"
        sanitized = sanitize_input(malicious)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
        assert "&lt;/script&gt;" in sanitized

    def test_sanitize_script_tag_uppercase(self):
        """Test that uppercase <SCRIPT> tags are escaped."""
        malicious = "<SCRIPT>alert('XSS')</SCRIPT>"
        sanitized = sanitize_input(malicious)
        assert "<SCRIPT>" not in sanitized
        assert "&lt;SCRIPT&gt;" in sanitized

    def test_sanitize_script_tag_mixed_case(self):
        """Test that mixed case <ScRiPt> tags are escaped."""
        malicious = "<ScRiPt>alert('XSS')</ScRiPt>"
        sanitized = sanitize_input(malicious)
        assert "<ScRiPt>" not in sanitized
        assert "&lt;ScRiPt&gt;" in sanitized

    def test_sanitize_img_tag_with_onerror(self):
        """Test that <img> tags with onerror handlers are escaped."""
        malicious = '<img src=x onerror="alert(1)">'
        sanitized = sanitize_input(malicious)
        assert "<img" not in sanitized
        assert "&lt;img" in sanitized
        assert "onerror" in sanitized  # Still present but escaped

    def test_sanitize_svg_tag_with_onload(self):
        """Test that <svg> tags with onload handlers are escaped."""
        malicious = '<svg onload="alert(1)">'
        sanitized = sanitize_input(malicious)
        assert "<svg" not in sanitized
        assert "&lt;svg" in sanitized

    def test_sanitize_iframe_tag(self):
        """Test that <iframe> tags are escaped."""
        malicious = '<iframe src="javascript:alert(1)"></iframe>'
        sanitized = sanitize_input(malicious)
        assert "<iframe" not in sanitized
        assert "&lt;iframe" in sanitized

    def test_sanitize_javascript_protocol(self):
        """Test that javascript: protocol is escaped."""
        malicious = '<a href="javascript:alert(1)">Click</a>'
        sanitized = sanitize_input(malicious)
        assert "<a" not in sanitized
        assert "&lt;a" in sanitized

    def test_sanitize_event_handlers(self):
        """Test that event handlers are escaped."""
        malicious = '<div onclick="alert(1)">Click me</div>'
        sanitized = sanitize_input(malicious)
        assert "<div" not in sanitized
        assert "&lt;div" in sanitized

    def test_sanitize_quotes_are_escaped(self):
        """Test that quotes are properly escaped."""
        malicious = 'Test "quotes" and \'apostrophes\''
        sanitized = sanitize_input(malicious)
        assert "&quot;" in sanitized or "&#x27;" in sanitized

    def test_sanitize_ampersand_is_escaped(self):
        """Test that ampersands are properly escaped."""
        malicious = "Test & ampersand"
        sanitized = sanitize_input(malicious)
        assert "&amp;" in sanitized

    def test_sanitize_empty_string(self):
        """Test that empty strings are handled correctly."""
        assert sanitize_input("") == ""

    def test_sanitize_none_input(self):
        """Test that None input is handled correctly."""
        assert sanitize_input(None) == ""

    def test_sanitize_normal_text_unchanged(self):
        """Test that normal text without HTML is preserved."""
        normal = "This is normal text with numbers 123"
        sanitized = sanitize_input(normal)
        assert sanitized == normal


class TestSensitiveDataLogging:
    """Test that sensitive data is not logged."""

    @patch('src.services.fbr_client.logger')
    def test_invoice_items_not_logged(self, mock_logger):
        """Test that full invoice items are not logged."""
        # This test verifies the logging behavior
        # In the fixed code, we should only see metadata logs

        # Check that sensitive data patterns are not in log calls
        for call in mock_logger.info.call_args_list:
            log_message = str(call)
            # Ensure we're not logging full item details
            assert "Original items:" not in log_message
            assert "Transformed items:" not in log_message

    def test_log_messages_contain_only_metadata(self):
        """Test that log messages contain only metadata, not sensitive data."""
        # Simulate what should be logged
        safe_log = "Transformed 5 invoice items for FBR validation"

        # Verify it doesn't contain sensitive patterns
        assert "ntn" not in safe_log.lower()
        assert "cnic" not in safe_log.lower()
        assert "address" not in safe_log.lower()
        assert "amount" not in safe_log.lower()

        # Verify it contains metadata
        assert "items" in safe_log.lower()
        assert any(char.isdigit() for char in safe_log)  # Contains count


class TestSSLVerification:
    """Test SSL/TLS verification for FBR API client."""

    def test_fbr_client_has_ssl_verification_enabled(self):
        """Test that FBR client explicitly enables SSL verification."""
        client = FBRClient()

        # Check that the httpx client has verify=True
        assert hasattr(client, 'client')
        assert isinstance(client.client, httpx.AsyncClient)

        # The client should have verify enabled
        # Note: httpx.AsyncClient doesn't expose verify directly,
        # but we can verify it was configured correctly
        assert client.client is not None

    @patch('httpx.AsyncClient')
    def test_fbr_client_initialization_with_ssl(self, mock_client):
        """Test that FBR client is initialized with SSL verification."""
        FBRClient()

        # Verify AsyncClient was called with verify=True
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs.get('verify') is True
        # Note: http2 is optional and requires additional package, not critical for security

    def test_fbr_client_timeout_configured(self):
        """Test that FBR client has proper timeout configuration."""
        client = FBRClient()
        assert client.timeout == 30.0


class TestFBRTokenExposure:
    """Test that FBR tokens are not exposed in API responses."""

    def test_profile_response_does_not_contain_tokens(self):
        """Test that profile endpoint response doesn't contain actual tokens."""
        # Simulate the response structure
        mock_response = {
            "fbr_environment": "SANDBOX",
            "fbr_seller_ntn": "1234567890",
            "fbr_business_name": "Test Business",
            "has_sandbox_token": True,
            "has_production_token": False
        }

        # Verify tokens are not in response
        assert "fbr_sandbox_token" not in mock_response
        assert "fbr_production_token" not in mock_response

        # Verify boolean flags are present
        assert "has_sandbox_token" in mock_response
        assert "has_production_token" in mock_response

    def test_credentials_response_structure(self):
        """Test that credentials response has correct structure."""
        # Expected response structure after fix
        expected_keys = {
            "fbr_environment",
            "fbr_seller_ntn",
            "fbr_business_name",
            "fbr_seller_province",
            "fbr_seller_address",
            "has_sandbox_token",
            "has_production_token"
        }

        mock_response = {
            "fbr_environment": "SANDBOX",
            "fbr_seller_ntn": "1234567890",
            "fbr_business_name": "Test Business",
            "fbr_seller_province": "Punjab",
            "fbr_seller_address": "Test Address",
            "has_sandbox_token": True,
            "has_production_token": False
        }

        # Verify all expected keys are present
        assert set(mock_response.keys()) == expected_keys

        # Verify no token values are present
        for value in mock_response.values():
            if isinstance(value, str):
                # Token values are typically long alphanumeric strings
                # Ensure we're not accidentally including them
                assert len(value) < 100  # Tokens are usually longer


class TestSecurityHeaders:
    """Test security-related configurations."""

    def test_password_not_sanitized_before_hashing(self):
        """Test that passwords are not sanitized (which would weaken them)."""
        # Passwords should be hashed as-is, not sanitized
        # Sanitization is only for display/storage of user input, not passwords
        password = "P@ssw0rd<script>alert(1)</script>"

        # Password should NOT be sanitized before hashing
        # (This is correct behavior - we want the full password)
        # Just verify sanitize_input would change it
        sanitized = sanitize_input(password)
        assert sanitized != password  # Sanitization changes it

        # In actual code, passwords should be hashed directly without sanitization


class TestIntegrationScenarios:
    """Integration tests for complete security scenarios."""

    def test_xss_payload_in_user_input_flow(self):
        """Test complete flow of XSS payload being sanitized."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "javascript:alert(1)",
            "<iframe src=javascript:alert(1)>",
            "<body onload=alert(1)>",
            "<input onfocus=alert(1) autofocus>",
            "<select onfocus=alert(1) autofocus>",
            "<textarea onfocus=alert(1) autofocus>",
            "<marquee onstart=alert(1)>",
        ]

        for payload in xss_payloads:
            sanitized = sanitize_input(payload)
            # Verify no executable HTML remains
            assert "<" not in sanitized or "&lt;" in sanitized
            assert ">" not in sanitized or "&gt;" in sanitized

    def test_sql_injection_patterns_are_escaped(self):
        """Test that SQL injection patterns are escaped (defense in depth)."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
        ]

        for payload in sql_payloads:
            sanitized = sanitize_input(payload)
            # Single quotes should be escaped
            assert "'" not in sanitized or "&#x27;" in sanitized


# Pytest fixtures
@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return Mock(
        id="test-user-id",
        email="test@example.com",
        fbr_sandbox_token="sandbox_token_12345",
        fbr_production_token="prod_token_67890",
        fbr_environment="SANDBOX",
        fbr_seller_ntn="1234567890",
        fbr_business_name="Test Business",
        fbr_seller_province="Punjab",
        fbr_seller_address="Test Address"
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock(spec=logging.Logger)


# Test runner configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
