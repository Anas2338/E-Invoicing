# Multi-Agent Architecture Patterns

This reference covers advanced patterns for implementing multi-agent systems using the OpenAI Agent SDK.

## Coordinator Pattern

A coordinator agent manages other specialized agents and routes tasks appropriately.

```python
import time
from openai import OpenAI

class AgentCoordinator:
    def __init__(self, client):
        self.client = client
        self.agents = {}
        self.setup_agents()

    def setup_agents(self):
        # Create specialized agents
        self.agents['researcher'] = self.client.beta.assistants.create(
            name="Research Agent",
            instructions="Specialized in research and information gathering. Always return structured data with sources.",
            model="gpt-4-turbo",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for current information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"}
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]
        )

        self.agents['analyst'] = self.client.beta.assistants.create(
            name="Data Analyst",
            instructions="Specialized in data analysis and insights. Always provide numerical analysis.",
            model="gpt-4-turbo",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_data",
                        "description": "Analyze numerical data",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "data": {"type": "array", "items": {"type": "number"}},
                                "operation": {"type": "string", "enum": ["mean", "median", "sum", "trend"]}
                            },
                            "required": ["data", "operation"]
                        }
                    }
                }
            ]
        )

    def route_query(self, query, thread_id):
        """Route query to appropriate agent based on content"""
        query_lower = query.lower()

        if any(keyword in query_lower for keyword in ['search', 'find', 'research', 'look up', 'information']):
            return self.run_agent(self.agents['researcher'].id, thread_id, query)
        elif any(keyword in query_lower for keyword in ['analyze', 'data', 'numbers', 'calculate', 'statistics']):
            return self.run_agent(self.agents['analyst'].id, thread_id, query)
        else:
            # Default to researcher for general queries
            return self.run_agent(self.agents['researcher'].id, thread_id, query)

    def run_agent(self, agent_id, thread_id, user_message):
        """Run a specific agent on a thread with user message"""
        # Add user message to thread
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Create and monitor run
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=agent_id
        )

        return self.monitor_run_completion(thread_id, run.id)

    def monitor_run_completion(self, thread_id, run_id):
        """Monitor run status and handle tool calls if needed"""
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run.status == "completed":
                # Get the messages
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="asc"
                )

                # Return the latest assistant message
                for msg in reversed(messages.data):
                    if msg.role == "assistant":
                        return msg.content[0].text.value
                return "No response generated"

            elif run.status == "requires_action":
                # Handle tool calls
                self.handle_tool_calls(run, thread_id)

            elif run.status in ["failed", "cancelled", "expired"]:
                return f"Run failed with status: {run.status}"

            time.sleep(1)  # Wait before checking again

    def handle_tool_calls(self, run, thread_id):
        """Handle required tool calls during run execution"""
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            try:
                # Execute the appropriate function based on tool call
                if tool_call.function.name == "web_search":
                    import json
                    args = json.loads(tool_call.function.arguments)
                    result = self.simulate_web_search(args["query"])
                elif tool_call.function.name == "analyze_data":
                    import json
                    args = json.loads(tool_call.function.arguments)
                    result = self.simulate_data_analysis(args["data"], args["operation"])
                else:
                    result = f"Unknown function: {tool_call.function.name}"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": str(result)
                })
            except Exception as e:
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"Error: {str(e)}"
                })

        # Submit tool outputs to continue the run
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

    def simulate_web_search(self, query):
        """Simulate web search - in practice, integrate with actual search API"""
        return f"Simulated search results for: {query}"

    def simulate_data_analysis(self, data, operation):
        """Simulate data analysis - in practice, implement actual analysis"""
        if operation == "mean":
            return sum(data) / len(data) if data else 0
        elif operation == "sum":
            return sum(data)
        else:
            return f"Operation {operation} on data {data}"

# Usage example
def main():
    client = OpenAI(api_key="your-api-key")
    coordinator = AgentCoordinator(client)

    # Create a thread for the conversation
    thread = client.beta.threads.create()

    # Route different types of queries
    research_result = coordinator.route_query("Find the latest trends in AI", thread.id)
    print(f"Research result: {research_result}")

    analysis_result = coordinator.route_query("Analyze this data: [10, 20, 30, 40]", thread.id)
    print(f"Analysis result: {analysis_result}")

if __name__ == "__main__":
    main()
```

## Hierarchical Agent Pattern

Create a hierarchy where higher-level agents delegate to lower-level specialists.

