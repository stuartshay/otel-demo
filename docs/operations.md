# OTel Demo Operations Guide

This document covers deployment, testing, and troubleshooting for the
OpenTelemetry demo application.

## Table of Contents

- [Local Development](#local-development)
- [Docker](#docker)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Observability](#observability)

---

## Local Development

### Quick Start

```bash
# Setup environment
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Run application
python app.py

# Test
curl http://localhost:8080/health
```

### Environment Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `localhost:4317` | OTel Collector gRPC endpoint |
| `OTEL_SERVICE_NAME` | `otel-demo` | Service name in traces |
| `OTEL_SERVICE_NAMESPACE` | `otel-demo` | Service namespace |
| `OTEL_ENVIRONMENT` | `homelab` | Deployment environment |
| `APP_VERSION` | `1.0.0` | Application version |
| `PORT` | `8080` | HTTP server port |

### Running with Local OTel Collector

```bash
# Start local collector (Docker)
docker run -d --name otel-collector \
  -p 4317:4317 \
  -p 4318:4318 \
  otel/opentelemetry-collector:latest

# Run app pointing to local collector
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317 python app.py
```

---

## Docker

### Build

```bash
# Build image
docker build -t otel-demo .

# Build with version tag
docker build -t otel-demo:v1.0.0 .

# Build with build args
docker build --build-arg APP_VERSION=v1.0.0 -t otel-demo:v1.0.0 .
```

### Run

```bash
# Basic run
docker run -p 8080:8080 otel-demo

# With OTel collector on host
docker run -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=host.docker.internal:4317 \
  otel-demo

# With custom configuration
docker run -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317 \
  -e OTEL_SERVICE_NAME=my-service \
  -e OTEL_ENVIRONMENT=staging \
  otel-demo
```

### Health Check

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' <container_id>

# View health check logs
docker inspect --format='{{json .State.Health}}' <container_id> | jq
```

---

## Kubernetes Deployment

The application is deployed via GitOps using the
[k8s-gitops](https://github.com/stuartshay/k8s-gitops) repository.

### Deployment Location

```
k8s-gitops/
└── apps/
    └── base/
        └── otel-demo/
            ├── deployment.yaml
            ├── service.yaml
            ├── ingress.yaml
            └── kustomization.yaml
```

### Manual Deploy (for testing)

```bash
# Apply manifests directly
kubectl apply -k apps/base/otel-demo/

# Check deployment
kubectl get pods -n otel-demo
kubectl logs -n otel-demo -l app=otel-demo

# Port forward for testing
kubectl port-forward -n otel-demo svc/otel-demo 8080:8080
```

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n otel-demo -o wide

# Check service
kubectl get svc -n otel-demo

# Check logs
kubectl logs -n otel-demo deployment/otel-demo --tail=50

# Check OTel connectivity
kubectl exec -n otel-demo deployment/otel-demo -- \
  curl -s http://localhost:8080/metrics | jq
```

---

## Testing

### Endpoint Tests

```bash
# Health check
curl -s http://localhost:8080/health | jq
# Expected: {"status": "healthy"}

# Readiness check
curl -s http://localhost:8080/ready | jq
# Expected: {"status": "ready"}

# Service info (includes trace ID)
curl -s http://localhost:8080/ | jq
# Returns service info with trace_id for verification

# Chain operation (nested spans)
curl -s http://localhost:8080/chain | jq
# Simulates DB, cache, and API calls

# Error demonstration
curl -s http://localhost:8080/error | jq
# Returns 500 with error trace

# Slow operation
curl -s http://localhost:8080/slow | jq
# Returns after 0.5-2s delay

# Metrics/config info
curl -s http://localhost:8080/metrics | jq
# Shows current OTel configuration
```

### Load Testing

```bash
# Simple load test with curl
for i in {1..100}; do
  curl -s http://localhost:8080/chain > /dev/null &
done
wait

# With Apache Bench
ab -n 1000 -c 10 http://localhost:8080/

# With hey (Go HTTP load generator)
hey -n 1000 -c 10 http://localhost:8080/chain
```

### Trace Verification

After calling an endpoint, use the returned `trace_id` to verify in New Relic:

```bash
# Get trace ID from response
TRACE_ID=$(curl -s http://localhost:8080/ | jq -r '.trace_id')
echo "View trace: https://one.newrelic.com/distributed-tracing?query=trace.id%3D${TRACE_ID}"
```

---

## Troubleshooting

### Common Issues

#### 1. Connection Refused to OTel Collector

```bash
# Check collector is running
curl -v localhost:4317

# Verify endpoint configuration
echo $OTEL_EXPORTER_OTLP_ENDPOINT

# Check collector logs (K8s)
kubectl logs -n observability deployment/otel-collector
```

#### 2. Traces Not Appearing in New Relic

```bash
# Verify collector is forwarding to New Relic
kubectl logs -n observability deployment/otel-collector | grep -i "new relic\|error"

# Check API key is set
kubectl get secret -n observability newrelic-api-key -o jsonpath='{.data.api-key}' | base64 -d
```

#### 3. Application Won't Start

```bash
# Check Python dependencies
pip list | grep opentelemetry

# Verify imports
python -c "from opentelemetry import trace; print('OK')"

# Check for port conflicts
lsof -i :8080
```

#### 4. Docker Build Fails

```bash
# Build with verbose output
docker build --progress=plain -t otel-demo .

# Check base image
docker pull python:3.12-slim
```

### Debug Mode

```bash
# Run with debug logging
OTEL_LOG_LEVEL=debug python app.py

# Enable Flask debug (development only!)
FLASK_DEBUG=1 python app.py
```

---

## Observability

### New Relic Queries

```sql
-- Find traces by service
FROM Span SELECT * WHERE service.name = 'otel-demo' SINCE 1 hour ago

-- Error rate
FROM Span SELECT percentage(count(*), WHERE otel.status_code = 'ERROR')
WHERE service.name = 'otel-demo' SINCE 1 hour ago

-- Latency percentiles
FROM Span SELECT percentile(duration.ms, 50, 95, 99)
WHERE service.name = 'otel-demo' AND name = 'chain-handler'
SINCE 1 hour ago

-- Throughput
FROM Span SELECT rate(count(*), 1 minute)
WHERE service.name = 'otel-demo' SINCE 1 hour ago TIMESERIES
```

### Key Metrics to Monitor

| Metric | Description | Alert Threshold |
| ------ | ----------- | --------------- |
| Error Rate | % of requests with errors | > 1% |
| P95 Latency | 95th percentile response time | > 500ms |
| Throughput | Requests per minute | < 10 (availability) |

### Dashboards

Create a dashboard in New Relic with:

1. **Service Health**: Error rate, throughput, latency
2. **Endpoint Breakdown**: Per-endpoint metrics
3. **Trace Samples**: Recent traces with errors
4. **Infrastructure**: Pod CPU/memory (if using K8s integration)

---

## CI/CD

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `lint.yml` | PR, push to main | Pre-commit hooks, linting |
| `docker.yml` | Push to main, tags | Build and push Docker image |

### Release Process

1. Create a git tag: `git tag v1.0.1`
2. Push tag: `git push origin v1.0.1`
3. GitHub Actions builds and pushes `stuartshay/otel-demo:v1.0.1`
4. Update k8s-gitops with new image tag
5. Argo CD syncs the deployment

---

## References

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/languages/python/)
- [Flask Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/flask/flask.html)
- [New Relic OTLP](https://docs.newrelic.com/docs/opentelemetry/best-practices/opentelemetry-otlp/)
- [k8s-gitops Deployment](https://github.com/stuartshay/k8s-gitops/tree/master/apps/base/otel-demo)
