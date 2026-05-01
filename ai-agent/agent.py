"""
AI Agent - Main orchestrator for autonomous invoice processing.

Coordinates all agent skills and manages scheduling for:
- 5-minute invoice processing cycles
- Hourly health checks
"""
import logging
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root and backend to path (works on both Windows and Docker)
# Backend must be in path for its relative imports (from src.*)
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

# CRITICAL: Import backend models using src.* (not backend.src.*) to match backend's own imports
# This ensures there's only ONE import path, preventing SQLAlchemy metadata conflicts
# Import ALL related models to resolve SQLAlchemy relationships
from src.models.user import User
from src.models.excel_upload_session import ExcelUploadSession
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus
from src.models.ai_agent_health_check import AIAgentHealthCheck, HealthStatus
from sqlalchemy import select, and_, func
import httpx

# Import skills AFTER models - they will use the already-registered models
from skills.priority_scheduler import PrioritySchedulerSkill
from skills.invoice_validator import InvoiceValidatorSkill
# FBRPosterSkill removed - invoices are now transferred to main DB for manual posting
from skills.error_handler import ErrorHandlerSkill
from skills.retry_manager import RetryManagerSkill

from config import config
from database import get_db_session, test_database_connection

# Configure logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set UTF-8 encoding for stdout on Windows to handle Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)


