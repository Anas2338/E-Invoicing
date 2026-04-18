"""
AI Agent - Main entry point for autonomous invoice processing.

This agent replaces the FTE worker with:
- Continuous monitoring (1-minute detection vs hourly)
- 5-minute processing precision (vs hourly batches)
- Intelligent error classification and adaptive retry strategies
- Priority-based processing
- Hourly health checks with anomaly detection
- Claude-powered decision making for complex scenarios

Usage:
    python -m main
"""
import signal
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent import AIAgent
from config import config
from validation import validate_environment
from health_server import start_health_server_thread

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE)
    ]
)

logger = logging.getLogger(__name__)

# Global agent instance for signal handling
agent_instance = None


def signal_handler(signum, frame):
    """
    Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"AI Agent: Received {signal_name} signal, initiating graceful shutdown...")

    if agent_instance:
        agent_instance.shutdown()

    logger.info("AI Agent: Shutdown complete")
    sys.exit(0)


def main():
    """
    Main entry point for AI Agent.
    Sets up signal handlers and starts the agent.
    """
    global agent_instance

    logger.info("=" * 80)
    logger.info("AI Agent: Initializing...")
    logger.info(f"  Version: {config.AGENT_VERSION}")
    logger.info(f"  Environment: {config.APP_ENV}")
    logger.info(f"  AI Provider: {config.AI_PROVIDER}")
    logger.info(f"  Processing Interval: {config.AGENT_CHECK_INTERVAL}s")
    logger.info(f"  Health Check Interval: 1 hour")
    logger.info("=" * 80)

    # Validate environment configuration before starting
    logger.info("Validating environment configuration...")
    validate_environment()
    logger.info("[OK] Environment validation complete")

    # Start health server for Hugging Face Spaces status
    logger.info("Starting health server on port 7860...")
    start_health_server_thread()
    logger.info("[OK] Health server started")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop

    try:
        # Create and start agent
        agent_instance = AIAgent()
        agent_instance.start()

    except Exception as e:
        logger.error(f"AI Agent: Fatal error during startup: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
