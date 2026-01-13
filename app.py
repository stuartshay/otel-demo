"""
OpenTelemetry Demo App - Flask application with OTel instrumentation.

This app demonstrates:
- Automatic Flask instrumentation
- Custom spans and attributes
- Trace context propagation
- Logging with trace correlation
"""

import logging
import os
import random
import time

from flask import Flask, jsonify
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
    """Health check endpoint (no tracing)."""
    return jsonify({"status": "healthy"})


@app.route("/ready")
def ready():
    """Readiness check endpoint."""
    return jsonify({"status": "ready"})


@app.route("/")
def index():
    """Main endpoint - returns service info with trace ID."""
    with tracer.start_as_current_span("index-handler") as span:
        span.set_attribute("http.custom_attribute", "index_page")
        logger.info("Handling index request")

        trace_id = format(span.get_span_context().trace_id, "032x")

        return jsonify(
            {
                "service": "otel-demo",
                "version": os.getenv("APP_VERSION", "1.0.0"),
                "message": "OpenTelemetry Demo App - Traces flowing to New Relic!",
                "trace_id": trace_id,
                "new_relic_url": f"https://one.newrelic.com/distributed-tracing?query=trace.id%3D{trace_id}",
            }
        )


@app.route("/chain")
def chain():
    """Demonstrates nested spans with simulated work."""
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
    """Demonstrates error recording in traces."""
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
    """Demonstrates a slow operation for performance analysis."""
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
    """Returns info about the app's observability configuration."""
    return jsonify(
        {
            "otel_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "not configured"),
            "service_name": os.getenv("OTEL_SERVICE_NAME", "otel-demo"),
            "service_namespace": os.getenv("OTEL_SERVICE_NAMESPACE", "otel-demo"),
            "environment": os.getenv("OTEL_ENVIRONMENT", "homelab"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "endpoints": {
                "/": "Service info with trace ID",
                "/health": "Health check (no tracing)",
                "/ready": "Readiness check",
                "/chain": "Nested spans demo (3 steps)",
                "/error": "Error recording demo",
                "/slow": "Slow operation demo (0.5-2s)",
                "/metrics": "This endpoint",
            },
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting otel-demo on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
