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

    # Distance service settings
    distance_service_endpoint: str = "localhost:50051"
    distance_service_timeout: int = 30

    # Swagger settings
    swagger_host: str = ""
    swagger_schemes: tuple[str, ...] = ("http",)

    # OAuth2/Cognito settings (for Swagger UI)
    cognito_domain: str = ""
    cognito_client_id: str = ""
    oauth2_enabled: bool = False

    # CORS settings
    cors_origins: tuple[str, ...] = ()

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

        # Parse CORS origins as tuple
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        cors_origins = tuple(s.strip() for s in cors_origins_str.split(",") if s.strip())

        # Parse PORT with validation
        port_env = os.getenv("PORT", "8080")
        try:
            port = int(port_env)
        except ValueError as exc:
            raise ValueError(f"Invalid PORT value: {port_env!r}. Port must be an integer.") from exc

        # Parse DB pool settings with validation
        db_pool_min_str = os.getenv("DB_POOL_MIN", "1")
        db_pool_max_str = os.getenv("DB_POOL_MAX", "5")
        db_connect_timeout_str = os.getenv("DB_CONNECT_TIMEOUT", "5")

        try:
            db_pool_min = int(db_pool_min_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid DB_POOL_MIN value: {db_pool_min_str!r}. Must be an integer."
            ) from exc

        try:
            db_pool_max = int(db_pool_max_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid DB_POOL_MAX value: {db_pool_max_str!r}. Must be an integer."
            ) from exc

        try:
            db_connect_timeout = int(db_connect_timeout_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid DB_CONNECT_TIMEOUT value: {db_connect_timeout_str!r}. Must be an integer."
            ) from exc

        return cls(
            # Server
            port=port,
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
            db_pool_min=db_pool_min,
            db_pool_max=db_pool_max,
            db_connect_timeout=db_connect_timeout,
            # Distance service
            distance_service_endpoint=os.getenv("DISTANCE_SERVICE_ENDPOINT", "localhost:50051"),
            distance_service_timeout=int(os.getenv("DISTANCE_SERVICE_TIMEOUT", "30")),
            # Swagger
            swagger_host=os.getenv("SWAGGER_HOST", ""),
            swagger_schemes=swagger_schemes,
            # OAuth2/Cognito
            cognito_domain=os.getenv("COGNITO_DOMAIN", ""),
            cognito_client_id=os.getenv("COGNITO_CLIENT_ID", ""),
            oauth2_enabled=os.getenv("OAUTH2_ENABLED", "false").lower() == "true",
            # CORS
            cors_origins=cors_origins,
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

    def validate_oauth2(self) -> None:
        """Validate OAuth2 configuration when enabled.

        Raises:
            RuntimeError: If OAuth2 is enabled but required settings are missing.
        """
        if self.oauth2_enabled and (not self.cognito_domain or not self.cognito_client_id):
            raise RuntimeError(
                "OAuth2 is enabled but configuration is incomplete. "
                "Set COGNITO_DOMAIN and COGNITO_CLIENT_ID environment variables, "
                "or disable OAuth2 by setting OAUTH2_ENABLED=false."
            )
