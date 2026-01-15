"""Tests for health check endpoints."""

from flask.testing import FlaskClient


class TestHealthEndpoints:
    """Test cases for /health and /ready endpoints."""

    def test_health_returns_healthy(self, client: FlaskClient) -> None:
        """Test that /health returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    def test_ready_returns_ready(self, client: FlaskClient) -> None:
        """Test that /ready returns ready status."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ready"

    def test_health_response_is_json(self, client: FlaskClient) -> None:
        """Test that /health returns JSON content type."""
        response = client.get("/health")

        assert response.content_type == "application/json"

    def test_ready_response_is_json(self, client: FlaskClient) -> None:
        """Test that /ready returns JSON content type."""
        response = client.get("/ready")

        assert response.content_type == "application/json"
