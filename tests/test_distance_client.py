"""
Unit tests for the DistanceClient gRPC service.

Tests cover:
- Connection initialization and singleton pattern
- Successful gRPC calls with proper response handling
- Error handling (UNAVAILABLE, INVALID_ARGUMENT, NOT_FOUND)
- OpenTelemetry span creation and attributes
- Health check functionality
- Context manager usage
"""

from unittest.mock import MagicMock, patch

import grpc
import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from app.proto.distance.v1 import distance_pb2
from app.services.distance_client import (
    DistanceClient,
    DistanceServiceError,
    ServiceUnavailableError,
    ValidationError,
)


@pytest.fixture
def mock_channel():
    """Mock gRPC channel."""
    with patch("grpc.insecure_channel") as mock:
        channel = MagicMock()
        mock.return_value = channel
        yield mock


@pytest.fixture
def mock_stub():
    """Mock DistanceService gRPC stub."""
    with patch("app.services.distance_client.distance_pb2_grpc.DistanceServiceStub") as mock:
        stub = MagicMock()
        mock.return_value = stub
        yield stub


@pytest.fixture
def mock_tracer():
    """Mock OpenTelemetry tracer to avoid actual tracing."""
    with (
        patch("app.services.distance_client.GrpcInstrumentorClient"),
        patch("app.services.distance_client.trace.get_tracer") as mock_tracer,
    ):
        tracer = MagicMock()
        span = MagicMock()
        tracer.start_as_current_span.return_value.__enter__.return_value = span
        mock_tracer.return_value = tracer
        yield tracer


@pytest.fixture
def client(mock_channel, mock_stub, mock_tracer):
    """Create DistanceClient with mocked dependencies."""
    # Reset singleton
    DistanceClient._instance = None
    DistanceClient._channel = None

    client = DistanceClient("localhost:50051", timeout=10)
    return client


class TestDistanceClientInitialization:
    """Test client initialization and singleton pattern."""

    def test_client_initialization(self, mock_channel, mock_stub):
        """Test client initializes with correct endpoint and timeout."""
        DistanceClient._instance = None
        DistanceClient._channel = None

        client = DistanceClient("test-endpoint:50051", timeout=15)

        assert client.endpoint == "test-endpoint:50051"
        assert client.timeout == 15
        mock_channel.assert_called_once()

    def test_singleton_pattern(self, mock_channel, mock_stub):
        """Test singleton pattern reuses the same instance."""
        DistanceClient._instance = None
        DistanceClient._channel = None

        client1 = DistanceClient("localhost:50051")
        client2 = DistanceClient("localhost:50051")

        assert client1 is client2
        # Channel should only be created once
        assert mock_channel.call_count == 1


class TestCalculateDistance:
    """Test calculate_distance method."""

    def test_calculate_distance_success(self, client, mock_stub):
        """Test successful distance calculation request."""
        # Mock response
        mock_response = distance_pb2.CalculateDistanceResponse(
            job_id="test-job-123",
            status="queued",
            queued_at=Timestamp(seconds=1234567890),
        )
        mock_stub.CalculateDistanceFromHome.return_value = mock_response

        # Call method
        response = client.calculate_distance("2026-01-25", "iphone_stuart")

        # Assertions
        assert response.job_id == "test-job-123"
        assert response.status == "queued"

        # Verify gRPC call
        call_args = mock_stub.CalculateDistanceFromHome.call_args
        request = call_args[0][0]
        assert request.date == "2026-01-25"
        assert request.device_id == "iphone_stuart"
        assert call_args[1]["timeout"] == 10

    def test_calculate_distance_all_devices(self, client, mock_stub):
        """Test calculation without device_id (all devices)."""
        mock_response = distance_pb2.CalculateDistanceResponse(
            job_id="test-job-456", status="queued"
        )
        mock_stub.CalculateDistanceFromHome.return_value = mock_response

        response = client.calculate_distance("2026-01-25")

        assert response.job_id == "test-job-456"
        request = mock_stub.CalculateDistanceFromHome.call_args[0][0]
        assert request.device_id == ""

    def test_calculate_distance_service_unavailable(self, client, mock_stub):
        """Test handling of UNAVAILABLE error."""
        mock_stub.CalculateDistanceFromHome.side_effect = grpc.RpcError()
        mock_error = mock_stub.CalculateDistanceFromHome.side_effect
        mock_error.code = lambda: grpc.StatusCode.UNAVAILABLE
        mock_error.details = lambda: "Connection refused"

        with pytest.raises(ServiceUnavailableError) as exc_info:
            client.calculate_distance("2026-01-25")

        assert "unreachable" in str(exc_info.value)

    def test_calculate_distance_validation_error(self, client, mock_stub):
        """Test handling of INVALID_ARGUMENT error."""
        mock_stub.CalculateDistanceFromHome.side_effect = grpc.RpcError()
        mock_error = mock_stub.CalculateDistanceFromHome.side_effect
        mock_error.code = lambda: grpc.StatusCode.INVALID_ARGUMENT
        mock_error.details = lambda: "Invalid date format"

        with pytest.raises(ValidationError) as exc_info:
            client.calculate_distance("invalid-date")

        assert "Invalid request" in str(exc_info.value)


