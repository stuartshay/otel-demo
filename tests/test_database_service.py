"""Tests for DatabaseService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from app.config import Config
from app.services.database import DatabaseService, LocationRecord

if TYPE_CHECKING:
    pass


class TestDatabaseService:
    """Test cases for DatabaseService class."""

    @pytest.fixture
    def mock_config(self) -> Config:
        """Create a mock configuration for database."""
        return Config(
            db_host="localhost",
            db_port=5432,
            db_name="test_db",
            db_user="test_user",
            db_password="test_password",  # noqa: S106  # pragma: allowlist secret
            db_pool_min=1,
            db_pool_max=2,
            db_connect_timeout=5,
        )

    @pytest.fixture
    def mock_pool(self) -> MagicMock:
        """Create a mock connection pool."""
        pool = MagicMock()
        conn = MagicMock()
        cursor = MagicMock()
        pool.getconn.return_value = conn
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        return pool

    def test_init_sets_config(self, mock_config: Config) -> None:
        """Test that initialization stores config."""
        service = DatabaseService(mock_config)
        assert service._config == mock_config
        assert service._pool is None

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_initialize_creates_pool(self, mock_pool_class: MagicMock, mock_config: Config) -> None:
        """Test that initialize creates a connection pool."""
        service = DatabaseService(mock_config)
        service.initialize()

        mock_pool_class.assert_called_once_with(
            minconn=1,
            maxconn=2,
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",  # pragma: allowlist secret
            connect_timeout=5,
        )

    def test_initialize_without_credentials(self) -> None:
        """Test that initialize fails without credentials."""
        config = Config(db_user=None, db_password=None)
        service = DatabaseService(config)

        with pytest.raises(RuntimeError, match="Database credentials not configured"):
            service.initialize()

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_close_closes_pool(self, mock_pool_class: MagicMock, mock_config: Config) -> None:
        """Test that close closes all connections."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        service.close()

        mock_pool.closeall.assert_called_once()
        assert service._pool is None

    def test_close_without_pool(self, mock_config: Config) -> None:
        """Test that close does nothing if pool not initialized."""
        service = DatabaseService(mock_config)
        service.close()  # Should not raise

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_connection_returns_connection(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_connection returns a connection from pool."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()

        with service.get_connection() as conn:
            assert conn == mock_conn

        mock_pool.getconn.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_connection_rollback_on_error(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_connection rollbacks on exception."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()

        with pytest.raises(ValueError), service.get_connection():
            raise ValueError("Test error")

        mock_conn.rollback.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_get_connection_without_pool(self, mock_config: Config) -> None:
        """Test that get_connection fails if pool not initialized."""
        service = DatabaseService(mock_config)

        with (
            pytest.raises(RuntimeError, match="Database pool not initialized"),
            service.get_connection(),
        ):
            pass

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_health_check_returns_status(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that health_check returns connection status."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_cursor.fetchone.return_value = ["PostgreSQL 14.0"]
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        result = service.health_check()

        assert result["status"] == "connected"
        assert result["database"] == "test_db"
        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["server_version"] == "PostgreSQL 14.0"

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_locations_returns_records(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_locations returns location records."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Mock database rows
        from datetime import datetime

        mock_cursor.fetchall.return_value = [
            (1, "iphone", "SS", 40.7128, -74.0060, 10, 100, 0, 85, datetime(2026, 1, 15, 12, 0)),
            (2, "iphone", "SS", 40.7129, -74.0061, 15, 101, 5, 80, datetime(2026, 1, 15, 12, 5)),
        ]
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        locations = service.get_locations(limit=10, offset=0)

        assert len(locations) == 2
        assert locations[0].id == 1
        assert locations[0].device_id == "iphone"
        assert locations[0].latitude == 40.7128
        assert locations[0].longitude == -74.0060
        assert locations[1].battery == 80

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_locations_with_device_filter(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_locations filters by device_id."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_cursor.fetchall.return_value = []
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        service.get_locations(device_id="iphone")

        # Verify the query included device_id parameter
        call_args = mock_cursor.execute.call_args
        assert "device_id = %s" in call_args[0][0]
        assert call_args[0][1][0] == "iphone"

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_locations_limits_max_100(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_locations caps limit at 100."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_cursor.fetchall.return_value = []
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        service.get_locations(limit=500)

        # Verify limit was capped to 100
        call_args = mock_cursor.execute.call_args
        assert 100 in call_args[0][1]  # limit should be 100

    @patch("app.services.database.pool.ThreadedConnectionPool")
    def test_get_locations_sanitizes_sort(
        self, mock_pool_class: MagicMock, mock_config: Config
    ) -> None:
        """Test that get_locations sanitizes sort column."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_cursor.fetchall.return_value = []
        mock_pool_class.return_value = mock_pool

        service = DatabaseService(mock_config)
        service.initialize()
        service.get_locations(sort="invalid_column; DROP TABLE users;--")

        # Verify it fell back to created_at
        call_args = mock_cursor.execute.call_args
        assert "ORDER BY created_at" in call_args[0][0]


class TestLocationRecord:
    """Test cases for LocationRecord dataclass."""

    def test_to_dict(self) -> None:
        """Test LocationRecord serialization."""
        record = LocationRecord(
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
        result = record.to_dict()

        assert result["id"] == 1
        assert result["device_id"] == "iphone"
        assert result["latitude"] == 40.7128
        assert result["battery"] == 85

    def test_to_dict_with_nulls(self) -> None:
        """Test LocationRecord serialization with null values."""
        record = LocationRecord(
            id=1,
            device_id="iphone",
            tid=None,
            latitude=None,
            longitude=None,
            accuracy=None,
            altitude=None,
            velocity=None,
            battery=None,
            created_at=None,
        )
        result = record.to_dict()

        assert result["id"] == 1
        assert result["latitude"] is None
        assert result["battery"] is None
