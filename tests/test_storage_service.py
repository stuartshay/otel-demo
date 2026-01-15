"""Tests for StorageService."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.services.storage import (
    DirectoryNotEmptyError,
    FileInfo,
    InvalidPathError,
    PathNotFoundError,
    StorageService,
)

if TYPE_CHECKING:
    pass


class TestStorageService:
    """Test cases for StorageService class."""

    @pytest.fixture
    def temp_storage(self, tmp_path: Path) -> StorageService:
        """Create a storage service with a temporary directory."""
        return StorageService(tmp_path)

    @pytest.fixture
    def populated_storage(self, temp_storage: StorageService, tmp_path: Path) -> StorageService:
        """Create a storage service with some test files."""
        # Create test files and directories
        (tmp_path / "file1.txt").write_text("Hello World")
        (tmp_path / "file2.txt").write_text("Test content")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.txt").write_text("Nested file")
        return temp_storage

    def test_init_sets_data_dir(self, tmp_path: Path) -> None:
        """Test that initialization sets the data directory correctly."""
        service = StorageService(tmp_path)
        assert service.data_dir == tmp_path.resolve()

    def test_get_safe_path_valid(self, temp_storage: StorageService) -> None:
        """Test that valid paths are resolved correctly."""
        result = temp_storage.get_safe_path("subdir/file.txt")
        assert result.name == "file.txt"
        assert result.parent.name == "subdir"

    def test_get_safe_path_empty(self, temp_storage: StorageService) -> None:
        """Test that empty path returns root directory."""
        result = temp_storage.get_safe_path("")
        assert result == temp_storage.data_dir

    def test_get_safe_path_traversal_attack(self, temp_storage: StorageService) -> None:
        """Test that path traversal attempts are blocked."""
        with pytest.raises(InvalidPathError):
            temp_storage.get_safe_path("../etc/passwd")

    def test_get_safe_path_double_dot(self, temp_storage: StorageService) -> None:
        """Test that double-dot paths are blocked."""
        with pytest.raises(InvalidPathError):
            temp_storage.get_safe_path("subdir/../../etc/passwd")

    def test_get_safe_path_absolute(self, temp_storage: StorageService) -> None:
        """Test that absolute paths outside data dir are blocked."""
        with pytest.raises(InvalidPathError):
            temp_storage.get_safe_path("/etc/passwd")

    def test_exists_true(self, populated_storage: StorageService) -> None:
        """Test exists returns true for existing file."""
        assert populated_storage.exists("file1.txt") is True

    def test_exists_false(self, temp_storage: StorageService) -> None:
        """Test exists returns false for non-existing file."""
        assert temp_storage.exists("nonexistent.txt") is False

    def test_exists_invalid_path(self, temp_storage: StorageService) -> None:
        """Test exists returns false for invalid paths (no exception)."""
        assert temp_storage.exists("../etc/passwd") is False

    def test_is_directory_true(self, populated_storage: StorageService) -> None:
        """Test is_directory returns true for directories."""
        assert populated_storage.is_directory("subdir") is True

    def test_is_directory_false(self, populated_storage: StorageService) -> None:
        """Test is_directory returns false for files."""
        assert populated_storage.is_directory("file1.txt") is False

    def test_list_directory_root(self, populated_storage: StorageService) -> None:
        """Test listing root directory returns all items."""
        items = populated_storage.list_directory("")
        names = [item.name for item in items]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names

    def test_list_directory_subdirectory(self, populated_storage: StorageService) -> None:
        """Test listing subdirectory."""
        items = populated_storage.list_directory("subdir")
        assert len(items) == 1
        assert items[0].name == "nested.txt"
        assert items[0].type == "file"

    def test_list_directory_not_found(self, temp_storage: StorageService) -> None:
        """Test listing non-existent directory raises error."""
        with pytest.raises(PathNotFoundError):
            temp_storage.list_directory("nonexistent")

    def test_list_directory_on_file(self, populated_storage: StorageService) -> None:
        """Test listing a file raises error."""
        with pytest.raises(InvalidPathError):
            populated_storage.list_directory("file1.txt")

    def test_read_file_content(self, populated_storage: StorageService) -> None:
        """Test reading file returns content and size."""
        content, size = populated_storage.read_file("file1.txt")
        assert content == "Hello World"
        assert size == 11

    def test_read_file_not_found(self, temp_storage: StorageService) -> None:
        """Test reading non-existent file raises error."""
        with pytest.raises(PathNotFoundError):
            temp_storage.read_file("nonexistent.txt")

    def test_read_file_on_directory(self, populated_storage: StorageService) -> None:
        """Test reading a directory raises error."""
        with pytest.raises(InvalidPathError):
            populated_storage.read_file("subdir")

    def test_write_file_creates_new(self, temp_storage: StorageService, tmp_path: Path) -> None:
        """Test writing creates a new file."""
        status, size = temp_storage.write_file("new.txt", "New content")
        assert status == "created"
        assert size == 11
        assert (tmp_path / "new.txt").read_text() == "New content"

    def test_write_file_updates_existing(
        self, populated_storage: StorageService, tmp_path: Path
    ) -> None:
        """Test writing updates an existing file."""
        status, size = populated_storage.write_file("file1.txt", "Updated")
        assert status == "updated"
        assert size == 7
        assert (tmp_path / "file1.txt").read_text() == "Updated"

    def test_write_file_creates_parent_dirs(
        self, temp_storage: StorageService, tmp_path: Path
    ) -> None:
        """Test writing creates parent directories."""
        status, _ = temp_storage.write_file("a/b/c/file.txt", "Deep file")
        assert status == "created"
        assert (tmp_path / "a" / "b" / "c" / "file.txt").exists()

    def test_write_file_empty_content(self, temp_storage: StorageService, tmp_path: Path) -> None:
        """Test writing empty content is allowed."""
        status, size = temp_storage.write_file("empty.txt", "")
        assert status == "created"
        assert size == 0
        assert (tmp_path / "empty.txt").read_text() == ""

    def test_delete_file(self, populated_storage: StorageService, tmp_path: Path) -> None:
        """Test deleting a file."""
        file_type = populated_storage.delete("file1.txt")
        assert file_type == "file"
        assert not (tmp_path / "file1.txt").exists()

    def test_delete_empty_directory(self, temp_storage: StorageService, tmp_path: Path) -> None:
        """Test deleting an empty directory."""
        (tmp_path / "empty_dir").mkdir()
        file_type = temp_storage.delete("empty_dir")
        assert file_type == "directory"
        assert not (tmp_path / "empty_dir").exists()

    def test_delete_non_empty_directory(self, populated_storage: StorageService) -> None:
        """Test deleting a non-empty directory raises error."""
        with pytest.raises(DirectoryNotEmptyError):
            populated_storage.delete("subdir")

    def test_delete_not_found(self, temp_storage: StorageService) -> None:
        """Test deleting non-existent path raises error."""
        with pytest.raises(PathNotFoundError):
            temp_storage.delete("nonexistent.txt")

    def test_create_directory_new(self, temp_storage: StorageService, tmp_path: Path) -> None:
        """Test creating a new directory."""
        status = temp_storage.create_directory("newdir")
        assert status == "created"
        assert (tmp_path / "newdir").is_dir()

    def test_create_directory_nested(self, temp_storage: StorageService, tmp_path: Path) -> None:
        """Test creating nested directories."""
        status = temp_storage.create_directory("a/b/c")
        assert status == "created"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_create_directory_exists(self, populated_storage: StorageService) -> None:
        """Test creating an existing directory returns 'exists'."""
        status = populated_storage.create_directory("subdir")
        assert status == "exists"

    def test_create_directory_file_exists(self, populated_storage: StorageService) -> None:
        """Test creating directory where file exists raises error."""
        with pytest.raises(InvalidPathError):
            populated_storage.create_directory("file1.txt")


class TestFileInfo:
    """Test cases for FileInfo dataclass."""

    def test_to_dict_file(self) -> None:
        """Test FileInfo serialization for a file."""
        info = FileInfo(name="test.txt", type="file", size=100)
        result = info.to_dict()
        assert result == {"name": "test.txt", "type": "file", "size": 100}

    def test_to_dict_directory(self) -> None:
        """Test FileInfo serialization for a directory."""
        info = FileInfo(name="subdir", type="directory")
        result = info.to_dict()
        assert result == {"name": "subdir", "type": "directory"}
