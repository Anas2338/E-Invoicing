"""
Password strength validation utility.

Enforces strong password policies:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Not in common passwords list
"""

import re
from typing import Tuple


# Common weak passwords to reject
COMMON_PASSWORDS = [
    'password', 'password123', '12345678', '123456789', '1234567890',
    'qwerty', 'qwerty123', 'abc123', 'password1', 'admin', 'admin123',
    'letmein', 'welcome', 'monkey', '1234', '12345', '123456', '1234567',
    'password!', 'pass123', 'test123', 'user123', 'demo123',
    # Add longer variations that meet 12 char minimum
    'password123!', 'password1234', 'qwerty123456', 'welcome12345',
    'admin1234567', 'letmein12345', '123456789012', 'password@123'
]


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength against security requirements.

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if password meets all requirements
        - error_message: Empty string if valid, error description if invalid
    """
    if not password:
        return False, "Password cannot be empty"

    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    # Check for digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password):
        return False, r"Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>_-+=[]\/;'`~)"

    # Check against common passwords (case-insensitive)
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common. Please choose a more unique password"

    # Check for common patterns
    if re.search(r'(.)\1{2,}', password):  # Three or more repeated characters
        return False, "Password contains too many repeated characters"

    # Check for sequential characters (e.g., "123", "abc")
    sequential_patterns = [
        '0123456789', 'abcdefghijklmnopqrstuvwxyz', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm'
    ]
    password_lower = password.lower()
    for pattern in sequential_patterns:
        for i in range(len(pattern) - 3):
            if pattern[i:i+4] in password_lower or pattern[i:i+4][::-1] in password_lower:
                return False, "Password contains sequential characters"

    return True, ""


def get_password_requirements() -> str:
    """
    Get a human-readable description of password requirements.

    Returns:
        String describing all password requirements
    """
    return (
        "Password must meet the following requirements:\n"
        "- At least 8 characters long\n"
        "- At least one uppercase letter (A-Z)\n"
        "- At least one lowercase letter (a-z)\n"
        "- At least one digit (0-9)\n"
        r"- At least one special character (!@#$%^&*(),.?\":{}|<>_-+=[]\/;'`~)" + "\n"
        "- Not a common password\n"
        "- No excessive repeated or sequential characters"
    )
