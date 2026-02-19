#!/usr/bin/env python3
"""
MCP SDK Helper Script

This script helps initialize and set up MCP servers with proper configuration
and best practices for security, performance, and scalability.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional


def create_mcp_server_config(
    name: str,
    description: str,
    transports: Optional[List[str]] = None,
    tools: Optional[List[Dict]] = None,
    resources: Optional[List[Dict]] = None
) -> Dict:
    """
    Create a configuration dictionary for an MCP server
    """
    config = {
        "name": name,
        "description": description,
        "transports": transports or ["stdio"],  # Default to stdio
        "tools": tools or [],
        "resources": resources or []
    }

    return config


def validate_mcp_config(config: Dict) -> List[str]:
    """
    Validate MCP server configuration and return list of errors
    """
    errors = []

    if not config.get("name"):
        errors.append("Name is required")

    if not config.get("description"):
        errors.append("Description is required")

    # Validate transports
    valid_transports = ["stdio", "tcp", "websocket", "http"]
    transports = config.get("transports", [])
    for transport in transports:
        if transport not in valid_transports:
            errors.append(f"Invalid transport: {transport}. Valid options: {valid_transports}")

    return errors


def generate_setup_code(config: Dict) -> str:
    """
    Generate Python code for setting up the MCP server
    """
    name = config["name"]
    transports = config["transports"]

    code = f'''from mcp.server import Server
from mcp.types import Tool, ResourceTemplate

# Initialize the MCP server
server = Server("{name}")

# Example tool definition
example_tool = Tool(
    name="example_tool",
    description="An example tool",
    inputSchema={{
        "type": "object",
        "properties": {{
            "param1": {{"type": "string", "description": "First parameter"}}
        }},
        "required": ["param1"]
    }}
)

# Register the example tool
@server.handler.register_tool(example_tool)
def example_tool_handler(params):
    param1 = params.get("param1")
    return {{"result": f"Processed {{param1}}" if param1 else "No parameter provided"}}

# Example resource definition
example_resource = ResourceTemplate(
    uriTemplate="urn:example:{{id}}",
    name="example_resource",
    description="An example resource"
)

# Register the example resource
@server.handler.register_resource_template(example_resource)
def example_resource_handler(id):
    return {{"id": id, "data": "resource data", "timestamp": __import__('datetime').datetime.now().isoformat()}}

# Run the server with selected transports
if __name__ == "__main__":
    import sys

'''

    if "stdio" in transports:
        code += '''    # Run with stdio transport
    from mcp.server.stdio import stdio_server
    with stdio_server(server, sys.stdin, sys.stdout):
        server.run()
'''

    if "tcp" in transports:
        code += '''
    # Run with TCP transport
    # from mcp.server.tcp import tcp_server
    # with tcp_server(server, host="localhost", port=8080) as server_socket:
    #     server.run()
'''

    if "http" in transports:
        code += '''
    # Run with HTTP transport
    # from mcp.server.http import HttpServer
    # import asyncio
    # http_server = HttpServer(server, host="localhost", port=8080)
    # asyncio.run(http_server.start())
'''

    return code


def main():
    parser = argparse.ArgumentParser(description="MCP SDK Helper")
    parser.add_argument("--name", required=True, help="Name of the MCP server")
    parser.add_argument("--description", required=True, help="Description of the MCP server")
    parser.add_argument("--transports", nargs="+", default=["stdio"],
                       help="Transports to use (default: stdio) - options: stdio, tcp, websocket, http")
    parser.add_argument("--output", "-o", help="Output file for generated code")
    parser.add_argument("--validate-only", action="store_true", help="Only validate configuration")

    args = parser.parse_args()

    # Create configuration
    config = create_mcp_server_config(
        name=args.name,
        description=args.description,
        transports=args.transports
    )

    # Validate configuration
    errors = validate_mcp_config(config)

    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("✅ Configuration is valid")

    if args.validate_only:
        print("Configuration passed validation")
        return

    # Generate setup code
    code = generate_setup_code(config)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(code)
        print(f"✅ Code generated and saved to {args.output}")
    else:
        print("\\n" + "="*50)
        print("Generated Setup Code:")
        print("="*50)
        print(code)


if __name__ == "__main__":
    main()