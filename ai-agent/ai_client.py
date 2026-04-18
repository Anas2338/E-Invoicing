"""
AI Client Abstraction Layer.

Provides unified interface for both Claude and Gemini AI providers
with automatic provider selection based on environment configuration.
Includes fallback to rule-based logic when AI API fails.
"""
import logging
from typing import Dict, Any, Protocol

from config import config
from fallback_classifier import RuleBasedClassifier

logger = logging.getLogger(__name__)


class AIProvider(Protocol):
    """Protocol defining the interface for AI providers."""

    def classify_error(
        self,
        error_message: str,
        error_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify an error as transient or permanent."""
        ...

    def analyze_failure_patterns(
        self,
        failure_data: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in failed invoices."""
        ...

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics."""
        ...


class AIClient:
    """
    Unified AI client that delegates to the configured provider.

    Automatically selects between Claude (production) and Gemini (development/free)
    based on environment configuration.
    """

    def __init__(self):
        """Initialize AI client with the configured provider."""
        self.provider_name = config.AI_PROVIDER
        self.fallback = RuleBasedClassifier()
        self.ai_failure_count = 0
        self.fallback_usage_count = 0

        if self.provider_name == "claude":
            from claude_client import ClaudeClient
            self.provider: AIProvider = ClaudeClient()
            logger.info("AI Client initialized with Claude provider (production)")
        elif self.provider_name == "gemini":
            from gemini_client import GeminiClient
            self.provider: AIProvider = GeminiClient()
            logger.info("AI Client initialized with Gemini provider (development/free)")
        else:
            raise ValueError(f"Unknown AI provider: {self.provider_name}. Must be 'claude' or 'gemini'")

    def classify_error(
        self,
        error_message: str,
        error_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use AI to classify an error as transient or permanent.
        Falls back to rule-based logic if AI API fails.

        Args:
            error_message: The error message to classify
            error_context: Additional context about the error

        Returns:
            Dictionary with classification result
        """
        try:
            logger.debug(f"[AI_CLASSIFY] Attempting AI classification for: {error_message[:100]}")
            result = self.provider.classify_error(error_message, error_context)
            logger.info(
                f"[AI_CLASSIFY_SUCCESS] classification={result.get('classification')} "
                f"confidence={result.get('confidence', 0):.2f}"
            )
            return result

        except Exception as e:
            self.ai_failure_count += 1
            self.fallback_usage_count += 1

            logger.warning(
                f"[AI_CLASSIFY_FAILED] AI classification failed: {type(e).__name__}: {str(e)}. "
                f"Falling back to rule-based logic. (failure_count={self.ai_failure_count})"
            )

            # Use fallback classifier
            result = self.fallback.classify_error(error_message, error_context)
            logger.info(
                f"[FALLBACK_CLASSIFY_SUCCESS] classification={result.get('classification')} "
                f"confidence={result.get('confidence', 0):.2f}"
            )
            return result

    def analyze_failure_patterns(
        self,
        failure_data: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in failed invoices to identify systemic issues.
        Falls back to rule-based logic if AI API fails.

        Args:
            failure_data: List of recent failures with error messages and context

        Returns:
            Dictionary with analysis results
        """
        try:
            logger.debug(f"[AI_ANALYZE] Attempting AI pattern analysis for {len(failure_data)} failures")
            result = self.provider.analyze_failure_patterns(failure_data)
            logger.info(f"[AI_ANALYZE_SUCCESS] patterns_found={len(result.get('patterns', []))}")
            return result

        except Exception as e:
            self.ai_failure_count += 1
            self.fallback_usage_count += 1

            logger.warning(
                f"[AI_ANALYZE_FAILED] AI pattern analysis failed: {type(e).__name__}: {str(e)}. "
                f"Falling back to rule-based logic. (failure_count={self.ai_failure_count})"
            )

            # Use fallback analyzer
            result = self.fallback.analyze_failure_patterns(failure_data)
            logger.info(
                f"[FALLBACK_ANALYZE_SUCCESS] patterns_found={len(result.get('patterns', []))}"
            )
            return result

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiting and fallback statistics.

        Returns:
            Dictionary with usage stats including provider name and fallback usage
        """
        try:
            stats = self.provider.get_usage_stats()
        except Exception as e:
            logger.warning(f"Failed to get provider stats: {e}")
            stats = {}

        stats["provider"] = self.provider_name
        stats["ai_failure_count"] = self.ai_failure_count
        stats["fallback_usage_count"] = self.fallback_usage_count
        stats["fallback_percentage"] = (
            (self.fallback_usage_count / max(self.ai_failure_count, 1)) * 100
            if self.ai_failure_count > 0 else 0
        )
        return stats
