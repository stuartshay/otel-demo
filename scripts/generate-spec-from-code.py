#!/usr/bin/env python3
"""
Generate OpenAPI specification from Flask app code.
This runs the Flask app in spec-generation mode without starting the server.
"""

import json
import os
import sys
from pathlib import Path

# Disable OpenTelemetry to avoid slow collector connection attempts
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402


def generate_spec():
    """Generate OpenAPI spec from Flask app."""
    # Create app with test config (no actual server needed)
    config = Config()
    app = create_app(config)

    # Make a test request to the apispec endpoint to generate the spec
    with app.test_client() as client:
        response = client.get("/apispec.json")
        if response.status_code == 200:
            return response.get_json()
        else:
            raise RuntimeError(f"Failed to get spec: HTTP {response.status_code}")


if __name__ == "__main__":
    try:
        spec = generate_spec()
        # Output to stdout
        print(json.dumps(spec, indent=2))
    except Exception as e:
        print(f"Error generating spec: {e}", file=sys.stderr)
        sys.exit(1)
