"""
Flask extensions initialization.

Centralizes the setup of Flask extensions including:
- Swagger/OpenAPI documentation
- Flask instrumentation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flasgger import Swagger
from opentelemetry.instrumentation.flask import FlaskInstrumentor

if TYPE_CHECKING:
    from flask import Flask

    from app.config import Config


def init_extensions(flask_app: Flask, config: Config) -> None:
    """Initialize all Flask extensions.

    Args:
        flask_app: Flask application instance.
        config: Application configuration.
    """
    # Instrument Flask for tracing
    FlaskInstrumentor().instrument_app(flask_app)

    # Initialize Swagger documentation
    _init_swagger(flask_app, config)


def _init_swagger(flask_app: Flask, config: Config) -> Swagger:
    """Initialize Swagger/OpenAPI documentation.

    Args:
        flask_app: Flask application instance.
        config: Application configuration.

    Returns:
        Configured Swagger instance.
    """
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
            "version": config.app_version,
            "contact": {
                "name": "Stuart Shay",
                "url": "https://github.com/stuartshay/otel-demo",
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT",
            },
        },
        "host": config.swagger_host,
        "basePath": "/",
        "schemes": list(config.swagger_schemes),
        "tags": [
            {"name": "Health", "description": "Health and readiness endpoints"},
            {"name": "Demo", "description": "OpenTelemetry demonstration endpoints"},
            {"name": "Database", "description": "PostgreSQL database operations"},
            {"name": "Files", "description": "NFS storage file operations"},
            {"name": "Observability", "description": "Observability configuration"},
        ],
    }

    # Add OAuth2 security definitions if enabled
    if config.oauth2_enabled and config.cognito_domain and config.cognito_client_id:
        swagger_template["securityDefinitions"] = {
            "oauth2": {
                "type": "oauth2",
                "flow": "accessCode",
                "authorizationUrl": f"{config.cognito_domain}/oauth2/authorize",
                "tokenUrl": f"{config.cognito_domain}/oauth2/token",
                "scopes": {
                    "openid": "OpenID Connect scope",
                    "email": "Access email address",
                    "profile": "Access user profile",
                },
            },
            "bearerAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Bearer token (e.g., 'Bearer eyJ...')",
            },
        }
        # Apply security globally; individual endpoints can override (e.g., health via security=[])
        swagger_template["security"] = [{"oauth2": ["openid", "email", "profile"]}]

    return Swagger(flask_app, config=swagger_config, template=swagger_template)
