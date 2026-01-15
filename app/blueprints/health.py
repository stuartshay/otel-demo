"""
Health check endpoints for Kubernetes probes.

Provides /health (liveness) and /ready (readiness) endpoints
that don't require tracing overhead.
"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
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


@health_bp.route("/ready")
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
