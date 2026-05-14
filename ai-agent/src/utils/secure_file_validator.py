"""Secure file validation for uploaded Excel files."""

import zipfile
import logging
from io import BytesIO
from typing import Tuple, Optional
import magic

logger = logging.getLogger(__name__)


class SecureFileValidator:
    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024
    MAX_COMPRESSION_RATIO = 10

    ALLOWED_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip',
    }

    ALLOWED_EXTENSIONS = {'.xlsx'}

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        if not filename:
            return False
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{extension}' in SecureFileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_magic_bytes(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        try:
            file_bytes.seek(0)
            header = file_bytes.read(2048)
            file_bytes.seek(0)
            mime_type = magic.from_buffer(header, mime=True)
            if mime_type not in SecureFileValidator.ALLOWED_MIME_TYPES:
                return False, f"Invalid file type. Detected: {mime_type}."
            return True, None
        except Exception as e:
            logger.error(f"Error validating magic bytes: {e}")
            return False, f"Error validating file type: {str(e)}"

    @staticmethod
    def validate_file_size(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        try:
            file_bytes.seek(0, 2)
            file_size = file_bytes.tell()
            file_bytes.seek(0)
            if file_size > SecureFileValidator.MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = SecureFileValidator.MAX_FILE_SIZE / (1024 * 1024)
                return False, f"File too large: {size_mb:.2f}MB. Maximum: {max_mb:.0f}MB"
            if file_size == 0:
                return False, "File is empty"
            return True, None
        except Exception as e:
            logger.error(f"Error validating file size: {e}")
            return False, f"Error validating file size: {str(e)}"

    @staticmethod
    def validate_zip_bomb(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        try:
            file_bytes.seek(0)
            compressed_size = file_bytes.seek(0, 2)
            file_bytes.seek(0)
            try:
                with zipfile.ZipFile(file_bytes, 'r') as zf:
                    total_uncompressed = sum(info.file_size for info in zf.infolist())
                    if total_uncompressed > SecureFileValidator.MAX_UNCOMPRESSED_SIZE:
                        return False, f"File expands too large when decompressed."
                    if compressed_size > 0:
                        compression_ratio = total_uncompressed / compressed_size
                        if compression_ratio > SecureFileValidator.MAX_COMPRESSION_RATIO:
                            return False, f"Suspicious compression ratio ({compression_ratio:.1f}x)."
            except zipfile.BadZipFile:
                return False, "File is not a valid Excel file (invalid ZIP structure)"
            file_bytes.seek(0)
            return True, None
        except Exception as e:
            logger.error(f"Error validating zip bomb: {e}")
            return False, f"Error validating file structure: {str(e)}"

    @staticmethod
    def validate_excel_structure(file_bytes: BytesIO) -> Tuple[bool, Optional[str]]:
        try:
            file_bytes.seek(0)
            with zipfile.ZipFile(file_bytes, 'r') as zf:
                required_files = ['[Content_Types].xml', 'xl/workbook.xml']
                file_list = zf.namelist()
                for rf in required_files:
                    if rf not in file_list:
                        return False, f"Invalid Excel file structure: missing {rf}"
                suspicious_patterns = [
                    '.exe', '.dll', '.bat', '.cmd', '.ps1', '.vbs', '.js',
                    'macro', 'vbaProject.bin',
                ]
                for file_name in file_list:
                    file_name_lower = file_name.lower()
                    for pattern in suspicious_patterns:
                        if pattern in file_name_lower:
                            return False, f"Excel file contains suspicious content: {file_name}"
            file_bytes.seek(0)
            return True, None
        except Exception as e:
            logger.error(f"Error validating Excel structure: {e}")
            return False, f"Error validating Excel structure: {str(e)}"

    @staticmethod
    def validate_file_comprehensive(file_bytes: BytesIO, filename: str) -> Tuple[bool, Optional[str]]:
        if not SecureFileValidator.validate_file_extension(filename):
            return False, "Invalid file extension. Only .xlsx files are allowed."
        is_valid, error = SecureFileValidator.validate_file_size(file_bytes)
        if not is_valid:
            return False, error
        is_valid, error = SecureFileValidator.validate_magic_bytes(file_bytes)
        if not is_valid:
            return False, error
        is_valid, error = SecureFileValidator.validate_zip_bomb(file_bytes)
        if not is_valid:
            return False, error
        is_valid, error = SecureFileValidator.validate_excel_structure(file_bytes)
        if not is_valid:
            return False, error
        return True, None
