"""Tests for files blueprint endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from app.services.storage import (
    DirectoryNotEmptyError,
    FileInfo,
    InvalidPathError,
    PathNotFoundError,
)

if TYPE_CHECKING:
    from flask.testing import FlaskClient


class TestFilesGetEndpoint:
    """Test cases for GET /files endpoints."""

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_root_directory(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test listing root directory."""
        mock_service = MagicMock()
        mock_service.is_directory.return_value = True
        mock_service.list_directory.return_value = [
            FileInfo(name="file1.txt", type="file", size=100),
            FileInfo(name="subdir", type="directory"),
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/files/")

        assert response.status_code == 200
        data = response.get_json()
        assert data["type"] == "directory"
        assert len(data["items"]) == 2
        assert "trace_id" in data

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_subdirectory(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test listing a subdirectory."""
        mock_service = MagicMock()
        mock_service.is_directory.return_value = True
        mock_service.list_directory.return_value = [
            FileInfo(name="nested.txt", type="file", size=50),
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/files/subdir")

        assert response.status_code == 200
        data = response.get_json()
        assert data["path"] == "subdir"
        assert data["type"] == "directory"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_file_content(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test reading file content."""
        mock_service = MagicMock()
        mock_service.is_directory.return_value = False
        mock_service.read_file.return_value = ("Hello World", 11)
        mock_get_service.return_value = mock_service

        response = client.get("/files/test.txt")

        assert response.status_code == 200
        data = response.get_json()
        assert data["type"] == "file"
        assert data["content"] == "Hello World"
        assert data["size"] == 11

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_nested_path(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test reading nested path."""
        mock_service = MagicMock()
        mock_service.is_directory.return_value = False
        mock_service.read_file.return_value = ("Nested content", 14)
        mock_get_service.return_value = mock_service

        response = client.get("/files/subdir/nested.txt")

        assert response.status_code == 200
        data = response.get_json()
        assert data["path"] == "subdir/nested.txt"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_invalid_path(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that invalid paths return 400."""
        mock_service = MagicMock()
        mock_service.is_directory.side_effect = InvalidPathError("Invalid path")
        mock_get_service.return_value = mock_service

        response = client.get("/files/../etc/passwd")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_not_found(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that non-existent paths return 404."""
        mock_service = MagicMock()
        mock_service.is_directory.return_value = False
        mock_service.read_file.side_effect = PathNotFoundError("Not found")
        mock_get_service.return_value = mock_service

        response = client.get("/files/nonexistent.txt")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestFilesWriteEndpoint:
    """Test cases for POST/PUT /files endpoints."""

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_create_file(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test creating a new file."""
        mock_service = MagicMock()
        mock_service.write_file.return_value = ("created", 11)
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files/new.txt",
            json={"content": "Hello World"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "created"
        assert data["size"] == 11
        assert "trace_id" in data

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_update_file(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test updating an existing file."""
        mock_service = MagicMock()
        mock_service.write_file.return_value = ("updated", 7)
        mock_get_service.return_value = mock_service

        response = client.put(
            "/files/existing.txt",
            json={"content": "Updated"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "updated"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_write_plain_text(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test writing plain text content."""
        mock_service = MagicMock()
        mock_service.write_file.return_value = ("created", 10)
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files/plain.txt",
            data="Plain text",
            content_type="text/plain",
        )

        assert response.status_code == 201
        mock_service.write_file.assert_called_once_with("plain.txt", "Plain text")

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_write_empty_content(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test writing empty content is allowed."""
        mock_service = MagicMock()
        mock_service.write_file.return_value = ("created", 0)
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files/empty.txt",
            json={"content": ""},
            content_type="application/json",
        )

        assert response.status_code == 201
        mock_service.write_file.assert_called_once_with("empty.txt", "")

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_write_invalid_path(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that invalid paths return 400."""
        mock_service = MagicMock()
        mock_service.write_file.side_effect = InvalidPathError("Invalid path")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files/../etc/passwd",
            json={"content": "malicious"},
            content_type="application/json",
        )

        assert response.status_code == 400

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_write_invalid_json(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that invalid JSON returns 400."""
        response = client.post(
            "/files/test.txt",
            data="not valid json",
            content_type="application/json",
        )

        assert response.status_code == 400


class TestFilesDeleteEndpoint:
    """Test cases for DELETE /files endpoints."""

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_file(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test deleting a file."""
        mock_service = MagicMock()
        mock_service.delete.return_value = "file"
        mock_get_service.return_value = mock_service

        response = client.delete("/files/test.txt")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "deleted"
        assert data["type"] == "file"
        assert "trace_id" in data

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_empty_directory(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test deleting an empty directory."""
        mock_service = MagicMock()
        mock_service.delete.return_value = "directory"
        mock_get_service.return_value = mock_service

        response = client.delete("/files/empty_dir")

        assert response.status_code == 200
        data = response.get_json()
        assert data["type"] == "directory"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_not_found(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that deleting non-existent path returns 404."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = PathNotFoundError("Not found")
        mock_get_service.return_value = mock_service

        response = client.delete("/files/nonexistent.txt")

        assert response.status_code == 404

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_non_empty_directory(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that deleting non-empty directory returns 400."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = DirectoryNotEmptyError("Not empty")
        mock_get_service.return_value = mock_service

        response = client.delete("/files/populated_dir")

        assert response.status_code == 400
        data = response.get_json()
        assert "not empty" in data["error"].lower()

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_invalid_path(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that deleting invalid path returns 400."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = InvalidPathError("Invalid path")
        mock_get_service.return_value = mock_service

        response = client.delete("/files/../etc/passwd")

        assert response.status_code == 400


class TestFilesCreateDirectoryEndpoint:
    """Test cases for POST /files (create directory) endpoint."""

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_create_directory(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test creating a new directory."""
        mock_service = MagicMock()
        mock_service.create_directory.return_value = "created"
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files",
            json={"path": "new_dir"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "created"
        assert data["type"] == "directory"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_create_directory_exists(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test creating existing directory returns 200."""
        mock_service = MagicMock()
        mock_service.create_directory.return_value = "exists"
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files",
            json={"path": "existing_dir"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "exists"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_create_directory_missing_path(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test creating directory without path returns 400."""
        response = client.post(
            "/files",
            json={},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Path is required" in data["error"]

    def test_create_directory_not_json(self, client: FlaskClient) -> None:
        """Test creating directory without JSON returns 400."""
        response = client.post(
            "/files",
            data="not json",
            content_type="text/plain",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "JSON body required" in data["error"]


class TestPathTraversalSecurity:
    """Security tests for path traversal attacks."""

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_get_blocks_parent_traversal(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that GET blocks parent directory traversal."""
        mock_service = MagicMock()
        mock_service.is_directory.side_effect = InvalidPathError("Invalid")
        mock_get_service.return_value = mock_service

        paths = [
            "../etc/passwd",
            "..%2Fetc%2Fpasswd",
            "subdir/../../etc/passwd",
        ]
        for path in paths:
            response = client.get(f"/files/{path}")
            assert response.status_code in (400, 404), f"Failed for path: {path}"

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_write_blocks_parent_traversal(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that POST/PUT blocks parent directory traversal."""
        mock_service = MagicMock()
        mock_service.write_file.side_effect = InvalidPathError("Invalid")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/files/../etc/cron.d/malicious",
            json={"content": "bad"},
            content_type="application/json",
        )
        assert response.status_code == 400

    @patch("app.blueprints.files._get_or_init_storage_service")
    def test_delete_blocks_parent_traversal(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that DELETE blocks parent directory traversal."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = InvalidPathError("Invalid")
        mock_get_service.return_value = mock_service

        response = client.delete("/files/../important_file")
        assert response.status_code == 400
