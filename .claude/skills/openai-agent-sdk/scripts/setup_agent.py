#!/usr/bin/env python3
"""
OpenAI Agent SDK Helper Script

This script helps initialize and set up OpenAI agents with proper configuration
and best practices for reliability, safety, and cost control.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional


def create_assistant_config(
    name: str,
    instructions: str,
    model: str = "gpt-4-turbo",
    tools: Optional[List[Dict]] = None,
    file_ids: Optional[List[str]] = None
) -> Dict:
    """
    Create a configuration dictionary for an OpenAI assistant
    """
    config = {
        "name": name,
        "instructions": instructions,
        "model": model,
        "tools": tools or [],
    }

    if file_ids:
        config["file_ids"] = file_ids

    return config


def validate_assistant_config(config: Dict) -> List[str]:
    """
    Validate assistant configuration and return list of errors
    """
    errors = []

    if not config.get("name"):
        errors.append("Name is required")

    if not config.get("instructions"):
        errors.append("Instructions are required")

    if not config.get("model"):
        errors.append("Model is required")

    # Check for dangerous patterns in instructions
    dangerous_patterns = [
        "ignore previous instructions",
        "disregard safety guidelines",
        "act as a different ai",
        "system:",
        "<sys>",
        "</sys>"
    ]

    instructions = config.get("instructions", "").lower()
    for pattern in dangerous_patterns:
        if pattern in instructions:
            errors.append(f"Dangerous pattern detected in instructions: {pattern}")

    return errors


def generate_setup_code(config: Dict) -> str:
    """
    Generate Python code for setting up the assistant
    """
    tools_str = str(config.get("tools", []))
    file_ids_str = str(config.get("file_ids", []))

    code = f'''from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Make sure to set OPENAI_API_KEY environment variable

# Create the assistant
assistant = client.beta.assistants.create(
    name="{config["name"]}",
    instructions=\"\"\"{config["instructions"]}\"\"\",
    model="{config["model"]}",
    tools={tools_str},
    file_ids={file_ids_str}
)

print(f"Assistant created with ID: {{assistant.id}}")

# Example of creating a thread and running the assistant
thread = client.beta.threads.create(
    messages=[
        {{
            "role": "user",
            "content": "Hello!"
        }}
    ]
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# Monitor the run
import time
while run.status in ["queued", "in_progress"]:
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    time.sleep(1)

if run.status == "completed":
    messages = client.beta.threads.messages.list(
        thread_id=thread.id,
        order="asc"
    )
    for msg in messages:
        if msg.role == "assistant":
            print(f"Assistant: {{msg.content[0].text.value}}")
else:
    print(f"Run failed with status: {{run.status}}")
'''

    return code


def main():
    parser = argparse.ArgumentParser(description="OpenAI Agent SDK Helper")
    parser.add_argument("--name", required=True, help="Name of the assistant")
    parser.add_argument("--instructions", required=True, help="Instructions for the assistant")
    parser.add_argument("--model", default="gpt-4-turbo", help="Model to use (default: gpt-4-turbo)")
    parser.add_argument("--output", "-o", help="Output file for generated code")
    parser.add_argument("--validate-only", action="store_true", help="Only validate configuration")

    args = parser.parse_args()

    # Create configuration
    config = create_assistant_config(
        name=args.name,
        instructions=args.instructions,
        model=args.model
    )

    # Validate configuration
    errors = validate_assistant_config(config)

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
        print("\n" + "="*50)
        print("Generated Setup Code:")
        print("="*50)
        print(code)


if __name__ == "__main__":
    main()