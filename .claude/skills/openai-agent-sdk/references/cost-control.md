# Cost Control for OpenAI Agent SDK

This reference covers strategies and best practices for controlling costs when using the OpenAI Agent SDK.

## Understanding OpenAI Pricing

### Current Pricing Model (as of 2024)
- **GPT-4 Turbo**: $0.01/1K input tokens, $0.03/1K output tokens
- **GPT-4**: $0.03/1K input tokens, $0.06/1K output tokens
- **GPT-3.5 Turbo**: $0.0005/1K input tokens, $0.0015/1K output tokens
- **Storage**: $0.05/GB/month for uploaded files
- **Usage-based**: Costs accumulate based on actual token usage

### Cost Calculation Formula
```
Total Cost = (Input Tokens ÷ 1000 × Price Per 1K Input) + (Output Tokens ÷ 1000 × Price Per 1K Output)
```

## Token Monitoring and Tracking

### Real-time Token Tracking
```python
import time
from collections import defaultdict
from datetime import datetime, timedelta

class TokenTracker:
    def __init__(self):
        self.daily_usage = defaultdict(lambda: {'input_tokens': 0, 'output_tokens': 0, 'cost': 0})
        self.monthly_budget = 100.0  # Default budget
        self.current_month = datetime.now().month

    def record_usage(self, input_tokens: int, output_tokens: int, model: str = "gpt-4-turbo"):
        """Record token usage for a specific interaction"""
        today = datetime.now().date()

        # Calculate cost based on model
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        self.daily_usage[today]['input_tokens'] += input_tokens
        self.daily_usage[today]['output_tokens'] += output_tokens
        self.daily_usage[today]['cost'] += cost

        return self.daily_usage[today]['cost']

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost based on model pricing"""
        pricing = {
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }

        rates = pricing.get(model, pricing["gpt-4-turbo"])  # Default to gpt-4-turbo
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]

        return input_cost + output_cost

    def get_daily_total(self, date=None):
        """Get total cost for a specific day"""
        if date is None:
            date = datetime.now().date()
        return self.daily_usage[date]['cost']

    def get_monthly_total(self):
        """Get total cost for the current month"""
        current_month = datetime.now().month
        monthly_total = 0

        for date, usage in self.daily_usage.items():
            if date.month == current_month:
                monthly_total += usage['cost']

        return monthly_total

    def is_within_budget(self):
        """Check if current month's usage is within budget"""
        return self.get_monthly_total() <= self.monthly_budget

    def get_remaining_budget(self):
        """Get remaining budget for the month"""
        return self.monthly_budget - self.get_monthly_total()
```

