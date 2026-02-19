# Security Best Practices for OpenAI Agent SDK

This reference covers security considerations and best practices when implementing agents with the OpenAI Agent SDK.

## Authentication and Authorization

### API Key Management
```python
import os
from openai import OpenAI

# Use environment variables for API keys
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# For multi-user applications, consider using scoped API keys
def get_client_for_user(user_id):
    # Retrieve user-specific API key from secure storage
    user_api_key = get_user_api_key(user_id)
    return OpenAI(api_key=user_api_key)
```

### Role-Based Access Control
```python
class SecureAgentManager:
    def __init__(self, client):
        self.client = client
        self.permissions = {}

    def can_access_agent(self, user_id, agent_id):
        """Check if user has permission to access a specific agent"""
        user_perms = self.permissions.get(user_id, [])
        return agent_id in user_perms

    def create_user_limited_agent(self, user_id, agent_config):
        """Create an agent with limited permissions based on user role"""
        # Validate user permissions
        if not self.validate_user_permissions(user_id, agent_config):
            raise PermissionError("User lacks required permissions")

        # Create agent with restricted tools
        restricted_tools = self.filter_allowed_tools(user_id, agent_config.get('tools', []))

        return self.client.beta.assistants.create(
            name=agent_config['name'],
            instructions=agent_config['instructions'],
            model=agent_config['model'],
            tools=restricted_tools
        )

    def validate_user_permissions(self, user_id, agent_config):
        """Validate that user can create agent with specified configuration"""
        # Implementation depends on your permission system
        required_perms = self.extract_required_permissions(agent_config)
        user_perms = self.get_user_permissions(user_id)
        return all(perm in user_perms for perm in required_perms)

    def filter_allowed_tools(self, user_id, tools):
        """Filter tools based on user permissions"""
        user_perms = self.get_user_permissions(user_id)
        allowed_tools = []

        for tool in tools:
            if self.tool_allowed_for_user(tool, user_perms):
                allowed_tools.append(tool)

        return allowed_tools
```

## Input Sanitization and Validation

### Sanitizing User Inputs
```python
import re
import html
from typing import Dict, Any

class InputSanitizer:
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text input to prevent injection attacks"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>\\"\';]', '', text)
        # HTML encode to prevent XSS
        sanitized = html.escape(sanitized)
        return sanitized.strip()

    @staticmethod
    def validate_json_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate that JSON data conforms to expected schema"""
        # Implementation depends on your validation requirements
        # Could use jsonschema library for more robust validation
        required_keys = schema.get('required', [])
        return all(key in data for key in required_keys)

    @staticmethod
    def sanitize_agent_instructions(instructions: str) -> str:
        """Sanitize agent instructions to prevent prompt injection"""
        # Remove system-level instructions that could override behavior
        dangerous_patterns = [
            r'ignore previous instructions',
            r'act as a different ai',
            r'disregard safety guidelines',
            r'system:',
            r'<sys>',
            r'</sys>'
        ]

        sanitized = instructions.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized):
                raise ValueError(f"Dangerous instruction pattern detected: {pattern}")

        return instructions
```

## Output Filtering and Validation

### Content Moderation
```python
def moderate_content(content: str) -> Dict[str, Any]:
    """Moderate content using OpenAI's moderation API"""
    from openai import OpenAI

    client = OpenAI()
    moderation_response = client.moderations.create(input=content)

    results = moderation_response.results[0]

    return {
        'flagged': results.flagged,
        'categories': results.categories.model_dump(),
        'category_scores': results.category_scores.model_dump()
    }

def filter_agent_response(response: str) -> str:
    """Filter agent response to remove potentially harmful content"""
    # Apply content moderation
    moderation = moderate_content(response)

    if moderation['flagged']:
        # Handle flagged content based on severity
        if moderation['categories']['sexual'] > 0.8:
            return "Response filtered due to inappropriate content."
        elif moderation['categories']['hate'] > 0.8:
            return "Response filtered due to hate speech."
        elif moderation['categories']['violence'] > 0.8:
            return "Response filtered due to violent content."

    return response
```

## Secure Tool Implementation

