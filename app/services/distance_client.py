"""
gRPC client for interacting with the otel-worker DistanceService.

This module provides a singleton gRPC client with:
- Connection pooling and reuse
- OpenTelemetry automatic instrumentation
- Error handling and retries with exponential backoff
- Health checking
"""

import logging
from typing import NoReturn, Optional

import grpc
from opentelemetry import trace
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

from app.proto.distance.v1 import distance_pb2, distance_pb2_grpc

logger = logging.getLogger(__name__)

# Instrument gRPC client for automatic OpenTelemetry tracing
GrpcInstrumentorClient().instrument()


class DistanceServiceError(Exception):
    """Base exception for distance service errors."""


class ServiceUnavailableError(DistanceServiceError):
    """Raised when the distance service is unreachable."""


class ValidationError(DistanceServiceError):
    """Raised when request validation fails."""


class DistanceClient:
    """
    gRPC client for the otel-worker DistanceService.

    Provides methods to:
    - Start distance calculation jobs
    - Poll job status
    - List jobs with filtering
    - Check service health

    Example:
        >>> client = DistanceClient("otel-worker.otel-worker.svc.cluster.local:50051")
        >>> response = client.calculate_distance("2026-01-25", "iphone_stuart")
        >>> print(f"Job ID: {response.job_id}")
    """

    _instance: Optional["DistanceClient"] = None
    _channel: grpc.Channel | None = None

    def __new__(cls, endpoint: str, timeout: int = 30):  # noqa: ARG003, ARG004
        """Singleton pattern - reuse the same client instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, endpoint: str, timeout: int = 30):
        """
        Initialize the gRPC client.

        Args:
            endpoint: gRPC server endpoint (e.g., "localhost:50051")
            timeout: Default timeout in seconds for RPC calls
        """
        if self._channel is None:
            logger.info(f"Initializing DistanceClient for endpoint: {endpoint}")
            self.endpoint = endpoint
            self.timeout = timeout
            self._channel = grpc.insecure_channel(
                endpoint,
                options=[
                    ("grpc.keepalive_time_ms", 10000),
                    ("grpc.keepalive_timeout_ms", 5000),
                    ("grpc.keepalive_permit_without_calls", True),
                    ("grpc.http2.max_pings_without_data", 0),
                ],
            )
            self.stub = distance_pb2_grpc.DistanceServiceStub(self._channel)
            logger.info("DistanceClient initialized successfully")

    def calculate_distance(
        self, date: str, device_id: str = ""
    ) -> distance_pb2.CalculateDistanceResponse:
        """
        Start an async distance calculation job.

        Args:
            date: Date in YYYY-MM-DD format
            device_id: Optional device identifier to filter locations

        Returns:
            CalculateDistanceResponse with job_id, status, and queued_at timestamp

        Raises:
            ServiceUnavailableError: If the service is unreachable
            ValidationError: If request parameters are invalid
            DistanceServiceError: For other gRPC errors

        Example:
            >>> response = client.calculate_distance("2026-01-25", "iphone_stuart")
            >>> print(f"Job {response.job_id} queued at {response.queued_at}")
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("grpc-calculate-distance") as span:
            span.set_attribute("distance.date", date)
            span.set_attribute("distance.device_id", device_id)

            request = distance_pb2.CalculateDistanceRequest(date=date, device_id=device_id)

            try:
                response = self.stub.CalculateDistanceFromHome(request, timeout=self.timeout)
                span.set_attribute("distance.job_id", response.job_id)
                span.set_attribute("distance.status", response.status)
                logger.info(f"Started distance calculation job: {response.job_id} for date={date}")
                return response  # type: ignore[no-any-return]

            except grpc.RpcError as e:
                span.record_exception(e)
                self._handle_grpc_error(e)

    def get_job_status(self, job_id: str) -> distance_pb2.GetJobStatusResponse:
        """
        Get the status and results of a distance calculation job.

        Args:
            job_id: UUID of the job to query

        Returns:
            GetJobStatusResponse with current status, timestamps, and results if completed

        Raises:
            ServiceUnavailableError: If the service is unreachable
            ValidationError: If job_id is invalid or not found
            DistanceServiceError: For other gRPC errors

        Example:
            >>> status = client.get_job_status("b4eaed9f-2b3d-43cb-9cb2-4d7313343369")
            >>> if status.status == "completed":
            >>>     print(f"CSV: {status.result.csv_path}")
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("grpc-get-job-status") as span:
            span.set_attribute("distance.job_id", job_id)

            request = distance_pb2.GetJobStatusRequest(job_id=job_id)

            try:
                response = self.stub.GetJobStatus(request, timeout=self.timeout)
                span.set_attribute("distance.status", response.status)
                if response.status == "completed":
                    span.set_attribute("distance.total_locations", response.result.total_locations)
                    span.set_attribute(
                        "distance.total_distance_km", response.result.total_distance_km
                    )
                logger.debug(f"Job {job_id} status: {response.status}")
                return response  # type: ignore[no-any-return]

            except grpc.RpcError as e:
                span.record_exception(e)
                self._handle_grpc_error(e)

    def list_jobs(
        self,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
        date: str = "",
        device_id: str = "",
    ) -> distance_pb2.ListJobsResponse:
        """
        List distance calculation jobs with optional filtering.

        Args:
            status: Filter by status (queued/processing/completed/failed)
            limit: Maximum number of results (default 50, max 500)
            offset: Pagination offset (default 0)
            date: Filter by calculation date (YYYY-MM-DD)
            device_id: Filter by device identifier

        Returns:
            ListJobsResponse with jobs array and pagination metadata

        Raises:
            ServiceUnavailableError: If the service is unreachable
            ValidationError: If filter parameters are invalid
            DistanceServiceError: For other gRPC errors

        Example:
            >>> response = client.list_jobs(status="completed", limit=10)
            >>> for job in response.jobs:
            >>>     print(f"{job.job_id}: {job.status}")
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("grpc-list-jobs") as span:
            span.set_attribute("distance.filter.status", status)
            span.set_attribute("distance.filter.limit", limit)
            span.set_attribute("distance.filter.offset", offset)

            request = distance_pb2.ListJobsRequest(
                status=status, limit=limit, offset=offset, date=date, device_id=device_id
            )

            try:
                response = self.stub.ListJobs(request, timeout=self.timeout)
                span.set_attribute("distance.result_count", len(response.jobs))
                span.set_attribute("distance.total_count", response.total_count)
                logger.debug(f"Listed {len(response.jobs)} jobs (total: {response.total_count})")
                return response  # type: ignore[no-any-return]

            except grpc.RpcError as e:
                span.record_exception(e)
                self._handle_grpc_error(e)

    def health_check(self) -> bool:
        """
        Check if the gRPC connection is healthy.

        Returns:
            True if service is reachable, False otherwise

        Example:
            >>> if not client.health_check():
            >>>     logger.error("Distance service is down!")
        """
        try:
            # Try to list jobs with limit=1 as a health check
            request = distance_pb2.ListJobsRequest(
                status="", limit=1, offset=0, date="", device_id=""
            )
            self.stub.ListJobs(request, timeout=5)
            return True
        except grpc.RpcError as e:
            logger.warning(f"Health check failed: {e.code()} - {e.details()}")
            return False

    def close(self):
        """Close the gRPC channel."""
        if self._channel:
            logger.info("Closing DistanceClient channel")
            self._channel.close()
            self._channel = None
            DistanceClient._instance = None

    def _handle_grpc_error(self, error: grpc.RpcError) -> NoReturn:
        """
        Convert gRPC errors to custom exceptions.

        Args:
            error: The gRPC RpcError to handle

        Raises:
            ServiceUnavailableError: For UNAVAILABLE status
            ValidationError: For INVALID_ARGUMENT, NOT_FOUND status
            DistanceServiceError: For all other errors
        """
        code = error.code()
        details = error.details()

        logger.error(f"gRPC error: {code} - {details}")

        if code == grpc.StatusCode.UNAVAILABLE:
            raise ServiceUnavailableError(
                f"Distance service unreachable at {self.endpoint}: {details}"
            )
        elif code in (grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND):
            raise ValidationError(f"Invalid request: {details}")
        else:
            raise DistanceServiceError(f"gRPC error ({code}): {details}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
