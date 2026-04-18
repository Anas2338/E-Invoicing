"""
Excel Monitor Skill - Detects new Excel uploads within 1 minute.

Uses cursor-based polling to efficiently detect new upload sessions
without scanning the entire table.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select

from skills import BaseSkill, SkillResult, SkillStatus
from database import get_db_session


class ExcelMonitorSkill(BaseSkill):
    """
    Skill for monitoring new Excel upload sessions.

    Implements cursor-based polling to detect new uploads within 1 minute
    of their creation.
    """

    def __init__(self):
        """Initialize Excel monitor skill."""
        super().__init__("excel_monitor")
        self.last_check_timestamp: Optional[datetime] = None

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Input data (no specific requirements for this skill)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # No specific input validation needed for monitoring
        return True, None

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Check for new Excel upload sessions since last check.

        Args:
            context: Execution context (unused for this skill)

        Returns:
            SkillResult with list of new session IDs
        """
        try:
            # Import here to avoid circular dependency
            from sqlalchemy.orm import Session
            import sys
            from pathlib import Path

            # Add project root and backend to path (works on both Windows and Docker)
            # Backend must be in path for its relative imports (from src.*)
            project_root = Path(__file__).parent.parent.parent
            backend_path = project_root / "backend"
            sys.path.insert(0, str(project_root))
            sys.path.insert(0, str(backend_path))

            # Import using src.* (not backend.src.*) to match backend's own imports
            from src.models.excel_upload_session import ExcelUploadSession

            with get_db_session() as db:
                # Determine cursor position
                if self.last_check_timestamp is None:
                    # First run: check last 5 minutes to catch any recent uploads
                    cursor = datetime.utcnow() - timedelta(minutes=5)
                else:
                    cursor = self.last_check_timestamp

                # Query for new sessions since cursor
                query = select(ExcelUploadSession).where(
                    ExcelUploadSession.upload_timestamp > cursor
                ).order_by(ExcelUploadSession.upload_timestamp)

                new_sessions = db.execute(query).scalars().all()

                # Update cursor to current time
                self.last_check_timestamp = datetime.utcnow()

                session_ids = [str(session.id) for session in new_sessions]

                if session_ids:
                    self.logger.info(f"Detected {len(session_ids)} new Excel upload(s)")

                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    data={
                        "new_sessions": session_ids,
                        "count": len(session_ids),
                        "cursor": self.last_check_timestamp.isoformat()
                    },
                    metadata={
                        "check_timestamp": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            return self.handle_error(e, context)

    def reset_cursor(self):
        """Reset cursor to start monitoring from current time."""
        self.last_check_timestamp = datetime.utcnow()
        self.logger.info("Excel monitor cursor reset")
