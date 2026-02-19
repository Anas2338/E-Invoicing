---
name: openai-agent-sdk
description: Build, configure, and use the OpenAI Agent SDK. Helps with agent components (models, tools, memory, workflows), generates correct SDK setup code, shows how to define agents, tools, and handoffs, provides best practices for reliability, safety, and cost control, includes examples for common patterns (multi-agent, tool calling, retrieval, background tasks), and warns when deprecated or incorrect SDK usage is detected.
---

# OpenAI Agent SDK Skill

This skill provides guidance for building, configuring, and using the OpenAI Agent SDK effectively. It helps users create robust, reliable, and safe agents with proper architecture and best practices.

## When to Use This Skill

Use this skill when you need to:
- Design and implement OpenAI agents with the Agent SDK
- Set up agent components (models, tools, memory, workflows)
- Generate correct Agent SDK code with proper patterns
- Implement multi-agent architectures
- Add tool calling and retrieval capabilities
- Ensure reliability, safety, and cost control
- Follow best practices for agent development
- Identify and fix deprecated or incorrect SDK usage

## Core Components of OpenAI Agent SDK

### 1. Agent Definition
- **Agent Class**: The core component that manages conversations and tool execution
- **Model Configuration**: Specify GPT-4, GPT-4 Turbo, or other supported models
- **System Instructions**: Define agent's purpose, behavior, and constraints
- **Tools Configuration**: Attach functions, retrieval, and code interpreter tools

### 2. Tool Integration
- **Function Tools**: Custom functions that agents can call
- **Retrieval Tools**: Knowledge base and document search capabilities
- **Code Interpreter**: Execute code in sandboxed environments
- **Custom Tools**: External API integrations and services

### 3. Memory Management
- **Thread Management**: Maintain conversation history and state
- **Message History**: Store and retrieve conversation context
- **State Persistence**: Save and restore agent state across sessions

## Agent SDK Setup Pattern

```python
from openai import OpenAI
from openai.types.beta.threads import Message, Run

# Initialize the client
client = OpenAI(api_key="your-api-key")

# Create an agent
agent = client.beta.assistants.create(
    name="Assistant Name",
    instructions="System instructions for the agent",
    model="gpt-4-turbo",
    tools=[
        {"type": "function", "function": {...}},
        {"type": "retrieval"},
        {"type": "code_interpreter"}
    ]
)

# Create a thread for conversation
thread = client.beta.threads.create(
    messages=[
        {
            "role": "user",
            "content": "Initial user message"
        }
    ]
)

# Run the agent
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=agent.id
)

# Monitor run status and get response
while run.status in ["queued", "in_progress"]:
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    time.sleep(1)

# Get the final response
messages = client.beta.threads.messages.list(
    thread_id=thread.id,
    order="asc"
)
```

## Best Practices

### 1. Reliability Patterns
- **Run Status Monitoring**: Always check run status before accessing results
- **Error Handling**: Implement proper exception handling for API calls
- **Timeout Management**: Set appropriate timeouts for long-running operations
- **Retry Logic**: Implement exponential backoff for failed requests

### 2. Safety Measures
- **Input Sanitization**: Validate and sanitize user inputs
- **Output Filtering**: Review and filter agent outputs before displaying
- **Rate Limiting**: Implement rate limiting to prevent API abuse
- **Content Moderation**: Use OpenAI's content moderation tools

### 3. Cost Control
- **Token Management**: Monitor token usage and set limits
- **Model Selection**: Choose appropriate models for the task
- **Caching**: Cache responses for repeated queries when appropriate
- **Resource Cleanup**: Delete threads and runs when no longer needed

## Common Patterns

### 1. Multi-Agent Architecture
```python
# Define multiple specialized agents
researcher = client.beta.assistants.create(
    name="Research Agent",
    instructions="Specialized in research and information gathering",
    model="gpt-4-turbo",
    tools=[...]
)

analyst = client.beta.assistants.create(
    name="Analysis Agent",
    instructions="Specialized in data analysis and insights",
    model="gpt-4-turbo",
    tools=[...]
)

# Implement agent handoff logic
def route_to_agent(query, thread_id):
    if "research" in query.lower():
        return run_agent(researcher.id, thread_id)
    elif "analyze" in query.lower():
        return run_agent(analyst.id, thread_id)
    else:
        # Default agent or routing logic
        pass
```

### 2. Tool Calling with Error Handling
```python
def create_tool_with_error_handling():
    return {
        "type": "function",
        "function": {
            "name": "search_database",
            "description": "Search the database for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }

# Handle tool calls in run processing
def handle_tool_calls(run, thread_id):
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        try:
            # Execute the tool call
            result = execute_tool(tool_call)

            # Submit tool output
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=[{
                    "tool_call_id": tool_call.id,
                    "output": str(result)
                }]
            )
        except Exception as e:
            # Handle tool execution errors
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=[{
                    "tool_call_id": tool_call.id,
                    "output": f"Error executing tool: {str(e)}"
                }]
            )
```

### 3. Retrieval-Augmented Generation (RAG)
```python
# Upload files for retrieval
file = client.files.create(
    file=open("knowledge_base.pdf", "rb"),
    purpose="assistants"
)

# Create agent with retrieval tool
rag_agent = client.beta.assistants.create(
    name="RAG Agent",
    instructions="Use provided documents to answer questions",
    model="gpt-4-turbo",
    tools=[{"type": "retrieval"}],
    file_ids=[file.id]
)
```

## Warning: Deprecated or Incorrect Usage

### Common Mistakes to Avoid
1. **Direct Message Creation**: Don't create messages directly without a run
2. **Synchronous Processing**: Don't assume runs complete immediately
3. **Missing Error Handling**: Always handle run failures and tool errors
4. **Inadequate Monitoring**: Don't ignore run status changes
5. **Resource Leaks**: Don't forget to clean up threads and runs

### Correct vs Incorrect Patterns
```python
# ❌ INCORRECT: Not monitoring run status
run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=agent.id)
messages = client.beta.threads.messages.list(thread_id=thread.id)  # May return incomplete messages

# ✅ CORRECT: Monitoring run completion
run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=agent.id)
while run.status in ["queued", "in_progress"]:
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    time.sleep(1)

if run.status == "completed":
    messages = client.beta.threads.messages.list(thread_id=thread.id, order="asc")
else:
    # Handle run failure
    print(f"Run failed with status: {run.status}")
```

## Complete Implementation Example

For a complete implementation with all best practices, see the references below.

## When to Consult References

- **Advanced Multi-Agent Patterns**: See `references/multi-agent.md`
- **Security Best Practices**: See `references/security.md`
- **Cost Optimization**: See `references/cost-control.md`
- **Error Handling Patterns**: See `references/error-handling.md`
- **Testing Strategies**: See `references/testing.md`