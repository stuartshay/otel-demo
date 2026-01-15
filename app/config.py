"""
Application configuration management.

Provides a centralized configuration dataclass with environment variable loading
and validation for all application settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables.

    Attributes:
        port: HTTP server port (default: 8080)
        data_dir: Path to NFS data storage (default: /data)

        # OpenTelemetry settings
        otel_endpoint: OTLP exporter endpoint (default: localhost:4317)
        service_name: Service name for traces (default: otel-demo)
        service_namespace: Service namespace (default: otel-demo)
        environment: Deployment environment (default: homelab)

        # Application metadata
        app_version: Application version (default: 1.0.0)
        build_number: CI build number (default: 0)
        build_date: Build timestamp (default: unknown)

        # Database settings
        db_host: PostgreSQL/PgBouncer host (default: 192.168.1.175)
        db_port: PostgreSQL/PgBouncer port (default: 6432)
        db_name: Database name (default: owntracks)
        db_user: Database username (required for DB operations)
        db_password: Database password (required for DB operations)
        db_pool_min: Minimum pool connections (default: 1)
        db_pool_max: Maximum pool connections (default: 5)
        db_connect_timeout: Connection timeout in seconds (default: 5)

        # Swagger settings
        swagger_host: Override host for Swagger UI (default: "")
        swagger_schemes: URL schemes for Swagger (default: ["http"])
    """

    # Server settings
    port: int = 8080
    data_dir: Path = field(default_factory=lambda: Path("/data"))

    # OpenTelemetry settings
    otel_endpoint: str = "localhost:4317"
    service_name: str = "otel-demo"
    service_namespace: str = "otel-demo"
    environment: str = "homelab"

    # Application metadata
    app_version: str = "1.0.0"
    build_number: str = "0"
    build_date: str = "unknown"

    # Database settings
    db_host: str = "192.168.1.175"
    db_port: int = 6432
    db_name: str = "owntracks"
    db_user: str | None = None
    db_password: str | None = None
    db_pool_min: int = 1
    db_pool_max: int = 5
    db_connect_timeout: int = 5

    # Swagger settings
    swagger_host: str = ""
    swagger_schemes: tuple[str, ...] = ("http",)

    @classmethod
    def from_env(cls) -> Config:
        """Create configuration from environment variables.

        Returns:
            Config instance populated from environment variables.

        Raises:
            ValueError: If PGBOUNCER_PORT is not a valid integer.
        """
        # Parse port with validation
        port_str = os.getenv("PGBOUNCER_PORT", "6432")
        try:
            db_port = int(port_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid PGBOUNCER_PORT value: {port_str!r}. Port must be an integer."
            ) from exc

        # Parse schemes as tuple
        schemes_str = os.getenv("SWAGGER_SCHEMES", "http")
        swagger_schemes = tuple(s.strip() for s in schemes_str.split(","))

        return cls(
            # Server
            port=int(os.getenv("PORT", "8080")),
            data_dir=Path(os.getenv("DATA_DIR", "/data")),
            # OpenTelemetry
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
            service_name=os.getenv("OTEL_SERVICE_NAME", "otel-demo"),
            service_namespace=os.getenv("OTEL_SERVICE_NAMESPACE", "otel-demo"),
            environment=os.getenv("OTEL_ENVIRONMENT", "homelab"),
            # App metadata
            app_version=os.getenv("APP_VERSION", "1.0.0"),
            build_number=os.getenv("BUILD_NUMBER", "0"),
            build_date=os.getenv("BUILD_DATE", "unknown"),
            # Database
            db_host=os.getenv("PGBOUNCER_HOST", "192.168.1.175"),
            db_port=db_port,
            db_name=os.getenv("POSTGRES_DB", "owntracks"),
            db_user=os.getenv("POSTGRES_USER"),
            db_password=os.getenv("POSTGRES_PASSWORD"),
            db_pool_min=int(os.getenv("DB_POOL_MIN", "1")),
            db_pool_max=int(os.getenv("DB_POOL_MAX", "5")),
            db_connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
            # Swagger
            swagger_host=os.getenv("SWAGGER_HOST", ""),
            swagger_schemes=swagger_schemes,
        )

    def validate_database(self) -> None:
        """Validate database configuration.

        Raises:
            RuntimeError: If required database credentials are missing.
        """
        if not self.db_user or not self.db_password:
            raise RuntimeError(
                "Database credentials not configured. "
                "Set POSTGRES_USER and POSTGRES_PASSWORD environment variables."
            )
