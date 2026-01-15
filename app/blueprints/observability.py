"""
Observability configuration endpoints.

Provides endpoints for viewing OTel configuration and available endpoints.
"""

import os

from flask import Blueprint, current_app, jsonify

observability_bp = Blueprint("observability", __name__)


@observability_bp.route("/metrics")
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
    config = current_app.config.get("APP_CONFIG")

    if config:
        otel_endpoint = config.otel_endpoint
        service_name = config.service_name
        service_namespace = config.service_namespace
        environment = config.environment
        version = config.app_version
    else:
        otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "not configured")
        service_name = os.getenv("OTEL_SERVICE_NAME", "otel-demo")
        service_namespace = os.getenv("OTEL_SERVICE_NAMESPACE", "otel-demo")
        environment = os.getenv("OTEL_ENVIRONMENT", "homelab")
        version = os.getenv("APP_VERSION", "1.0.0")

    return jsonify(
        {
            "otel_endpoint": otel_endpoint,
            "service_name": service_name,
            "service_namespace": service_namespace,
            "environment": environment,
            "version": version,
            "endpoints": {
                "/": "Redirect to Swagger UI",
                "/info": "Service info with trace ID",
                "/health": "Health check (no tracing)",
                "/ready": "Readiness check",
                "/chain": "Nested spans demo (3 steps)",
                "/error": "Error recording demo",
                "/slow": "Slow operation demo (0.5-2s)",
                "/metrics": "This endpoint",
                "/db/status": "Database connection status",
                "/db/locations": "Query owntracks locations",
                "/files": "List files in NFS storage",
                "/files/<path>": "Read/write/delete files (GET/POST/DELETE)",
                "/apidocs": "Swagger UI documentation",
                "/apispec.json": "OpenAPI specification",
            },
        }
    )
