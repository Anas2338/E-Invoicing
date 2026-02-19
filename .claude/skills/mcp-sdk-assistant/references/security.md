# Security Best Practices for MCP SDK

This reference covers security considerations and best practices when implementing MCP servers and clients.

## Authentication and Authorization

### Transport-Level Security
```python
from mcp.server.tcp import tcp_server
import ssl

class SecureMCPServer:
    def __init__(self, server, certfile: str, keyfile: str):
        self.server = server
        self.certfile = certfile
        self.keyfile = keyfile

    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for secure connections"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False  # In production, validate hostnames
        return context

    def run_secure_tcp_server(self, host: str = "localhost", port: int = 8080):
        """Run TCP server with SSL encryption"""
        context = self.create_ssl_context()

        with tcp_server(self.server, host=host, port=port, ssl_context=context):
            self.server.run()
```

### API Key Authentication
```python
from mcp.server import Server
import jwt
import time
from typing import Optional

class AuthenticatedMCPServer:
    def __init__(self, server: Server, secret_key: str):
        self.server = server
        self.secret_key = secret_key

    def authenticate_request(self, token: str) -> Optional[dict]:
        """Authenticate request using JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except jwt.InvalidTokenError:
            return None

    def require_auth(self, tool):
        """Decorator to require authentication for tools"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(params):
                # Extract token from params or headers
                token = params.get("auth_token")
                if not token:
                    return {"error": "Authentication required"}

                user_info = self.authenticate_request(token)
                if not user_info:
                    return {"error": "Invalid or expired token"}

                # Add user info to parameters
                params["user_info"] = user_info

                # Call original function
                return func(params)
            return wrapper
        return decorator

# Usage example
# server = Server("secure-server")
# auth_server = AuthenticatedMCPServer(server, "your-secret-key")

# @auth_server.require_auth(
#     Tool(
#         name="secure_operation",
#         description="An operation requiring authentication",
#         inputSchema={"type": "object", "properties": {"data": {"type": "string"}}}
#     )
# )
# def secure_operation_handler(params):
#     user_info = params["user_info"]
#     data = params["data"]
#     return {"message": f"Hello {user_info['user_id']}", "processed": data}
```

## Input Validation and Sanitization

### Parameter Validation
```python
from typing import Dict, Any, Union
import re

class InputValidator:
    @staticmethod
    def validate_string_param(value: Any, max_length: int = 1000, pattern: str = None) -> str:
        """Validate string parameter"""
        if not isinstance(value, str):
            raise ValueError("Expected string parameter")

        if len(value) > max_length:
            raise ValueError(f"String too long, max {max_length} characters")

        if pattern and not re.match(pattern, value):
            raise ValueError(f"String does not match required pattern: {pattern}")

        return value

    @staticmethod
    def validate_int_param(value: Any, min_val: int = None, max_val: int = None) -> int:
        """Validate integer parameter"""
        if not isinstance(value, int):
            raise ValueError("Expected integer parameter")

        if min_val is not None and value < min_val:
            raise ValueError(f"Value too small, minimum {min_val}")

        if max_val is not None and value > max_val:
            raise ValueError(f"Value too large, maximum {max_val}")

        return value

    @staticmethod
    def validate_safe_path(path: str, base_dir: str) -> str:
        """Validate path to prevent directory traversal"""
        import os
        from pathlib import Path

        # Normalize the path
        safe_path = Path(path).resolve()
        base_path = Path(base_dir).resolve()

        # Check that the safe path is within the base directory
        if not str(safe_path).startswith(str(base_path)):
            raise ValueError("Path traversal detected")

        return str(safe_path)
```

