---
name: mcp-sdk-assistant
description: Build, configure, and use the official MCP SDK. Helps with MCP components (servers, tools, resources, transports), generates correct MCP SDK setup and configuration code, shows how to define tools, resources, and handlers, provides best practices for security, performance, and scalability, includes examples for common MCP patterns (tool invocation, context servers, file and web resources), and warns when deprecated or incorrect MCP SDK usage is detected.
---

# MCP SDK Assistant Skill

This skill provides guidance for building, configuring, and using the official Model Context Protocol (MCP) SDK effectively. It helps users create robust, secure, and scalable MCP implementations with proper architecture and best practices.

## When to Use This Skill

Use this skill when you need to:
- Design and implement MCP servers, clients, or tools
- Set up MCP components (servers, tools, resources, transports)
- Generate correct MCP SDK configuration and setup code
- Implement tool definitions, resources, and handlers
- Follow security, performance, and scalability best practices
- Work with common MCP patterns (tool invocation, context servers, file/web resources)
- Identify and fix deprecated or incorrect MCP SDK usage

## Core Components of MCP SDK

### 1. MCP Servers
- **Transport Layer**: Handles connections (stdio, TCP, WebSocket, etc.)
- **Request/Response Handling**: Manages MCP protocol messages
- **Tool Registration**: Registers available tools with the server
- **Resource Providers**: Exposes resources for consumption

### 2. MCP Clients
- **Connection Management**: Establishes and maintains MCP connections
- **Tool Invocation**: Calls registered tools on servers
- **Resource Consumption**: Accesses provided resources
- **Session Management**: Manages MCP sessions

### 3. Tools and Resources
- **Tool Definitions**: Function specifications with parameters
- **Resource Schemas**: Structured data representations
- **Handlers**: Implementation logic for tools/resources
- **Context Providers**: Supplies contextual information

## MCP SDK Setup Pattern

```python
from mcp.server import Server
from mcp.types import Tool, ResourceTemplate
import asyncio

# Initialize the MCP server
server = Server("my-mcp-server")

# Define a tool
@server.handler.register_tool(
    Tool(
        name="example_tool",
        description="An example tool",
        inputSchema={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"}
            },
            "required": ["param1"]
        }
    )
)
def example_tool_handler(params):
    """Implementation of the example tool"""
    param1 = params.get("param1")
    return {"result": f"Processed {param1}"}

# Define a resource
@server.handler.register_resource_template(
    ResourceTemplate(
        uriTemplate="urn:example:{id}",
        name="example_resource",
        description="An example resource"
    )
)
def example_resource_handler(id):
    """Implementation of the example resource"""
    return {"id": id, "data": "resource data"}

# Run the server
if __name__ == "__main__":
    from mcp.server.stdio import stdio_server
    import sys

    # Run with stdio transport
    with stdio_server(server, sys.stdin, sys.stdout):
        server.run()
```

## Best Practices

### 1. Security Patterns
- **Authentication**: Implement proper authentication for MCP connections
- **Authorization**: Validate permissions before executing tools/resources
- **Input Validation**: Sanitize and validate all inputs to prevent injection
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Secure Transports**: Use encrypted transports when possible

### 2. Performance Optimization
- **Connection Pooling**: Reuse connections when possible
- **Caching**: Cache resource responses where appropriate
- **Async Processing**: Use async handlers for I/O-bound operations
- **Resource Pagination**: Implement pagination for large resource sets
- **Efficient Serialization**: Optimize JSON serialization/deserialization

### 3. Scalability Considerations
- **Stateless Servers**: Keep servers stateless when possible
- **Load Balancing**: Design for horizontal scaling
- **Resource Management**: Implement proper resource cleanup
- **Health Checks**: Provide health check endpoints
- **Monitoring**: Add metrics and logging

## Common Patterns

### 1. Tool Invocation Pattern
```python
from mcp.client import Client
from mcp.transport import StdioTransport

async def invoke_mcp_tool():
    # Connect to MCP server
    transport = StdioTransport(sys.stdin, sys.stdout)
    client = Client(transport)

    await client.connect()

    # Invoke a tool
    result = await client.call_tool(
        "example_tool",
        {"param1": "test_value"}
    )

    print(f"Tool result: {result}")

    await client.disconnect()
```

### 2. Context Server Pattern
```python
from mcp.server import Server
from mcp.types import PromptsCapability, ResourcesCapability

server = Server("context-provider")

@server.handler.register_prompts_capability
def get_prompts():
    """Provide context-aware prompts"""
    return [
        {
            "name": "project-context",
            "description": "Provides project-specific context",
            "instructions": "Current project details..."
        }
    ]

@server.handler.register_resources_capability
def get_resources():
    """Provide context resources"""
    return [
        ResourceTemplate(
            uriTemplate="urn:project:info",
            name="project-info",
            description="Project information"
        )
    ]

# Register resource handler
@server.handler.register_resource_template(
    ResourceTemplate(
        uriTemplate="urn:project:info",
        name="project-info",
        description="Project information"
    )
)
def project_info_handler():
    return {"project": "example-project", "version": "1.0.0"}
```

### 3. File Resource Pattern
```python
import os
from pathlib import Path

@server.handler.register_resource_template(
    ResourceTemplate(
        uriTemplate="urn:file:{path}",
        name="file-resource",
        description="Access to local files"
    )
)
def file_resource_handler(path):
    """Safely access local files"""
    # Validate path to prevent directory traversal
    safe_path = Path(path).resolve()
    base_dir = Path("/safe/base/path").resolve()

    if not str(safe_path).startswith(str(base_dir)):
        raise ValueError("Path traversal detected")

    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(safe_path, 'r') as f:
        content = f.read()

    return {"path": str(safe_path), "content": content}
```

## Warning: Deprecated or Incorrect Usage

### Common Mistakes to Avoid
1. **Unsafe Path Access**: Don't allow directory traversal in file resources
2. **Missing Input Validation**: Always validate tool parameters
3. **Improper Error Handling**: Handle exceptions gracefully
4. **Resource Leaks**: Clean up resources properly
5. **Hardcoded Secrets**: Don't embed credentials in code

### Correct vs Incorrect Patterns
```python
# ❌ INCORRECT: Unsafe file access
@server.handler.register_resource_template(...)
def unsafe_file_handler(path):
    with open(path, 'r') as f:  # Vulnerable to directory traversal
        return f.read()

# ✅ CORRECT: Safe file access with validation
@server.handler.register_resource_template(...)
def safe_file_handler(path):
    # Validate path to prevent directory traversal
    safe_path = Path(path).resolve()
    base_dir = Path("/allowed/directory").resolve()

    if not str(safe_path).startswith(str(base_dir)):
        raise ValueError("Path traversal detected")

    with open(safe_path, 'r') as f:
        return f.read()
```

## Complete Implementation Example

For a complete implementation with all best practices, see the references below.

## When to Consult References

- **Advanced Server Patterns**: See `references/server-patterns.md`
- **Security Best Practices**: See `references/security.md`
- **Performance Optimization**: See `references/performance.md`
- **Error Handling Patterns**: See `references/error-handling.md`
- **Testing Strategies**: See `references/testing.md`