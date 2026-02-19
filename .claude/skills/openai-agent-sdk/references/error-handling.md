# Error Handling Patterns for OpenAI Agent SDK

This reference covers comprehensive error handling patterns when working with the OpenAI Agent SDK.

## Common Error Types and Handling

### API-Level Errors
```python
from openai import OpenAI, APIError, RateLimitError, AuthenticationError
import time
import random
from typing import Optional, Dict, Any

class OpenAIAPIErrorHandler:
    @staticmethod
    def handle_api_error(error: Exception, retry_count: int = 0) -> Dict[str, Any]:
        """Handle different types of OpenAI API errors"""
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'retry_count': retry_count,
            'should_retry': False,
            'delay_before_retry': 0
        }

        if isinstance(error, RateLimitError):
            error_info.update({
                'should_retry': True,
                'delay_before_retry': min(2 ** retry_count * 1 + random.uniform(0, 1), 60)
            })
        elif isinstance(error, AuthenticationError):
            error_info.update({
                'should_retry': False,
                'fatal': True
            })
        elif isinstance(error, APIError):
            # Some API errors might be retryable
            if "server_error" in str(error).lower():
                error_info.update({
                    'should_retry': True,
                    'delay_before_retry': min(2 ** retry_count * 0.5, 30)
                })

        return error_info

    @staticmethod
    def exponential_backoff_with_jitter(max_retries: int = 3):
        """Generator for exponential backoff with jitter"""
        for attempt in range(max_retries):
            yield min(2 ** attempt + random.uniform(0, 1), 60)
```

### Run-Level Error Handling
```python
from enum import Enum

class RunStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REQUIRES_ACTION = "requires_action"

class RunErrorHandler:
    @staticmethod
    def handle_run_failure(run, thread_id: str, client) -> Dict[str, Any]:
        """Handle different run failure states"""
        if run.status == RunStatus.FAILED.value:
            return {
                'success': False,
                'error': f"Run failed: {getattr(run, 'last_error', {}).get('message', 'Unknown error')}",
                'can_retry': True
            }
        elif run.status == RunStatus.EXPIRED.value:
            return {
                'success': False,
                'error': "Run expired - thread may be too old or inactive",
                'can_retry': False
            }
        elif run.status == RunStatus.CANCELLED.value:
            return {
                'success': False,
                'error': "Run was cancelled",
                'can_retry': True
            }
        else:
            return {
                'success': False,
                'error': f"Unexpected run status: {run.status}",
                'can_retry': False
            }

    @staticmethod
    def safe_get_run_result(client, thread_id: str, run_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Safely get run result with timeout and error handling"""
        import time

        start_time = time.time()
        run = None

        try:
            while time.time() - start_time < timeout:
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )

                if run.status in [RunStatus.COMPLETED.value, RunStatus.FAILED.value,
                                 RunStatus.CANCELLED.value, RunStatus.EXPIRED.value]:
                    break
                elif run.status == RunStatus.REQUIRES_ACTION.value:
                    # Handle tool calls
                    return {'status': RunStatus.REQUIRES_ACTION.value, 'run': run}

                time.sleep(1)

            if run is None:
                return {
                    'success': False,
                    'error': f"Could not retrieve run within {timeout} seconds",
                    'timeout': True
                }

            if run.status == RunStatus.COMPLETED.value:
                # Get the messages
                messages = client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="asc"
                )

                # Find the latest assistant message
                for msg in reversed(messages.data):
                    if msg.role == "assistant":
                        return {
                            'success': True,
                            'response': msg.content[0].text.value if msg.content else "",
                            'run_id': run_id
                        }

                return {
                    'success': False,
                    'error': "No assistant response found in completed run"
                }
            else:
                return RunErrorHandler.handle_run_failure(run, thread_id, client)

        except Exception as e:
            return {
                'success': False,
                'error': f"Exception while monitoring run: {str(e)}"
            }
```

## Robust Agent Client with Error Handling