### Safe File Operations
```python
import os
from pathlib import Path
from typing import BinaryIO, TextIO

class SafeFileOperations:
    def __init__(self, allowed_directories: list):
        self.allowed_directories = [Path(d).resolve() for d in allowed_directories]

    def validate_file_path(self, path: str) -> Path:
        """Validate that a file path is within allowed directories"""
        file_path = Path(path).resolve()

        for allowed_dir in self.allowed_directories:
            if str(file_path).startswith(str(allowed_dir)):
                return file_path

        raise ValueError(f"File path not in allowed directories: {path}")

    def safe_read_file(self, path: str, max_size: int = 10 * 1024 * 1024) -> str:  # 10MB limit
        """Safely read a file with size limits"""
        safe_path = self.validate_file_path(path)

        if not safe_path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        if not safe_path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        size = safe_path.stat().st_size
        if size > max_size:
            raise ValueError(f"File too large: {size} bytes, maximum {max_size}")

        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()

    def safe_write_file(self, path: str, content: str, max_size: int = 10 * 1024 * 1024) -> int:
        """Safely write a file with size limits"""
        safe_path = self.validate_file_path(path)

        # Ensure parent directory exists
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        if len(content.encode('utf-8')) > max_size:
            raise ValueError(f"Content too large: {len(content)} characters, maximum {max_size}")

        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return len(content)
```

## Injection Prevention

### Command Injection Protection
```python
import subprocess
import shlex
from typing import List

class SafeCommandExecution:
    @staticmethod
    def safe_run_command(command_parts: List[str], allowed_commands: List[str] = None) -> dict:
        """Safely run a command with validation"""
        if not command_parts:
            raise ValueError("Empty command provided")

        command_name = command_parts[0]

        if allowed_commands and command_name not in allowed_commands:
            raise ValueError(f"Command not allowed: {command_name}")

        # Use shlex to properly handle arguments
        try:
            result = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                timeout=30,
                check=False  # Don't raise on non-zero exit
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "success": False}
        except Exception as e:
            return {"error": f"Command execution failed: {str(e)}", "success": False}

    @staticmethod
    def validate_shell_command(command: str) -> str:
        """Validate shell command to prevent injection"""
        dangerous_patterns = [
            r'[;&|]',  # Logical operators
            r'\$\(.*\)',  # Command substitution
            r'`.*`',  # Backtick command substitution
            r'>',  # Redirection
            r'<',  # Input redirection
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                raise ValueError(f"Dangerous command pattern detected: {pattern}")

        return command
```

## Resource Access Controls

### Restricted Resource Provider
```python
from mcp.types import ResourceTemplate
from typing import Dict, Any
import time

class RestrictedResourceProvider:
    def __init__(self, server, rate_limits: Dict[str, int]):
        self.server = server
        self.rate_limits = rate_limits  # requests per minute per resource
        self.access_logs = {}  # Track access by resource and user

    def register_rate_limited_resource(self, template: ResourceTemplate, user_id: str = None):
        """Register a resource with rate limiting"""
        def decorator(func):
            @self.server.handler.register_resource_template(template)
            def wrapper(*args, **kwargs):
                resource_key = f"{template.name}:{user_id or 'anonymous'}"

                # Check rate limit
                current_time = time.time()
                if resource_key in self.access_logs:
                    accesses = [t for t in self.access_logs[resource_key]
                               if current_time - t < 60]  # Last minute
                    if len(accesses) >= self.rate_limits.get(template.name, 10):
                        raise Exception(f"Rate limit exceeded for {template.name}")

                    self.access_logs[resource_key].append(current_time)
                else:
                    self.access_logs[resource_key] = [current_time]

                # Call original function
                return func(*args, **kwargs)
            return wrapper
        return decorator

# Example usage
# provider = RestrictedResourceProvider(server, {"sensitive-data": 5})  # 5 requests/minute
#
# @provider.register_rate_limited_resource(
#     ResourceTemplate(
#         uriTemplate="urn:sensitive:data",
#         name="sensitive-data",
#         description="Sensitive data resource"
#     ),
#     user_id="user123"
# )
# def sensitive_data_handler():
#     return {"data": "sensitive information"}
```

## Secure Configuration Management

