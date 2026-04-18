"""
Rule-based fallback logic for AI classification.

Used when AI API is unavailable or fails, ensuring the agent
continues to function with deterministic heuristics.
"""
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RuleBasedClassifier:
    """
    Fallback classifier using rule-based heuristics.

    Used when AI API fails to ensure continuous operation.
    """

    # Transient error patterns (should retry)
    TRANSIENT_PATTERNS = [
        r"timeout",
        r"timed out",
        r"connection.*reset",
        r"connection.*refused",
        r"temporarily unavailable",
        r"service unavailable",
        r"502 bad gateway",
        r"503 service unavailable",
        r"504 gateway timeout",
        r"rate limit",
        r"too many requests",
        r"network.*error",
        r"socket.*error",
        r"dns.*error",
        r"ssl.*error",
        r"certificate.*error",
    ]

    # Permanent error patterns (should not retry)
    PERMANENT_PATTERNS = [
        r"invalid.*format",
        r"malformed",
        r"validation.*failed",
        r"schema.*error",
        r"unauthorized",
        r"forbidden",
        r"not found",
        r"400 bad request",
        r"401 unauthorized",
        r"403 forbidden",
        r"404 not found",
        r"duplicate",
        r"already exists",
        r"constraint.*violation",
        r"foreign key",
        r"unique.*constraint",
    ]

    def __init__(self):
        """Initialize rule-based classifier."""
        self.transient_regex = re.compile(
            "|".join(self.TRANSIENT_PATTERNS),
            re.IGNORECASE
        )
        self.permanent_regex = re.compile(
            "|".join(self.PERMANENT_PATTERNS),
            re.IGNORECASE
        )

    def classify_error(
        self,
        error_message: str,
        error_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify error using rule-based heuristics.

        Args:
            error_message: The error message to classify
            error_context: Additional context about the error

        Returns:
            Dictionary with classification result
        """
        logger.info(
            f"[FALLBACK_CLASSIFIER] Using rule-based classification for: {error_message[:100]}"
        )

        error_lower = error_message.lower()

        # Check for transient patterns
        if self.transient_regex.search(error_message):
            return {
                "classification": "transient",
                "confidence": 0.85,
                "reasoning": "Matched transient error pattern (network/timeout/rate limit)",
                "should_retry": True,
                "recommended_action": "retry_with_backoff",
                "fallback_used": True
            }

        # Check for permanent patterns
        if self.permanent_regex.search(error_message):
            return {
                "classification": "permanent",
                "confidence": 0.85,
                "reasoning": "Matched permanent error pattern (validation/auth/constraint)",
                "should_retry": False,
                "recommended_action": "mark_failed",
                "fallback_used": True
            }

        # Check HTTP status codes from context
        status_code = error_context.get("status_code")
        if status_code:
            if status_code in [408, 429, 502, 503, 504]:
                return {
                    "classification": "transient",
                    "confidence": 0.90,
                    "reasoning": f"HTTP {status_code} indicates transient failure",
                    "should_retry": True,
                    "recommended_action": "retry_with_backoff",
                    "fallback_used": True
                }
            elif status_code in [400, 401, 403, 404, 409, 422]:
                return {
                    "classification": "permanent",
                    "confidence": 0.90,
                    "reasoning": f"HTTP {status_code} indicates permanent failure",
                    "should_retry": False,
                    "recommended_action": "mark_failed",
                    "fallback_used": True
                }

        # Default to transient with low confidence (safer to retry)
        logger.warning(
            f"[FALLBACK_CLASSIFIER] Could not confidently classify error, "
            f"defaulting to transient: {error_message[:100]}"
        )
        return {
            "classification": "transient",
            "confidence": 0.50,
            "reasoning": "No clear pattern matched, defaulting to transient for safety",
            "should_retry": True,
            "recommended_action": "retry_with_backoff",
            "fallback_used": True
        }

    def analyze_failure_patterns(
        self,
        failure_data: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze failure patterns using rule-based heuristics.

        Args:
            failure_data: List of recent failures

        Returns:
            Dictionary with analysis results
        """
        logger.info(
            f"[FALLBACK_ANALYZER] Analyzing {len(failure_data)} failures with rule-based logic"
        )

        if not failure_data:
            return {
                "patterns": [],
                "recommendations": [],
                "fallback_used": True
            }

        # Count error types
        error_counts: Dict[str, int] = {}
        for failure in failure_data:
            error_msg = failure.get("error_message", "").lower()

            # Categorize by pattern
            if self.transient_regex.search(error_msg):
                error_counts["transient_errors"] = error_counts.get("transient_errors", 0) + 1
            elif self.permanent_regex.search(error_msg):
                error_counts["permanent_errors"] = error_counts.get("permanent_errors", 0) + 1
            else:
                error_counts["unknown_errors"] = error_counts.get("unknown_errors", 0) + 1

        # Generate recommendations
        recommendations = []
        total = len(failure_data)

        if error_counts.get("transient_errors", 0) / total > 0.5:
            recommendations.append(
                "High rate of transient errors detected. "
                "Check network connectivity and FBR API availability."
            )

        if error_counts.get("permanent_errors", 0) / total > 0.3:
            recommendations.append(
                "Significant permanent errors detected. "
                "Review invoice data quality and validation rules."
            )

        return {
            "patterns": [
                {
                    "type": error_type,
                    "count": count,
                    "percentage": (count / total) * 100
                }
                for error_type, count in error_counts.items()
            ],
            "recommendations": recommendations,
            "total_failures": total,
            "fallback_used": True
        }
