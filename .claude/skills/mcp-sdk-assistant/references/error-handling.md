# Error Handling Patterns for MCP SDK

This reference covers comprehensive error handling patterns when working with the MCP SDK.

## Common Error Types and Handling

### MCP Protocol Errors
```python
from mcp.types import Error
from typing import Dict, Any, Optional
import traceback
import logging

class MCPErrorHandler:
    @staticmethod
    def handle_protocol_error(error: Exception) -> Dict[str, Any]:
        """Handle MCP protocol-specific errors"""
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        # Categorize the error
        if "timeout" in str(error).lower():
            error_info['severity'] = 'warning'
            error_info['code'] = 'TIMEOUT_ERROR'
        elif "connection" in str(error).lower() or "transport" in str(error).lower():
            error_info['severity'] = 'error'
            error_info['code'] = 'CONNECTION_ERROR'
        elif "validation" in str(error).lower():
            error_info['severity'] = 'error'
            error_info['code'] = 'VALIDATION_ERROR'
        else:
            error_info['severity'] = 'error'
            error_info['code'] = 'UNKNOWN_ERROR'

        return error_info

    @staticmethod
    def create_mcp_error(code: str, message: str, data: Optional[Dict] = None) -> Error:
        """Create standardized MCP error response"""
        error_dict = {
            "code": code,
            "message": message
        }

        if data:
            error_dict["data"] = data

        return Error(**error_dict)
```

### Tool Execution Error Handling
```python
from typing import Union
import asyncio

class ToolExecutionHandler:
    @staticmethod
    async def safe_tool_execution(tool_func, params: Dict[str, Any],
                                 timeout: float = 30.0) -> Dict[str, Any]:
        """Safely execute a tool with timeout and error handling"""
        try:
            # Execute with timeout
            result = await asyncio.wait_for(tool_func(params), timeout=timeout)

            return {
                'success': True,
                'result': result,
                'error': None
            }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'result': None,
                'error': f'Tool execution timed out after {timeout} seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': f'Tool execution failed: {str(e)}'
            }

    @staticmethod
    def validate_tool_parameters(params: Dict[str, Any],
                               required_params: list,
                               param_schema: Dict[str, Any]) -> tuple[bool, list]:
        """Validate tool parameters against schema"""
        errors = []

        # Check required parameters
        for param in required_params:
            if param not in params:
                errors.append(f"Missing required parameter: {param}")

        # Validate parameter types and constraints
        for param_name, param_value in params.items():
            if param_name in param_schema:
                schema = param_schema[param_name]

                # Validate type
                expected_type = schema.get('type')
                if expected_type:
                    if expected_type == 'string' and not isinstance(param_value, str):
                        errors.append(f"Parameter {param_name} must be string, got {type(param_value).__name__}")
                    elif expected_type == 'integer' and not isinstance(param_value, int):
                        errors.append(f"Parameter {param_name} must be integer, got {type(param_value).__name__}")
                    elif expected_type == 'number' and not isinstance(param_value, (int, float)):
                        errors.append(f"Parameter {param_name} must be number, got {type(param_value).__name__}")
                    elif expected_type == 'boolean' and not isinstance(param_value, bool):
                        errors.append(f"Parameter {param_name} must be boolean, got {type(param_value).__name__}")
                    elif expected_type == 'array' and not isinstance(param_value, list):
                        errors.append(f"Parameter {param_name} must be array, got {type(param_value).__name__}")
                    elif expected_type == 'object' and not isinstance(param_value, dict):
                        errors.append(f"Parameter {param_name} must be object, got {type(param_value).__name__}")

        return len(errors) == 0, errors
```

## Robust Server Implementation with Error Handling