### Environment-Safe Configuration
```python
import os
from typing import Optional

class SecureConfig:
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.settings = {}

    def load_config(self) -> Dict[str, Any]:
        """Load configuration securely"""
        # Load from environment variables first (more secure)
        self.settings = {
            "server_host": os.getenv("MCP_SERVER_HOST", "localhost"),
            "server_port": int(os.getenv("MCP_SERVER_PORT", "8080")),
            "ssl_enabled": os.getenv("MCP_SSL_ENABLED", "false").lower() == "true",
            "rate_limit": int(os.getenv("MCP_RATE_LIMIT", "100")),
            "max_connections": int(os.getenv("MCP_MAX_CONNECTIONS", "10")),
        }

        # Load from file if provided (less secure, use cautiously)
        if self.config_file:
            import json
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.settings.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")

        return self.settings

    def get_setting(self, key: str, default=None):
        """Safely get a configuration setting"""
        return self.settings.get(key, default)

    def validate_config(self) -> List[str]:
        """Validate configuration settings"""
        errors = []

        port = self.settings.get("server_port", 8080)
        if not (1 <= port <= 65535):
            errors.append("Port must be between 1 and 65535")

        host = self.settings.get("server_host", "")
        if not host:
            errors.append("Server host cannot be empty")

        rate_limit = self.settings.get("rate_limit", 100)
        if rate_limit <= 0:
            errors.append("Rate limit must be positive")

        return errors
```

## Audit Logging

### Security Event Logging
```python
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityAuditor:
    def __init__(self):
        self.logger = logging.getLogger("mcp.security")
        self.logger.setLevel(logging.INFO)

        # Create security log handler
        handler = logging.FileHandler("mcp_security.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_authentication_attempt(self, user_id: str, success: bool, ip_address: str = None):
        """Log authentication attempts"""
        status = "SUCCESS" if success else "FAILURE"
        self.logger.info(f"AUTH {status} - User: {user_id}, IP: {ip_address}")

    def log_unauthorized_access(self, user_id: str, resource: str, ip_address: str = None):
        """Log unauthorized access attempts"""
        self.logger.warning(f"UNAUTHORIZED ACCESS - User: {user_id}, Resource: {resource}, IP: {ip_address}")

    def log_potential_attack(self, attack_type: str, details: Dict[str, Any], ip_address: str = None):
        """Log potential security attacks"""
        self.logger.critical(f"POTENTIAL ATTACK - Type: {attack_type}, Details: {details}, IP: {ip_address}")

    def log_configuration_change(self, user_id: str, config_changes: Dict[str, Any]):
        """Log security-relevant configuration changes"""
        self.logger.info(f"CONFIG CHANGE - User: {user_id}, Changes: {config_changes}")
```

## Complete Secure Server Example

```python
def create_secure_mcp_server():
    """Create a complete secure MCP server implementation"""
    import os

    # Initialize server
    server = Server("secure-mcp-server")

    # Initialize security components
    validator = InputValidator()
    file_ops = SafeFileOperations([os.getcwd(), "/tmp"])
    auditor = SecurityAuditor()
    config = SecureConfig()

    # Validate configuration
    config_errors = config.validate_config()
    if config_errors:
        raise Exception(f"Configuration validation failed: {config_errors}")

    # Register a secure tool
    @server.handler.register_tool(
        Tool(
            name="secure_file_read",
            description="Securely read files with validation",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to read"}
                },
                "required": ["file_path"]
            }
        )
    )
    def secure_file_read_handler(params):
        try:
            file_path = params["file_path"]

            # Validate input
            safe_path = validator.validate_string_param(file_path, max_length=500)
            validated_path = file_ops.validate_file_path(safe_path)

            # Read file securely
            content = file_ops.safe_read_file(validated_path)

            # Log successful access
            auditor.log_authentication_attempt("system", True)

            return {
                "file_path": str(validated_path),
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            # Log security event
            auditor.log_potential_attack("malicious_file_access", {
                "error": str(e),
                "attempted_path": params.get("file_path", "unknown")
            })

            return {
                "error": "Security validation failed",
                "success": False
            }

    return server

# Usage
# secure_server = create_secure_mcp_server()
#
# # Run with stdio
# from mcp.server.stdio import stdio_server
# import sys
#
# with stdio_server(secure_server, sys.stdin, sys.stdout):
#     secure_server.run()
```