"""
Unit tests for distance calculation REST API endpoints.

Tests cover:
- POST /api/distance/calculate - Start async distance calculation jobs
- GET /api/distance/jobs/<job_id> - Get job status and results
- GET /api/distance/jobs - List jobs with filtering
- GET /api/distance/download/<filename> - Download CSV results
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.config import Config
from app.proto.distance.v1.distance_pb2 import (
    CalculateDistanceResponse,
    GetJobStatusResponse,
    ListJobsResponse,
)
from app.services.distance_client import (
    ServiceUnavailableError,
    ValidationError,
)


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config(
        port=8080,
        data_dir=Path("/tmp/test_data"),
        otel_endpoint="localhost:4317",
        service_name="otel-demo-test",
        distance_service_endpoint="localhost:50051",
        distance_service_timeout=30,
    )


@pytest.fixture
def app(test_config):
    """Create Flask app in test mode."""
    app = create_app(test_config)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def mock_distance_client():
    """Mock DistanceClient for testing."""
    with patch("app.blueprints.distance.get_distance_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


# =============================================================================
# POST /api/distance/calculate Tests
# =============================================================================


class TestCalculateDistance:
    """Tests for POST /api/distance/calculate endpoint."""

    def test_calculate_distance_success(self, client, mock_distance_client):
        """Test successful distance calculation request."""
        # Mock response
        response = CalculateDistanceResponse()
        response.job_id = "test-job-id"
        response.status = "queued"
        response.queued_at.GetCurrentTime()

        mock_distance_client.calculate_distance.return_value = response

        # Make request
        resp = client.post(
            "/api/distance/calculate",
            json={"date": "2026-01-25", "device_id": "iphone_stuart"},
        )

        # Assertions
        assert resp.status_code == 202
        data = resp.get_json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "queued"
        assert "queued_at" in data
        assert data["status_url"] == "/api/distance/jobs/test-job-id"
        assert "trace_id" in data

        mock_distance_client.calculate_distance.assert_called_once_with(
            "2026-01-25", "iphone_stuart"
        )

    def test_calculate_distance_all_devices(self, client, mock_distance_client):
        """Test distance calculation for all devices (no device_id)."""
        response = CalculateDistanceResponse()
        response.job_id = "test-job-id-all"
        response.status = "queued"
        response.queued_at.GetCurrentTime()

        mock_distance_client.calculate_distance.return_value = response

        resp = client.post("/api/distance/calculate", json={"date": "2026-01-25"})

        assert resp.status_code == 202
        data = resp.get_json()
        assert data["job_id"] == "test-job-id-all"

        mock_distance_client.calculate_distance.assert_called_once_with("2026-01-25", "")

    def test_calculate_distance_missing_date(self, client, mock_distance_client):
        """Test request with missing date field."""
        resp = client.post("/api/distance/calculate", json={"device_id": "iphone"})

        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "date" in data["error"]["message"].lower()
        assert "trace_id" in data

    def test_calculate_distance_invalid_date_format(self, client, mock_distance_client):
        """Test request with invalid date format."""
        resp = client.post("/api/distance/calculate", json={"date": "2026/01/25"})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "format" in data["error"]["message"].lower()

    def test_calculate_distance_future_date(self, client, mock_distance_client):
        """Test request with future date."""
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = client.post("/api/distance/calculate", json={"date": future_date})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "future" in data["error"]["message"].lower()

    def test_calculate_distance_invalid_device_id(self, client, mock_distance_client):
        """Test request with invalid device_id format."""
        resp = client.post(
            "/api/distance/calculate", json={"date": "2026-01-25", "device_id": "test@device"}
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "device_id" in data["error"]["message"].lower()

    def test_calculate_distance_not_json(self, client, mock_distance_client):
        """Test request without JSON content-type."""
        resp = client.post("/api/distance/calculate", data="not json")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "json" in data["error"]["message"].lower()

    def test_calculate_distance_service_unavailable(self, client, mock_distance_client):
        """Test service unavailable error."""
        mock_distance_client.calculate_distance.side_effect = ServiceUnavailableError(
            "Service unavailable"
        )

        resp = client.post("/api/distance/calculate", json={"date": "2026-01-25"})

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"

    def test_calculate_distance_validation_error(self, client, mock_distance_client):
        """Test validation error from service."""
        mock_distance_client.calculate_distance.side_effect = ValidationError("Invalid date")

        resp = client.post("/api/distance/calculate", json={"date": "2026-01-25"})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


# =============================================================================
# GET /api/distance/jobs/<job_id> Tests
# =============================================================================


class TestGetJobStatus:
    """Tests for GET /api/distance/jobs/<job_id> endpoint."""

    def test_get_job_status_queued(self, client, mock_distance_client):
        """Test retrieving queued job status."""
        response = GetJobStatusResponse()
        response.job_id = "test-job-id"
        response.status = "queued"
        response.queued_at.GetCurrentTime()

        mock_distance_client.get_job_status.return_value = response

        resp = client.get("/api/distance/jobs/test-job-id")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "queued"
        assert "queued_at" in data
        assert "started_at" not in data
        assert "result" not in data
        assert "trace_id" in data

    def test_get_job_status_processing(self, client, mock_distance_client):
        """Test retrieving processing job status."""
        response = GetJobStatusResponse()
        response.job_id = "test-job-id"
        response.status = "processing"
        response.queued_at.GetCurrentTime()
        response.started_at.GetCurrentTime()

        mock_distance_client.get_job_status.return_value = response

        resp = client.get("/api/distance/jobs/test-job-id")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "processing"
        assert "started_at" in data
        assert "result" not in data

    def test_get_job_status_completed(self, client, mock_distance_client):
        """Test retrieving completed job with results."""
        response = GetJobStatusResponse()
        response.job_id = "test-job-id"
        response.status = "completed"
        response.queued_at.GetCurrentTime()
        response.started_at.GetCurrentTime()
        response.completed_at.GetCurrentTime()

        result = response.result
        result.csv_path = "/data/csv/distance_20260125_iphone_stuart.csv"
        result.total_distance_km = 19.44
        result.total_locations = 1464
        result.max_distance_km = 0.31
        result.min_distance_km = 0.001
        result.processing_time_ms = 252
        result.date = "2026-01-25"
        result.device_id = "iphone_stuart"

        mock_distance_client.get_job_status.return_value = response

        resp = client.get("/api/distance/jobs/test-job-id")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "completed"
        assert "completed_at" in data
        assert "result" in data
        assert data["result"]["total_distance_km"] == 19.44
        assert data["result"]["total_locations"] == 1464
        assert "csv_download_url" in data["result"]
        assert "distance_20260125_iphone_stuart.csv" in data["result"]["csv_download_url"]

    def test_get_job_status_failed(self, client, mock_distance_client):
        """Test retrieving failed job with error."""
        response = GetJobStatusResponse()
        response.job_id = "test-job-id"
        response.status = "failed"
        response.queued_at.GetCurrentTime()
        response.started_at.GetCurrentTime()
        response.completed_at.GetCurrentTime()
        response.error_message = "Database connection failed"

        mock_distance_client.get_job_status.return_value = response

        resp = client.get("/api/distance/jobs/test-job-id")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Database connection failed"
        assert "result" not in data

    def test_get_job_status_not_found(self, client, mock_distance_client):
        """Test job not found error."""
        mock_distance_client.get_job_status.side_effect = ValidationError("Job not found")

        resp = client.get("/api/distance/jobs/nonexistent-job-id")

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_job_status_service_unavailable(self, client, mock_distance_client):
        """Test service unavailable error."""
        mock_distance_client.get_job_status.side_effect = ServiceUnavailableError(
            "Service unavailable"
        )

        resp = client.get("/api/distance/jobs/test-job-id")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


# =============================================================================
# GET /api/distance/jobs Tests
# =============================================================================


class TestListJobs:
    """Tests for GET /api/distance/jobs endpoint."""

    def test_list_jobs_no_filters(self, client, mock_distance_client):
        """Test listing all jobs without filters."""
        response = ListJobsResponse()
        response.total_count = 100

        for i in range(3):
            job = response.jobs.add()
            job.job_id = f"job-{i}"
            job.status = "completed"
            job.date = "2026-01-25"
            job.device_id = "iphone_stuart"
            job.queued_at.GetCurrentTime()
            job.completed_at.GetCurrentTime()

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs")

        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["jobs"]) == 3
        assert data["total_count"] == 100
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["next_offset"] == 50
        assert "trace_id" in data

        mock_distance_client.list_jobs.assert_called_once_with("", 50, 0, "", "")

    def test_list_jobs_with_status_filter(self, client, mock_distance_client):
        """Test listing jobs filtered by status."""
        response = ListJobsResponse()
        response.total_count = 10

        for i in range(2):
            job = response.jobs.add()
            job.job_id = f"job-{i}"
            job.status = "queued"
            job.date = "2026-01-25"
            job.device_id = ""
            job.queued_at.GetCurrentTime()

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs?status=queued")

        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["jobs"]) == 2
        assert data["total_count"] == 10
        assert all(job["status"] == "queued" for job in data["jobs"])

        mock_distance_client.list_jobs.assert_called_once_with("queued", 50, 0, "", "")

    def test_list_jobs_with_pagination(self, client, mock_distance_client):
        """Test pagination with limit and offset."""
        response = ListJobsResponse()
        response.total_count = 100

        for i in range(10):
            job = response.jobs.add()
            job.job_id = f"job-{i + 20}"
            job.status = "completed"
            job.date = "2026-01-25"
            job.device_id = "iphone"
            job.queued_at.GetCurrentTime()

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs?limit=10&offset=20")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["limit"] == 10
        assert data["offset"] == 20
        assert data["next_offset"] == 30

        mock_distance_client.list_jobs.assert_called_once_with("", 10, 20, "", "")

    def test_list_jobs_last_page(self, client, mock_distance_client):
        """Test last page with no next_offset."""
        response = ListJobsResponse()
        response.total_count = 15

        for i in range(5):
            job = response.jobs.add()
            job.job_id = f"job-{i + 10}"
            job.status = "completed"
            job.date = "2026-01-25"
            job.device_id = "iphone"
            job.queued_at.GetCurrentTime()

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs?limit=10&offset=10")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["next_offset"] is None  # No more pages

    def test_list_jobs_with_date_filter(self, client, mock_distance_client):
        """Test filtering by date."""
        response = ListJobsResponse()
        response.total_count = 5

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs?date=2026-01-25")

        assert resp.status_code == 200
        mock_distance_client.list_jobs.assert_called_once_with("", 50, 0, "2026-01-25", "")

    def test_list_jobs_with_device_filter(self, client, mock_distance_client):
        """Test filtering by device_id."""
        response = ListJobsResponse()
        response.total_count = 3

        mock_distance_client.list_jobs.return_value = response

        resp = client.get("/api/distance/jobs?device_id=iphone_stuart")

        assert resp.status_code == 200
        mock_distance_client.list_jobs.assert_called_once_with("", 50, 0, "", "iphone_stuart")

    def test_list_jobs_invalid_limit_too_high(self, client, mock_distance_client):
        """Test limit exceeding maximum."""
        resp = client.get("/api/distance/jobs?limit=1000")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "limit" in data["error"]["message"].lower()

    def test_list_jobs_invalid_limit_too_low(self, client, mock_distance_client):
        """Test limit less than minimum."""
        resp = client.get("/api/distance/jobs?limit=0")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_list_jobs_invalid_offset(self, client, mock_distance_client):
        """Test negative offset."""
        resp = client.get("/api/distance/jobs?offset=-1")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_list_jobs_invalid_status(self, client, mock_distance_client):
        """Test invalid status value."""
        resp = client.get("/api/distance/jobs?status=invalid")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "status" in data["error"]["message"].lower()

    def test_list_jobs_invalid_date_format(self, client, mock_distance_client):
        """Test invalid date format."""
        resp = client.get("/api/distance/jobs?date=2026/01/25")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "date" in data["error"]["message"].lower()

    def test_list_jobs_service_unavailable(self, client, mock_distance_client):
        """Test service unavailable error."""
        mock_distance_client.list_jobs.side_effect = ServiceUnavailableError("Service unavailable")

        resp = client.get("/api/distance/jobs")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


# =============================================================================
# GET /api/distance/download/<filename> Tests
# =============================================================================


class TestDownloadCSV:
    """Tests for GET /api/distance/download/<filename> endpoint."""

    def test_download_csv_success(self, client, tmp_path):
        """Test successful CSV download."""
        # The test config uses /tmp/test_data, so create the file there
        csv_dir = Path("/tmp/test_data/csv")
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_file = csv_dir / "distance_20260125_iphone_stuart.csv"
        csv_file.write_text("timestamp,device_id,latitude,longitude,distance_from_home_km\n")

        try:
            resp = client.get("/api/distance/download/distance_20260125_iphone_stuart.csv")

            assert resp.status_code == 200
            assert resp.mimetype == "text/csv"
            assert "attachment" in resp.headers.get("Content-Disposition", "")
        finally:
            # Cleanup
            if csv_file.exists():
                csv_file.unlink()

    def test_download_csv_file_not_found(self, client, tmp_path):
        """Test file not found error."""
        # File doesn't exist
        resp = client.get("/api/distance/download/distance_20260125_nonexistent.csv")

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_download_csv_invalid_prefix(self, client, mock_distance_client):
        """Test filename without distance_ prefix."""
        resp = client.get("/api/distance/download/invalid_20260125.csv")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "distance_" in data["error"]["message"]

    def test_download_csv_invalid_extension(self, client, mock_distance_client):
        """Test filename without .csv extension."""
        resp = client.get("/api/distance/download/distance_20260125.txt")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert ".csv" in data["error"]["message"]

    def test_download_csv_path_traversal_dotdot(self, client, mock_distance_client):
        """Test path traversal attempt with ../."""
        # Use a filename with .. that will be caught by validation
        resp = client.get("/api/distance/download/distance_..test.csv")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "traversal" in data["error"]["message"].lower()

    def test_download_csv_path_traversal_slash(self, client, mock_distance_client):
        """Test path traversal attempt with  backslash."""
        # Test with backslash (Windows path separator)
        resp = client.get("/api/distance/download/distance_test\\test.csv")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_download_csv_not_a_file(self, client, tmp_path):
        """Test when path is a directory, not a file."""
        # Create a directory with the CSV filename
        csv_dir = Path("/tmp/test_data/csv")
        csv_dir.mkdir(parents=True, exist_ok=True)
        dir_path = csv_dir / "distance_20260125.csv"
        dir_path.mkdir(exist_ok=True)  # Create directory instead of file

        try:
            resp = client.get("/api/distance/download/distance_20260125.csv")

            assert resp.status_code == 404
            data = resp.get_json()
            assert data["error"]["code"] == "NOT_FOUND"
        finally:
            # Cleanup
            if dir_path.exists() and dir_path.is_dir():
                dir_path.rmdir()