```python
from mcp.server import Server
from mcp.types import Tool, ResourceTemplate
import logging
from contextlib import contextmanager

class RobustMCPServer:
    def __init__(self, name: str, log_level: int = logging.INFO):
        self.server = Server(name)
        self.logger = logging.getLogger(f"mcp.{name}")
        self.logger.setLevel(log_level)

        # Add console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.error_handler = MCPErrorHandler()
        self.tool_handler = ToolExecutionHandler()

    def register_safe_tool(self, tool: Tool):
        """Decorator to register a tool with comprehensive error handling"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(params):
                try:
                    # Validate parameters
                    required_params = tool.inputSchema.get('required', [])
                    param_schema = tool.inputSchema.get('properties', {})

                    is_valid, validation_errors = self.tool_handler.validate_tool_parameters(
                        params, required_params, param_schema
                    )

                    if not is_valid:
                        self.logger.error(f"Parameter validation failed for {tool.name}: {validation_errors}")
                        return {
                            "error": "Parameter validation failed",
                            "details": validation_errors
                        }

                    # Execute the tool
                    result = func(params)

                    self.logger.info(f"Tool {tool.name} executed successfully")
                    return result

                except Exception as e:
                    self.logger.error(f"Tool {tool.name} execution failed: {str(e)}")
                    self.logger.debug(f"Full traceback: {traceback.format_exc()}")

                    return {
                        "error": f"Tool execution failed: {str(e)}",
                        "tool_name": tool.name
                    }

            return wrapper
        return decorator

    def register_safe_resource(self, template: ResourceTemplate):
        """Decorator to register a resource with comprehensive error handling"""
        def decorator(func):
            @self.server.handler.register_resource_template(template)
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)

                    self.logger.info(f"Resource {template.name} accessed successfully")
                    return result

                except Exception as e:
                    self.logger.error(f"Resource {template.name} access failed: {str(e)}")
                    self.logger.debug(f"Full traceback: {traceback.format_exc()}")

                    return {
                        "error": f"Resource access failed: {str(e)}",
                        "resource_name": template.name
                    }

            return wrapper
        return decorator

    @contextmanager
    def error_boundary(self, operation_name: str = "operation"):
        """Context manager for error boundaries"""
        try:
            yield
        except Exception as e:
            self.logger.error(f"{operation_name} failed: {str(e)}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise  # Re-raise the exception after logging
```

## Circuit Breaker Pattern for MCP Services

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped, blocking requests
    HALF_OPEN = "half_open" # Testing if service is recovered

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.success_count = 0
        self.success_threshold = 3  # Number of successes to close circuit

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - requests blocked")

        if self.state == CircuitState.HALF_OPEN:
            # Test the service with one request
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure()
                raise e

        if self.state == CircuitState.CLOSED:
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure()
                raise e

    def _record_failure(self):
        """Record a failure and potentially trip the circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.success_count = 0  # Reset success count when opening

    def _record_success(self):
        """Record a success and potentially close the circuit"""
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN and self.success_count >= self.success_threshold:
            self._reset()

    def _reset(self):
        """Reset the circuit breaker after successful operation"""
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED

class CircuitBreakerMCPServer(RobustMCPServer):
    def __init__(self, name: str, log_level: int = logging.INFO):
        super().__init__(name, log_level)
        self.circuit_breakers = {}

    def get_circuit_breaker(self, resource_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a specific resource"""
        if resource_name not in self.circuit_breakers:
            self.circuit_breakers[resource_name] = CircuitBreaker(
                failure_threshold=3,
                timeout=120  # 2 minutes
            )
        return self.circuit_breakers[resource_name]

    def register_protected_resource(self, template: ResourceTemplate):
        """Register a resource with circuit breaker protection"""
        def decorator(func):
            cb = self.get_circuit_breaker(template.name)

            @self.server.handler.register_resource_template(template)
            def wrapper(*args, **kwargs):
                try:
                    result = cb.call(func, *args, **kwargs)
                    return result
                except Exception as e:
                    self.logger.warning(f"Circuit breaker tripped for {template.name}: {str(e)}")
                    return {
                        "error": "Service temporarily unavailable due to circuit breaker",
                        "resource_name": template.name,
                        "retry_after": 120  # Suggest retry after 2 minutes
                    }

            return wrapper
        return decorator
```

## Retry Logic with Exponential Backoff

```python
import random
import asyncio
from typing import Callable, Any, Optional

