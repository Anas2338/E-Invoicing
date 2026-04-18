"""
Claude API Client Wrapper.

Provides rate-limited access to Claude API with prompt caching support
for efficient decision-making in invoice processing.
"""
import logging
import time
from typing import Optional, Dict, Any
from anthropic import Anthropic
from anthropic.types import Message

from config import config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """
    Wrapper for Claude API with rate limiting and prompt caching.

    Implements token bucket algorithm for rate limiting to stay within
    API quotas while maximizing throughput.
    """

    def __init__(self):
        """Initialize Claude API client with rate limiting."""
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.CLAUDE_MODEL

        # Rate limiting: Token bucket algorithm
        self.rate_limit_rpm = config.CLAUDE_RATE_LIMIT_RPM
        self.tokens = self.rate_limit_rpm  # Start with full bucket
        self.last_refill = time.time()
        self.tokens_per_second = self.rate_limit_rpm / 60.0

        logger.info(f"Claude API client initialized (model: {self.model}, rate limit: {self.rate_limit_rpm} RPM)")

    def _wait_for_token(self):
        """
        Wait for rate limit token using token bucket algorithm.

        Refills tokens based on elapsed time and blocks if bucket is empty.
        """
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens based on elapsed time
        self.tokens = min(
            self.rate_limit_rpm,
            self.tokens + (elapsed * self.tokens_per_second)
        )
        self.last_refill = now

        # If no tokens available, wait until we have one
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.tokens_per_second
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            self.tokens = 1
            self.last_refill = time.time()

        # Consume one token
        self.tokens -= 1

    def classify_error(
        self,
        error_message: str,
        error_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use Claude to classify an error as transient or permanent.

        Args:
            error_message: The error message to classify
            error_context: Additional context about the error (invoice data, attempt count, etc.)

        Returns:
            Dictionary with classification result:
            {
                "classification": "transient" | "permanent",
                "confidence": float (0-1),
                "reasoning": str,
                "recommended_action": str,
                "retry_delay_seconds": int (if transient)
            }
        """
        self._wait_for_token()

        prompt = f"""You are an expert system for classifying invoice processing errors in an FBR (Federal Board of Revenue) e-invoicing system.

Error Message: {error_message}

Context:
- Invoice Number: {error_context.get('invoice_number', 'N/A')}
- Retry Count: {error_context.get('retry_count', 0)}
- Error Source: {error_context.get('error_source', 'unknown')}

Classify this error as either:
1. TRANSIENT: Temporary issue that may resolve with retry (network issues, rate limits, temporary service unavailability)
2. PERMANENT: Persistent issue requiring human intervention (validation errors, authentication failures, malformed data)

Respond in JSON format:
{{
    "classification": "transient" or "permanent",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation",
    "recommended_action": "specific action to take",
    "retry_delay_seconds": integer (only if transient, otherwise 0)
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=config.CLAUDE_MAX_TOKENS,
                temperature=config.CLAUDE_TEMPERATURE,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            response_text = message.content[0].text
            import json
            result = json.loads(response_text)

            logger.info(f"Error classified as {result['classification']} (confidence: {result['confidence']})")
            return result

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            # Fallback: treat as transient with low confidence
            return {
                "classification": "transient",
                "confidence": 0.3,
                "reasoning": f"API call failed, defaulting to transient: {str(e)}",
                "recommended_action": "Retry with exponential backoff",
                "retry_delay_seconds": 300
            }

    def analyze_failure_patterns(
        self,
        failure_data: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in failed invoices to identify systemic issues.

        Args:
            failure_data: List of recent failures with error messages and context

        Returns:
            Dictionary with analysis results:
            {
                "patterns_detected": list[str],
                "root_cause_hypothesis": str,
                "recommended_actions": list[str],
                "severity": "low" | "medium" | "high"
            }
        """
        self._wait_for_token()

        # Summarize failure data for prompt
        failure_summary = "\n".join([
            f"- {f.get('error_message', 'Unknown error')} (count: {f.get('count', 1)})"
            for f in failure_data[:10]  # Limit to top 10 for token efficiency
        ])

        prompt = f"""You are analyzing failure patterns in an FBR e-invoicing system.

Recent Failures (last hour):
{failure_summary}

Total Failures: {sum(f.get('count', 1) for f in failure_data)}

Identify patterns and provide actionable insights in JSON format:
{{
    "patterns_detected": ["pattern1", "pattern2"],
    "root_cause_hypothesis": "most likely root cause",
    "recommended_actions": ["action1", "action2"],
    "severity": "low" | "medium" | "high"
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=config.CLAUDE_MAX_TOKENS,
                temperature=config.CLAUDE_TEMPERATURE,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            import json
            result = json.loads(response_text)

            logger.info(f"Failure pattern analysis complete (severity: {result['severity']})")
            return result

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return {
                "patterns_detected": [],
                "root_cause_hypothesis": "Unable to analyze due to API error",
                "recommended_actions": ["Review logs manually"],
                "severity": "medium"
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiting statistics.

        Returns:
            Dictionary with usage stats
        """
        return {
            "rate_limit_rpm": self.rate_limit_rpm,
            "tokens_available": int(self.tokens),
            "tokens_per_second": self.tokens_per_second
        }
