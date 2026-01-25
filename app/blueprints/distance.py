"""
Distance calculation endpoints.

Provides REST API interface to otel-worker gRPC service for distance calculations
from home location. Supports async job management with polling and CSV downloads.
"""

import logging
import os
from datetime import datetime

import requests
from flask import Blueprint, Response, current_app, jsonify, request
from opentelemetry import trace

from app.services.distance_client import (
    DistanceClient,
    DistanceServiceError,
    ServiceUnavailableError,
    ValidationError,
)

distance_bp = Blueprint("distance", __name__, url_prefix="/api/distance")
logger = logging.getLogger(__name__)


def get_tracer() -> trace.Tracer:
    """Get the tracer from the current app context."""
    return current_app.config.get("TRACER") or trace.get_tracer(__name__)


def get_distance_client() -> DistanceClient:
    """Get or create singleton DistanceClient instance."""
    config = current_app.config.get("APP_CONFIG")
    if config:
        endpoint = config.distance_service_endpoint
        timeout = config.distance_service_timeout
    else:
        # Fallback to environment variables if config not available
        endpoint = os.getenv("DISTANCE_SERVICE_ENDPOINT", "localhost:50051")
        timeout = int(os.getenv("DISTANCE_SERVICE_TIMEOUT", "30"))
    return DistanceClient(endpoint, timeout)


def get_trace_id(span: trace.Span) -> str:
    """Extract trace ID from span context."""
    return format(span.get_span_context().trace_id, "032x")


def error_response(message: str, code: str, trace_id: str, status_code: int = 400):
    """Standard error response format."""
    return (
        jsonify(
            {
                "error": {"code": code, "message": message},
                "trace_id": trace_id,
            }
        ),
        status_code,
    )


