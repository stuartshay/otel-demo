"""
OpenTelemetry Demo App - Flask application with OTel instrumentation.

This app demonstrates:
- Automatic Flask instrumentation
- Custom spans and attributes
- Trace context propagation
- Logging with trace correlation
- Swagger/OpenAPI documentation
"""

import logging
import os
import random
import time
from pathlib import Path

from flasgger import Swagger
from flask import Flask, jsonify, redirect, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_NAMESPACE, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s",
)
logger = logging.getLogger(__name__)


def configure_opentelemetry():
    """Configure OpenTelemetry with OTLP exporter."""
    resource = Resource.create(
        {
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "otel-demo"),
            SERVICE_NAMESPACE: os.getenv("OTEL_SERVICE_NAMESPACE", "otel-demo"),
            "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "homelab"),
            "service.version": os.getenv("APP_VERSION", "1.0.0"),
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    logger.info(f"Configuring OTLP exporter to: {otlp_endpoint}")

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # Using cluster-internal communication
    )

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# Initialize OTel
tracer = configure_opentelemetry()

# Flask app
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Swagger/OpenAPI configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,  # noqa: ARG005
            "model_filter": lambda tag: True,  # noqa: ARG005
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

swagger_template = {
    "info": {
        "title": "OTel Demo API",
        "description": "OpenTelemetry Demo App - Flask application with distributed tracing",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "contact": {
            "name": "Stuart Shay",
            "url": "https://github.com/stuartshay/otel-demo",
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    },
    "host": "",  # Will be set dynamically
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {"name": "Health", "description": "Health and readiness endpoints"},
        {"name": "Demo", "description": "OpenTelemetry demonstration endpoints"},
        {"name": "Files", "description": "NFS storage file operations"},
        {"name": "Observability", "description": "Observability configuration"},
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)


class OTelLogFilter(logging.Filter):
    """Add trace context to log records."""

    def filter(self, record):
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            record.otelTraceID = format(ctx.trace_id, "032x")
            record.otelSpanID = format(ctx.span_id, "016x")
        else:
            record.otelTraceID = "0" * 32
            record.otelSpanID = "0" * 16
        return True


# Add filter to logger
for handler in logging.root.handlers:
    handler.addFilter(OTelLogFilter())


@app.route("/health")
def health():
    """Health check endpoint.
    ---
    tags:
      - Health
    summary: Health check
    description: Returns the health status of the application. Used by Kubernetes liveness probes.
    responses:
      200:
        description: Application is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
    """
    return jsonify({"status": "healthy"})


@app.route("/ready")
def ready():
    """Readiness check endpoint.
    ---
    tags:
      - Health
    summary: Readiness check
    description: Returns the readiness status of the application. Used by Kubernetes readiness probes.
    responses:
      200:
        description: Application is ready to receive traffic
        schema:
          type: object
          properties:
            status:
              type: string
              example: ready
    """
    return jsonify({"status": "ready"})


@app.route("/")
def index():
    """Redirect to Swagger UI (not documented in API)."""
    return redirect("/apidocs/")


@app.route("/info")
def info():
    """Service info endpoint.
    ---
    tags:
      - Demo
    summary: Service information
    description: Returns service information including version, build info, and a trace ID for verification in New Relic.
    responses:
      200:
        description: Service information with trace ID
        schema:
          type: object
          properties:
            service:
              type: string
              example: otel-demo
            version:
              type: string
              example: "1.0.42"
            build_number:
              type: string
              example: "42"
            build_date:
              type: string
              example: "2026-01-13T18:00:00Z"
            message:
              type: string
              example: "OpenTelemetry Demo App - Traces flowing to New Relic!"
            trace_id:
              type: string
              example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret
            new_relic_url:
              type: string
              example: "https://one.newrelic.com/distributed-tracing?query=trace.id%3D..."
    """
    with tracer.start_as_current_span("index-handler") as span:
        span.set_attribute("http.custom_attribute", "index_page")
        span.set_attribute("app.version", os.getenv("APP_VERSION", "dev"))
        span.set_attribute("app.build_number", os.getenv("BUILD_NUMBER", "0"))
        logger.info("Handling index request")

        trace_id = format(span.get_span_context().trace_id, "032x")

        return jsonify(
            {
                "service": "otel-demo",
                "version": os.getenv("APP_VERSION", "dev"),
                "build_number": os.getenv("BUILD_NUMBER", "0"),
                "build_date": os.getenv("BUILD_DATE", "unknown"),
                "message": "OpenTelemetry Demo App - Traces flowing to New Relic!",
                "trace_id": trace_id,
                "new_relic_url": f"https://one.newrelic.com/distributed-tracing?query=trace.id%3D{trace_id}",
            }
        )


@app.route("/chain")
def chain():
    """Nested spans demonstration.
    ---
    tags:
      - Demo
    summary: Chain operation with nested spans
    description: |
      Demonstrates nested spans with simulated work across three steps:
      1. Database query (PostgreSQL)
      2. Cache lookup (Redis)
      3. External API call

      Each step creates a child span with relevant attributes.
    responses:
      200:
        description: Chain operation completed successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: "chain complete"
            steps:
              type: array
              items:
                type: string
              example: ["db_query", "cache_check", "api_call"]
            trace_id:
              type: string
              example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret
    """
    with tracer.start_as_current_span("chain-handler") as parent:
        parent.set_attribute("chain.steps", 3)
        logger.info("Starting chain operation")

        results = []

        with tracer.start_as_current_span("step-1-database") as span:
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.operation", "SELECT")
            time.sleep(random.uniform(0.01, 0.05))  # Simulate DB query
            logger.info("Step 1: Database query completed")
            results.append("db_query")

        with tracer.start_as_current_span("step-2-cache") as span:
            span.set_attribute("cache.system", "redis")
            span.set_attribute("cache.hit", random.choice([True, False]))
            time.sleep(random.uniform(0.005, 0.02))  # Simulate cache lookup
            logger.info("Step 2: Cache lookup completed")
            results.append("cache_check")

        with tracer.start_as_current_span("step-3-external-api") as span:
            span.set_attribute("http.method", "GET")
            span.set_attribute("http.url", "https://api.example.com/data")
            time.sleep(random.uniform(0.02, 0.1))  # Simulate API call
            logger.info("Step 3: External API call completed")
            results.append("api_call")

        return jsonify(
            {
                "status": "chain complete",
                "steps": results,
                "trace_id": format(parent.get_span_context().trace_id, "032x"),
            }
        )


@app.route("/error")
def error_endpoint():
    """Error recording demonstration.
    ---
    tags:
      - Demo
    summary: Simulated error endpoint
    description: |
      Demonstrates how errors are recorded in OpenTelemetry traces.
      This endpoint intentionally raises an exception to show error handling.
    responses:
      500:
        description: Simulated error response
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "Simulated error for tracing demo"
            trace_id:
              type: string
              example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret
    """
    with tracer.start_as_current_span("error-handler") as span:
        try:
            span.set_attribute("error.simulated", True)
            logger.warning("About to simulate an error")
            raise ValueError("Simulated error for tracing demo")
        except ValueError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logger.error(f"Caught simulated error: {e}")
            return jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            ), 500