class TestGetJobStatus:
    """Test get_job_status method."""

    def test_get_job_status_queued(self, client, mock_stub):
        """Test getting status of queued job."""
        mock_response = distance_pb2.GetJobStatusResponse(
            job_id="test-job-123",
            status="queued",
            queued_at=Timestamp(seconds=1234567890),
        )
        mock_stub.GetJobStatus.return_value = mock_response

        response = client.get_job_status("test-job-123")

        assert response.job_id == "test-job-123"
        assert response.status == "queued"
        assert mock_stub.GetJobStatus.call_args[0][0].job_id == "test-job-123"

    def test_get_job_status_completed(self, client, mock_stub):
        """Test getting status of completed job with results."""
        result = distance_pb2.JobResult(
            csv_path="/data/csv/distance_20260125.csv",
            total_distance_km=19.44,
            total_locations=1464,
            max_distance_km=0.31,
            min_distance_km=0.001,
            date="2026-01-25",
            device_id="iphone_stuart",
            processing_time_ms=252,
        )
        mock_response = distance_pb2.GetJobStatusResponse(
            job_id="test-job-123",
            status="completed",
            queued_at=Timestamp(seconds=1234567890),
            started_at=Timestamp(seconds=1234567891),
            completed_at=Timestamp(seconds=1234567892),
            result=result,
        )
        mock_stub.GetJobStatus.return_value = mock_response

        response = client.get_job_status("test-job-123")

        assert response.status == "completed"
        assert response.result.csv_path == "/data/csv/distance_20260125.csv"
        assert response.result.total_distance_km == 19.44
        assert response.result.total_locations == 1464

    def test_get_job_status_failed(self, client, mock_stub):
        """Test getting status of failed job with error message."""
        mock_response = distance_pb2.GetJobStatusResponse(
            job_id="test-job-123",
            status="failed",
            queued_at=Timestamp(seconds=1234567890),
            started_at=Timestamp(seconds=1234567891),
            completed_at=Timestamp(seconds=1234567892),
            error_message="No location data found for date 2026-01-25",
        )
        mock_stub.GetJobStatus.return_value = mock_response

        response = client.get_job_status("test-job-123")

        assert response.status == "failed"
        assert "No location data found" in response.error_message

    def test_get_job_status_not_found(self, client, mock_stub):
        """Test handling of NOT_FOUND error for invalid job_id."""
        mock_stub.GetJobStatus.side_effect = grpc.RpcError()
        mock_error = mock_stub.GetJobStatus.side_effect
        mock_error.code = lambda: grpc.StatusCode.NOT_FOUND
        mock_error.details = lambda: "Job not found"

        with pytest.raises(ValidationError) as exc_info:
            client.get_job_status("invalid-job-id")

        assert "Invalid request" in str(exc_info.value)


class TestListJobs:
    """Test list_jobs method."""

    def test_list_jobs_no_filters(self, client, mock_stub):
        """Test listing jobs without filters."""
        job1 = distance_pb2.JobSummary(
            job_id="job-1",
            status="completed",
            date="2026-01-25",
            device_id="iphone_stuart",
        )
        job2 = distance_pb2.JobSummary(
            job_id="job-2", status="queued", date="2026-01-24", device_id=""
        )
        mock_response = distance_pb2.ListJobsResponse(
            jobs=[job1, job2], total_count=2, limit=50, offset=0
        )
        mock_stub.ListJobs.return_value = mock_response

        response = client.list_jobs()

        assert len(response.jobs) == 2
        assert response.total_count == 2
        assert response.jobs[0].job_id == "job-1"
        assert response.jobs[1].job_id == "job-2"

    def test_list_jobs_with_status_filter(self, client, mock_stub):
        """Test listing jobs filtered by status."""
        job = distance_pb2.JobSummary(job_id="job-1", status="completed", date="2026-01-25")
        mock_response = distance_pb2.ListJobsResponse(jobs=[job], total_count=1, limit=50, offset=0)
        mock_stub.ListJobs.return_value = mock_response

        response = client.list_jobs(status="completed", limit=10)

        assert len(response.jobs) == 1
        request = mock_stub.ListJobs.call_args[0][0]
        assert request.status == "completed"
        assert request.limit == 10

    def test_list_jobs_with_pagination(self, client, mock_stub):
        """Test listing jobs with pagination."""
        mock_response = distance_pb2.ListJobsResponse(jobs=[], total_count=100, limit=20, offset=40)
        mock_stub.ListJobs.return_value = mock_response

        response = client.list_jobs(limit=20, offset=40)

        assert response.total_count == 100
        assert response.limit == 20
        assert response.offset == 40

    def test_list_jobs_with_date_and_device_filters(self, client, mock_stub):
        """Test listing jobs with date and device_id filters."""
        mock_response = distance_pb2.ListJobsResponse(jobs=[], total_count=0, limit=50, offset=0)
        mock_stub.ListJobs.return_value = mock_response

        client.list_jobs(date="2026-01-25", device_id="iphone_stuart")

        request = mock_stub.ListJobs.call_args[0][0]
        assert request.date == "2026-01-25"
        assert request.device_id == "iphone_stuart"


