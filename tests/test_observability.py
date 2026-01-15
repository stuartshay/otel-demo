"""Tests for observability blueprint endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask.testing import FlaskClient


class TestMetricsEndpoint:
    """Test cases for /metrics endpoint."""

    def test_metrics_returns_otel_config(self, client: FlaskClient) -> None:
        """Test that /metrics returns OpenTelemetry configuration."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()
        assert "otel_endpoint" in data
        assert "service_name" in data
        assert "service_namespace" in data
        assert "environment" in data
        assert "version" in data

    def test_metrics_returns_endpoints_list(self, client: FlaskClient) -> None:
        """Test that /metrics includes available endpoints."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()
        assert "endpoints" in data
        endpoints = data["endpoints"]

        # Verify key endpoints are documented
        assert "/" in endpoints
        assert "/health" in endpoints
        assert "/ready" in endpoints
        assert "/metrics" in endpoints
        assert "/db/status" in endpoints
        assert "/db/locations" in endpoints
        assert "/files" in endpoints

    def test_metrics_reflects_test_config(self, client: FlaskClient) -> None:
        """Test that /metrics reflects the test configuration."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()

        # These should match the test_config fixture
        assert data["service_name"] == "otel-demo-test"
        assert data["service_namespace"] == "test"
        assert data["environment"] == "test"
        assert data["version"] == "1.0.0-test"

    def test_metrics_response_is_json(self, client: FlaskClient) -> None:
        """Test that /metrics returns JSON content type."""
        response = client.get("/metrics")

        assert response.content_type == "application/json"

    def test_metrics_otel_endpoint_configured(self, client: FlaskClient) -> None:
        """Test that OTEL endpoint is properly configured."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()
        # Should have the test config endpoint
        assert data["otel_endpoint"] == "localhost:4317"

    def test_metrics_endpoints_have_descriptions(self, client: FlaskClient) -> None:
        """Test that endpoint descriptions are non-empty strings."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()

        for endpoint, description in data["endpoints"].items():
            assert isinstance(endpoint, str), f"Endpoint key should be string: {endpoint}"
            assert isinstance(description, str), f"Description should be string: {description}"
            assert len(description) > 0, f"Description should not be empty for {endpoint}"
