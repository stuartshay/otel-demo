"""
File storage service for NFS operations.

Provides safe file and directory operations within a configured
data directory, with path traversal protection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Config

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a file or directory."""

    name: str
    type: str  # "file" or "directory"
    size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {"name": self.name, "type": self.type}
        if self.size is not None:
            result["size"] = self.size
        return result


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class PathNotFoundError(StorageError):
    """Raised when a path does not exist."""

    pass


class InvalidPathError(StorageError):
    """Raised when a path is invalid or attempts traversal."""

    pass


class DirectoryNotEmptyError(StorageError):
    """Raised when trying to delete a non-empty directory."""

    pass


class StorageService:
    """File storage service with path safety.

    Provides safe file and directory operations within a configured
    data directory. All paths are validated to prevent traversal attacks.

    Example:
        service = StorageService(Path("/data"))

        # List directory
        items = service.list_directory("subdir")

        # Read file
        content = service.read_file("subdir/file.txt")

        # Write file
        service.write_file("subdir/new.txt", "Hello!")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize storage service.

        Args:
            data_dir: Root directory for all storage operations.
        """
        self._data_dir = data_dir.resolve()

    @property
    def data_dir(self) -> Path:
        """Get the root data directory."""
        return self._data_dir

    def get_safe_path(self, filepath: str) -> Path:
        """Validate and return safe path within data directory.

        Args:
            filepath: Relative path to validate.

        Returns:
            Resolved absolute path within data directory.

        Raises:
            InvalidPathError: If path attempts traversal outside data directory.
        """
        if not filepath:
            return self._data_dir

        try:
            target = (self._data_dir / filepath).resolve()
            # Ensure path is within data directory
            if self._data_dir in target.parents or target == self._data_dir:
                return target
            raise InvalidPathError(f"Invalid path: {filepath}")
        except (ValueError, OSError) as e:
            raise InvalidPathError(f"Invalid path: {filepath}") from e

    def exists(self, filepath: str) -> bool:
        """Check if a path exists.

        Args:
            filepath: Relative path to check.

        Returns:
            True if path exists, False otherwise.
        """
        try:
            target = self.get_safe_path(filepath)
            return target.exists()
        except InvalidPathError:
            return False

    def is_directory(self, filepath: str) -> bool:
        """Check if path is a directory.

        Args:
            filepath: Relative path to check.

        Returns:
            True if path is a directory, False otherwise.
        """
        try:
            target = self.get_safe_path(filepath)
            return target.is_dir()
        except InvalidPathError:
            return False

    def list_directory(self, filepath: str = "") -> list[FileInfo]:
        """List contents of a directory.

        Args:
            filepath: Relative path to directory (empty for root).

        Returns:
            List of FileInfo objects for directory contents.

        Raises:
            InvalidPathError: If path is invalid.
            PathNotFoundError: If directory does not exist.
        """
        target = self.get_safe_path(filepath)

        if not target.exists():
            raise PathNotFoundError(f"Path not found: {filepath or '/'}")

        if not target.is_dir():
            raise InvalidPathError(f"Not a directory: {filepath}")

        items: list[FileInfo] = []
        for item in sorted(target.iterdir()):
            if item.is_dir():
                items.append(FileInfo(name=item.name, type="directory"))
            else:
                items.append(FileInfo(name=item.name, type="file", size=item.stat().st_size))

        logger.info(f"Listed directory: {filepath or '/'} ({len(items)} items)")
        return items

    def read_file(self, filepath: str) -> tuple[str, int]:
        """Read file content.

        Args:
            filepath: Relative path to file.

        Returns:
            Tuple of (content, size_in_bytes).

        Raises:
            InvalidPathError: If path is invalid or is a directory.
            PathNotFoundError: If file does not exist.
        """
        target = self.get_safe_path(filepath)

        if not target.exists():
            raise PathNotFoundError(f"Path not found: {filepath}")

        if target.is_dir():
            raise InvalidPathError(f"Path is a directory: {filepath}")

        content = target.read_text()
        logger.info(f"Read file: {filepath} ({len(content)} bytes)")
        return content, len(content)

    def write_file(self, filepath: str, content: str) -> tuple[str, int]:
        """Write content to a file.

        Creates parent directories if needed.

        Args:
            filepath: Relative path to file.
            content: Content to write.

        Returns:
            Tuple of (status, size_in_bytes) where status is "created" or "updated".

        Raises:
            InvalidPathError: If path is invalid.
        """
        target = self.get_safe_path(filepath)

        existed = target.exists()

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content)
        status = "updated" if existed else "created"
        logger.info(f"File {status}: {filepath} ({len(content)} bytes)")
        return status, len(content)

    def delete(self, filepath: str) -> str:
        """Delete a file or empty directory.

        Args:
            filepath: Relative path to delete.

        Returns:
            Type of deleted item ("file" or "directory").

        Raises:
            InvalidPathError: If path is invalid.
            PathNotFoundError: If path does not exist.
            DirectoryNotEmptyError: If directory is not empty.
        """
        target = self.get_safe_path(filepath)

        if not target.exists():
            raise PathNotFoundError(f"Path not found: {filepath}")

        if target.is_dir():
            if any(target.iterdir()):
                raise DirectoryNotEmptyError(f"Directory not empty: {filepath}")
            target.rmdir()
            file_type = "directory"
        else:
            target.unlink()
            file_type = "file"

        logger.info(f"Deleted {file_type}: {filepath}")
        return file_type

    def create_directory(self, filepath: str) -> str:
        """Create a directory.

        Creates parent directories if needed.

        Args:
            filepath: Relative path to create.

        Returns:
            Status ("created" or "exists").

        Raises:
            InvalidPathError: If path is invalid or exists as a file.
        """
        target = self.get_safe_path(filepath)

        if target.exists():
            if target.is_dir():
                return "exists"
            raise InvalidPathError(f"Path exists as file: {filepath}")

        target.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {filepath}")
        return "created"


# Global storage service instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance.

    Returns:
        The initialized StorageService.

    Raises:
        RuntimeError: If service is not initialized.
    """
    if _storage_service is None:
        raise RuntimeError("Storage service not initialized")
    return _storage_service


def init_storage_service(config: Config) -> StorageService:
    """Initialize the global storage service.

    Args:
        config: Application configuration.

    Returns:
        The initialized StorageService.
    """
    global _storage_service
    _storage_service = StorageService(config.data_dir)
    return _storage_service