class TestHealthCheck:
    """Test health_check method."""

    def test_health_check_success(self, client, mock_stub):
        """Test successful health check."""
        mock_response = distance_pb2.ListJobsResponse(jobs=[], total_count=0, limit=1, offset=0)
        mock_stub.ListJobs.return_value = mock_response

        result = client.health_check()

        assert result is True
        # Should use timeout of 5 seconds
        assert mock_stub.ListJobs.call_args[1]["timeout"] == 5

    def test_health_check_failure(self, client, mock_stub):
        """Test failed health check."""
        mock_stub.ListJobs.side_effect = grpc.RpcError()
        mock_error = mock_stub.ListJobs.side_effect
        mock_error.code = lambda: grpc.StatusCode.UNAVAILABLE
        mock_error.details = lambda: "Connection refused"

        result = client.health_check()

        assert result is False


class TestErrorHandling:
    """Test error handling for various gRPC errors."""

    def test_deadline_exceeded_error(self, client, mock_stub):
        """Test handling of DEADLINE_EXCEEDED error."""
        mock_stub.CalculateDistanceFromHome.side_effect = grpc.RpcError()
        mock_error = mock_stub.CalculateDistanceFromHome.side_effect
        mock_error.code = lambda: grpc.StatusCode.DEADLINE_EXCEEDED
        mock_error.details = lambda: "Timeout"

        with pytest.raises(DistanceServiceError) as exc_info:
            client.calculate_distance("2026-01-25")

        assert "timeout" in str(exc_info.value).lower()

    def test_unknown_error(self, client, mock_stub):
        """Test handling of unknown gRPC errors."""
        mock_stub.GetJobStatus.side_effect = grpc.RpcError()
        mock_error = mock_stub.GetJobStatus.side_effect
        mock_error.code = lambda: grpc.StatusCode.INTERNAL
        mock_error.details = lambda: "Internal server error"

        with pytest.raises(DistanceServiceError) as exc_info:
            client.get_job_status("test-job")

        assert "INTERNAL" in str(exc_info.value)


class TestContextManager:
    """Test context manager usage."""

    def test_context_manager_closes_channel(self, mock_channel, mock_stub):
        """Test that context manager properly closes the channel."""
        DistanceClient._instance = None
        DistanceClient._channel = None

        with DistanceClient("localhost:50051") as client:
            assert client is not None

        # Verify close was called on the mocked channel
        mock_channel.return_value.close.assert_called_once()  # type: ignore[attr-defined]

    def test_manual_close(self, client):
        """Test manual close() call."""
        channel = client._channel
        assert channel is not None

        client.close()

        channel.close.assert_called_once()  # type: ignore[attr-defined]
        assert client._channel is None
        assert DistanceClient._instance is None


class TestOpenTelemetryInstrumentation:
    """Test OpenTelemetry span creation and attributes."""

    def test_span_attributes_on_calculate_distance(self, client, mock_stub, mock_tracer):
        """Test that calculate_distance creates span with correct attributes."""
        mock_response = distance_pb2.CalculateDistanceResponse(
            job_id="test-job-123", status="queued"
        )
        mock_stub.CalculateDistanceFromHome.return_value = mock_response

        client.calculate_distance("2026-01-25", "iphone_stuart")

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_with("grpc-calculate-distance")

        # Verify span attributes were set
        span = mock_tracer.start_as_current_span.return_value.__enter__.return_value
        span.set_attribute.assert_any_call("distance.date", "2026-01-25")
        span.set_attribute.assert_any_call("distance.device_id", "iphone_stuart")
        span.set_attribute.assert_any_call("distance.job_id", "test-job-123")
        span.set_attribute.assert_any_call("distance.status", "queued")

    def test_span_records_exception(self, client, mock_stub, mock_tracer):
        """Test that exceptions are recorded in spans."""
        mock_stub.CalculateDistanceFromHome.side_effect = grpc.RpcError()
        mock_error = mock_stub.CalculateDistanceFromHome.side_effect
        mock_error.code = lambda: grpc.StatusCode.UNAVAILABLE
        mock_error.details = lambda: "Connection refused"

        with pytest.raises(ServiceUnavailableError):
            client.calculate_distance("2026-01-25")

        # Verify exception was recorded
        span = mock_tracer.start_as_current_span.return_value.__enter__.return_value
        assert span.record_exception.call_count == 1
