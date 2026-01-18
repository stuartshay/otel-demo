#!/usr/bin/env python3
"""
Generate OpenAPI specification from Flask app code.

This script is designed for CI/CD pipelines to generate the OpenAPI spec
without starting a real HTTP server. It imports the Flask app, initializes
it using test configuration, and uses Flask's test client to request the
/apispec.json endpoint.

OpenTelemetry is disabled via environment variables to prevent slow or flaky
collector connection attempts, keeping spec generation fast and deterministic
in automated environments.
"""

import json
import os
import sys
from pathlib import Path

# Disable OpenTelemetry exports to avoid slow collector connection attempts
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402


def generate_spec():
    """Generate OpenAPI spec from Flask app."""
    # Create app with default config (no actual server needed)
    config = Config()
    app = create_app(config)

    # Make a test request to the apispec endpoint to generate the spec
    with app.test_client() as client:
        response = client.get("/apispec.json")
        if response.status_code == 200:
            return response.get_json()
        else:
            error_msg = f"Failed to get spec from /apispec.json: HTTP {response.status_code}"
            if response.data:
                error_msg += f"\nResponse: {response.data.decode('utf-8')[:200]}"
            raise RuntimeError(error_msg)


if __name__ == "__main__":
    try:
        spec = generate_spec()
        # Output to stdout
        print(json.dumps(spec, indent=2))
    except Exception as e:
        print(f"Error generating spec: {e}", file=sys.stderr)
        sys.exit(1)