```python
class RobustAgentClient:
    def __init__(self, api_key: str, max_retries: int = 3, timeout: int = 300):
        self.client = OpenAI(api_key=api_key)
        self.max_retries = max_retries
        self.timeout = timeout
        self.api_handler = OpenAIAPIErrorHandler()
        self.run_handler = RunErrorHandler()

    def create_assistant_with_retry(self, **kwargs) -> Any:
        """Create assistant with retry logic"""
        for attempt in range(self.max_retries):
            try:
                return self.client.beta.assistants.create(**kwargs)
            except Exception as e:
                error_info = self.api_handler.handle_api_error(e, attempt)

                if not error_info['should_retry'] or attempt >= self.max_retries - 1:
                    raise e

                if error_info['delay_before_retry']:
                    time.sleep(error_info['delay_before_retry'])

        raise Exception(f"Failed to create assistant after {self.max_retries} attempts")

    def run_assistant_with_error_handling(self, thread_id: str, assistant_id: str) -> Dict[str, Any]:
        """Run assistant with comprehensive error handling"""
        for attempt in range(self.max_retries):
            try:
                # Create the run
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=assistant_id
                )

                # Monitor the run with error handling
                result = self.run_handler.safe_get_run_result(
                    self.client, thread_id, run.id, self.timeout
                )

                # If requires action, handle tool calls
                if result.get('status') == RunStatus.REQUIRES_ACTION.value:
                    tool_result = self.handle_tool_calls_with_retry(
                        result['run'], thread_id
                    )

                    if tool_result['success']:
                        # Continue monitoring after tool calls
                        continue_result = self.run_handler.safe_get_run_result(
                            self.client, thread_id, run.id, self.timeout
                        )
                        return continue_result
                    else:
                        return tool_result

                return result

            except Exception as e:
                error_info = self.api_handler.handle_api_error(e, attempt)

                if not error_info['should_retry'] or attempt >= self.max_retries - 1:
                    return {
                        'success': False,
                        'error': f"Failed after {self.max_retries} attempts: {str(e)}"
                    }

                if error_info['delay_before_retry']:
                    time.sleep(error_info['delay_before_retry'])

        return {'success': False, 'error': 'Max retries exceeded'}

    def handle_tool_calls_with_retry(self, run, thread_id: str) -> Dict[str, Any]:
        """Handle tool calls with error handling"""
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            try:
                # Execute the tool
                output = self.execute_tool_safely(tool_call)

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": str(output)
                })

            except Exception as e:
                # Log the error and return an error message as output
                error_output = f"Error executing tool {tool_call.function.name}: {str(e)}"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": error_output
                })

        try:
            # Submit all tool outputs at once
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )

            return {'success': True}

        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to submit tool outputs: {str(e)}"
            }

    def execute_tool_safely(self, tool_call) -> Any:
        """Safely execute a tool call with error handling"""
        import json

        try:
            # Parse the function arguments
            args = json.loads(tool_call.function.arguments)

            # Map function name to actual function
            tool_functions = {
                "get_current_weather": self.get_weather,
                "search_web": self.web_search,
                "calculate": self.perform_calculation,
                # Add more functions as needed
            }

            func = tool_functions.get(tool_call.function.name)
            if func:
                return func(**args)
            else:
                return f"Unknown function: {tool_call.function.name}"

        except json.JSONDecodeError:
            return f"Invalid JSON arguments for function {tool_call.function.name}"
        except Exception as e:
            return f"Error in {tool_call.function.name}: {str(e)}"

    # Example tool functions (implement based on your needs)
    def get_weather(self, location: str) -> str:
        """Example weather tool"""
        # In practice, call a weather API
        return f"Weather in {location}: Sunny, 72°F"

    def web_search(self, query: str) -> str:
        """Example web search tool"""
        # In practice, call a search API
        return f"Search results for '{query}': [simulated results]"

    def perform_calculation(self, expression: str) -> float:
        """Example calculation tool"""
        # In practice, use a safe evaluation method
        # Never use eval() in production - use libraries like numexpr or similar
        try:
            # This is a simplified example - use a safe evaluator in production
            allowed_operators = ['+', '-', '*', '/', '(', ')', '.', ' ']
            safe_expression = ''.join(c for c in expression if c.isdigit() or c in allowed_operators)
            return eval(safe_expression)  # NOSONAR - Simplified example
        except:
            return 0.0
```

## Circuit Breaker Pattern

