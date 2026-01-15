"""Blueprints package for Flask route handlers."""

from app.blueprints.database import database_bp
from app.blueprints.demo import demo_bp
from app.blueprints.files import files_bp
from app.blueprints.health import health_bp
from app.blueprints.observability import observability_bp

__all__ = [
    "health_bp",
    "demo_bp",
    "observability_bp",
    "database_bp",
    "files_bp",
]