```python
class HierarchicalAgent:
    def __init__(self, client):
        self.client = client
        self.specialists = {}
        self.manager = None
        self.setup_agents()

    def setup_agents(self):
        # Manager agent that delegates to specialists
        self.manager = self.client.beta.assistants.create(
            name="Manager Agent",
            instructions="You are a manager that delegates tasks to specialists. Break down complex tasks and assign to appropriate specialists.",
            model="gpt-4-turbo",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_task",
                        "description": "Delegate a task to a specialist agent",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "agent_type": {"type": "string", "enum": ["research", "analysis", "writing"]},
                                "task": {"type": "string", "description": "The task to delegate"},
                                "context": {"type": "string", "description": "Context for the task"}
                            },
                            "required": ["agent_type", "task", "context"]
                        }
                    }
                }
            ]
        )

        # Specialist agents
        self.specialists['research'] = self.client.beta.assistants.create(
            name="Research Specialist",
            instructions="You are a research specialist. Conduct thorough research and provide well-sourced information.",
            model="gpt-4-turbo",
            tools=[{
                "type": "function",
                "function": {
                    "name": "search_academic_papers",
                    "description": "Search for academic papers on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"}
                        },
                        "required": ["topic"]
                    }
                }
            }]
        )

        self.specialists['analysis'] = self.client.beta.assistants.create(
            name="Analysis Specialist",
            instructions="You are an analysis specialist. Perform detailed analysis and provide insights.",
            model="gpt-4-turbo",
            tools=[{
                "type": "function",
                "function": {
                    "name": "perform_statistical_analysis",
                    "description": "Perform statistical analysis on data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "items": {"type": "number"}},
                            "analysis_type": {"type": "string", "enum": ["correlation", "regression", "distribution"]}
                        },
                        "required": ["data", "analysis_type"]
                    }
                }
            }]
        )

        self.specialists['writing'] = self.client.beta.assistants.create(
            name="Writing Specialist",
            instructions="You are a writing specialist. Create well-structured, professional content.",
            model="gpt-4-turbo",
            tools=[]
        )

    def process_complex_query(self, query, thread_id):
        """Process a complex query using hierarchical delegation"""
        # Add user query to thread
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=query
        )

        # Run manager agent to delegate tasks
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.manager.id
        )

        return self.monitor_and_delegate(thread_id, run.id)

    def monitor_and_delegate(self, thread_id, run_id):
        """Monitor run and handle delegation to specialists"""
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run.status == "completed":
                # Get final response
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="asc"
                )

                for msg in reversed(messages.data):
                    if msg.role == "assistant":
                        return msg.content[0].text.value
                return "No response generated"

            elif run.status == "requires_action":
                # Handle delegation to specialists
                self.handle_delegation(run, thread_id)

            elif run.status in ["failed", "cancelled", "expired"]:
                return f"Run failed with status: {run.status}"

            time.sleep(1)

    def handle_delegation(self, run, thread_id):
        """Handle delegation to specialist agents"""
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            try:
                import json
                args = json.loads(tool_call.function.arguments)

                if tool_call.function.name == "delegate_task":
                    # Run the appropriate specialist
                    specialist_result = self.run_specialist(
                        args["agent_type"],
                        args["task"],
                        args["context"],
                        thread_id
                    )

                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": specialist_result
                    })
                else:
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": f"Unknown function: {tool_call.function.name}"
                    })
            except Exception as e:
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"Error in delegation: {str(e)}"
                })

        # Submit tool outputs to continue the manager's run
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

    def run_specialist(self, agent_type, task, context, thread_id):
        """Run a specialist agent for a specific task"""
        # Create a new thread for the specialist task
        specialist_thread = self.client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Context: {context}\nTask: {task}"
                }
            ]
        )

        specialist_id = self.specialists[agent_type].id
        run = self.client.beta.threads.runs.create(
            thread_id=specialist_thread.id,
            assistant_id=specialist_id
        )

        # Monitor specialist completion
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=specialist_thread.id,
                run_id=run.id
            )

            if run.status == "completed":
                messages = self.client.beta.threads.messages.list(
                    thread_id=specialist_thread.id,
                    order="asc"
                )

                for msg in reversed(messages.data):
                    if msg.role == "assistant":
                        result = msg.content[0].text.value
                        # Clean up the specialist thread
                        # self.client.beta.threads.delete(specialist_thread.id)  # Uncomment to clean up
                        return result
                return "No response from specialist"

            elif run.status in ["failed", "cancelled", "expired"]:
                # Clean up the specialist thread
                # self.client.beta.threads.delete(specialist_thread.id)  # Uncomment to clean up
                return f"Specialist failed with status: {run.status}"

            time.sleep(1)
```