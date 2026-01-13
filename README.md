# OTel Demo

[![CI](https://github.com/stuartshay/otel-demo/actions/workflows/lint.yml/badge.svg)](https://github.com/stuartshay/otel-demo/actions/workflows/lint.yml)
[![Docker](https://github.com/stuartshay/otel-demo/actions/workflows/docker.yml/badge.svg)](https://github.com/stuartshay/otel-demo/actions/workflows/docker.yml)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-stuartshay%2Fotel--demo-blue?logo=docker)](https://hub.docker.com/repository/docker/stuartshay/otel-demo)
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

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Service info with trace ID and New Relic link |
| `/health` | Health check (no tracing) |
| `/ready` | Readiness check |
| `/chain` | Nested spans demo (3 simulated steps) |
| `/error` | Error recording demo |
| `/slow` | Slow operation demo (0.5-2s delay) |
| `/metrics` | Observability configuration info |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `localhost:4317` | OTel Collector gRPC endpoint |
| `OTEL_SERVICE_NAME` | `otel-demo` | Service name in traces |
| `OTEL_SERVICE_NAMESPACE` | `otel-demo` | Service namespace |
| `OTEL_ENVIRONMENT` | `homelab` | Deployment environment |
| `APP_VERSION` | `1.0.0` | Application version |
| `PORT` | `8080` | HTTP server port |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings (traces to localhost:4317)
python app.py

# Or with custom OTel endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317 python app.py
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

```
https://one.newrelic.com/distributed-tracing
```

Filter by:
- `service.name = otel-demo`
- `service.namespace = otel-demo`

## License

MIT
