# MCP Server Implementation Template

This template provides a basic structure for implementing an MCP server with the official SDK.

## Basic Server Structure

```python
from mcp.server import Server
from mcp.types import Tool, ResourceTemplate
import sys

class MCPServer:
    def __init__(self, name: str):
        self.server = Server(name)

    def add_tool(self, tool: Tool, handler):
        """Add a tool with its handler"""
        @self.server.handler.register_tool(tool)
        def tool_handler(params):
            return handler(params)

    def add_resource(self, template: ResourceTemplate, handler):
        """Add a resource with its handler"""
        @self.server.handler.register_resource_template(template)
        def resource_handler(*args, **kwargs):
            return handler(*args, **kwargs)

    def run_stdio(self):
        """Run the server with stdio transport"""
        from mcp.server.stdio import stdio_server

        with stdio_server(self.server, sys.stdin, sys.stdout):
            self.server.run()

# Example usage
if __name__ == "__main__":
    server = MCPServer("my-mcp-server")

    # Define a simple tool
    example_tool = Tool(
        name="hello_world",
        description="Returns a hello world message",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"}
            },
            "required": ["name"]
        }
    )

    def hello_handler(params):
        name = params.get("name", "World")
        return {"message": f"Hello, {name}!"}

    server.add_tool(example_tool, hello_handler)

    # Define a simple resource
    example_resource = ResourceTemplate(
        uriTemplate="urn:greeting:{name}",
        name="greeting-resource",
        description="Generates personalized greetings"
    )

    def greeting_handler(name):
        return {"greeting": f"Greetings, {name}!", "timestamp": __import__('datetime').datetime.now().isoformat()}

    server.add_resource(example_resource, greeting_handler)

    # Run the server
    server.run_stdio()
```

## Advanced Server with Error Handling

```python
from mcp.server import Server
from mcp.types import Tool
import logging
import traceback

class RobustMCPServer:
    def __init__(self, name: str):
        self.server = Server(name)
        self.logger = logging.getLogger(name)

    def safe_register_tool(self, tool: Tool):
        """Decorator to register a tool with error handling"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(params):
                try:
                    self.logger.info(f"Executing tool: {tool.name}")
                    result = func(params)
                    self.logger.info(f"Tool {tool.name} completed successfully")
                    return result
                except Exception as e:
                    self.logger.error(f"Tool {tool.name} failed: {str(e)}")
                    self.logger.debug(f"Full traceback: {traceback.format_exc()}")

                    return {
                        "error": f"Tool execution failed: {str(e)}",
                        "tool": tool.name
                    }
            return wrapper
        return decorator

    def run_with_logging(self):
        """Run the server with enhanced logging"""
        import sys
        from mcp.server.stdio import stdio_server

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        with stdio_server(self.server, sys.stdin, sys.stdout):
            self.logger.info("Starting MCP server...")
            self.server.run()
```

## Client Implementation Template

```python
import asyncio
from mcp.client import Client
from mcp.transport import Transport

class MCPClient:
    def __init__(self, transport: Transport):
        self.client = Client(transport)

    async def connect(self):
        """Connect to the MCP server"""
        await self.client.connect()

    async def disconnect(self):
        """Disconnect from the MCP server"""
        await self.client.disconnect()

    async def call_tool(self, tool_name: str, params: dict):
        """Call a tool on the MCP server"""
        try:
            result = await self.client.call_tool(tool_name, params)
            return result
        except Exception as e:
            print(f"Error calling tool {tool_name}: {str(e)}")
            return {"error": str(e)}

# Example client usage
async def example_client_usage():
    # This assumes you have a transport set up
    # transport = YourTransportImplementation()
    # client = MCPClient(transport)
    #
    # await client.connect()
    # result = await client.call_tool("hello_world", {"name": "Alice"})
    # print(result)
    # await client.disconnect()
```

## Configuration Template

```python
# config.py
import os

class MCPConfig:
    # Server settings
    SERVER_NAME = os.getenv("MCP_SERVER_NAME", "default-mcp-server")
    SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
    SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8080"))

    # Security settings
    SSL_ENABLED = os.getenv("MCP_SSL_ENABLED", "false").lower() == "true"
    AUTH_REQUIRED = os.getenv("MCP_AUTH_REQUIRED", "false").lower() == "true"

    # Performance settings
    MAX_CONNECTIONS = int(os.getenv("MCP_MAX_CONNECTIONS", "10"))
    REQUEST_TIMEOUT = int(os.getenv("MCP_REQUEST_TIMEOUT", "30"))

    # Logging settings
    LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("MCP_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
```