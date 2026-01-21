"""
OTel Demo App - Flask application with OpenTelemetry instrumentation.

This package provides a modular Flask application demonstrating:
- Automatic Flask instrumentation
- Custom spans and attributes
- Trace context propagation
- Logging with trace correlation
- Swagger/OpenAPI documentation
"""

from flask import Flask

from app.config import Config
from app.extensions import init_extensions
from app.telemetry import configure_logging, configure_opentelemetry

__all__ = ["create_app", "Config"]


def create_app(config: Config | None = None) -> Flask:
    """Application factory for creating Flask app instances.

    Args:
        config: Optional configuration object. If not provided,
                configuration is loaded from environment variables.

    Returns:
        Configured Flask application instance.
    """
    if config is None:
        config = Config.from_env()

    # Configure OpenTelemetry before creating app
    tracer = configure_opentelemetry(config)
    configure_logging()

    # Create Flask app
    flask_app = Flask(__name__)
    flask_app.config["APP_CONFIG"] = config
    flask_app.config["TRACER"] = tracer

    # Initialize extensions (Swagger, Flask instrumentation)
    init_extensions(flask_app, config)

    # Register blueprints
    _register_blueprints(flask_app)

    # Note: Database connection pool cleanup is handled during app shutdown,
    # not on every request teardown, to maintain connection pooling benefits.
    # A teardown handler is intentionally not registered here, because closing
    # the pool after every request would defeat the purpose of connection
    # pooling. The pool is automatically closed when the application shuts down.

    # Register shutdown handler for pool cleanup
    @flask_app.teardown_appcontext
    def shutdown_db_pool(exception: BaseException | None) -> None:
        """Close database pool on application shutdown.

        This is called when the application context is torn down,
        which happens at the end of a request normally, but we need
        to ensure it's only called on actual app shutdown, not per-request.
        """
        # Only close pool if we're truly shutting down
        # In production with gunicorn, this happens on worker shutdown
        if flask_app.config.get("TESTING") or not flask_app.debug:
            from app.services.database import close_db_service

            close_db_service()

    return flask_app


def _register_blueprints(flask_app: Flask) -> None:
    """Register all application blueprints."""
    from app.blueprints.database import database_bp
    from app.blueprints.demo import demo_bp
    from app.blueprints.files import files_bp
    from app.blueprints.health import health_bp
    from app.blueprints.observability import observability_bp

    flask_app.register_blueprint(health_bp)
    flask_app.register_blueprint(demo_bp)
    flask_app.register_blueprint(observability_bp)
    flask_app.register_blueprint(database_bp)
    flask_app.register_blueprint(files_bp)