### Safe Function Tool Execution
```python
import subprocess
import tempfile
import os
from pathlib import Path

class SecureToolExecutor:
    @staticmethod
    def safe_execute_command(command: str, allowed_commands: list = None) -> str:
        """Safely execute system commands with whitelisting"""
        if allowed_commands and not any(cmd in command for cmd in allowed_commands):
            raise ValueError("Command not in allowed list")

        # Validate command doesn't contain dangerous elements
        dangerous_elements = [';', '&', '|', '$(', '`']
        if any(elem in command for elem in dangerous_elements):
            raise ValueError("Command contains dangerous elements")

        try:
            # Execute in a controlled environment
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=tempfile.mkdtemp()  # Temporary directory
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Command execution failed: {str(e)}"

    @staticmethod
    def safe_file_operations(file_path: str, operation: str, content: str = None) -> str:
        """Safely perform file operations with validation"""
        # Validate file path doesn't escape allowed directories
        base_dir = Path("/safe/app/data/")
        target_path = (base_dir / file_path).resolve()

        if not str(target_path).startswith(str(base_dir)):
            raise ValueError("Path escapes allowed directory")

        if operation == "read":
            with open(target_path, 'r') as f:
                return f.read()
        elif operation == "write" and content is not None:
            with open(target_path, 'w') as f:
                f.write(content)
            return f"File {target_path} written successfully"
        else:
            raise ValueError("Invalid operation")
```

## Privacy Protection

### Data Minimization and Retention
```python
import time
from datetime import datetime, timedelta

class PrivacyManager:
    def __init__(self):
        self.retention_period = timedelta(days=30)  # Default 30-day retention

    def should_retain_conversation(self, thread_id: str) -> bool:
        """Determine if a conversation should be retained"""
        # Check if thread is older than retention period
        thread_created = self.get_thread_creation_time(thread_id)
        if datetime.now() - thread_created > self.retention_period:
            return False
        return True

    def anonymize_conversation_data(self, messages: list) -> list:
        """Anonymize conversation data by removing personally identifiable information"""
        anonymized_messages = []

        for message in messages:
            # Remove or hash PII
            content = self.remove_pii(message.content[0].text.value if message.content else "")

            anonymized_messages.append({
                'role': message.role,
                'content': content,
                'timestamp': message.created_at  # Keep timestamp for analytics
            })

        return anonymized_messages

    def remove_pii(self, text: str) -> str:
        """Remove personally identifiable information from text"""
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REMOVED]', text)

        # Phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REMOVED]', text)

        # Credit card numbers
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC_REMOVED]', text)

        # SSN pattern
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REMOVED]', text)

        return text
```

## Audit Logging

### Activity Logging for Compliance
```python
import logging
from datetime import datetime

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('agent_audit')
        handler = logging.FileHandler('agent_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_agent_access(self, user_id: str, agent_id: str, action: str):
        """Log agent access for audit trail"""
        self.logger.info(f"USER:{user_id} | AGENT:{agent_id} | ACTION:{action} | TIME:{datetime.now()}")

    def log_tool_execution(self, user_id: str, tool_name: str, params: dict):
        """Log tool execution for security monitoring"""
        # Log only non-sensitive parameters
        safe_params = {k: v for k, v in params.items() if k != 'password'}
        self.logger.info(f"USER:{user_id} | TOOL:{tool_name} | PARAMS:{safe_params} | TIME:{datetime.now()}")

    def log_security_event(self, event_type: str, details: str):
        """Log security-related events"""
        self.logger.warning(f"SECURITY_EVENT:{event_type} | DETAILS:{details} | TIME:{datetime.now()}")
```

## Implementation Example

```python
def create_secure_agent_system():
    """Example implementation of a secure agent system"""
    from openai import OpenAI
    import os

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Initialize security components
    sanitizer = InputSanitizer()
    executor = SecureToolExecutor()
    privacy_manager = PrivacyManager()
    audit_logger = AuditLogger()

    # Create a secure agent with validation
    def create_secured_agent(user_id, config):
        # Validate user permissions
        if not can_user_create_agent(user_id, config):
            raise PermissionError("Insufficient permissions")

        # Sanitize inputs
        sanitized_name = sanitizer.sanitize_text(config['name'])
        sanitized_instructions = sanitizer.sanitize_agent_instructions(config['instructions'])

        # Log the creation
        audit_logger.log_agent_access(user_id, "new_agent", "CREATE")

        # Create the agent
        agent = client.beta.assistants.create(
            name=sanitized_name,
            instructions=sanitized_instructions,
            model=config['model'],
            tools=config.get('tools', [])
        )

        return agent

    return create_secured_agent
```