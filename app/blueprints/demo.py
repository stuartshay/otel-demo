"""
OpenTelemetry demonstration endpoints.

Provides endpoints that demonstrate various OTel tracing features:
- Service info with trace IDs
- Nested spans
- Error recording
- Slow operations
"""

import logging
import os
import random
import time

from flask import Blueprint, current_app, jsonify, redirect
from opentelemetry import trace

demo_bp = Blueprint("demo", __name__)
logger = logging.getLogger(__name__)


def get_tracer() -> trace.Tracer:
    """Get the tracer from the current app context."""
    return current_app.config.get("TRACER") or trace.get_tracer(__name__)


@demo_bp.route("/")
def index():
    """Redirect to Swagger UI (not documented in API)."""
    return redirect("/apidocs/")


@demo_bp.route("/info")
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
    tracer = get_tracer()
    with tracer.start_as_current_span("index-handler") as span:
        config = current_app.config.get("APP_CONFIG")
        version = config.app_version if config else os.getenv("APP_VERSION", "dev")
        build_number = config.build_number if config else os.getenv("BUILD_NUMBER", "0")
        build_date = config.build_date if config else os.getenv("BUILD_DATE", "unknown")

        span.set_attribute("http.custom_attribute", "index_page")
        span.set_attribute("app.version", version)
        span.set_attribute("app.build_number", build_number)
        logger.info("Handling index request")

        trace_id = format(span.get_span_context().trace_id, "032x")

        return jsonify(
            {
                "service": "otel-demo",
                "version": version,
                "build_number": build_number,
                "build_date": build_date,
                "message": "OpenTelemetry Demo App - Traces flowing to New Relic!",
                "trace_id": trace_id,
                "new_relic_url": f"https://one.newrelic.com/distributed-tracing?query=trace.id%3D{trace_id}",
            }
        )


@demo_bp.route("/chain")
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
    tracer = get_tracer()
    with tracer.start_as_current_span("chain-handler") as parent:
        parent.set_attribute("chain.steps", 3)
        logger.info("Starting chain operation")

        results = []

        with tracer.start_as_current_span("step-1-database") as span:
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.operation", "SELECT")
            time.sleep(random.uniform(0.01, 0.05))
            logger.info("Step 1: Database query completed")
            results.append("db_query")

        with tracer.start_as_current_span("step-2-cache") as span:
            span.set_attribute("cache.system", "redis")
            span.set_attribute("cache.hit", random.choice([True, False]))
            time.sleep(random.uniform(0.005, 0.02))
            logger.info("Step 2: Cache lookup completed")
            results.append("cache_check")

        with tracer.start_as_current_span("step-3-external-api") as span:
            span.set_attribute("http.method", "GET")
            span.set_attribute("http.url", "https://api.example.com/data")
            time.sleep(random.uniform(0.02, 0.1))
            logger.info("Step 3: External API call completed")
            results.append("api_call")

        return jsonify(
            {
                "status": "chain complete",
                "steps": results,
                "trace_id": format(parent.get_span_context().trace_id, "032x"),
            }
        )


@demo_bp.route("/error")
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
    tracer = get_tracer()
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


@demo_bp.route("/slow")
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
    tracer = get_tracer()
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
