"""
Retry Manager Skill - Manages adaptive retry strategies with exponential backoff.

Implements exponential backoff with jitter and circuit breaker pattern
to prevent overwhelming failing services.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import time

from skills import BaseSkill, SkillResult, SkillStatus
from config import config


class CircuitBreaker:
    """
    Circuit breaker to prevent retry storms.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, threshold: int, timeout: int):
        """
        Initialize circuit breaker.

        Args:
            threshold: Number of consecutive failures before opening
            timeout: Seconds to wait before attempting recovery
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.threshold:
            self.state = "OPEN"

    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if timeout has elapsed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = "HALF_OPEN"
                    return True
            return False

        # HALF_OPEN state
        return True

    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state


class RetryManagerSkill(BaseSkill):
    """
    Skill for managing retry strategies with exponential backoff and circuit breaker.

    Implements:
    - Exponential backoff: delay = base_delay * 2^retry_count + jitter
    - Circuit breaker: prevents retry storms
    - Adaptive delays based on error classification
    """

    def __init__(self):
        """Initialize retry manager skill."""
        super().__init__("retry_manager")
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Must contain 'invoice_id', 'retry_count', and optionally 'error_classification'

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'invoice_id' not in data:
            return False, "Missing required field: invoice_id"

        if 'retry_count' not in data:
            return False, "Missing required field: retry_count"

        return True, None

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Calculate retry delay and check if retry should be attempted.

        Args:
            context: Must contain 'invoice_id', 'retry_count', optionally 'error_classification'

        Returns:
            SkillResult with retry decision and delay
        """
        try:
            invoice_id = context['invoice_id']
            retry_count = context['retry_count']
            error_classification = context.get('error_classification', {})

            # Get or create circuit breaker for this invoice
            circuit_breaker = self._get_circuit_breaker(invoice_id)

            # Check circuit breaker
            if not circuit_breaker.can_attempt():
                self.logger.warning(
                    f"Circuit breaker OPEN for invoice {invoice_id}, "
                    f"blocking retry attempt"
                )
                return SkillResult(
                    status=SkillStatus.FAILURE,
                    data={
                        "should_retry": False,
                        "reason": "circuit_breaker_open",
                        "circuit_state": circuit_breaker.get_state()
                    },
                    error="Circuit breaker is open, retry blocked"
                )

            # Check max retry attempts
            if retry_count >= config.RETRY_MAX_ATTEMPTS:
                self.logger.warning(
                    f"Invoice {invoice_id} exceeded max retry attempts ({config.RETRY_MAX_ATTEMPTS})"
                )
                return SkillResult(
                    status=SkillStatus.FAILURE,
                    data={
                        "should_retry": False,
                        "reason": "max_attempts_exceeded",
                        "retry_count": retry_count,
                        "max_attempts": config.RETRY_MAX_ATTEMPTS
                    },
                    error=f"Max retry attempts ({config.RETRY_MAX_ATTEMPTS}) exceeded"
                )

            # Check if error is permanent (no retry for permanent errors)
            if error_classification.get('classification') == 'permanent':
                self.logger.info(
                    f"Invoice {invoice_id} has permanent error, no retry scheduled"
                )
                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    data={
                        "should_retry": False,
                        "reason": "permanent_error",
                        "retry_count": retry_count
                    }
                )

            # Calculate retry delay
            if error_classification.get('retry_delay_seconds'):
                # Use Claude-recommended delay
                base_delay = error_classification['retry_delay_seconds']
            else:
                # Use exponential backoff
                base_delay = config.RETRY_BASE_DELAY * (2 ** retry_count)

            # Add jitter to prevent thundering herd
            jitter = random.randint(0, config.RETRY_JITTER_MAX)
            retry_delay = base_delay + jitter

            # Calculate next retry time
            next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)

            self.logger.info(
                f"Invoice {invoice_id} retry scheduled: "
                f"attempt {retry_count + 1}/{config.RETRY_MAX_ATTEMPTS}, "
                f"delay {retry_delay}s, next retry at {next_retry_at.isoformat()}"
            )

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "should_retry": True,
                    "retry_delay_seconds": retry_delay,
                    "next_retry_at": next_retry_at.isoformat(),
                    "retry_count": retry_count,
                    "max_attempts": config.RETRY_MAX_ATTEMPTS,
                    "circuit_state": circuit_breaker.get_state()
                },
                metadata={
                    "base_delay": base_delay,
                    "jitter": jitter,
                    "error_classification": error_classification
                }
            )

        except Exception as e:
            return self.handle_error(e, context)

    def record_retry_success(self, invoice_id: str) -> SkillResult:
        """
        Record successful retry for circuit breaker.

        Args:
            invoice_id: Invoice ID

        Returns:
            SkillResult with success status
        """
        try:
            circuit_breaker = self._get_circuit_breaker(invoice_id)
            circuit_breaker.record_success()

            self.logger.info(f"Retry success recorded for invoice {invoice_id}, circuit breaker reset")

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "invoice_id": invoice_id,
                    "circuit_state": circuit_breaker.get_state()
                }
            )

        except Exception as e:
            return self.handle_error(e, {"invoice_id": invoice_id})

    def record_retry_failure(self, invoice_id: str) -> SkillResult:
        """
        Record failed retry for circuit breaker.

        Args:
            invoice_id: Invoice ID

        Returns:
            SkillResult with failure status
        """
        try:
            circuit_breaker = self._get_circuit_breaker(invoice_id)
            circuit_breaker.record_failure()

            self.logger.warning(
                f"Retry failure recorded for invoice {invoice_id}, "
                f"circuit breaker state: {circuit_breaker.get_state()}"
            )

            return SkillResult(
                status=SkillStatus.SUCCESS,
                data={
                    "invoice_id": invoice_id,
                    "circuit_state": circuit_breaker.get_state(),
                    "failure_count": circuit_breaker.failure_count
                }
            )

        except Exception as e:
            return self.handle_error(e, {"invoice_id": invoice_id})

    def _get_circuit_breaker(self, invoice_id: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for invoice.

        Args:
            invoice_id: Invoice ID

        Returns:
            CircuitBreaker instance
        """
        if invoice_id not in self.circuit_breakers:
            self.circuit_breakers[invoice_id] = CircuitBreaker(
                threshold=config.CIRCUIT_BREAKER_THRESHOLD,
                timeout=config.CIRCUIT_BREAKER_TIMEOUT
            )

        return self.circuit_breakers[invoice_id]