### Monitoring Run Costs
```python
from openai import OpenAI

class CostAwareClient:
    def __init__(self, api_key: str, budget_limit: float = 100.0):
        self.client = OpenAI(api_key=api_key)
        self.token_tracker = TokenTracker()
        self.budget_limit = budget_limit
        self.budget_alert_threshold = 0.8  # Alert at 80% of budget

    def create_assistant_with_cost_monitoring(self, **kwargs):
        """Create an assistant with cost monitoring"""
        assistant = self.client.beta.assistants.create(**kwargs)

        # Log initial cost (minimal for creation)
        self.token_tracker.record_usage(10, 10, kwargs.get('model', 'gpt-4-turbo'))

        return assistant

    def run_assistant_with_cost_limits(self, thread_id: str, assistant_id: str, model: str = "gpt-4-turbo"):
        """Run an assistant with cost monitoring and limits"""
        # Check if we're approaching budget limit
        if self.token_tracker.get_monthly_total() > self.budget_limit * self.budget_alert_threshold:
            print(f"⚠️  WARNING: Approaching budget limit. Current: ${self.token_tracker.get_monthly_total():.2f}, Limit: ${self.budget_limit:.2f}")

        # Create the run
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Monitor the run
        final_run = self.monitor_run_with_cost_tracking(thread_id, run.id, model)

        return final_run

    def monitor_run_with_cost_tracking(self, thread_id: str, run_id: str, model: str):
        """Monitor run completion and track costs"""
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run.status == "completed":
                # Get usage statistics from the run
                # Note: This is approximate since OpenAI doesn't expose exact usage per run in the beta API
                # In practice, you'd need to estimate based on response length
                estimated_input_tokens = self.estimate_tokens_from_messages(thread_id)
                estimated_output_tokens = self.estimate_tokens_from_response(thread_id)

                cost = self.token_tracker.record_usage(estimated_input_tokens, estimated_output_tokens, model)

                # Check if budget exceeded
                if not self.token_tracker.is_within_budget():
                    print(f"🚨 BUDGET EXCEEDED: Current cost ${self.token_tracker.get_monthly_total():.2f}")

                return run

            elif run.status == "requires_action":
                # Handle tool calls and continue monitoring
                self.handle_tool_calls_with_cost_tracking(run, thread_id, model)

            elif run.status in ["failed", "cancelled", "expired"]:
                return run

            time.sleep(1)

    def estimate_tokens_from_messages(self, thread_id: str) -> int:
        """Estimate input tokens from thread messages"""
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        total_chars = 0

        for message in messages.data:
            for content_block in message.content:
                if hasattr(content_block, 'text'):
                    total_chars += len(content_block.text.value)

        # Rough estimate: 1 token ≈ 4 characters
        return max(total_chars // 4, 10)  # Minimum 10 tokens

    def estimate_tokens_from_response(self, thread_id: str) -> int:
        """Estimate output tokens from latest assistant response"""
        messages = self.client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)

        if messages.data and messages.data[0].role == "assistant":
            content = messages.data[0].content[0].text.value if messages.data[0].content else ""
            return max(len(content) // 4, 5)  # Minimum 5 tokens

        return 0

    def handle_tool_calls_with_cost_tracking(self, run, thread_id: str, model: str):
        """Handle tool calls with cost tracking"""
        # Process tool calls
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            # Estimate cost impact of tool execution
            # In practice, tool execution doesn't directly consume tokens but may lead to more agent responses

            # Simulate tool execution and continue
            result = self.execute_tool_safely(tool_call)

            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": str(result)
            })

            # Record small cost for tool call processing
            self.token_tracker.record_usage(5, 2, model)  # Small overhead

        # Submit tool outputs
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

    def execute_tool_safely(self, tool_call):
        """Safely execute a tool call"""
        # Implementation depends on your specific tools
        # This is a placeholder
        return f"Tool {tool_call.function.name} executed safely"
```

## Cost Optimization Strategies

### 1. Model Selection Optimization
```python
class ModelOptimizer:
    @staticmethod
    def select_optimal_model(task_complexity: str, sensitivity: str = "normal") -> str:
        """
        Select the most cost-effective model based on task requirements
        """
        model_map = {
            ("simple", "normal"): "gpt-3.5-turbo",
            ("moderate", "normal"): "gpt-4-turbo",
            ("complex", "normal"): "gpt-4-turbo",
            ("simple", "critical"): "gpt-4-turbo",  # Use better model for critical tasks even if simple
            ("moderate", "critical"): "gpt-4-turbo",
            ("complex", "critical"): "gpt-4-turbo",
        }

        return model_map.get((task_complexity, sensitivity), "gpt-4-turbo")

    @staticmethod
    def can_downgrade_model(current_model: str, task_requirements: dict) -> tuple[bool, str]:
        """
        Determine if a cheaper model can be used for the current task
        """
        if current_model == "gpt-4" and not task_requirements.get('reasoning', False):
            return True, "gpt-4-turbo"
        elif current_model == "gpt-4-turbo" and task_requirements.get('simple', False):
            return True, "gpt-3.5-turbo"

        return False, current_model
```

