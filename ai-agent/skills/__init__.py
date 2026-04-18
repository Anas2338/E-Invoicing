"""
Agent Skills - Base skill class and skill registry.

Provides a common interface for all agent skills and a registry
pattern for skill discovery and execution.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SkillStatus(str, Enum):
    """Status of skill execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class SkillResult:
    """
    Result of skill execution.

    Provides standardized output format for all skills.
    """

    def __init__(
        self,
        status: SkillStatus,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize skill result.

        Args:
            status: Execution status
            data: Result data (if successful)
            error: Error message (if failed)
            metadata: Additional metadata (timing, retries, etc.)
        """
        self.status = status
        self.data = data or {}
        self.error = error
        self.metadata = metadata or {}

    def is_success(self) -> bool:
        """Check if skill execution was successful."""
        return self.status == SkillStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if skill execution failed."""
        return self.status == SkillStatus.FAILURE

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseSkill(ABC):
    """
    Base class for all agent skills.

    Defines the interface that all skills must implement:
    - execute: Main skill logic
    - validate_input: Input validation
    - handle_error: Error handling
    """

    def __init__(self, name: str):
        """
        Initialize base skill.

        Args:
            name: Skill name for logging and identification
        """
        self.name = name
        self.logger = logging.getLogger(f"skill.{name}")

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Execute the skill with given context.

        Args:
            context: Execution context with input data

        Returns:
            SkillResult with execution outcome
        """
        pass

    @abstractmethod
    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data before execution.

        Args:
            data: Input data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    def handle_error(self, exception: Exception, context: Dict[str, Any]) -> SkillResult:
        """
        Handle errors during skill execution.

        Args:
            exception: The exception that occurred
            context: Execution context

        Returns:
            SkillResult with error information
        """
        error_message = f"{self.name} failed: {str(exception)}"
        self.logger.error(error_message, exc_info=True)

        return SkillResult(
            status=SkillStatus.FAILURE,
            error=error_message,
            metadata={
                "exception_type": type(exception).__name__,
                "context": context
            }
        )

    def run(self, context: Dict[str, Any]) -> SkillResult:
        """
        Run the skill with input validation and error handling.

        This is the main entry point for skill execution.

        Args:
            context: Execution context

        Returns:
            SkillResult with execution outcome
        """
        import time
        start_time = time.time()

        # Structured logging: START
        self.logger.info(
            f"[SKILL_START] skill={self.name} context_keys={list(context.keys())}"
        )

        try:
            # Validate input
            is_valid, error_message = self.validate_input(context)
            if not is_valid:
                elapsed = time.time() - start_time
                self.logger.warning(
                    f"[SKILL_VALIDATION_FAILED] skill={self.name} "
                    f"error='{error_message}' elapsed={elapsed:.3f}s"
                )
                return SkillResult(
                    status=SkillStatus.FAILURE,
                    error=f"Input validation failed: {error_message}",
                    metadata={"elapsed_seconds": elapsed}
                )

            # Execute skill
            result = self.execute(context)
            elapsed = time.time() - start_time

            # Structured logging: COMPLETE
            log_level = logging.INFO if result.is_success() else logging.ERROR
            self.logger.log(
                log_level,
                f"[SKILL_COMPLETE] skill={self.name} status={result.status.value} "
                f"elapsed={elapsed:.3f}s"
            )

            # Add timing to metadata
            result.metadata["elapsed_seconds"] = elapsed
            return result

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(
                f"[SKILL_ERROR] skill={self.name} "
                f"exception={type(e).__name__} elapsed={elapsed:.3f}s",
                exc_info=True
            )
            result = self.handle_error(e, context)
            result.metadata["elapsed_seconds"] = elapsed
            return result


class SkillRegistry:
    """
    Registry for managing and discovering agent skills.

    Provides centralized skill management and execution.
    """

    def __init__(self):
        """Initialize skill registry."""
        self._skills: Dict[str, BaseSkill] = {}
        self.logger = logging.getLogger("skill.registry")

    def register(self, skill: BaseSkill):
        """
        Register a skill.

        Args:
            skill: Skill instance to register
        """
        self._skills[skill.name] = skill
        self.logger.info(f"Registered skill: {skill.name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill instance or None if not found
        """
        return self._skills.get(name)

    def execute(self, name: str, context: Dict[str, Any]) -> SkillResult:
        """
        Execute a skill by name.

        Args:
            name: Skill name
            context: Execution context

        Returns:
            SkillResult with execution outcome
        """
        skill = self.get(name)
        if not skill:
            return SkillResult(
                status=SkillStatus.FAILURE,
                error=f"Skill not found: {name}"
            )

        return skill.run(context)

    def list_skills(self) -> list[str]:
        """
        List all registered skills.

        Returns:
            List of skill names
        """
        return list(self._skills.keys())


# Global skill registry instance
skill_registry = SkillRegistry()
