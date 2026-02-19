# MCP Server Implementation Patterns

This reference covers advanced patterns for implementing MCP servers with the official SDK.

## Basic Server Structure

```python
from mcp.server import Server
from mcp.types import Tool, ResourceTemplate, PromptsCapability
from mcp.server.http import HttpServer
import asyncio
import logging

class MCPServer:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.server = Server(f"{name}/{version}")
        self.logger = logging.getLogger(__name__)

    def register_tool(self, tool: Tool):
        """Decorator to register a tool with the server"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def register_resource_template(self, template: ResourceTemplate):
        """Decorator to register a resource template with the server"""
        def decorator(func):
            @self.server.handler.register_resource_template(template)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    async def start_http_server(self, host: str = "localhost", port: int = 8080):
        """Start the server with HTTP transport"""
        http_server = HttpServer(self.server, host=host, port=port)
        await http_server.start()

        self.logger.info(f"MCP server started on {host}:{port}")

        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            self.logger.info("Shutting down server...")
            await http_server.stop()

    def run_stdio(self):
        """Run the server with stdio transport"""
        from mcp.server.stdio import stdio_server
        import sys

        with stdio_server(self.server, sys.stdin, sys.stdout):
            self.server.run()
```

## Multi-Transport Server

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.tcp import tcp_server
import threading
import socket
import sys

class MultiTransportMCPServer:
    def __init__(self, name: str):
        self.server = Server(name)
        self.transports = []

    def add_stdio_transport(self):
        """Add stdio transport to the server"""
        def run_stdio():
            with stdio_server(self.server, sys.stdin, sys.stdout):
                self.server.run()

        self.transports.append(("stdio", run_stdio))
        return self

    def add_tcp_transport(self, host: str = "localhost", port: int = 8080):
        """Add TCP transport to the server"""
        def run_tcp():
            with tcp_server(self.server, host=host, port=port) as server_socket:
                self.server.run()

        self.transports.append(("tcp", run_tcp))
        return self

    def start_all_transports(self):
        """Start all configured transports in separate threads"""
        threads = []

        for transport_name, transport_func in self.transports:
            thread = threading.Thread(target=transport_func, daemon=True)
            thread.start()
            threads.append((transport_name, thread))

        # Wait for all threads to complete
        for _, thread in threads:
            thread.join()
```

## Advanced Tool Registration

```python
from mcp.types import Tool
from typing import Dict, Any, Callable
import inspect

class AdvancedToolRegistrar:
    def __init__(self, server):
        self.server = server

    def register_function_as_tool(self,
                                 name: str,
                                 description: str,
                                 fn: Callable) -> Tool:
        """Automatically register a Python function as an MCP tool"""
        # Extract function signature
        sig = inspect.signature(fn)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # Default to string type, but could be enhanced to detect types
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"

            properties[param_name] = {
                "type": param_type,
                "description": getattr(param, 'description', f'Parameter {param_name}')
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        # Create the tool
        tool = Tool(
            name=name,
            description=description,
            inputSchema={
                "type": "object",
                "properties": properties,
                "required": required
            }
        )

        # Register the tool
        @self.server.handler.register_tool(tool)
        def handler(params):
            # Call the function with the parameters
            return fn(**params)

        return tool

# Usage example
def example_calculation(x: int, y: int, operation: str = "add") -> Dict[str, Any]:
    """Example calculation function"""
    if operation == "add":
        return {"result": x + y}
    elif operation == "multiply":
        return {"result": x * y}
    else:
        return {"result": "unknown operation"}

# registrar = AdvancedToolRegistrar(server)
# registrar.register_function_as_tool(
#     "calculation-tool",
#     "Performs basic arithmetic operations",
#     example_calculation
# )
```

## Resource Provider Patterns

```python
from mcp.types import ResourceTemplate, TextResourceContents
from typing import Optional
import asyncio
from datetime import datetime

class ResourceProvider:
    def __init__(self, server):
        self.server = server
        self.resource_cache = {}

    def register_dynamic_resource(self, template: ResourceTemplate, refresh_interval: int = 300):
        """Register a resource that refreshes periodically"""
        def decorator(func):
            # Cache the result temporarily
            async def cached_handler(*args, **kwargs):
                cache_key = f"{template.uriTemplate}:{hash(str(args) + str(kwargs))}"

                # Check if cached and not expired
                if cache_key in self.resource_cache:
                    cached_result, timestamp = self.resource_cache[cache_key]
                    if (datetime.now() - timestamp).seconds < refresh_interval:
                        return cached_result

                # Call the function and cache the result
                result = await func(*args, **kwargs)
                self.resource_cache[cache_key] = (result, datetime.now())
                return result

            @self.server.handler.register_resource_template(template)
            async def handler(*args, **kwargs):
                return await cached_handler(*args, **kwargs)

            return handler
        return decorator

# Example: Dynamic system information resource
import psutil
import os

# @provider.register_dynamic_resource(
#     ResourceTemplate(
#         uriTemplate="urn:system:stats",
#         name="system-stats",
#         description="Current system statistics"
#     ),
#     refresh_interval=60  # Refresh every minute
# )
# async def system_stats_handler():
#     return {
#         "cpu_percent": psutil.cpu_percent(interval=1),
#         "memory_percent": psutil.virtual_memory().percent,
#         "disk_usage": psutil.disk_usage('/').percent,
#         "timestamp": datetime.now().isoformat()
#     }
```

## Error Handling and Monitoring

```python
import functools
import traceback
from typing import Dict, Any

class MonitoredMCPServer:
    def __init__(self, server):
        self.server = server
        self.error_count = 0
        self.request_count = 0

    def monitored_tool(self, tool):
        """Decorator to add monitoring and error handling to tools"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.request_count += 1
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.error_count += 1
                    # Log the error with context
                    print(f"Tool error in {tool.name}: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")

                    # Return error information to client
                    return {
                        "error": str(e),
                        "tool_name": tool.name,
                        "timestamp": datetime.now().isoformat()
                    }
            return wrapper
        return decorator

    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics"""
        return {
            "requests_processed": self.request_count,
            "errors_encountered": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1)
        }
```