#!/usr/bin/env python3
"""
Script to analyze error logs and suggest solutions
This script would be used to automatically parse and analyze error logs
"""

import re
from typing import Dict, List, Tuple

def identify_error_type(error_log: str) -> str:
    """Identify the type of error from the log"""
    error_patterns = {
        'null_reference': [
            r'Cannot read property.*of (null|undefined)',
            r'Cannot read.*of (null|undefined)',
            r'NullPointerException',
            r'AttributeError.*NoneType.*no attribute'
        ],
        'syntax_error': [
            r'SyntaxError.*',
            r'IndentationError.*',
            r'expected.*found.*'
        ],
        'type_error': [
            r'TypeError.*',
            r'cannot convert.*',
            r'unsupported operand type.*'
        ],
        'connection_error': [
            r'Connection refused',
            r'Connection timed out',
            r'Network is unreachable',
            r'ECONNREFUSED'
        ],
        'index_error': [
            r'IndexError.*out of range',
            r'ArrayIndexOutOfBoundsException',
            r'list index out of range'
        ]
    }

    for error_type, patterns in error_patterns.items():
        for pattern in patterns:
            if re.search(pattern, error_log, re.IGNORECASE):
                return error_type

    return 'unknown'

def suggest_solutions(error_type: str, error_log: str) -> List[str]:
    """Suggest solutions based on error type"""
    solutions = {
        'null_reference': [
            "Add null checks before accessing properties: if (obj && obj.prop)",
            "Use optional chaining: obj?.prop?.subprop",
            "Ensure proper initialization of variables before use",
            "Check if the API/DB is returning expected data"
        ],
        'syntax_error': [
            "Check for missing brackets, parentheses, or semicolons",
            "Verify proper indentation (especially in Python)",
            "Use a linter or IDE syntax checker to identify issues",
            "Compare with working code to spot differences"
        ],
        'type_error': [
            "Verify data types before operations",
            "Add type checking: typeof variable === 'expected_type'",
            "Convert types explicitly if needed",
            "Check API responses match expected types"
        ],
        'connection_error': [
            "Check if the target service is running",
            "Verify network connectivity",
            "Check firewall settings and port availability",
            "Confirm connection parameters (host, port, credentials)"
        ],
        'index_error': [
            "Check array/list length before accessing by index",
            "Use bounds checking: if (index < array.length)",
            "Verify loop conditions don't exceed array bounds",
            "Consider using safer iteration methods"
        ]
    }

    return solutions.get(error_type, ["No specific solutions found for this error type"])

def analyze_error_log(error_log: str) -> Dict:
    """Analyze an error log and return structured analysis"""
    error_type = identify_error_type(error_log)
    solutions = suggest_solutions(error_type, error_log)

    return {
        'error_type': error_type,
        'suggested_solutions': solutions,
        'original_log': error_log
    }

def main():
    """Main function to run the error log analyzer"""
    print("Error Log Analyzer")
    print("Enter an error log to analyze (or 'quit' to exit):")

    while True:
        error_input = input("\nError log: ")
        if error_input.lower() == 'quit':
            break

        if error_input.strip():
            analysis = analyze_error_log(error_input)
            print(f"\nError Type: {analysis['error_type']}")
            print("Suggested Solutions:")
            for i, solution in enumerate(analysis['suggested_solutions'], 1):
                print(f"  {i}. {solution}")

if __name__ == "__main__":
    main()