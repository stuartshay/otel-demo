"""
OpenTelemetry configuration and instrumentation.

Provides centralized setup for:
- TracerProvider configuration
- OTLP exporter setup
- Log correlation with trace/span IDs
- Instrumentation for Flask and psycopg2
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_NAMESPACE, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from app.config import Config

logger = logging.getLogger(__name__)


class TraceIdLogFilter(logging.Filter):
    """Log filter that adds OpenTelemetry trace context to log records.

    Adds `otelTraceID` and `otelSpanID` attributes to each log record,
    enabling correlation between logs and distributed traces.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace context to the log record.

        Args:
            record: The log record to process.

        Returns:
            Always returns True (all records pass through).
        """
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            record.otelTraceID = format(ctx.trace_id, "032x")
            record.otelSpanID = format(ctx.span_id, "016x")
        else:
            record.otelTraceID = "0" * 32
            record.otelSpanID = "0" * 16
        return True


def configure_logging() -> None:
    """Configure logging with trace correlation format.

    Sets up the root logger with a format that includes trace and span IDs,
    and adds the TraceIdLogFilter to all handlers.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s"
        ),
    )

    # Add filter to all handlers
    log_filter = TraceIdLogFilter()
    for handler in logging.root.handlers:
        handler.addFilter(log_filter)


def configure_opentelemetry(config: Config) -> trace.Tracer:
    """Configure OpenTelemetry with OTLP exporter.

    Sets up the TracerProvider with resource attributes and configures
    the OTLP gRPC exporter for sending traces to the collector.

    Args:
        config: Application configuration with OTel settings.

    Returns:
        Configured tracer instance for creating spans.
    """
    resource = Resource.create(
        {
            SERVICE_NAME: config.service_name,
            SERVICE_NAMESPACE: config.service_namespace,
            "deployment.environment": config.environment,
            "service.version": config.app_version,
        }
    )

    provider = TracerProvider(resource=resource)

    logger.info(f"Configuring OTLP exporter to: {config.otel_endpoint}")

    exporter = OTLPSpanExporter(
        endpoint=config.otel_endpoint,
        insecure=True,  # Using cluster-internal communication
    )

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument psycopg2 for database tracing (after tracer provider is set)
    Psycopg2Instrumentor().instrument()

    return trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """Get the current tracer instance.

    Returns:
        The global tracer for the application module.
    """
    return trace.get_tracer(__name__)
