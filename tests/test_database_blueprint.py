"""Tests for database blueprint endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from app.services.database import LocationRecord

if TYPE_CHECKING:
    from flask.testing import FlaskClient


class TestDatabaseStatusEndpoint:
    """Test cases for /db/status endpoint."""

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_status_connected(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that /db/status returns connection info when connected."""
        mock_service = MagicMock()
        mock_service.health_check.return_value = {
            "status": "connected",
            "database": "owntracks",
            "host": "192.168.1.175",
            "port": 6432,
            "server_version": "PostgreSQL 14.0",
        }
        mock_get_service.return_value = mock_service

        response = client.get("/db/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "connected"
        assert data["database"] == "owntracks"
        assert "trace_id" in data

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_status_error(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that /db/status returns 500 on connection failure."""
        mock_get_service.side_effect = Exception("Connection refused")

        response = client.get("/db/status")

        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "error"
        assert "trace_id" in data

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_status_response_is_json(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/status returns JSON content type."""
        mock_service = MagicMock()
        mock_service.health_check.return_value = {"status": "connected"}
        mock_get_service.return_value = mock_service

        response = client.get("/db/status")

        assert response.content_type == "application/json"


class TestDatabaseLocationsEndpoint:
    """Test cases for /db/locations endpoint."""

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_returns_data(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations returns location records."""
        mock_service = MagicMock()
        mock_service.get_locations.return_value = [
            LocationRecord(
                id=1,
                device_id="iphone",
                tid="SS",
                latitude=40.7128,
                longitude=-74.0060,
                accuracy=10,
                altitude=100,
                velocity=0,
                battery=85,
                created_at="2026-01-15T12:00:00",
            )
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert len(data["locations"]) == 1
        assert data["locations"][0]["device_id"] == "iphone"
        assert "trace_id" in data

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_with_params(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations accepts query parameters."""
        mock_service = MagicMock()
        mock_service.get_locations.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations?limit=10&offset=5&sort=latitude&order=asc")

        assert response.status_code == 200
        mock_service.get_locations.assert_called_once_with(
            limit=10,
            offset=5,
            sort="latitude",
            order="ASC",
            device_id=None,
        )

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_with_device_id(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations filters by device_id."""
        mock_service = MagicMock()
        mock_service.get_locations.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations?device_id=iphone")

        assert response.status_code == 200
        mock_service.get_locations.assert_called_once()
        call_kwargs = mock_service.get_locations.call_args[1]
        assert call_kwargs["device_id"] == "iphone"

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_invalid_limit(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations returns 400 for invalid limit."""
        response = client.get("/db/locations?limit=invalid")

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert "Invalid limit" in data["error"]

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_negative_offset(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations returns 400 for negative offset."""
        response = client.get("/db/locations?offset=-5")

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_caps_limit_at_100(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations caps limit at 100."""
        mock_service = MagicMock()
        mock_service.get_locations.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations?limit=500")

        assert response.status_code == 200
        mock_service.get_locations.assert_called_once()
        call_kwargs = mock_service.get_locations.call_args[1]
        assert call_kwargs["limit"] == 100

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_error(self, mock_get_service: MagicMock, client: FlaskClient) -> None:
        """Test that /db/locations returns 500 on database error."""
        mock_service = MagicMock()
        mock_service.get_locations.side_effect = Exception("Query failed")
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations")

        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "error"
        assert "trace_id" in data

    @patch("app.blueprints.database._get_or_init_db_service")
    def test_db_locations_response_format(
        self, mock_get_service: MagicMock, client: FlaskClient
    ) -> None:
        """Test that /db/locations response has correct format."""
        mock_service = MagicMock()
        mock_service.get_locations.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/db/locations")

        assert response.status_code == 200
        data = response.get_json()
        assert "count" in data
        assert "limit" in data
        assert "offset" in data
        assert "sort" in data
        assert "order" in data
        assert "locations" in data
        assert "trace_id" in data
