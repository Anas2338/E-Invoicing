# AI Agent Tests

This directory contains test files for the AI Agent.

## Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests
└── fixtures/       # Test fixtures and sample data
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_agent.py

# Run with coverage
pytest --cov=. tests/
```

## Test Coverage

Tests should cover:
- Agent orchestrator logic
- Individual skills (error handler, retry manager, etc.)
- AI client with fallback logic
- Database operations
- Configuration validation
- Metrics collection

## Writing Tests

Use pytest fixtures for common setup:
```python
import pytest
from agent import AIAgent

@pytest.fixture
def agent():
    return AIAgent()

def test_agent_initialization(agent):
    assert agent is not None
```
