"""
Pytest configuration and fixtures.

Provides fixtures for testing Flask application endpoints with
mocked dependencies for OpenTelemetry.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.config import Config

if TYPE_CHECKING:
    from flask import Flask
    from flask.testing import FlaskClient


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    return Config(
        port=8080,
        data_dir=Path("/tmp/test-data"),
        otel_endpoint="localhost:4317",
        service_name="otel-demo-test",
        service_namespace="test",
        environment="test",
        app_version="1.0.0-test",
        build_number="0",
        build_date="2026-01-01T00:00:00Z",
        db_host="localhost",
        db_port=5432,
        db_name="test_db",
        db_user="test_user",
        db_password="test_password",  # noqa: S106  # pragma: allowlist secret
        db_pool_min=1,
        db_pool_max=2,
        db_connect_timeout=5,
        swagger_host="",
        swagger_schemes=("http",),
        cognito_domain="",
        cognito_client_id="",
        oauth2_enabled=False,
    )


@pytest.fixture
def mock_otel() -> Generator[MagicMock, None, None]:
    """Mock OpenTelemetry to avoid actual tracing during tests."""
    with (
        patch("app.telemetry.OTLPSpanExporter") as mock_exporter,
        patch("app.telemetry.BatchSpanProcessor") as mock_processor,
        patch("app.telemetry.Psycopg2Instrumentor") as mock_psycopg2,
    ):
        mock_exporter.return_value = MagicMock()
        mock_processor.return_value = MagicMock()
        mock_psycopg2.return_value.instrument = MagicMock()
        yield mock_exporter


@pytest.fixture
def app(test_config: Config, mock_otel: MagicMock) -> Flask:
    """Create test Flask application."""
    flask_app = create_app(test_config)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create test client for making requests."""
    return app.test_client()