@app.route("/slow")
def slow_endpoint():
    """Slow operation demonstration.
    ---
    tags:
      - Demo
    summary: Slow operation for performance analysis
    description: |
      Demonstrates a slow operation with a random delay between 0.5 and 2.0 seconds.
      Useful for testing latency monitoring and performance analysis in traces.
    responses:
      200:
        description: Slow operation completed
        schema:
          type: object
          properties:
            status:
              type: string
              example: complete
            delay_seconds:
              type: number
              format: float
              example: 1.23
            trace_id:
              type: string
              example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret
    """
    with tracer.start_as_current_span("slow-handler") as span:
        delay = random.uniform(0.5, 2.0)
        span.set_attribute("delay.seconds", delay)
        logger.info(f"Starting slow operation with {delay:.2f}s delay")

        time.sleep(delay)

        logger.info("Slow operation completed")
        return jsonify(
            {
                "status": "complete",
                "delay_seconds": round(delay, 2),
                "trace_id": format(span.get_span_context().trace_id, "032x"),
            }
        )


@app.route("/metrics")
def metrics_info():
    """Observability configuration info.
    ---
    tags:
      - Observability
    summary: Get observability configuration
    description: Returns the current OpenTelemetry configuration and available endpoints.
    responses:
      200:
        description: Observability configuration
        schema:
          type: object
          properties:
            otel_endpoint:
              type: string
              example: "localhost:4317"
            service_name:
              type: string
              example: "otel-demo"
            service_namespace:
              type: string
              example: "otel-demo"
            environment:
              type: string
              example: "homelab"
            version:
              type: string
              example: "1.0.0"
            endpoints:
              type: object
              additionalProperties:
                type: string
    """
    return jsonify(
        {
            "otel_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "not configured"),
            "service_name": os.getenv("OTEL_SERVICE_NAME", "otel-demo"),
            "service_namespace": os.getenv("OTEL_SERVICE_NAMESPACE", "otel-demo"),
            "environment": os.getenv("OTEL_ENVIRONMENT", "homelab"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "endpoints": {
                "/": "Redirect to Swagger UI",
                "/info": "Service info with trace ID",
                "/health": "Health check (no tracing)",
                "/ready": "Readiness check",
                "/chain": "Nested spans demo (3 steps)",
                "/error": "Error recording demo",
                "/slow": "Slow operation demo (0.5-2s)",
                "/metrics": "This endpoint",
                "/files": "List files in NFS storage",
                "/files/<path>": "Read/write/delete files (GET/POST/DELETE)",
                "/apidocs": "Swagger UI documentation",
                "/apispec.json": "OpenAPI specification",
            },
        }
    )


# =============================================================================
# File Storage Endpoints (NFS)
# =============================================================================

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))