```python
import time
from enum import Enum

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

    def call(self, func, *args, **kwargs):
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
                self._reset()
                return result
            except Exception as e:
                self._record_failure()
                raise e

        if self.state == CircuitState.CLOSED:
            try:
                result = func(*args, **kwargs)
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

    def _reset(self):
        """Reset the circuit breaker after successful operation"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

class CircuitBreakerAgentClient(RobustAgentClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120)

    def run_assistant_with_circuit_breaker(self, thread_id: str, assistant_id: str) -> Dict[str, Any]:
        """Run assistant with circuit breaker protection"""
        try:
            return self.circuit_breaker.call(
                self.run_assistant_with_error_handling,
                thread_id=thread_id,
                assistant_id=assistant_id
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Circuit breaker protection triggered: {str(e)}'
            }
```

## Fallback Strategies

```python
class FallbackAgentManager:
    def __init__(self, primary_client: RobustAgentClient):
        self.primary_client = primary_client
        self.fallback_clients = []
        self.fallback_enabled = True

    def add_fallback_client(self, client):
        """Add a fallback client to use if primary fails"""
        self.fallback_clients.append(client)

    def run_with_fallback(self, thread_id: str, assistant_id: str) -> Dict[str, Any]:
        """Run with fallback strategy"""
        clients_to_try = [self.primary_client] + self.fallback_clients

        for i, client in enumerate(clients_to_try):
            try:
                if hasattr(client, 'run_assistant_with_error_handling'):
                    result = client.run_assistant_with_error_handling(
                        thread_id=thread_id,
                        assistant_id=assistant_id
                    )
                else:
                    # Assume it's a basic OpenAI client
                    run = client.beta.threads.runs.create(
                        thread_id=thread_id,
                        assistant_id=assistant_id
                    )
                    result = {'success': True, 'run': run}  # Simplified

                if result.get('success', False):
                    if i > 0:  # Not the primary client
                        print(f"✅ Fallback client {i} succeeded")
                    return result

            except Exception as e:
                print(f"Client {i} failed: {str(e)}")
                continue

        return {
            'success': False,
            'error': 'All clients failed including fallbacks'
        }

    def enable_fallback(self, enabled: bool):
        """Enable or disable fallback mechanism"""
        self.fallback_enabled = enabled
```

## Complete Error-Handled Example

```python
def create_production_ready_agent_system(api_key: str):
    """
    Create a production-ready agent system with comprehensive error handling
    """
    # Create the robust client with circuit breaker
    robust_client = CircuitBreakerAgentClient(
        api_key=api_key,
        max_retries=3,
        timeout=300
    )

    # Create fallback manager
    fallback_manager = FallbackAgentManager(robust_client)

    # You could add additional fallback clients here
    # For now, we'll just use the same client as fallback (in production, use different API keys/endpoints)

    def safe_process_request(thread_id: str, assistant_id: str) -> Dict[str, Any]:
        """Safely process a request with all error handling mechanisms"""
        try:
            # Use fallback system
            result = fallback_manager.run_with_fallback(thread_id, assistant_id)

            if not result['success']:
                # Return a safe default response
                return {
                    'success': False,
                    'response': "I'm currently experiencing technical difficulties. Please try again later.",
                    'error': result.get('error', 'Unknown error occurred'),
                    'fallback_used': True
                }

            return result

        except Exception as e:
            return {
                'success': False,
                'response': "An unexpected error occurred. Our team has been notified.",
                'error': str(e),
                'fallback_used': True
            }

    return {
        'client': robust_client,
        'fallback_manager': fallback_manager,
        'process_request': safe_process_request
    }

# Usage example
if __name__ == "__main__":
    import os

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        exit(1)

    # Create production-ready system
    agent_system = create_production_ready_agent_system(api_key)

    # Create a thread
    thread = agent_system['client'].client.beta.threads.create(
        messages=[{
            "role": "user",
            "content": "Hello, how are you?"
        }]
    )

    # Create an assistant
    assistant = agent_system['client'].create_assistant_with_retry(
        name="Robust Assistant",
        instructions="You are a helpful assistant.",
        model="gpt-4-turbo"
    )

    # Process request safely
    result = agent_system['process_request'](thread.id, assistant.id)

    if result['success']:
        print(f"✅ Success: {result.get('response', 'Response processed')}")
    else:
        print(f"❌ Error: {result['error']}")
```