import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, Awaitable
from functools import wraps
import time
import random
import logging
from enum import Enum


logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for tracking requests across services.

    Returns:
        A unique string identifier
    """
    timestamp = str(int(time.time() * 1000000))  # Microsecond precision
    random_part = str(random.randint(1000, 9999))
    return f"corr_{timestamp}_{random_part}"


def calculate_hash(data: Any) -> str:
    """
    Calculate SHA-256 hash of the provided data.

    Args:
        data: Data to hash (will be converted to JSON string)

    Returns:
        Hexadecimal string representation of the hash
    """
    if isinstance(data, str):
        data_str = data
    else:
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))

    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


def validate_fbr_invoice_structure(invoice_data: Dict[str, Any]) -> bool:
    """
    Validate the basic structure of an FBR invoice according to specification.

    Args:
        invoice_data: Dictionary containing invoice data

    Returns:
        True if the structure is valid, False otherwise
    """
    # This is a simplified validation - actual implementation would depend
    # on the specific FBR technical specification
    required_fields = ['invoice_number', 'issue_date', 'supplier_info', 'customer_info', 'items']

    for field in required_fields:
        if field not in invoice_data:
            logger.warning(f"Missing required field in invoice: {field}")
            return False

    # Validate date format if present
    if 'issue_date' in invoice_data:
        try:
            # Attempt to parse the date
            datetime.fromisoformat(invoice_data['issue_date'].replace('Z', '+00:00'))
        except ValueError:
            logger.warning("Invalid date format in invoice")
            return False

    return True


def sanitize_input(input_data: str) -> str:
    """
    Sanitize input to prevent injection attacks.

    Args:
        input_data: Raw input string to sanitize

    Returns:
        Sanitized string
    """
    # Remove or escape potentially dangerous characters
    sanitized = input_data.replace('<script', '&lt;script').replace('javascript:', 'javascript_')
    return sanitized.strip()


def format_currency(amount: float, currency: str = "PKR") -> str:
    """
    Format a currency amount according to standard conventions.

    Args:
        amount: Numeric amount to format
        currency: Currency code (default PKR for Pakistani Rupees)

    Returns:
        Formatted currency string
    """
    return f"{currency} {amount:,.2f}"


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.utcnow().isoformat()


def convert_to_snake_case(name: str) -> str:
    """
    Convert camelCase or PascalCase string to snake_case.

    Args:
        name: String to convert

    Returns:
        Snake case representation of the string
    """
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i != 0:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)


def exponential_backoff(base_delay: float = 1.0, max_delay: float = 60.0, max_attempts: int = 5):
    """
    Decorator to implement exponential backoff for retrying failed operations.

    Args:
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        max_attempts: Maximum number of retry attempts
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_attempts - 1:  # Last attempt
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}")
                        raise e

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, 0.1 * delay)  # Add up to 10% jitter
                    total_delay = delay + jitter

                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                                 f"Retrying in {total_delay:.2f} seconds...")

                    await asyncio.sleep(total_delay)

            raise last_exception  # This shouldn't be reached but included for type safety

        return wrapper
    return decorator


def rate_limit(calls_per_window: int, window_seconds: int):
    """
    Decorator to implement rate limiting.

    Args:
        calls_per_window: Number of allowed calls per time window
        window_seconds: Duration of the time window in seconds
    """
    def decorator(func: Callable) -> Callable:
        # Using a simple in-memory store (in production, use Redis or similar)
        call_times = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal call_times

            current_time = time.time()

            # Clean up old entries
            call_times = {k: v for k, v in call_times.items()
                         if current_time - v < window_seconds}

            # Check if limit exceeded
            if len(call_times) >= calls_per_window:
                raise Exception(f"Rate limit exceeded: {calls_per_window} calls per {window_seconds} seconds")

            # Record the call
            call_id = f"{func.__name__}_{current_time}"
            call_times[call_id] = current_time

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def validate_environment(env: str) -> bool:
    """
    Validate that the environment is either SANDBOX or PRODUCTION.

    Args:
        env: Environment string to validate

    Returns:
        True if valid, False otherwise
    """
    return env.upper() in ['SANDBOX', 'PRODUCTION']


def mask_sensitive_data(data: Dict[str, Any], fields_to_mask: list = None) -> Dict[str, Any]:
    """
    Mask sensitive fields in data dictionary.

    Args:
        data: Dictionary containing data to mask
        fields_to_mask: List of field names to mask (defaults to common sensitive fields)

    Returns:
        Dictionary with sensitive fields masked
    """
    if fields_to_mask is None:
        fields_to_mask = ['password', 'token', 'secret', 'key', 'authorization', 'auth']

    masked_data = data.copy()

    for key, value in masked_data.items():
        if key.lower() in [f.lower() for f in fields_to_mask]:
            masked_data[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, fields_to_mask)
        elif isinstance(value, list):
            masked_data[key] = [mask_sensitive_data(item, fields_to_mask) if isinstance(item, dict) else item
                               for item in value]

    return masked_data


def create_idempotency_key(user_id: str, request_data: Dict[str, Any]) -> str:
    """
    Create an idempotency key based on user and request data.

    Args:
        user_id: ID of the requesting user
        request_data: Request data to include in the key calculation

    Returns:
        Unique idempotency key
    """
    # Combine user ID and request data hash to create a unique key
    request_hash = calculate_hash(request_data)
    idempotency_key = f"{user_id}:{request_hash}"
    return idempotency_key


def is_valid_json(json_string: str) -> bool:
    """
    Check if a string is valid JSON.

    Args:
        json_string: String to validate

    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(json_string)
        return True
    except ValueError:
        return False


def get_file_extension(file_name: str) -> str:
    """
    Extract file extension from a file name.

    Args:
        file_name: Name of the file

    Returns:
        File extension (including the dot)
    """
    parts = file_name.rsplit('.', 1)
    return f".{parts[1]}" if len(parts) > 1 else ""


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.2 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"