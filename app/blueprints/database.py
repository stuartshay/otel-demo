"""
Database endpoints for PostgreSQL operations.

Provides endpoints for database health checks and querying
the owntracks locations table.
"""

import logging

from flask import Blueprint, current_app, jsonify, request
from opentelemetry import trace

from app.services.database import DatabaseService, get_db_service, init_db_service

database_bp = Blueprint("database", __name__, url_prefix="/db")
logger = logging.getLogger(__name__)


def get_tracer() -> trace.Tracer:
    """Get the tracer from the current app context."""
    return current_app.config.get("TRACER") or trace.get_tracer(__name__)


def _get_or_init_db_service() -> DatabaseService:
    """Get database service, initializing if needed."""
    try:
        return get_db_service()
    except RuntimeError:
        # Service not initialized, try to initialize it
        config = current_app.config.get("APP_CONFIG")
        if config:
            return init_db_service(config)
        raise


@database_bp.route("/status")
def db_status():
    """Database connection status.
    ---
    tags:
      - Database
    summary: Check database connection
    description: Tests the connection to PostgreSQL via PgBouncer and returns connection info.
    responses:
      200:
        description: Database connection successful
        schema:
          type: object
          properties:
            status:
              type: string
              example: connected
            database:
              type: string
              example: owntracks
            host:
              type: string
              example: "192.168.1.175"
            port:
              type: integer
              example: 6432
            server_version:
              type: string
              example: "140005"
            trace_id:
              type: string
      500:
        description: Database connection failed
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("db-status") as span:
        try:
            db_service = _get_or_init_db_service()
            result = db_service.health_check()

            span.set_attribute("db.connected", True)
            span.set_attribute("db.system", "postgresql")

            result["trace_id"] = format(span.get_span_context().trace_id, "032x")
            return jsonify(result)

        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Database connection failed"))
            logger.error(f"Database connection failed: {e}", exc_info=True)
            return jsonify(
                {
                    "status": "error",
                    "error": "Database connection failed. Please try again later.",
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            ), 500


@database_bp.route("/locations")
def db_locations():
    """Query owntracks locations.
    ---
    tags:
      - Database
    summary: Get location records from owntracks
    description: |
      Retrieves location records from the owntracks.locations table.
      Supports pagination, sorting, and filtering by device_id.
    parameters:
      - name: limit
        in: query
        type: integer
        default: 20
        description: Maximum number of records to return (max 100)
        example: 10
      - name: offset
        in: query
        type: integer
        default: 0
        description: Number of records to skip for pagination
        example: 0
      - name: sort
        in: query
        type: string
        default: created_at
        description: Column to sort by
        enum: [created_at, latitude, longitude, accuracy, altitude, velocity, battery]
        example: created_at
      - name: order
        in: query
        type: string
        default: desc
        description: Sort order
        enum: [asc, desc]
        example: desc
      - name: device_id
        in: query
        type: string
        required: false
        description: Filter by device identifier
        example: "iphone"
    responses:
      200:
        description: Location records
        schema:
          type: object
          properties:
            count:
              type: integer
              example: 10
            limit:
              type: integer
              example: 20
            offset:
              type: integer
              example: 0
            sort:
              type: string
              example: created_at
            order:
              type: string
              example: desc
            locations:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  device_id:
                    type: string
                    description: Device identifier
                  tid:
                    type: string
                    description: Tracker ID
                  latitude:
                    type: number
                    format: float
                  longitude:
                    type: number
                    format: float
                  accuracy:
                    type: integer
                    description: Accuracy in meters
                  altitude:
                    type: integer
                    description: Altitude in meters
                  velocity:
                    type: integer
                    description: Velocity in km/h
                  battery:
                    type: integer
                    description: Battery percentage
                  created_at:
                    type: string
                    format: datetime
            trace_id:
              type: string
      400:
        description: Invalid parameters
      500:
        description: Database query failed
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("db-locations") as span:
        try:
            # Parse and validate parameters
            limit_raw = request.args.get("limit", "20")
            offset_raw = request.args.get("offset", "0")

            try:
                limit = min(int(limit_raw), 100)
                offset = int(offset_raw)
                if limit < 0 or offset < 0:
                    raise ValueError("Negative values not allowed")
            except ValueError:
                error_msg = "Invalid limit or offset parameter; expected non-negative integers."
                span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                return jsonify(
                    {
                        "status": "error",
                        "error": error_msg,
                        "trace_id": format(span.get_span_context().trace_id, "032x"),
                    }
                ), 400

            sort = request.args.get("sort", "created_at")
            order = request.args.get("order", "desc").upper()
            device_id = request.args.get("device_id")

            span.set_attribute("db.limit", limit)
            span.set_attribute("db.offset", offset)
            span.set_attribute("db.sort", sort)
            span.set_attribute("db.order", order)
            if device_id:
                span.set_attribute("db.device_id", device_id)

            db_service = _get_or_init_db_service()
            locations = db_service.get_locations(
                limit=limit,
                offset=offset,
                sort=sort,
                order=order,
                device_id=device_id,
            )

            span.set_attribute("db.result_count", len(locations))
            logger.info(f"Retrieved {len(locations)} location records")

            return jsonify(
                {
                    "count": len(locations),
                    "limit": limit,
                    "offset": offset,
                    "sort": sort,
                    "order": order.lower(),
                    "locations": [loc.to_dict() for loc in locations],
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            )

        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Database query failed"))
            logger.error(f"Database query failed: {e}", exc_info=True)

            # Check if it's a table not found error
            error_msg = str(e)
            if "relation" in error_msg and "does not exist" in error_msg:
                app_config = current_app.config.get("APP_CONFIG")
                db_name = app_config.db_name if app_config else "unknown"
                return jsonify(
                    {
                        "status": "error",
                        "error": "The 'locations' table does not exist in this database. This endpoint requires an owntracks database schema.",
                        "database": db_name,
                        "trace_id": format(span.get_span_context().trace_id, "032x"),
                    }
                ), 404

            return jsonify(
                {
                    "status": "error",
                    "error": "Internal server error while querying locations.",
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            ), 500