@distance_bp.route("/calculate", methods=["POST"])
def calculate_distance():
    """Start distance calculation job.
    ---
    tags:
      - Distance
    summary: Calculate distance from home
    description: |
      Start an async distance calculation job for a specific date. The job will
      calculate distances from home location (40.736097°N, 74.039373°W) for all
      location data points on that date.

      Returns a job_id that can be used to poll for status and results.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - date
          properties:
            date:
              type: string
              format: date
              description: Date in YYYY-MM-DD format
              example: "2026-01-25"
            device_id:
              type: string
              description: Optional device identifier to filter locations (empty = all devices)
              example: "iphone_stuart"
    responses:
      202:
        description: Job created successfully
        schema:
          type: object
          properties:
            job_id:
              type: string
              example: "b4eaed9f-2b3d-43cb-9cb2-4d7313343369"
            status:
              type: string
              example: "queued"
            queued_at:
              type: string
              format: date-time
              example: "2026-01-25T15:24:54.545Z"
            status_url:
              type: string
              example: "/api/distance/jobs/b4eaed9f-2b3d-43cb-9cb2-4d7313343369"
            trace_id:
              type: string
              example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret
      400:
        description: Invalid request parameters
        schema:
          type: object
          properties:
            error:
              type: object
              properties:
                code:
                  type: string
                  example: "VALIDATION_ERROR"
                message:
                  type: string
                  example: "Invalid date format. Expected YYYY-MM-DD"
            trace_id:
              type: string
      503:
        description: Distance service unavailable
        schema:
          type: object
          properties:
            error:
              type: object
              properties:
                code:
                  type: string
                  example: "SERVICE_UNAVAILABLE"
                message:
                  type: string
            trace_id:
              type: string
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("calculate-distance-handler") as span:
        trace_id = get_trace_id(span)

        # Validate request body
        if not request.is_json:
            return error_response("Request must be JSON", "VALIDATION_ERROR", trace_id, 400)

        data = request.get_json()
        date = data.get("date")
        device_id = data.get("device_id", "")

        # Validate date field
        if not date:
            return error_response("Missing required field: date", "VALIDATION_ERROR", trace_id, 400)

        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            # Check if date is not in future
            if date_obj.date() > datetime.now().date():
                return error_response(
                    "Date cannot be in the future", "VALIDATION_ERROR", trace_id, 400
                )
        except ValueError:
            return error_response(
                "Invalid date format. Expected YYYY-MM-DD",
                "VALIDATION_ERROR",
                trace_id,
                400,
            )

        # Validate device_id if provided
        if device_id and not device_id.replace("_", "").isalnum():
            return error_response(
                "device_id must be alphanumeric with underscores",
                "VALIDATION_ERROR",
                trace_id,
                400,
            )

        span.set_attribute("distance.date", date)
        span.set_attribute("distance.device_id", device_id)

        # Call gRPC service
        try:
            client = get_distance_client()
            response = client.calculate_distance(date, device_id)

            span.set_attribute("distance.job_id", response.job_id)
            span.set_attribute("distance.job_status", response.status)

            logger.info(
                f"Started distance calculation job {response.job_id} for date={date}, device_id={device_id}"
            )

            return (
                jsonify(
                    {
                        "job_id": response.job_id,
                        "status": response.status,
                        "queued_at": response.queued_at.ToDatetime().isoformat() + "Z",
                        "status_url": f"/api/distance/jobs/{response.job_id}",
                        "trace_id": trace_id,
                    }
                ),
                202,
            )

        except ServiceUnavailableError as e:
            span.record_exception(e)
            logger.error(f"Distance service unavailable: {e}")
            return error_response(str(e), "SERVICE_UNAVAILABLE", trace_id, 503)

        except ValidationError as e:
            span.record_exception(e)
            logger.warning(f"Validation error: {e}")
            return error_response(str(e), "VALIDATION_ERROR", trace_id, 400)

        except DistanceServiceError as e:
            span.record_exception(e)
            logger.error(f"Distance service error: {e}")
            return error_response(str(e), "INTERNAL_ERROR", trace_id, 500)


@distance_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """Get job status and results.
    ---
    tags:
      - Distance
    summary: Get job status
    description: |
      Retrieve the status and results of a distance calculation job.

      Status values:
      - queued: Job is waiting to be processed
      - processing: Job is currently running
      - completed: Job finished successfully (includes result)
      - failed: Job failed (includes error_message)
    parameters:
      - in: path
        name: job_id
        type: string
        required: true
        description: Job UUID
        example: "b4eaed9f-2b3d-43cb-9cb2-4d7313343369"
    responses:
      200:
        description: Job status retrieved successfully
        schema:
          type: object
          properties:
            job_id:
              type: string
            status:
              type: string
              enum: [queued, processing, completed, failed]
            queued_at:
              type: string
              format: date-time
            started_at:
              type: string
              format: date-time
            completed_at:
              type: string
              format: date-time
            result:
              type: object
              properties:
                csv_download_url:
                  type: string
                  example: "/api/distance/download/distance_20260125_iphone_stuart.csv"
                total_distance_km:
                  type: number
                  example: 19.44
                total_locations:
                  type: integer
                  example: 1464
                max_distance_km:
                  type: number
                  example: 0.31
                min_distance_km:
                  type: number
                  example: 0.001
                processing_time_ms:
                  type: integer
                  example: 252
                date:
                  type: string
                  example: "2026-01-25"
                device_id:
                  type: string
                  example: "iphone_stuart"
            error_message:
              type: string
            trace_id:
              type: string
      404:
        description: Job not found
      503:
        description: Distance service unavailable
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("get-job-status-handler") as span:
        trace_id = get_trace_id(span)
        span.set_attribute("distance.job_id", job_id)

        try:
            client = get_distance_client()
            response = client.get_job_status(job_id)

            span.set_attribute("distance.job_status", response.status)

            # Build response
            result_data: dict[str, str | int | dict[str, str | int | float]] = {
                "job_id": response.job_id,
                "status": response.status,
                "queued_at": response.queued_at.ToDatetime().isoformat() + "Z",
                "trace_id": trace_id,
            }

            if response.started_at.seconds > 0:
                result_data["started_at"] = response.started_at.ToDatetime().isoformat() + "Z"

            if response.completed_at.seconds > 0:
                result_data["completed_at"] = response.completed_at.ToDatetime().isoformat() + "Z"

            if response.status == "completed" and response.result:
                result = response.result
                csv_filename = os.path.basename(result.csv_path)
                result_data["result"] = {
                    "csv_download_url": f"/api/distance/download/{csv_filename}",
                    "total_distance_km": result.total_distance_km,
                    "total_locations": result.total_locations,
                    "max_distance_km": result.max_distance_km,
                    "min_distance_km": result.min_distance_km,
                    "processing_time_ms": result.processing_time_ms,
                    "date": result.date,
                    "device_id": result.device_id,
                }
                span.set_attribute("distance.total_locations", result.total_locations)
                span.set_attribute("distance.total_distance_km", result.total_distance_km)

            if response.status == "failed" and response.error_message:
                result_data["error_message"] = response.error_message

            logger.info(f"Retrieved job {job_id} status: {response.status}")
            return jsonify(result_data)

        except ValidationError as e:
            span.record_exception(e)
            logger.warning(f"Job {job_id} not found: {e}")
            return error_response(str(e), "NOT_FOUND", trace_id, 404)

        except ServiceUnavailableError as e:
            span.record_exception(e)
            logger.error(f"Distance service unavailable: {e}")
            return error_response(str(e), "SERVICE_UNAVAILABLE", trace_id, 503)

        except DistanceServiceError as e:
            span.record_exception(e)
            logger.error(f"Distance service error: {e}")
            return error_response(str(e), "INTERNAL_ERROR", trace_id, 500)


