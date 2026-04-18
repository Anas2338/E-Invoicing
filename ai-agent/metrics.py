"""
Monitoring metrics for AI Agent.

Tracks operational metrics including processing latency,
decision accuracy, retry success rates, and system health.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: datetime
    processing_latency_avg: float
    processing_latency_p95: float
    processing_latency_p99: float
    decision_accuracy: float
    retry_success_rate: float
    total_processed: int
    total_failed: int
    total_retried: int
    ai_fallback_rate: float
    active_circuit_breakers: int


class MetricsCollector:
    """
    Collects and aggregates operational metrics for the AI Agent.

    Thread-safe metrics collection with sliding window aggregation.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.

        Args:
            window_size: Number of recent events to keep for aggregation
        """
        self.window_size = window_size
        self.lock = Lock()

        # Processing latency tracking
        self.processing_latencies: deque = deque(maxlen=window_size)

        # Decision tracking
        self.decisions_made: deque = deque(maxlen=window_size)
        self.decisions_correct: deque = deque(maxlen=window_size)

        # Retry tracking
        self.retry_attempts: deque = deque(maxlen=window_size)
        self.retry_successes: deque = deque(maxlen=window_size)

        # AI fallback tracking
        self.ai_calls: deque = deque(maxlen=window_size)
        self.ai_fallbacks: deque = deque(maxlen=window_size)

        # Counters
        self.total_processed = 0
        self.total_failed = 0
        self.total_retried = 0
        self.total_ai_calls = 0
        self.total_ai_fallbacks = 0

        # Circuit breaker tracking
        self.active_circuit_breakers = 0

        # Start time
        self.start_time = datetime.now()

        logger.info(f"MetricsCollector initialized with window_size={window_size}")

    def record_processing(
        self,
        latency_seconds: float,
        success: bool,
        invoice_id: Optional[str] = None
    ) -> None:
        """
        Record invoice processing metrics.

        Args:
            latency_seconds: Time taken to process invoice
            success: Whether processing succeeded
            invoice_id: Optional invoice ID for logging
        """
        with self.lock:
            self.processing_latencies.append(latency_seconds)
            self.total_processed += 1

            if not success:
                self.total_failed += 1

        logger.debug(
            f"[METRIC_PROCESSING] invoice_id={invoice_id} "
            f"latency={latency_seconds:.3f}s success={success}"
        )

    def record_decision(
        self,
        decision_type: str,
        correct: Optional[bool] = None
    ) -> None:
        """
        Record AI decision metrics.

        Args:
            decision_type: Type of decision made (e.g., 'error_classification')
            correct: Whether the decision was correct (if known)
        """
        with self.lock:
            self.decisions_made.append({
                "type": decision_type,
                "timestamp": datetime.now(),
                "correct": correct
            })

            if correct is not None:
                self.decisions_correct.append(correct)

        logger.debug(f"[METRIC_DECISION] type={decision_type} correct={correct}")

    def record_retry(
        self,
        success: bool,
        attempt_number: int,
        invoice_id: Optional[str] = None
    ) -> None:
        """
        Record retry attempt metrics.

        Args:
            success: Whether retry succeeded
            attempt_number: Retry attempt number
            invoice_id: Optional invoice ID for logging
        """
        with self.lock:
            self.retry_attempts.append({
                "attempt": attempt_number,
                "timestamp": datetime.now(),
                "success": success
            })

            if success:
                self.retry_successes.append(True)

            self.total_retried += 1

        logger.debug(
            f"[METRIC_RETRY] invoice_id={invoice_id} "
            f"attempt={attempt_number} success={success}"
        )

    def record_ai_call(
        self,
        fallback_used: bool,
        operation: str
    ) -> None:
        """
        Record AI API call metrics.

        Args:
            fallback_used: Whether fallback logic was used
            operation: Type of AI operation (e.g., 'classify_error')
        """
        with self.lock:
            self.ai_calls.append({
                "operation": operation,
                "timestamp": datetime.now(),
                "fallback": fallback_used
            })

            if fallback_used:
                self.ai_fallbacks.append(True)
                self.total_ai_fallbacks += 1

            self.total_ai_calls += 1

        logger.debug(
            f"[METRIC_AI_CALL] operation={operation} fallback={fallback_used}"
        )

    def set_circuit_breakers(self, count: int) -> None:
        """
        Update active circuit breaker count.

        Args:
            count: Number of currently active circuit breakers
        """
        with self.lock:
            self.active_circuit_breakers = count

    def get_snapshot(self) -> MetricSnapshot:
        """
        Get current metrics snapshot.

        Returns:
            MetricSnapshot with current aggregated metrics
        """
        with self.lock:
            # Calculate processing latency percentiles
            latencies = sorted(self.processing_latencies)
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                p95_idx = int(len(latencies) * 0.95)
                p99_idx = int(len(latencies) * 0.99)
                p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
                p99_latency = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]
            else:
                avg_latency = p95_latency = p99_latency = 0.0

            # Calculate decision accuracy
            if self.decisions_correct:
                accuracy = sum(self.decisions_correct) / len(self.decisions_correct)
            else:
                accuracy = 0.0

            # Calculate retry success rate
            if self.retry_attempts:
                retry_success_rate = len(self.retry_successes) / len(self.retry_attempts)
            else:
                retry_success_rate = 0.0

            # Calculate AI fallback rate
            if self.ai_calls:
                ai_fallback_rate = len(self.ai_fallbacks) / len(self.ai_calls)
            else:
                ai_fallback_rate = 0.0

            return MetricSnapshot(
                timestamp=datetime.now(),
                processing_latency_avg=avg_latency,
                processing_latency_p95=p95_latency,
                processing_latency_p99=p99_latency,
                decision_accuracy=accuracy,
                retry_success_rate=retry_success_rate,
                total_processed=self.total_processed,
                total_failed=self.total_failed,
                total_retried=self.total_retried,
                ai_fallback_rate=ai_fallback_rate,
                active_circuit_breakers=self.active_circuit_breakers
            )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics and statistics
        """
        snapshot = self.get_snapshot()
        uptime = datetime.now() - self.start_time

        return {
            "timestamp": snapshot.timestamp.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "processing": {
                "total_processed": snapshot.total_processed,
                "total_failed": snapshot.total_failed,
                "failure_rate": (
                    snapshot.total_failed / max(snapshot.total_processed, 1)
                ),
                "latency_avg_seconds": snapshot.processing_latency_avg,
                "latency_p95_seconds": snapshot.processing_latency_p95,
                "latency_p99_seconds": snapshot.processing_latency_p99,
            },
            "decisions": {
                "accuracy": snapshot.decision_accuracy,
                "total_decisions": len(self.decisions_made),
            },
            "retries": {
                "total_retried": snapshot.total_retried,
                "success_rate": snapshot.retry_success_rate,
            },
            "ai": {
                "total_calls": self.total_ai_calls,
                "total_fallbacks": self.total_ai_fallbacks,
                "fallback_rate": snapshot.ai_fallback_rate,
            },
            "circuit_breakers": {
                "active_count": snapshot.active_circuit_breakers,
            }
        }

    def log_summary(self) -> None:
        """Log current metrics summary."""
        summary = self.get_summary()

        logger.info("=" * 60)
        logger.info("METRICS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Uptime: {summary['uptime_seconds']:.0f}s")
        logger.info(
            f"Processing: {summary['processing']['total_processed']} total, "
            f"{summary['processing']['total_failed']} failed "
            f"({summary['processing']['failure_rate']:.1%} failure rate)"
        )
        logger.info(
            f"Latency: avg={summary['processing']['latency_avg_seconds']:.3f}s, "
            f"p95={summary['processing']['latency_p95_seconds']:.3f}s, "
            f"p99={summary['processing']['latency_p99_seconds']:.3f}s"
        )
        logger.info(
            f"Decisions: {summary['decisions']['total_decisions']} made, "
            f"{summary['decisions']['accuracy']:.1%} accuracy"
        )
        logger.info(
            f"Retries: {summary['retries']['total_retried']} attempts, "
            f"{summary['retries']['success_rate']:.1%} success rate"
        )
        logger.info(
            f"AI: {summary['ai']['total_calls']} calls, "
            f"{summary['ai']['total_fallbacks']} fallbacks "
            f"({summary['ai']['fallback_rate']:.1%} fallback rate)"
        )
        logger.info(
            f"Circuit Breakers: {summary['circuit_breakers']['active_count']} active"
        )
        logger.info("=" * 60)


# Global metrics collector instance
metrics = MetricsCollector()