### 2. Caching and Memoization
```python
import hashlib
import json
from datetime import datetime, timedelta

class ResponseCache:
    def __init__(self, ttl_hours: int = 24):
        self.cache = {}
        self.ttl = timedelta(hours=ttl_hours)

    def _generate_key(self, user_input: str, context: str = "") -> str:
        """Generate a cache key from input and context"""
        combined = f"{user_input}|{context}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_cached_response(self, user_input: str, context: str = "") -> tuple[bool, str]:
        """Get cached response if available and not expired"""
        key = self._generate_key(user_input, context)

        if key in self.cache:
            cached_item = self.cache[key]
            if datetime.now() - cached_item['timestamp'] < self.ttl:
                return True, cached_item['response']
            else:
                # Remove expired entry
                del self.cache[key]

        return False, ""

    def cache_response(self, user_input: str, context: str, response: str):
        """Cache a response"""
        key = self._generate_key(user_input, context)
        self.cache[key] = {
            'response': response,
            'timestamp': datetime.now()
        }

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics"""
        total_items = len(self.cache)
        expired_items = sum(1 for item in self.cache.values()
                           if datetime.now() - item['timestamp'] >= self.ttl)

        return {
            'total_cached': total_items,
            'expired': expired_items,
            'valid': total_items - expired_items
        }

# Usage in agent system
class CachedAgentSystem:
    def __init__(self, cost_client: CostAwareClient):
        self.cost_client = cost_client
        self.response_cache = ResponseCache(ttl_hours=24)

    def get_response_with_caching(self, thread_id: str, user_input: str, context: str = ""):
        """Get agent response with caching to reduce costs"""
        # Check cache first
        is_cached, cached_response = self.response_cache.get_cached_response(user_input, context)

        if is_cached:
            print("✅ Using cached response - saving tokens and cost")
            return cached_response

        # If not cached, get fresh response
        # First add user message to thread
        self.cost_client.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        # Run the assistant
        run = self.cost_client.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.get_active_assistant_id()  # You'd implement this
        )

        # Monitor completion
        while run.status in ["queued", "in_progress"]:
            run = self.cost_client.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            time.sleep(1)

        if run.status == "completed":
            messages = self.cost_client.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="asc"
            )

            # Get the latest assistant response
            response = ""
            for msg in reversed(messages.data):
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    break

            # Cache the response
            self.response_cache.cache_response(user_input, context, response)

            return response
        else:
            return f"Error: Run failed with status {run.status}"
```

### 3. Resource Cleanup
```python
class ResourceManager:
    def __init__(self, client):
        self.client = client
        self.cleanup_threshold_days = 7  # Days after which inactive resources are cleaned up

    def cleanup_old_threads(self):
        """Clean up old threads to save storage costs"""
        import openai
        from datetime import datetime, timedelta

        # Get all threads (in practice, you'd paginate through all threads)
        # Note: OpenAI API doesn't currently expose a way to list all threads
        # You'd need to track thread IDs in your application

        # Example cleanup logic (would need thread tracking in your app):
        cutoff_date = datetime.now() - timedelta(days=self.cleanup_threshold_days)

        # This is pseudocode - you'd need to implement thread tracking in your app
        # for thread_id in self.tracked_threads:
        #     if self.get_thread_age(thread_id) > self.cleanup_threshold_days:
        #         try:
        #             self.client.beta.threads.delete(thread_id)
        #             print(f"Cleaned up thread {thread_id}")
        #         except Exception as e:
        #             print(f"Failed to clean up thread {thread_id}: {e}")

    def cleanup_old_files(self):
        """Clean up old uploaded files to save storage costs"""
        files = self.client.files.list()

        for file_obj in files:
            # Assuming file_obj has a created_at attribute
            file_date = datetime.fromtimestamp(file_obj.created_at)
            age = datetime.now() - file_date

            if age.days > self.cleanup_threshold_days:
                # Check if file is still in use before deleting
                if not self.is_file_in_use(file_obj.id):
                    try:
                        self.client.files.delete(file_obj.id)
                        print(f"Cleaned up file {file_obj.filename}")
                    except Exception as e:
                        print(f"Failed to clean up file {file_obj.filename}: {e}")

    def is_file_in_use(self, file_id: str) -> bool:
        """Check if a file is still referenced by any assistants"""
        assistants = self.client.beta.assistants.list()

        for assistant in assistants:
            if hasattr(assistant, 'file_ids') and file_id in assistant.file_ids:
                return True
        return False
```