class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2 ** attempt)
        # Add jitter: ±25% of calculated delay
        jitter = random.uniform(-0.25, 0.25) * delay
        return min(delay + jitter, self.max_delay)

    async def execute_with_retry(self, func: Callable, *args,
                                should_retry_predicate: Optional[Callable[[Exception], bool]] = None,
                                **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry this specific error
                if should_retry_predicate and not should_retry_predicate(e):
                    raise e

                # If this was the last attempt, raise the exception
                if attempt >= self.max_retries:
                    break

                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s")

                await asyncio.sleep(delay)

        # If we get here, all retries exhausted
        raise last_exception

class RetryableMCPServer(CircuitBreakerMCPServer):
    def __init__(self, name: str, log_level: int = logging.INFO):
        super().__init__(name, log_level)
        self.retry_handlers = {}

    def get_retry_handler(self, operation_name: str) -> RetryHandler:
        """Get or create a retry handler for an operation"""
        if operation_name not in self.retry_handlers:
            self.retry_handlers[operation_name] = RetryHandler()
        return self.retry_handlers[operation_name]

    def register_retryable_tool(self, tool: Tool,
                              max_retries: int = 3,
                              transient_error_predicate: Optional[Callable[[Exception], bool]] = None):
        """Register a tool with retry logic"""
        def decorator(func):
            retry_handler = RetryHandler(max_retries=max_retries)

            @self.server.handler.register_tool(tool)
            async def wrapper(params):
                try:
                    result = await retry_handler.execute_with_retry(
                        func,
                        params,
                        should_retry_predicate=transient_error_predicate
                    )
                    return result
                except Exception as e:
                    self.logger.error(f"All retry attempts failed for {tool.name}: {str(e)}")
                    return {
                        "error": f"Operation failed after {max_retries + 1} attempts: {str(e)}",
                        "tool_name": tool.name
                    }

            return wrapper
        return decorator
```

## Fallback Strategies

```python
from typing import List

class FallbackManager:
    def __init__(self):
        self.fallback_chains = {}

    def register_fallback_chain(self, primary_name: str, fallback_names: List[str]):
        """Register a fallback chain for a primary service"""
        self.fallback_chains[primary_name] = fallback_names

    async def execute_with_fallback(self, primary_func: Callable,
                                  fallback_funcs: List[Callable],
                                  *args, **kwargs) -> Any:
        """Execute primary function with fallbacks"""
        services = [primary_func] + fallback_funcs

        last_exception = None
        for i, service in enumerate(services):
            try:
                result = await service(*args, **kwargs)

                if i > 0:  # Primary failed, fallback used
                    self.logger.warning(f"Fallback #{i} used for service")

                return result
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Service #{i + 1} failed: {str(e)}")
                continue

        # All services failed
        raise last_exception

class FallbackMCPServer(RetryableMCPServer):
    def __init__(self, name: str, log_level: int = logging.INFO):
        super().__init__(name, log_level)
        self.fallback_manager = FallbackManager()

    def register_tool_with_fallback(self, primary_tool: Tool,
                                  fallback_tools: List[Tool],
                                  fallback_functions: List[Callable]):
        """Register a tool with fallback alternatives"""
        primary_func = None

        # Register the primary tool
        @self.server.handler.register_tool(primary_tool)
        def primary_wrapper(params):
            def exec_primary():
                return primary_func(params)

            # Prepare fallback functions
            fallback_funcs = []
            for i, (tool, func) in enumerate(zip(fallback_tools, fallback_functions)):
                @self.server.handler.register_tool(tool)  # Register fallback tools too
                def fallback_wrapper(f_params, f_func=func):
                    try:
                        return f_func(f_params)
                    except Exception as e:
                        self.logger.error(f"Fallback tool {tool.name} failed: {str(e)}")
                        raise e
                fallback_funcs.append(fallback_wrapper)

            try:
                return self.fallback_manager.execute_with_fallback(
                    exec_primary, fallback_funcs
                )
            except Exception as e:
                self.logger.error(f"All fallbacks failed: {str(e)}")
                return {
                    "error": "All services failed",
                    "details": str(e)
                }

        def decorator(func):
            nonlocal primary_func
            primary_func = func
            return func
        return decorator
```

## Graceful Degradation

```python
import signal
import asyncio
from typing import Dict, Callable

class GracefulDegradationManager:
    def __init__(self):
        self.degraded_services = set()
        self.service_dependencies = {}  # service -> [dependencies]
        self.degradation_handlers = {}  # service -> degradation_func

    def register_service_dependency(self, service: str, dependencies: List[str]):
        """Register dependencies for a service"""
        self.service_dependencies[service] = dependencies

    def register_degradation_handler(self, service: str, handler: Callable):
        """Register a degradation handler for a service"""
        self.degradation_handlers[service] = handler

    def degrade_service(self, service: str):
        """Mark a service as degraded"""
        self.degraded_services.add(service)
        self.logger.info(f"Service {service} marked as degraded")

    def is_service_degraded(self, service: str) -> bool:
        """Check if a service or its dependencies are degraded"""
        if service in self.degraded_services:
            return True

        # Check dependencies
        deps = self.service_dependencies.get(service, [])
        return any(dep in self.degraded_services for dep in deps)

    def get_degraded_response(self, service: str, original_error: Exception = None):
        """Get appropriate degraded response for a service"""
        handler = self.degradation_handlers.get(service)
        if handler:
            return handler(original_error)

        # Default degraded response
        return {
            "warning": f"Service {service} is operating in degraded mode",
            "message": "Using cached or reduced functionality"
        }

class DegradableMCPServer(FallbackMCPServer):
    def __init__(self, name: str, log_level: int = logging.INFO):
        super().__init__(name, log_level)
        self.degradation_manager = GracefulDegradationManager()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Here you would typically stop accepting new requests
        # and finish processing existing ones

    def register_degradable_tool(self, tool: Tool,
                               degradation_handler: Optional[Callable] = None):
        """Register a tool that can degrade gracefully"""
        if degradation_handler:
            self.degradation_manager.register_degradation_handler(tool.name, degradation_handler)

        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(params):
                if self.degradation_manager.is_service_degraded(tool.name):
                    self.logger.warning(f"Tool {tool.name} is degraded, returning fallback response")
                    return self.degradation_manager.get_degraded_response(tool.name)

                try:
                    result = func(params)
                    return result
                except Exception as e:
                    # Check if this error warrants degrading the service
                    if self._should_degrade_service(tool.name, e):
                        self.degradation_manager.degrade_service(tool.name)
                        return self.degradation_manager.get_degraded_response(tool.name, e)

                    raise e

            return wrapper
        return decorator

    def _should_degrade_service(self, service: str, error: Exception) -> bool:
        """Determine if a service should be degraded based on error"""
        error_str = str(error).lower()

        # Degrade on persistent infrastructure errors
        persistent_errors = [
            "connection refused", "timeout", "network", "database",
            "connection", "socket", "broken pipe"
        ]

        return any(err in error_str for err in persistent_errors)
```

## Complete Error-Handled Example

```python
def create_production_ready_mcp_server():
    """
    Create a production-ready MCP server with comprehensive error handling
    """
    import os

    # Create the degradable server with circuit breakers and retries
    server_instance = DegradableMCPServer("production-mcp-server")

    # Register a critical tool with full error handling
    @server_instance.register_degradable_tool(
        Tool(
            name="critical_operation",
            description="A critical operation with full error handling",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Input data"}
                },
                "required": ["data"]
            }
        ),
        degradation_handler=lambda error: {
            "status": "degraded",
            "message": "Using reduced functionality due to service degradation",
            "original_error": str(error) if error else None
        }
    )
    def critical_operation_handler(params):
        data = params["data"]

        # Simulate potential failure points
        if len(data) > 1000:
            raise ValueError("Data too large")

        if "error" in data.lower():
            raise RuntimeError("Simulated runtime error")

        return {
            "processed_data": data.upper(),
            "length": len(data),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

    # Register a resource with circuit breaker protection
    @server_instance.register_protected_resource(
        ResourceTemplate(
            uriTemplate="urn:protected:resource",
            name="protected-resource",
            description="A protected resource with circuit breaker"
        )
    )
    def protected_resource_handler():
        # Simulate occasional failures
        import random
        if random.random() < 0.1:  # 10% failure rate for demo
            raise Exception("Simulated resource failure")

        return {"data": "protected resource data", "status": "success"}

    # Register a retryable tool
    @server_instance.register_retryable_tool(
        Tool(
            name="flaky_operation",
            description="An operation that might fail occasionally",
            inputSchema={
                "type": "object",
                "properties": {
                    "attempt": {"type": "integer", "default": 1}
                }
            }
        ),
        max_retries=3
    )
    async def flaky_operation_handler(params):
        import random
        attempt = params.get("attempt", 1)

        # Simulate random failures
        if random.random() < 0.3:  # 30% failure rate
            raise Exception(f"Flaky operation failed on attempt {attempt}")

        return {"result": f"Success on attempt {attempt}", "attempt": attempt}

    return server_instance

# Usage example
# server = create_production_ready_mcp_server()
#
# # Run the server
# from mcp.server.stdio import stdio_server
# import sys
#
# try:
#     with stdio_server(server.server, sys.stdin, sys.stdout):
#         server.server.run()
# except KeyboardInterrupt:
#     print("Server shutting down gracefully...")
# finally:
#     # Cleanup resources
#     pass
```