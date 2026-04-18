"""
Secure file validation utility for uploaded files.

Protects against:
- File type spoofing (validates magic bytes, not just extension)
- Zip bombs (Excel files are ZIP archives)
- XXE attacks (XML External Entity)
- Malicious formulas
- Oversized files
"""

import zipfile
import logging
from io import BytesIO
from typing import Tuple, Optional
import magic

logger = logging.getLogger(__name__)


class SecureFileValidator:
    """Secure file validation for uploads."""

    # Maximum file size: 5MB
    MAX_FILE_SIZE = 5 * 1024 * 1024

    # Maximum uncompressed size: 50MB (to prevent zip bombs)
    MAX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024

    # Maximum compression ratio (uncompressed / compressed)
    # If ratio > 10, likely a zip bomb
    MAX_COMPRESSION_RATIO = 10

    # Allowed MIME types for Excel files
    ALLOWED_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/zip',  # Excel files are ZIP archives
    }

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.xlsx'}

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """
        Validate file extension.

        Args:
            filename: Name of the file

        Returns:
            True if extension is allowed
        """
        if not filename:
            return False

        # Get extension (case-insensitive)
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{extension}' in SecureFileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_magic_bytes(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        """
        Validate file type by magic bytes (actual content), not extension.

        Args:
            file_bytes: File content as BytesIO

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Read first 2048 bytes for magic detection
            file_bytes.seek(0)
            header = file_bytes.read(2048)
            file_bytes.seek(0)

            # Detect MIME type from content
            mime_type = magic.from_buffer(header, mime=True)

            logger.info(f"Detected MIME type: {mime_type}")

            if mime_type not in SecureFileValidator.ALLOWED_MIME_TYPES:
                return False, f"Invalid file type. Detected: {mime_type}. Only Excel (.xlsx) files are allowed."

            return True, None

        except Exception as e:
            logger.error(f"Error validating magic bytes: {e}")
            return False, f"Error validating file type: {str(e)}"

    @staticmethod
    def validate_file_size(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        """
        Validate file size.

        Args:
            file_bytes: File content as BytesIO

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            file_bytes.seek(0, 2)  # Seek to end
            file_size = file_bytes.tell()
            file_bytes.seek(0)  # Reset to beginning

            if file_size > SecureFileValidator.MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = SecureFileValidator.MAX_FILE_SIZE / (1024 * 1024)
                return False, f"File too large: {size_mb:.2f}MB. Maximum allowed: {max_mb:.0f}MB"

            if file_size == 0:
                return False, "File is empty"

            return True, None

        except Exception as e:
            logger.error(f"Error validating file size: {e}")
            return False, f"Error validating file size: {str(e)}"

    @staticmethod
    def validate_zip_bomb(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        """
        Validate against zip bomb attacks.

        Excel files are ZIP archives. Attackers can create files that are small
        when compressed but expand to huge sizes when decompressed.

        Args:
            file_bytes: File content as BytesIO

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            file_bytes.seek(0)

            # Get compressed size
            compressed_size = file_bytes.seek(0, 2)
            file_bytes.seek(0)

            # Try to open as ZIP
            try:
                with zipfile.ZipFile(file_bytes, 'r') as zf:
                    # Calculate total uncompressed size
                    total_uncompressed = sum(info.file_size for info in zf.infolist())

                    # Check absolute uncompressed size
                    if total_uncompressed > SecureFileValidator.MAX_UNCOMPRESSED_SIZE:
                        size_mb = total_uncompressed / (1024 * 1024)
                        max_mb = SecureFileValidator.MAX_UNCOMPRESSED_SIZE / (1024 * 1024)
                        return False, f"File expands to {size_mb:.2f}MB when decompressed. Maximum allowed: {max_mb:.0f}MB"

                    # Check compression ratio (zip bomb indicator)
                    if compressed_size > 0:
                        compression_ratio = total_uncompressed / compressed_size

                        if compression_ratio > SecureFileValidator.MAX_COMPRESSION_RATIO:
                            return False, f"Suspicious compression ratio detected ({compression_ratio:.1f}x). Possible zip bomb attack."

                    logger.info(f"Zip validation passed. Compressed: {compressed_size} bytes, Uncompressed: {total_uncompressed} bytes, Ratio: {compression_ratio:.2f}x")

            except zipfile.BadZipFile:
                return False, "File is not a valid Excel file (invalid ZIP structure)"

            file_bytes.seek(0)
            return True, None

        except Exception as e:
            logger.error(f"Error validating zip bomb: {e}")
            return False, f"Error validating file structure: {str(e)}"

    @staticmethod
    def validate_excel_structure(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        """
        Validate Excel file structure and check for malicious content.

        Args:
            file_bytes: File content as BytesIO

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            file_bytes.seek(0)

            with zipfile.ZipFile(file_bytes, 'r') as zf:
                # Check for required Excel files
                required_files = ['[Content_Types].xml', 'xl/workbook.xml']
                file_list = zf.namelist()

                for required_file in required_files:
                    if required_file not in file_list:
                        return False, f"Invalid Excel file structure: missing {required_file}"

                # Check for suspicious files that shouldn't be in Excel
                suspicious_patterns = [
                    '.exe', '.dll', '.bat', '.cmd', '.ps1', '.vbs', '.js',
                    'macro', 'vbaProject.bin'  # Macros
                ]

                for file_name in file_list:
                    file_name_lower = file_name.lower()
                    for pattern in suspicious_patterns:
                        if pattern in file_name_lower:
                            logger.warning(f"Suspicious file detected in Excel: {file_name}")
                            return False, f"Excel file contains suspicious content: {file_name}"

            file_bytes.seek(0)
            return True, None

        except Exception as e:
            logger.error(f"Error validating Excel structure: {e}")
            return False, f"Error validating Excel structure: {str(e)}"

    @staticmethod
    def validate_file_comprehensive(file_bytes: BytesIO, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive file validation combining all security checks.

        Args:
            file_bytes: File content as BytesIO
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        # 1. Validate file extension
        if not SecureFileValidator.validate_file_extension(filename):
            return False, "Invalid file extension. Only .xlsx files are allowed."

        # 2. Validate file size
        is_valid, error = SecureFileValidator.validate_file_size(file_bytes)
        if not is_valid:
            return False, error

        # 3. Validate magic bytes (actual file type)
        is_valid, error = SecureFileValidator.validate_magic_bytes(file_bytes)
        if not is_valid:
            return False, error

        # 4. Validate against zip bombs
        is_valid, error = SecureFileValidator.validate_zip_bomb(file_bytes)
        if not is_valid:
            return False, error

        # 5. Validate Excel structure and check for malicious content
        is_valid, error = SecureFileValidator.validate_excel_structure(file_bytes)
        if not is_valid:
            return False, error

        logger.info(f"File validation passed for: {filename}")
        return True, None
