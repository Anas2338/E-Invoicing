"""
Utility functions for error log analysis
"""

import re
from typing import Dict, List, Optional

def extract_error_context(log_text: str, lines_before: int = 3, lines_after: int = 3) -> List[str]:
    """
    Extract context around error messages in logs
    """
    lines = log_text.split('\n')
    error_lines = []

    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
            start = max(0, i - lines_before)
            end = min(len(lines), i + lines_after + 1)
            error_lines.extend(lines[start:end])
            error_lines.append("---")  # Separator between error contexts

    # Remove duplicate separator at the end
    if error_lines and error_lines[-1] == "---":
        error_lines.pop()

    return error_lines

def identify_language(log_text: str) -> Optional[str]:
    """
    Identify the programming language from error logs
    """
    patterns = {
        'javascript': [r'at.*\.js:', r'TypeError', r'ReferenceError', r'SyntaxError'],
        'python': [r'Traceback', r'File.*\.py', r'NameError', r'AttributeError', r'ImportError'],
        'java': [r'java\.lang\.', r'Exception in thread', r'Caused by:'],
        'csharp': [r'at System\.', r'Exception:.*in.*cs:'],
        'go': [r'panic:', r'goroutine.*\[running\]:'],
        'php': [r'Fatal error', r'Parse error', r'Warning:.*on line'],
        'ruby': [r'require.*failed', r'NoMethodError', r'undefined method'],
        'rust': [r'error:.*aborting due to', r'Compilation failed']
    }

    for language, regexes in patterns.items():
        for pattern in regexes:
            if re.search(pattern, log_text, re.IGNORECASE):
                return language

    return None

def extract_error_message(log_text: str) -> Optional[str]:
    """
    Extract the main error message from logs
    """
    # Common patterns for error messages
    patterns = [
        r'(Error|Exception|Failed|Fatal):?\s*(.+?)(?:\n|$)',
        r'panic:\s*(.+?)(?:\n|$)',
        r'(.+Error:.+?)(?:\n|$)',
        r'(.+Exception:.+?)(?:\n|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, log_text, re.IGNORECASE)
        if match:
            return match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)

    return None

def format_error_analysis(error_type: str, message: str, context: List[str]) -> Dict:
    """
    Format error analysis in a structured way
    """
    return {
        'error_type': error_type,
        'message': message,
        'context': context,
        'suggested_solutions': []
    }