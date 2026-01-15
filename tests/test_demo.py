"""Tests for demo/tracing endpoints."""

from flask.testing import FlaskClient


class TestDemoEndpoints:
    """Test cases for demo endpoints (/info, /chain, /error, /slow)."""

    def test_info_returns_service_info(self, client: FlaskClient) -> None:
        """Test that /info returns service information."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "service" in data
        assert data["service"] == "otel-demo"
        assert "OpenTelemetry" in data["message"]

    def test_info_includes_trace_context(self, client: FlaskClient) -> None:
        """Test that /info includes trace context."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.get_json()
        assert "trace_id" in data
        # trace_id should be a 32-character hex string
        assert len(data["trace_id"]) == 32

    def test_chain_returns_steps(self, client: FlaskClient) -> None:
        """Test that /chain returns processing status."""
        response = client.get("/chain")

        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "chain complete"
        assert "steps" in data
        assert isinstance(data["steps"], list)

    def test_chain_includes_trace_id(self, client: FlaskClient) -> None:
        """Test that /chain includes trace ID."""
        response = client.get("/chain")

        assert response.status_code == 200
        data = response.get_json()
        assert "trace_id" in data

    def test_error_returns_500(self, client: FlaskClient) -> None:
        """Test that /error returns HTTP 500."""
        response = client.get("/error")

        assert response.status_code == 500
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "error"
        assert "message" in data

    def test_slow_returns_success(self, client: FlaskClient) -> None:
        """Test that /slow returns success with duration."""
        response = client.get("/slow")

        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "complete"
        assert "delay_seconds" in data
        assert data["delay_seconds"] > 0
