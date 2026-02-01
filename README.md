# OTel Demo

[![CI](https://github.com/stuartshay/otel-demo/actions/workflows/lint.yml/badge.svg)](https://github.com/stuartshay/otel-demo/actions/workflows/lint.yml)
[![Docker](https://github.com/stuartshay/otel-demo/actions/workflows/docker.yml/badge.svg)](https://github.com/stuartshay/otel-demo/actions/workflows/docker.yml)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-stuartshay%2Fotel--demo-blue?logo=docker)](https://hub.docker.com/repository/docker/stuartshay/otel-demo)
[![npm version](https://img.shields.io/npm/v/@stuartshay/otel-types.svg)](https://www.npmjs.com/package/@stuartshay/otel-types)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OpenTelemetry Demo App - A Python Flask application instrumented with OpenTelemetry for distributed tracing.

## Overview

This demo app is designed to test and validate OpenTelemetry Collector deployments, specifically for the [k8s-gitops](https://github.com/stuartshay/k8s-gitops) homelab cluster with New Relic as the observability backend.

## Features

- **Automatic Flask instrumentation** - HTTP requests are traced automatically
- **Custom spans** - Demonstrates nested spans with simulated work
- **Error recording** - Shows how exceptions are captured in traces
- **Log correlation** - Logs include trace and span IDs
- **Multiple endpoints** - Various demos for different tracing scenarios
- **Swagger/OpenAPI** - Interactive API documentation at `/apidocs`

## Endpoints

| Endpoint | Description |
| -------- | ----------- |
| `/` | Redirect to Swagger UI |
| `/info` | Service info with trace ID and New Relic link |
| `/health` | Health check (no tracing) |
| `/ready` | Readiness check |
| `/chain` | Nested spans demo (3 simulated steps) |
| `/error` | Error recording demo |
| `/slow` | Slow operation demo (0.5-2s delay) |
| `/metrics` | Observability configuration info |
| `/db/status` | Database connection status and info |
| `/db/locations` | Query locations from PostgreSQL (with pagination) |
| `/apidocs` | Swagger UI documentation |
| `/apispec.json` | OpenAPI specification |

## Environment Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `localhost:4317` | OTel Collector gRPC endpoint |
| `OTEL_SERVICE_NAME` | `otel-demo` | Service name in traces |
| `OTEL_SERVICE_NAMESPACE` | `otel-demo` | Service namespace |
| `OTEL_ENVIRONMENT` | `homelab` | Deployment environment |
| `APP_VERSION` | `1.0.0` | Application version |
| `PORT` | `8080` | HTTP server port |
| `POSTGRES_USER` | `development` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `development` | PostgreSQL password |
| `POSTGRES_DB` | `opendata` | PostgreSQL database name |
| `PGBOUNCER_HOST` | `192.168.1.175` | PgBouncer connection pooler host |
| `PGBOUNCER_PORT` | `6432` | PgBouncer port (use for pooled connections) |

## Quick Start

```bash
# Using Makefile (recommended)
make setup          # Set up venv and install dependencies
make start          # Start server (loads .env automatically)
make logs           # View logs
make stop           # Stop server

# Or manually
pip install -r requirements.txt
python run.py       # With .env file for configuration
```

See [Makefile Usage Guide](docs/makefile-guide.md) for all available commands.

## Running Locally

### Using Makefile

```bash
# Start development server
make start          # Starts on port 8080, loads .env

# Check status
make status         # View server PID and endpoints
make health         # Test /health endpoint
make db-status      # Test /db/status endpoint

# View logs
make logs           # Tail logs in real-time

# Stop server
make stop

# Restart after changes
make restart
```

### Manual Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with .env file loaded
source venv/bin/activate
python run.py

# Or with custom OTel endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317 python run.py
```

## Docker

```bash
# Build
docker build -t otel-demo .

# Run
docker run -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=host.docker.internal:4317 \
  otel-demo
```

## Kubernetes Deployment

See the k8s-gitops repo for the full deployment:

- [apps/base/otel-demo/](https://github.com/stuartshay/k8s-gitops/tree/master/apps/base/otel-demo)

## New Relic Integration

Traces are exported via OTLP to the OpenTelemetry Collector, which forwards them to New Relic. View traces at:

```text
https://one.newrelic.com/distributed-tracing
```

Filter by:

- `service.name = otel-demo`
- `service.namespace = otel-demo`

## Versioning

This project uses semantic versioning with dynamic patch versions:

- **VERSION file**: Stores major.minor version (e.g., `1.0`)
- **Build number**: GitHub Actions run number becomes the patch version
- **Result**: Version is calculated as `{major}.{minor}.{build_number}` (e.g., `1.0.104`)

Example:

- VERSION file contains: `1.0`
- GitHub Actions build #104
- Resulting version: `1.0.104`

This ensures every build has a unique, incrementing version number.

## License

MIT