def get_safe_path(filepath: str) -> Path | None:
    """Validate and return safe path within DATA_DIR, or None if invalid."""
    try:
        # Normalize and resolve the path
        target = (DATA_DIR / filepath).resolve()
        # Ensure it's within DATA_DIR (prevent path traversal)
        if DATA_DIR.resolve() in target.parents or target == DATA_DIR.resolve():
            return target
        return None
    except (ValueError, OSError):
        return None


@app.route("/files", methods=["GET"])
@app.route("/files/", methods=["GET"])
@app.route("/files/<path:filepath>", methods=["GET"])
def get_files(filepath: str = ""):
    """List files or read file content.
    ---
    tags:
      - Files
    summary: List directory or read file
    description: |
      If path is a directory, returns a list of files and subdirectories.
      If path is a file, returns the file content.
      Supports nested paths like `/files/subdir/file.txt`.
    parameters:
      - name: filepath
        in: path
        type: string
        required: false
        description: Path to file or directory (relative to storage root)
        default: ""
    responses:
      200:
        description: Directory listing or file content
        schema:
          type: object
          properties:
            path:
              type: string
              example: "subdir"
            type:
              type: string
              enum: [directory, file]
              example: directory
            items:
              type: array
              description: Only present for directories
              items:
                type: object
                properties:
                  name:
                    type: string
                  type:
                    type: string
                    enum: [file, directory]
                  size:
                    type: integer
            content:
              type: string
              description: Only present for files
            size:
              type: integer
              description: File size in bytes (only for files)
            trace_id:
              type: string
      404:
        description: Path not found
      400:
        description: Invalid path (path traversal attempt)
    """
    with tracer.start_as_current_span("files-get") as span:
        span.set_attribute("file.path", filepath or "/")

        # Handle root directory
        if not filepath:
            target = DATA_DIR
        else:
            safe_path = get_safe_path(filepath)
            if safe_path is None:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
                return jsonify({"error": "Invalid path", "path": filepath}), 400
            target = safe_path

        if not target.exists():
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Not found"))
            return jsonify({"error": "Path not found", "path": filepath}), 404

        trace_id = format(span.get_span_context().trace_id, "032x")

        if target.is_dir():
            span.set_attribute("file.type", "directory")
            items: list[dict[str, str | int]] = []
            for item in sorted(target.iterdir()):
                item_info: dict[str, str | int] = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_file():
                    item_info["size"] = item.stat().st_size
                items.append(item_info)

            span.set_attribute("file.item_count", len(items))
            logger.info(f"Listed directory: {filepath or '/'} ({len(items)} items)")

            return jsonify(
                {
                    "path": filepath or "/",
                    "type": "directory",
                    "items": items,
                    "trace_id": trace_id,
                }
            )
        else:
            span.set_attribute("file.type", "file")
            span.set_attribute("file.size", target.stat().st_size)
            content = target.read_text()
            logger.info(f"Read file: {filepath} ({len(content)} bytes)")

            return jsonify(
                {
                    "path": filepath,
                    "type": "file",
                    "content": content,
                    "size": len(content),
                    "trace_id": trace_id,
                }
            )


