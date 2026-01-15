"""
OpenTelemetry Demo App - Flask application with OTel instrumentation.

This is the application entrypoint that uses the app factory pattern.
The modular application code is organized in the `app` package.

This app demonstrates:
- Automatic Flask instrumentation
- Custom spans and attributes
- Trace context propagation
- Logging with trace correlation
- Swagger/OpenAPI documentation
- Database connection pooling
- Modular enterprise architecture
"""

import logging
import os

from app import create_app
from app.config import Config

# Create application with configuration from environment
config = Config.from_env()
app = create_app(config)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting otel-demo on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
