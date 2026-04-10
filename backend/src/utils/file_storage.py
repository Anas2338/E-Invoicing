"""
File storage utilities for Excel file management.
"""
import os
from pathlib import Path
from typing import Optional
from uuid import UUID
from datetime import datetime


class FileStorageService:
    """Service for managing Excel file storage."""

    def __init__(self, base_upload_dir: str = "uploads"):
        """
        Initialize file storage service.

        Args:
            base_upload_dir: Base directory for uploads (default: "uploads")
        """
        self.base_upload_dir = Path(base_upload_dir)
        self._ensure_base_dir_exists()

    def _ensure_base_dir_exists(self) -> None:
        """Ensure base upload directory exists."""
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    def get_user_directory(self, user_id: UUID) -> Path:
        """
        Get user-specific upload directory.

        Args:
            user_id: User UUID

        Returns:
            Path to user directory
        """
        user_dir = self.base_upload_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def generate_file_path(self, user_id: UUID, original_filename: str) -> str:
        """
        Generate unique file path for uploaded Excel file.

        Args:
            user_id: User UUID
            original_filename: Original filename from upload

        Returns:
            Relative file path for storage
        """
        user_dir = self.get_user_directory(user_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Extract file extension
        file_ext = Path(original_filename).suffix
        if not file_ext:
            file_ext = ".xlsx"

        # Generate unique filename with timestamp
        filename = f"{timestamp}{file_ext}"
        file_path = user_dir / filename

        # Return relative path as string
        return str(file_path)

    def get_absolute_path(self, relative_path: str) -> Path:
        """
        Convert relative file path to absolute path.

        Args:
            relative_path: Relative file path

        Returns:
            Absolute Path object
        """
        return Path.cwd() / relative_path

    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Relative or absolute file path

        Returns:
            True if file exists, False otherwise
        """
        abs_path = self.get_absolute_path(file_path)
        return abs_path.exists() and abs_path.is_file()

    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            file_path: Relative or absolute file path

        Returns:
            True if file was deleted, False if file didn't exist
        """
        abs_path = self.get_absolute_path(file_path)
        if abs_path.exists():
            abs_path.unlink()
            return True
        return False

    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        Get file size in bytes.

        Args:
            file_path: Relative or absolute file path

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        abs_path = self.get_absolute_path(file_path)
        if abs_path.exists():
            return abs_path.stat().st_size
        return None

    def save_uploaded_file(self, user_id: UUID, file_content: bytes, original_filename: str) -> str:
        """
        Save uploaded file to storage.

        Args:
            user_id: User UUID
            file_content: File content as bytes
            original_filename: Original filename from upload

        Returns:
            Relative file path where file was saved
        """
        file_path = self.generate_file_path(user_id, original_filename)
        abs_path = self.get_absolute_path(file_path)

        # Write file content
        abs_path.write_bytes(file_content)

        return file_path