## Budget Alerts and Limits

### Automated Budget Management
```python
class BudgetManager:
    def __init__(self, token_tracker: TokenTracker, alert_callback=None):
        self.token_tracker = token_tracker
        self.alert_callback = alert_callback
        self.thresholds = {
            0.5: "Monthly budget 50% reached",
            0.75: "Monthly budget 75% reached",
            0.9: "Monthly budget 90% reached",
            1.0: "Monthly budget limit reached"
        }

    def check_budget_and_alert(self):
        """Check current spending against budget and send alerts if needed"""
        monthly_total = self.token_tracker.get_monthly_total()
        budget_limit = self.token_tracker.monthly_budget

        for threshold, message in sorted(self.thresholds.items(), reverse=True):
            if monthly_total >= budget_limit * threshold:
                self.send_alert(message, monthly_total, budget_limit)
                return True  # Alert sent, stop checking lower thresholds

        return False

    def send_alert(self, message: str, current: float, limit: float):
        """Send budget alert"""
        alert_msg = f"{message} - Current: ${current:.2f}, Limit: ${limit:.2f}"

        if self.alert_callback:
            self.alert_callback(alert_msg)
        else:
            print(f"🚨 BUDGET ALERT: {alert_msg}")

    def set_new_budget(self, new_budget: float):
        """Update the monthly budget limit"""
        old_budget = self.token_tracker.monthly_budget
        self.token_tracker.monthly_budget = new_budget
        print(f"Budget updated from ${old_budget:.2f} to ${new_budget:.2f}")
```

## Complete Cost-Controlled Implementation Example

```python
def create_cost_efficient_agent_system(api_key: str, monthly_budget: float = 100.0):
    """
    Create a complete cost-controlled agent system
    """
    # Initialize core components
    cost_client = CostAwareClient(api_key, monthly_budget)
    budget_manager = BudgetManager(cost_client.token_tracker)
    model_optimizer = ModelOptimizer()
    cached_system = CachedAgentSystem(cost_client)

    # Create the main agent with cost considerations
    def create_cost_aware_agent(name: str, instructions: str, task_complexity: str = "moderate"):
        # Optimize model selection based on task
        model = model_optimizer.select_optimal_model(task_complexity)

        assistant = cost_client.create_assistant_with_cost_monitoring(
            name=name,
            instructions=instructions,
            model=model,
            tools=[]  # Add appropriate tools
        )

        return assistant

    # Main function to process requests with cost controls
    def process_request_with_cost_control(thread_id: str, user_input: str, context: str = ""):
        # Check budget before processing
        budget_manager.check_budget_and_alert()

        # Use cached response if available, otherwise process normally
        return cached_system.get_response_with_caching(thread_id, user_input, context)

    return {
        'create_agent': create_cost_aware_agent,
        'process_request': process_request_with_cost_control,
        'token_tracker': cost_client.token_tracker,
        'budget_manager': budget_manager
    }

# Usage example
if __name__ == "__main__":
    import os

    # Initialize cost-controlled agent system
    api_key = os.getenv("OPENAI_API_KEY")
    agent_system = create_cost_efficient_agent_system(api_key, monthly_budget=50.0)

    # Create an assistant
    assistant = agent_system['create_agent'](
        name="Cost-Conscious Assistant",
        instructions="Help users with their queries efficiently.",
        task_complexity="moderate"
    )

    # Create a thread
    thread = OpenAI(api_key=api_key).beta.threads.create()

    # Process a request with cost control
    response = agent_system['process_request'](
        thread_id=thread.id,
        user_input="What's the weather like today?",
        context="user_location: New York"
    )

    print(f"Response: {response}")
    print(f"Current month cost: ${agent_system['token_tracker'].get_monthly_total():.2f}")
```