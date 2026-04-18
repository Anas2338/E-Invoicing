"""
Error Handler Skill - Classifies errors using AI (Claude or Qwen).

Uses AI to intelligently classify errors as transient or permanent,
enabling adaptive retry strategies.
"""
from typing import Dict, Any, Optional

from skills import BaseSkill, SkillResult, SkillStatus
from ai_client import AIClient


class ErrorHandlerSkill(BaseSkill):
    """
    Skill for intelligent error classification and handling.

    Uses AI (Claude in production, Qwen in development) to classify errors
    as transient (retry-able) or permanent (requires human intervention).
    """

    def __init__(self):
        """Initialize error handler skill."""
        super().__init__("error_handler")
        self.ai_client = AIClient()

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Must contain 'error_message' and 'error_context' keys

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'error_message' not in data:
            return False, "Missing required field: error_message"

        if 'error_context' not in data:
            return False, "Missing required field: error_context"

        if not isinstance(data['error_context'], dict):
            return False, "error_context must be a dictionary"

        return True, None

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Classify error using Claude API.

        Args:
            context: Must contain 'error_message' and 'error_context'

        Returns:
            SkillResult with classification outcome
        """
        try:
            error_message = context['error_message']
            error_context = context['error_context']

            # Use AI to classify error
            classification = self.ai_client.classify_error(
                error_message=error_message,
                error_context=error_context
            )

            self.logger.info(
                f"Error classified as {classification['classification']} "
                f"(confidence: {classification['confidence']:.2f})"
            )

            # Normalize classification to lowercase for comparison
            classification_lower = classification['classification'].lower()

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "classification": classification_lower,
                    "confidence": classification['confidence'],
                    "reasoning": classification['reasoning'],
                    "recommended_action": classification['recommended_action'],
                    "retry_delay_seconds": classification.get('retry_delay_seconds', 0),
                    "is_transient": classification_lower == 'transient',
                    "is_permanent": classification_lower == 'permanent'
                },
                metadata={
                    "error_message": error_message,
                    "error_context": error_context
                }
            )

        except Exception as e:
            return self.handle_error(e, context)

    def analyze_failure_patterns(self, failure_data: list[Dict[str, Any]]) -> SkillResult:
        """
        Analyze patterns in multiple failures.

        Args:
            failure_data: List of recent failures with error messages and context

        Returns:
            SkillResult with pattern analysis
        """
        try:
            analysis = self.ai_client.analyze_failure_patterns(failure_data)

            self.logger.info(
                f"Failure pattern analysis complete: {len(analysis['patterns_detected'])} patterns detected, "
                f"severity: {analysis['severity']}"
            )

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "patterns_detected": analysis['patterns_detected'],
                    "root_cause_hypothesis": analysis['root_cause_hypothesis'],
                    "recommended_actions": analysis['recommended_actions'],
                    "severity": analysis['severity']
                },
                metadata={
                    "failure_count": len(failure_data)
                }
            )

        except Exception as e:
            return self.handle_error(e, {"failure_data": failure_data})