@app.route("/files/<path:filepath>", methods=["POST", "PUT"])
def write_file(filepath: str):
    """Write content to a file.
    ---
    tags:
      - Files
    summary: Create or update a file
    description: |
      Writes content to a file. Creates parent directories if they don't exist.
      Content should be sent as the request body (text/plain or application/json with "content" field).
    parameters:
      - name: filepath
        in: path
        type: string
        required: true
        description: Path to the file (relative to storage root)
      - name: body
        in: body
        required: true
        description: File content (plain text or JSON with "content" field)
        schema:
          type: object
          properties:
            content:
              type: string
              example: "Hello, World!"
    responses:
      201:
        description: File created
        schema:
          type: object
          properties:
            status:
              type: string
              example: created
            path:
              type: string
            size:
              type: integer
            trace_id:
              type: string
      200:
        description: File updated
        schema:
          type: object
          properties:
            status:
              type: string
              example: updated
            path:
              type: string
            size:
              type: integer
            trace_id:
              type: string
      400:
        description: Invalid path or missing content
    """
    with tracer.start_as_current_span("files-write") as span:
        span.set_attribute("file.path", filepath)

        target = get_safe_path(filepath)
        if target is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": filepath}), 400

        # Get content from request
        if request.is_json:
            data = request.get_json()
            content = data.get("content", "")
        else:
            content = request.get_data(as_text=True)

        if not content and content != "":
            span.set_status(trace.Status(trace.StatusCode.ERROR, "No content"))
            return jsonify({"error": "No content provided"}), 400

        # Check if file exists (for status code)
        existed = target.exists()

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        target.write_text(content)
        span.set_attribute("file.size", len(content))
        span.set_attribute("file.created", not existed)

        status = "updated" if existed else "created"
        status_code = 200 if existed else 201
        logger.info(f"File {status}: {filepath} ({len(content)} bytes)")

        return jsonify(
            {
                "status": status,
                "path": filepath,
                "size": len(content),
                "trace_id": format(span.get_span_context().trace_id, "032x"),
            }
        ), status_code


@app.route("/files/<path:filepath>", methods=["DELETE"])
def delete_file(filepath: str):
    """Delete a file or empty directory.
    ---
    tags:
      - Files
    summary: Delete a file or empty directory
    description: |
      Deletes a file or an empty directory.
      Non-empty directories cannot be deleted (returns 400).
    parameters:
      - name: filepath
        in: path
        type: string
        required: true
        description: Path to the file or directory to delete
    responses:
      200:
        description: File or directory deleted
        schema:
          type: object
          properties:
            status:
              type: string
              example: deleted
            path:
              type: string
            type:
              type: string
              enum: [file, directory]
            trace_id:
              type: string
      404:
        description: Path not found
      400:
        description: Invalid path or directory not empty
    """
    with tracer.start_as_current_span("files-delete") as span:
        span.set_attribute("file.path", filepath)

        target = get_safe_path(filepath)
        if target is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": filepath}), 400

        if not target.exists():
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Not found"))
            return jsonify({"error": "Path not found", "path": filepath}), 404

        trace_id = format(span.get_span_context().trace_id, "032x")

        if target.is_dir():
            # Check if directory is empty
            if any(target.iterdir()):
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Not empty"))
                return jsonify({"error": "Directory not empty", "path": filepath}), 400
            target.rmdir()
            file_type = "directory"
        else:
            target.unlink()
            file_type = "file"

        span.set_attribute("file.type", file_type)
        logger.info(f"Deleted {file_type}: {filepath}")

        return jsonify(
            {
                "status": "deleted",
                "path": filepath,
                "type": file_type,
                "trace_id": trace_id,
            }
        )


@app.route("/files", methods=["POST"])
def create_directory():
    """Create a new directory.
    ---
    tags:
      - Files
    summary: Create a directory
    description: Creates a new directory. Parent directories are created if needed.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - path
          properties:
            path:
              type: string
              description: Directory path to create
              example: "subdir/newdir"
    responses:
      201:
        description: Directory created
        schema:
          type: object
          properties:
            status:
              type: string
              example: created
            path:
              type: string
            type:
              type: string
              example: directory
            trace_id:
              type: string
      200:
        description: Directory already exists
      400:
        description: Invalid path or missing path parameter
    """
    with tracer.start_as_current_span("files-mkdir") as span:
        if not request.is_json:
            return jsonify({"error": "JSON body required"}), 400

        data = request.get_json()
        dirpath = data.get("path", "")

        if not dirpath:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "No path"))
            return jsonify({"error": "Path is required"}), 400

        span.set_attribute("file.path", dirpath)

        target = get_safe_path(dirpath)
        if target is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": dirpath}), 400

        trace_id = format(span.get_span_context().trace_id, "032x")

        if target.exists():
            if target.is_dir():
                return jsonify(
                    {
                        "status": "exists",
                        "path": dirpath,
                        "type": "directory",
                        "trace_id": trace_id,
                    }
                )
            else:
                return jsonify({"error": "Path exists as file", "path": dirpath}), 400

        target.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dirpath}")

        return jsonify(
            {
                "status": "created",
                "path": dirpath,
                "type": "directory",
                "trace_id": trace_id,
            }
        ), 201


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting otel-demo on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
