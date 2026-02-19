import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys
from functools import wraps


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO"):
    """
    Set up structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create a handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(handler)


def log_api_call(endpoint: str, method: str, status_code: int, duration: float,
                 request_data: Optional[Dict] = None, response_data: Optional[Dict] = None):
    """
    Log API calls with structured information.

    Args:
        endpoint: The API endpoint that was called
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code of the response
        duration: Time taken for the request in seconds
        request_data: Request payload (if applicable)
        response_data: Response payload (if applicable)
    """
    logger = logging.getLogger('api')

    log_data = {
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration * 1000,  # Convert to milliseconds
    }

    if request_data:
        log_data['request_data'] = request_data

    if response_data:
        log_data['response_data'] = response_data

    if 200 <= status_code < 400:
        logger.info(f"API call to {endpoint} completed successfully", extra=log_data)
    elif 400 <= status_code < 500:
        logger.warning(f"API call to {endpoint} resulted in client error", extra=log_data)
    else:
        logger.error(f"API call to {endpoint} resulted in server error", extra=log_data)


def log_fbr_interaction(endpoint: str, method: str, status_code: int, duration: float,
                        request_payload: Dict, response_payload: Dict,
                        environment: str, correlation_id: Optional[str] = None):
    """
    Log FBR API interactions with structured information for audit purposes.

    Args:
        endpoint: The FBR API endpoint that was called
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code of the response
        duration: Time taken for the request in seconds
        request_payload: Request payload sent to FBR
        response_payload: Response payload received from FBR
        environment: Environment (SANDBOX/PRODUCTION)
        correlation_id: Optional correlation ID for request/response matching
    """
    logger = logging.getLogger('fbr_interaction')

    log_data = {
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration * 1000,  # Convert to milliseconds
        'environment': environment,
        'correlation_id': correlation_id
    }

    # Limit the size of payloads for logging to prevent huge logs
    # In production, you might want to store full payloads in a separate audit system
    log_data['request_payload_summary'] = {
        'size': len(json.dumps(request_payload)),
        'keys': list(request_payload.keys())[:10]  # First 10 keys as example
    }

    log_data['response_payload_summary'] = {
        'size': len(json.dumps(response_payload)),
        'keys': list(response_payload.keys())[:10]  # First 10 keys as example
    }

    logger.info(f"FBR API interaction with {endpoint}", extra=log_data)


def log_audit_event(user_id: str, action: str, resource_type: str, resource_id: str,
                   previous_state: Optional[Dict] = None, new_state: Optional[Dict] = None,
                   success: bool = True, ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
    """
    Log audit events for compliance and security purposes.

    Args:
        user_id: ID of the user performing the action
        action: Description of the action performed
        resource_type: Type of resource affected (e.g., 'invoice', 'user')
        resource_id: ID of the specific resource affected
        previous_state: Previous state of the resource (if applicable)
        new_state: New state of the resource (if applicable)
        success: Whether the action was successful
        ip_address: IP address of the request
        user_agent: User agent string of the request
    """
    logger = logging.getLogger('audit')

    log_data = {
        'user_id': user_id,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'success': success,
        'timestamp': datetime.utcnow().isoformat()
    }

    if previous_state:
        log_data['previous_state'] = previous_state

    if new_state:
        log_data['new_state'] = new_state

    if ip_address:
        log_data['ip_address'] = ip_address

    if user_agent:
        log_data['user_agent'] = user_agent

    logger.info(f"Audit event: {action} performed by user {user_id}", extra=log_data)


def log_exception(exception: Exception, context: str = "", extra_data: Optional[Dict] = None):
    """
    Log exceptions with context information.

    Args:
        exception: The exception that occurred
        context: Context or description of where the exception occurred
        extra_data: Additional data to include in the log
    """
    logger = logging.getLogger('errors')

    log_data = {
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'context': context
    }

    if extra_data:
        log_data.update(extra_data)

    logger.exception(f"Exception occurred: {str(exception)}", extra=log_data)


def log_execution_time(func_name: str):
    """
    Decorator to log the execution time of functions.

    Args:
        func_name: Name of the function being timed
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                logger = logging.getLogger('performance')
                logger.info(f"Function {func_name} executed in {duration:.3f}s", extra={
                    'function': func_name,
                    'duration_ms': duration * 1000
                })

                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()

                logger = logging.getLogger('performance')
                logger.error(f"Function {func_name} failed after {duration:.3f}s", extra={
                    'function': func_name,
                    'duration_ms': duration * 1000,
                    'error': str(e)
                })

                raise

        return wrapper
    return decorator


# Initialize logging with the configured level
setup_logging(level="INFO")