@distance_bp.route("/jobs", methods=["GET"])
def list_jobs():
    """List distance calculation jobs.
    ---
    tags:
      - Distance
    summary: List jobs
    description: |
      List distance calculation jobs with optional filtering and pagination.

      Query parameters allow filtering by status, date, device_id and pagination control.
    parameters:
      - in: query
        name: status
        type: string
        enum: [queued, processing, completed, failed]
        description: Filter by job status
      - in: query
        name: date
        type: string
        format: date
        description: Filter by calculation date (YYYY-MM-DD)
        example: "2026-01-25"
      - in: query
        name: device_id
        type: string
        description: Filter by device identifier
        example: "iphone_stuart"
      - in: query
        name: limit
        type: integer
        default: 50
        minimum: 1
        maximum: 500
        description: Maximum number of results
      - in: query
        name: offset
        type: integer
        default: 0
        minimum: 0
        description: Pagination offset
    responses:
      200:
        description: Jobs retrieved successfully
        schema:
          type: object
          properties:
            jobs:
              type: array
              items:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                  date:
                    type: string
                  device_id:
                    type: string
                  queued_at:
                    type: string
                    format: date-time
                  completed_at:
                    type: string
                    format: date-time
            total_count:
              type: integer
              example: 42
            limit:
              type: integer
              example: 50
            offset:
              type: integer
              example: 0
            next_offset:
              type: integer
              nullable: true
              example: 50
            trace_id:
              type: string
      400:
        description: Invalid query parameters
      503:
        description: Distance service unavailable
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("list-jobs-handler") as span:
        trace_id = get_trace_id(span)

        # Parse query parameters
        status = request.args.get("status", "")
        date = request.args.get("date", "")
        device_id = request.args.get("device_id", "")

        try:
            limit = int(request.args.get("limit", "50"))
            offset = int(request.args.get("offset", "0"))
        except ValueError:
            return error_response(
                "limit and offset must be integers", "VALIDATION_ERROR", trace_id, 400
            )

        # Validate limit and offset
        if limit < 1 or limit > 500:
            return error_response(
                "limit must be between 1 and 500", "VALIDATION_ERROR", trace_id, 400
            )

        if offset < 0:
            return error_response("offset must be non-negative", "VALIDATION_ERROR", trace_id, 400)

        # Validate status if provided
        valid_statuses = ["queued", "processing", "completed", "failed"]
        if status and status not in valid_statuses:
            return error_response(
                f"status must be one of: {', '.join(valid_statuses)}",
                "VALIDATION_ERROR",
                trace_id,
                400,
            )

        # Validate date format if provided
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return error_response(
                    "Invalid date format. Expected YYYY-MM-DD",
                    "VALIDATION_ERROR",
                    trace_id,
                    400,
                )

        span.set_attribute("distance.filter.status", status or "all")
        span.set_attribute("distance.filter.limit", limit)
        span.set_attribute("distance.filter.offset", offset)

        try:
            client = get_distance_client()
            response = client.list_jobs(status, limit, offset, date, device_id)

            # Build jobs array
            jobs = []
            for job in response.jobs:
                job_data = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "date": job.date,
                    "device_id": job.device_id,
                    "queued_at": job.queued_at.ToDatetime().isoformat() + "Z",
                }
                if job.completed_at.seconds > 0:
                    job_data["completed_at"] = job.completed_at.ToDatetime().isoformat() + "Z"
                jobs.append(job_data)

            # Calculate next_offset
            next_offset = None
            if offset + limit < response.total_count:
                next_offset = offset + limit

            span.set_attribute("distance.result_count", len(jobs))
            span.set_attribute("distance.total_count", response.total_count)

            logger.info(
                f"Listed {len(jobs)} jobs (total: {response.total_count}, offset: {offset})"
            )

            return jsonify(
                {
                    "jobs": jobs,
                    "total_count": response.total_count,
                    "limit": limit,
                    "offset": offset,
                    "next_offset": next_offset,
                    "trace_id": trace_id,
                }
            )

        except ServiceUnavailableError as e:
            span.record_exception(e)
            logger.error(f"Distance service unavailable: {e}")
            return error_response(str(e), "SERVICE_UNAVAILABLE", trace_id, 503)

        except DistanceServiceError as e:
            span.record_exception(e)
            logger.error(f"Distance service error: {e}")
            return error_response(str(e), "INTERNAL_ERROR", trace_id, 500)


@distance_bp.route("/download/<filename>", methods=["GET"])
def download_csv(filename: str):
    """Download CSV result file.
    ---
    tags:
      - Distance
    summary: Download CSV file
    description: |
      Download a distance calculation result CSV file.

      CSV format:
      - timestamp, device_id, latitude, longitude, distance_from_home_km, accuracy, battery, velocity
      - Summary footer with total/max/min distances

      Security: Validates filename to prevent path traversal attacks.
    parameters:
      - in: path
        name: filename
        type: string
        required: true
        description: CSV filename (must start with 'distance_' and end with '.csv')
        example: "distance_20260125_iphone_stuart.csv"
    produces:
      - text/csv
    responses:
      200:
        description: CSV file
        headers:
          Content-Type:
            type: string
            example: "text/csv"
          Content-Disposition:
            type: string
            example: "attachment; filename=distance_20260125.csv"
      400:
        description: Invalid filename
      404:
        description: File not found
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("download-csv-handler") as span:
        trace_id = get_trace_id(span)
        span.set_attribute("distance.filename", filename)

        # Validate filename format
        if not filename.startswith("distance_") or not filename.endswith(".csv"):
            return error_response(
                "Invalid filename format. Must start with 'distance_' and end with '.csv'",
                "VALIDATION_ERROR",
                trace_id,
                400,
            )

        # Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return error_response(
                "Invalid filename: path traversal detected",
                "VALIDATION_ERROR",
                trace_id,
                400,
            )

        # Proxy CSV download request to otel-worker
        # Get otel-worker endpoint from config
        config = current_app.config.get("APP_CONFIG")
        if config and config.distance_service_endpoint:
            # Extract host from gRPC endpoint (e.g., "otel-worker.otel-worker.svc.cluster.local:50051")
            endpoint_parts = config.distance_service_endpoint.split(":")
            if len(endpoint_parts) >= 1:  # noqa: PLR2004
                worker_host = endpoint_parts[0]
                # Use HTTP port 8080 instead of gRPC port 50051
                worker_url = f"http://{worker_host}:8080/download/{filename}"
            else:
                worker_url = (
                    f"http://otel-worker.otel-worker.svc.cluster.local:8080/download/{filename}"
                )
        else:
            worker_url = (
                f"http://otel-worker.otel-worker.svc.cluster.local:8080/download/{filename}"
            )

        span.set_attribute("distance.worker_url", worker_url)
        logger.info(f"Proxying CSV download to otel-worker: {filename}")

        try:
            # Proxy request to otel-worker with streaming
            response = requests.get(worker_url, timeout=30, stream=True)

            if response.status_code == 404:  # noqa: PLR2004
                logger.warning(f"CSV file not found on worker: {filename}")
                return error_response(f"File not found: {filename}", "NOT_FOUND", trace_id, 404)

            if response.status_code != 200:  # noqa: PLR2004
                logger.error(f"Worker returned HTTP {response.status_code} for {filename}")
                return error_response(
                    f"Failed to download file from worker: HTTP {response.status_code}",
                    "DOWNLOAD_FAILED",
                    trace_id,
                    response.status_code,
                )

            # Stream the response from otel-worker to client
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            flask_response = Response(generate(), mimetype="text/csv")
            flask_response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

            logger.info(f"Successfully proxied CSV download: {filename}")
            span.set_attribute("distance.proxy_status", "success")
            return flask_response

        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading CSV from worker: {filename}")
            return error_response("Download request timed out", "TIMEOUT", trace_id, 504)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download CSV from worker: {e}")
            return error_response(
                f"Failed to download file: {e!s}", "DOWNLOAD_ERROR", trace_id, 500
            )

        except Exception as e:
            logger.error(f"Unexpected error proxying CSV download: {e}", exc_info=True)
            return error_response("An unexpected error occurred", "INTERNAL_ERROR", trace_id, 500)
