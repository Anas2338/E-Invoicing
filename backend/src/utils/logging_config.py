"""
Logging configuration for FTE Worker.

This module provides centralized logging configuration with:
- Structured log formatting
- Multiple handlers (console, file, rotating file)
- Log level configuration
- Performance monitoring
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure logging for FTE Worker.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: current directory)
        log_to_console: Enable console logging
        log_to_file: Enable file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("fte_worker")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handlers
    if log_to_file:
        if log_dir is None:
            log_dir = Path.cwd()
        else:
            log_dir = Path(log_dir)
            # Only create directory if it doesn't exist (lazy creation)
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                # If we can't create the log directory, fall back to console-only logging
                logger.warning(f"Cannot create log directory {log_dir}: {e}. Falling back to console logging only.")
                return logger

        # Rotating file handler for general logs
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "fte_worker.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Separate error log file
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "fte_worker_error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "fte_worker") -> logging.Logger:
    """
    Get configured logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Performance logging helper
class PerformanceLogger:
    """Context manager for logging execution time."""

    def __init__(self, logger: logging.Logger, operation: str):
        """
        Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Description of operation being timed
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log execution time."""
        import time
        elapsed = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation} (took {elapsed:.2f}s)")
        else:
            self.logger.error(
                f"Failed: {self.operation} (took {elapsed:.2f}s) - {exc_type.__name__}: {exc_val}"
            )
        return False  # Don't suppress exceptions


# Example usage:
if __name__ == "__main__":
    # Setup logging
    logger = setup_logging(
        log_level="INFO",
        log_dir=Path("/var/log/fte-worker"),
        log_to_console=True,
        log_to_file=True
    )

    # Test logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test performance logging
    with PerformanceLogger(logger, "test operation"):
        import time
        time.sleep(1)