class AIAgent:
    """
    Main AI Agent orchestrator.

    Manages scheduling and coordination of all agent skills.
    """

    def __init__(self):
        """Initialize AI Agent with scheduler and skills."""
        self.scheduler = BackgroundScheduler()
        self.start_time = datetime.utcnow()
        self.is_running = False

        logger.info("AI Agent: Orchestrator initialized")

    def start(self):
        """
        Start the AI Agent scheduler.

        Configures and starts:
        - 5-minute invoice processing job
        - Hourly health check job
        """
        logger.info("AI Agent: Starting scheduler...")

        # Schedule 5-minute invoice processing job
        self.scheduler.add_job(
            func=self._process_invoices_job,
            trigger=IntervalTrigger(seconds=config.AGENT_CHECK_INTERVAL),
            id='process_invoices',
            name='Process Pending Invoices',
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs
            coalesce=True  # Combine missed runs into one
        )
        logger.info(f"  Scheduled: Invoice processing every {config.AGENT_CHECK_INTERVAL}s")

        # Schedule hourly health check job
        self.scheduler.add_job(
            func=self._health_check_job,
            trigger=CronTrigger.from_crontab(config.HEALTH_CHECK_CRON),
            id='health_check',
            name='Hourly Health Check',
            replace_existing=True,
            max_instances=1
        )
        logger.info(f"  Scheduled: Health check at {config.HEALTH_CHECK_CRON}")

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("AI Agent: Scheduler started successfully")
        logger.info("AI Agent: Running... (Press Ctrl+C to stop)")

        # Keep main thread alive and update heartbeat
        try:
            while self.is_running:
                self._update_heartbeat()
                time.sleep(60)  # Update heartbeat every minute
        except KeyboardInterrupt:
            logger.info("AI Agent: Keyboard interrupt received")
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the AI Agent."""
        logger.info("AI Agent: Shutting down scheduler...")

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        self.is_running = False
        logger.info("AI Agent: Scheduler stopped")

    def _process_invoices_job(self):
        """
        5-minute invoice processing and transfer job.

        Queries validated invoices whose scheduled time has arrived,
        and immediately transfers them to main database.
        """
        logger.info("=" * 80)
        logger.info("AI Agent: Starting invoice processing cycle")
        logger.info("=" * 80)

        try:
            # Update heartbeat at start of job
            self._update_heartbeat()

            # Import transfer service
            from src.services.transfer_service import TransferService
            from src.database.session import get_db_session as get_main_db_session
            import asyncio

            with get_db_session() as automation_db:
                with get_main_db_session() as main_db:
                    # Convert UTC to PKT (Pakistan Time, UTC+5)
                    now_utc = datetime.utcnow()
                    now_pkt = now_utc + timedelta(hours=5)  # PKT is UTC+5

                    logger.info(f"AI Agent: Current time - UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}, PKT: {now_pkt.strftime('%Y-%m-%d %H:%M:%S')}")

                    # SECURITY: Process invoices per user to ensure data isolation
                    # Step 1: Get distinct users with validated invoices ready for transfer
                    users_with_pending_query = select(AutomationInvoice.user_id).distinct().where(
                        and_(
                            AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
                            AutomationInvoice.scheduled_date <= now_pkt.date(),
                            AutomationInvoice.scheduled_time <= now_pkt.time()
                        )
                    )
                    users_with_pending = automation_db.execute(users_with_pending_query).scalars().all()

                    if not users_with_pending:
                        logger.info("AI Agent: No validated invoices ready for transfer")
                        return

                    logger.info(f"AI Agent: Found {len(users_with_pending)} user(s) with validated invoices ready for transfer")

                    # Step 2: Process each user's invoices separately with fair batch limits
                    all_validated_invoices = []
                    for user_id in users_with_pending:
                        # Query this user's validated invoices with per-user limit
                        user_query = select(AutomationInvoice).where(
                            and_(
                                AutomationInvoice.user_id == user_id,  # ✅ USER ISOLATION
                                AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
                                AutomationInvoice.scheduled_date <= now_pkt.date(),
                                AutomationInvoice.scheduled_time <= now_pkt.time()
                            )
                        ).order_by(
                            AutomationInvoice.scheduled_date.asc(),
                            AutomationInvoice.scheduled_time.asc(),
                            AutomationInvoice.priority.asc()
                        ).limit(config.BATCH_SIZE_PER_USER)

                        user_invoices = automation_db.execute(user_query).scalars().all()
                        all_validated_invoices.extend(user_invoices)

                        logger.info(f"AI Agent: User {user_id} - {len(user_invoices)} invoice(s) queued for transfer")

                    if not all_validated_invoices:
                        logger.info("AI Agent: No validated invoices ready for transfer")
                        return

                    logger.info(f"AI Agent: Total {len(all_validated_invoices)} validated invoice(s) ready for immediate transfer")

                    # Transfer invoices immediately using TransferService
                    transfer_service = TransferService()

                    transferred_count = 0
                    failed_count = 0

                    for invoice in all_validated_invoices:
                        try:
                            logger.info(
                                f"AI Agent: Transferring invoice {invoice.invoice_number} (ID: {invoice.id}) "
                                f"scheduled for {invoice.scheduled_date} {invoice.scheduled_time}"
                            )

                            # Transform and transfer invoice
                            manual_invoice = transfer_service.transform_invoice_data(invoice)

                            # Check for duplicate
                            if transfer_service.check_duplicate(main_db, invoice.user_id, invoice.id):
                                logger.warning(f"Duplicate detected: invoice {invoice.id} already transferred")
                                invoice.status = AutomationInvoiceStatus.TRANSFERRED
                                invoice.transferred_at = datetime.utcnow()
                                invoice.transfer_error = "Duplicate - already transferred"
                                automation_db.add(invoice)
                                automation_db.commit()
                                failed_count += 1
                                continue

                            # Insert into main database
                            main_db.add(manual_invoice)
                            main_db.flush()

                            # Update automation invoice status
                            invoice.status = AutomationInvoiceStatus.TRANSFERRED
                            invoice.transferred_at = datetime.utcnow()
                            invoice.transfer_error = None
                            automation_db.add(invoice)

                            # Commit both databases
                            main_db.commit()
                            automation_db.commit()

                            transferred_count += 1
                            logger.info(f"[SUCCESS] Transferred invoice {invoice.invoice_number} -> Main DB ID: {manual_invoice.id}")

                        except Exception as e:
                            # Rollback both sessions
                            main_db.rollback()
                            automation_db.rollback()

                            error_type = transfer_service.classify_error(e)
                            error_details = f"[{error_type}] {type(e).__name__}: {str(e)}"
                            logger.error(f"[FAILED] Transfer failed for invoice {invoice.invoice_number}: {error_details}")

                            # Mark as failed
                            invoice.status = AutomationInvoiceStatus.TRANSFER_FAILED
                            invoice.transfer_error = error_details[:2000]
                            automation_db.add(invoice)
                            automation_db.commit()

                            failed_count += 1

                    logger.info("AI Agent: Invoice processing cycle completed")
                    logger.info(f"  [OK] Invoices transferred: {transferred_count}")
                    logger.info(f"  [FAIL] Invoices failed: {failed_count}")
                    logger.info(f"  -> Check http://localhost:3000/invoices/history for transferred invoices")
                    logger.info("=" * 80)

        except Exception as e:
            logger.error(f"AI Agent: Error in invoice processing job: {str(e)}", exc_info=True)

    def _health_check_job(self):
        """
        Hourly health check job.

        Counts pending/failed invoices, tests FBR API, checks database,
        detects anomalies, and stores results in ai_agent_health_check table.

        NOTE: Health check queries are intentionally system-wide (not filtered by user_id)
        to monitor overall agent infrastructure health. This is acceptable for monitoring
        purposes as it only aggregates counts without exposing individual user data.
        """
        logger.info("=" * 80)
        logger.info("AI Agent: Starting hourly health check")
        logger.info("=" * 80)

        try:
            with get_db_session() as db:
                # Count invoices by status
                pending_count = db.execute(
                    select(func.count(AutomationInvoice.id)).where(
                        AutomationInvoice.status == AutomationInvoiceStatus.PENDING
                    )
                ).scalar()

                failed_count = db.execute(
                    select(func.count(AutomationInvoice.id)).where(
                        AutomationInvoice.status == AutomationInvoiceStatus.FAILED
                    )
                ).scalar()

                # Calculate processing backlog (pending invoices past their scheduled time)
                now = datetime.utcnow()
                backlog_count = db.execute(
                    select(func.count(AutomationInvoice.id)).where(
                        and_(
                            AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
                            AutomationInvoice.scheduled_date < now.date()
                        )
                    )
                ).scalar()

                # Test database connectivity and latency
                db_healthy, db_latency = test_database_connection()
                db_status = "healthy" if db_healthy else "unhealthy"

                # Test FBR API connectivity and latency
                fbr_status, fbr_latency = self._test_fbr_api()

                # Analyze failure patterns (last hour)
                one_hour_ago = now - timedelta(hours=1)
                recent_failures = db.execute(
                    select(AutomationInvoice).where(
                        and_(
                            AutomationInvoice.status == AutomationInvoiceStatus.FAILED,
                            AutomationInvoice.processed_at >= one_hour_ago
                        )
                    )
                ).scalars().all()

                failure_patterns = self._analyze_failure_patterns(recent_failures)
                common_errors = self._extract_common_errors(recent_failures)

                # Detect anomalies
                anomalies = self._detect_anomalies(
                    pending_count=pending_count,
                    failed_count=failed_count,
                    backlog_count=backlog_count,
                    db_latency=db_latency,
                    fbr_status=fbr_status,
                    recent_failures=recent_failures
                )

                # Determine overall health status
                overall_status = self._determine_health_status(anomalies, db_status, fbr_status)

                # Generate recommended actions
                recommended_actions = self._generate_recommendations(anomalies, overall_status)

                # Store health check result
                health_check = AIAgentHealthCheck(
                    check_timestamp=now,
                    overall_status=overall_status,
                    pending_invoice_count=pending_count,
                    failed_invoice_count=failed_count,
                    processing_backlog=backlog_count,
                    failure_patterns=failure_patterns,
                    common_errors=common_errors,
                    fbr_api_status=fbr_status,
                    fbr_api_latency_ms=fbr_latency,
                    database_status=db_status,
                    database_latency_ms=db_latency,
                    agent_cpu_percent=None,  # TODO: Implement CPU monitoring
                    agent_memory_mb=None,  # TODO: Implement memory monitoring
                    anomalies_detected=anomalies,
                    recommended_actions=recommended_actions,
                    agent_version=config.AGENT_VERSION,
                    agent_uptime_seconds=self.get_uptime_seconds()
                )

                db.add(health_check)
                db.commit()

                logger.info("AI Agent: Health check completed")
                logger.info(f"  Overall Status: {overall_status}")
                logger.info(f"  Pending Invoices: {pending_count}")
                logger.info(f"  Failed Invoices: {failed_count}")
                logger.info(f"  Processing Backlog: {backlog_count}")
                logger.info(f"  Database: {db_status} ({db_latency}ms)")
                logger.info(f"  FBR API: {fbr_status} ({fbr_latency}ms)")
                logger.info(f"  Anomalies: {len(anomalies)}")
                logger.info("=" * 80)

        except Exception as e:
            logger.error(f"AI Agent: Error in health check job: {str(e)}", exc_info=True)

    def _update_heartbeat(self):
        """
        Update heartbeat file for Docker health checks.

        Writes current timestamp to heartbeat file.
        Docker health check verifies file exists and is recent.
        """
        try:
            config.HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
            config.HEARTBEAT_FILE.write_text(str(time.time()))
        except Exception as e:
            logger.warning(f"AI Agent: Failed to update heartbeat: {str(e)}")

    def get_uptime_seconds(self) -> int:
        """
        Get agent uptime in seconds.

        Returns:
            Uptime in seconds since agent started
        """
        return int((datetime.utcnow() - self.start_time).total_seconds())

    def _log_decision(self, db, invoice_id, decision_type: str, result):
        """
        Log AI Agent decision to automation_log table.

        Args:
            db: Database session
            invoice_id: Invoice UUID
            decision_type: Type of decision made
            result: SkillResult with decision details OR dict with decision data
        """
        action_map = {
            "validation_failed": AutomationLogAction.VALIDATE,
            "submission_success": AutomationLogAction.SUBMIT,
            "retry_scheduled": AutomationLogAction.RETRY,
            "max_retries_exceeded": AutomationLogAction.RETRY,
            "permanent_failure": AutomationLogAction.SUBMIT,
            "validated_ready_for_transfer": AutomationLogAction.VALIDATE
        }

        status_map = {
            "validation_failed": AutomationLogStatus.FAILURE,
            "submission_success": AutomationLogStatus.SUCCESS,
            "retry_scheduled": AutomationLogStatus.SUCCESS,
            "max_retries_exceeded": AutomationLogStatus.FAILURE,
            "permanent_failure": AutomationLogStatus.FAILURE,
            "validated_ready_for_transfer": AutomationLogStatus.SUCCESS
        }

        # Get user_id from invoice for audit trail
        invoice = db.get(AutomationInvoice, invoice_id)
        user_id_str = str(invoice.user_id) if invoice else None

        # Handle both dict and SkillResult objects
        if isinstance(result, dict):
            decision_data = result
            error_msg = result.get("error") or "Success"
        else:
            # SkillResult object
            decision_data = result.data
            error_msg = result.error or "Success"

        log = AutomationLog(
            automation_invoice_id=invoice_id,
            action=action_map.get(decision_type, AutomationLogAction.VALIDATE),
            status=status_map.get(decision_type, AutomationLogStatus.FAILURE),
            details={
                "decision_type": decision_type,
                "ai_decision": decision_data,
                "rationale": error_msg,
                "model_used": config.CLAUDE_MODEL,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id_str  # ✅ USER CONTEXT FOR AUDIT
            }
        )

        db.add(log)

    def _test_fbr_api(self) -> tuple[str, int]:
        """
        Test FBR API connectivity and latency.

        Returns:
            Tuple of (status, latency_ms)
        """
        try:
            start_time = time.time()
            response = httpx.get(
                config.FBR_SANDBOX_BASE_URL,
                timeout=10.0
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code < 500:
                return "healthy", latency_ms
            else:
                return "degraded", latency_ms

        except Exception as e:
            logger.warning(f"FBR API health check failed: {str(e)}")
            return "unhealthy", 0

    def _analyze_failure_patterns(self, recent_failures) -> dict:
        """
        Analyze patterns in recent failures.

        Args:
            recent_failures: List of failed invoices

        Returns:
            Dictionary with failure pattern analysis
        """
        if not recent_failures:
            return {}

        # Group failures by error type
        error_types = {}
        for invoice in recent_failures:
            error = invoice.validation_errors or "Unknown error"
            error_key = error[:50]  # First 50 chars as key
            error_types[error_key] = error_types.get(error_key, 0) + 1

        return {
            "total_failures": len(recent_failures),
            "error_distribution": error_types,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }

    def _extract_common_errors(self, recent_failures) -> dict:
        """
        Extract common error messages from recent failures.

        Args:
            recent_failures: List of failed invoices

        Returns:
            Dictionary with common errors and counts
        """
        error_counts = {}

        for invoice in recent_failures:
            error = invoice.validation_errors or "Unknown error"
            error_counts[error] = error_counts.get(error, 0) + 1

        # Return top 5 most common errors
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            error: count
            for error, count in sorted_errors
        }

    def _detect_anomalies(
        self,
        pending_count: int,
        failed_count: int,
        backlog_count: int,
        db_latency: int,
        fbr_status: str,
        recent_failures
    ) -> list[str]:
        """
        Detect anomalies based on configured thresholds.

        Args:
            pending_count: Number of pending invoices
            failed_count: Number of failed invoices
            backlog_count: Number of backlogged invoices
            db_latency: Database latency in ms
            fbr_status: FBR API status
            recent_failures: List of recent failures

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Anomaly 1: High failure rate (20% in last hour)
        total_recent = len(recent_failures)
        if total_recent > 10:  # Only check if significant sample size
            failure_rate = total_recent / (total_recent + pending_count) if (total_recent + pending_count) > 0 else 0
            if failure_rate >= config.ANOMALY_FAILURE_RATE_THRESHOLD:
                anomalies.append(f"High failure rate: {failure_rate:.1%} in last hour")

        # Anomaly 2: Large backlog
        if backlog_count >= config.ANOMALY_BACKLOG_THRESHOLD:
            anomalies.append(f"Large processing backlog: {backlog_count} invoices")

        # Anomaly 3: High database latency
        if db_latency >= config.ANOMALY_DATABASE_LATENCY_THRESHOLD:
            anomalies.append(f"High database latency: {db_latency}ms")

        # Anomaly 4: FBR API unhealthy
        if fbr_status == "unhealthy":
            anomalies.append("FBR API is unhealthy")

        return anomalies

    def _determine_health_status(self, anomalies: list, db_status: str, fbr_status: str) -> str:
        """
        Determine overall health status based on anomalies and service status.

        Args:
            anomalies: List of detected anomalies
            db_status: Database status
            fbr_status: FBR API status

        Returns:
            Health status: "healthy", "degraded", or "unhealthy"
        """
        if db_status == "unhealthy" or fbr_status == "unhealthy":
            return HealthStatus.UNHEALTHY

        if len(anomalies) >= 2 or fbr_status == "degraded":
            return HealthStatus.DEGRADED

        if len(anomalies) == 1:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _generate_recommendations(self, anomalies: list, overall_status: str) -> list[str]:
        """
        Generate recommended actions based on anomalies and health status.

        Args:
            anomalies: List of detected anomalies
            overall_status: Overall health status

        Returns:
            List of recommended actions
        """
        recommendations = []

        if not anomalies:
            return ["System operating normally"]

        for anomaly in anomalies:
            if "failure rate" in anomaly.lower():
                recommendations.append("Investigate common error patterns and consider pausing processing")
            elif "backlog" in anomaly.lower():
                recommendations.append("Review processing capacity and consider scaling resources")
            elif "database latency" in anomaly.lower():
                recommendations.append("Check database connection pool and query performance")
            elif "fbr api" in anomaly.lower():
                recommendations.append("Monitor FBR API status and consider retry backoff")

        if overall_status == "unhealthy":
            recommendations.append("CRITICAL: Manual intervention required")

        return recommendations


if __name__ == "__main__":
    """
    Main entry point for AI Agent.

    Creates and starts the agent scheduler.
    """
    agent = AIAgent()
    agent.start()
