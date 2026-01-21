"""
Database service with connection pooling.

Provides thread-safe connection pooling for PostgreSQL via PgBouncer,
with proper resource management and health checking.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from psycopg2 import pool

if TYPE_CHECKING:
    from psycopg2.extensions import connection

    from app.config import Config

logger = logging.getLogger(__name__)


@dataclass
class LocationRecord:
    """Represents a location record from the owntracks database."""

    id: int
    device_id: str
    tid: str | None
    latitude: float | None
    longitude: float | None
    accuracy: int | None
    altitude: float | None
    velocity: int | None
    battery: int | None
    battery_status: str | None
    connection_type: str | None
    trigger: str | None
    timestamp: str | None
    created_at: str | None
    raw_payload: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "tid": self.tid,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "velocity": self.velocity,
            "battery": self.battery,
            "battery_status": self.battery_status,
            "connection_type": self.connection_type,
            "trigger": self.trigger,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "raw_payload": self.raw_payload,
        }


class DatabaseService:
    """Database service with connection pooling.

    Provides thread-safe connection pooling for PostgreSQL operations.
    Uses psycopg2's ThreadedConnectionPool for concurrent access.

    Example:
        config = Config.from_env()
        db_service = DatabaseService(config)
        db_service.initialize()

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        db_service.close()
    """

    def __init__(self, config: Config) -> None:
        """Initialize database service.

        Args:
            config: Application configuration with database settings.
        """
        self._config = config
        self._pool: pool.ThreadedConnectionPool | None = None

    def initialize(self) -> None:
        """Initialize the connection pool.

        Raises:
            RuntimeError: If database credentials are not configured.
            psycopg2.Error: If connection to database fails.
        """
        self._config.validate_database()

        logger.info(
            f"Initializing database pool: {self._config.db_host}:{self._config.db_port}"
            f"/{self._config.db_name} (min={self._config.db_pool_min}, max={self._config.db_pool_max})"
        )

        self._pool = pool.ThreadedConnectionPool(
            minconn=self._config.db_pool_min,
            maxconn=self._config.db_pool_max,
            host=self._config.db_host,
            port=self._config.db_port,
            database=self._config.db_name,
            user=self._config.db_user,
            password=self._config.db_password,
            connect_timeout=self._config.db_connect_timeout,
        )

        logger.info("Database pool initialized successfully")

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Database pool closed")

    @contextmanager
    def get_connection(self) -> Iterator[connection]:
        """Get a connection from the pool.

        Yields:
            A database connection that will be returned to the pool.

        Raises:
            RuntimeError: If pool is not initialized.
            psycopg2.pool.PoolError: If no connections available.
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def health_check(self) -> dict[str, Any]:
        """Check database connectivity and return status info.

        Returns:
            Dictionary with connection status and server version.

        Raises:
            Exception: If connection fails (caller should handle).
        """
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]

        return {
            "status": "connected",
            "database": self._config.db_name,
            "host": self._config.db_host,
            "port": self._config.db_port,
            "server_version": version,
        }

    def get_locations(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "created_at",
        order: str = "DESC",
        device_id: str | None = None,
    ) -> list[LocationRecord]:
        """Query location records from the database.

        Args:
            limit: Maximum number of records to return (max 100).
            offset: Number of records to skip.
            sort: Column to sort by.
            order: Sort order ('ASC' or 'DESC').
            device_id: Optional filter by device ID.

        Returns:
            List of LocationRecord objects.
        """
        # Validate and sanitize parameters
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        allowed_sorts = {
            "timestamp": "timestamp",
            "created_at": "created_at",
            "latitude": "latitude",
            "longitude": "longitude",
            "accuracy": "accuracy",
            "altitude": "altitude",
            "velocity": "velocity",
            "battery": "battery",
            "battery_status": "battery_status",
        }
        # Default to created_at to avoid unstable ordering when timestamp may be NULL
        sort_column = allowed_sorts.get(sort, "created_at")

        order = "DESC" if order.upper() not in ("ASC", "DESC") else order.upper()

        with self.get_connection() as conn, conn.cursor() as cur:
            if device_id:
                query = f"""
                    SELECT id, device_id, tid, latitude, longitude,
                           accuracy, altitude, velocity, battery, battery_status,
                           connection_type, trigger, timestamp, created_at, raw_payload
                    FROM public.locations
                    WHERE device_id = %s
                    ORDER BY {sort_column} {order}
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, (device_id, limit, offset))
            else:
                query = f"""
                    SELECT id, device_id, tid, latitude, longitude,
                           accuracy, altitude, velocity, battery, battery_status,
                           connection_type, trigger, timestamp, created_at, raw_payload
                    FROM public.locations
                    ORDER BY {sort_column} {order}
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, (limit, offset))

            rows = cur.fetchall()

        def _to_float_safe(value: Any, field: str, record_id: Any) -> float | None:
            """Safely convert value to float, returning None on failure."""
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid %s value %r for location id %r; storing as None",
                    field,
                    value,
                    record_id,
                )
                return None

        return [
            LocationRecord(
                id=row[0],
                device_id=row[1],
                tid=row[2],
                latitude=_to_float_safe(row[3], "latitude", row[0]),
                longitude=_to_float_safe(row[4], "longitude", row[0]),
                accuracy=row[5],
                altitude=row[6],
                velocity=row[7],
                battery=row[8],
                battery_status=row[9],
                connection_type=row[10],
                trigger=row[11],
                timestamp=row[12].isoformat() if row[12] else None,
                created_at=row[13].isoformat() if row[13] else None,
                raw_payload=row[14],
            )
            for row in rows
        ]


# Global database service instance (initialized by app factory)
_db_service: DatabaseService | None = None
_db_service_lock = threading.Lock()


def get_db_service() -> DatabaseService:
    """Get the global database service instance.

    Returns:
        The initialized DatabaseService.

    Raises:
        RuntimeError: If service is not initialized.
    """
    if _db_service is None:
        raise RuntimeError("Database service not initialized")
    return _db_service


def init_db_service(config: Config) -> DatabaseService:
    """Initialize the global database service.

    Thread-safe initialization using a lock to prevent race conditions
    in multi-threaded environments like gunicorn.

    Args:
        config: Application configuration.

    Returns:
        The initialized DatabaseService.

    Raises:
        RuntimeError: If database credentials are missing.
        Exception: If database connection fails.
    """
    global _db_service
    with _db_service_lock:
        if _db_service is not None:
            return _db_service
        _db_service = DatabaseService(config)
        _db_service.initialize()  # Let exceptions propagate
        return _db_service


def close_db_service() -> None:
    """Close the global database service and release resources.

    Thread-safe cleanup that closes the connection pool if initialized.
    Safe to call multiple times.
    """
    global _db_service
    with _db_service_lock:
        if _db_service is not None:
            logger.info("Closing database connection pool")
            _db_service.close()
            _db_service = None
