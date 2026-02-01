# Copilot Rules for otel-demo Repo

These rules ensure Copilot/assistants follow best practices for OpenTelemetry
demo application development.

## Always Read First

- **README**: Read `README.md` for application overview and endpoints
- **docs**: Read `docs/operations.md` for deployment and testing
- **env**: Check environment variables in README for OTel configuration
- **pre-commit**: ALWAYS run `pre-commit run -a` and fix issues before commit/PR

## Project Overview

This is a Python Flask application instrumented with OpenTelemetry for
distributed tracing. It demonstrates:

- Automatic Flask instrumentation
- Custom spans and attributes
- Trace context propagation
- Logging with trace correlation

## Target Infrastructure

| Property | Value |
|----------|-------|
| K8s Cluster | k8s-pi5-cluster |
| Namespace | otel-demo |
| OTel Collector | otel-collector.observability:4317 |
| Backend | New Relic |
| Docker Image | stuartshay/otel-demo |

## Development Workflow

### Branch Strategy

⚠️ **CRITICAL RULE**: NEVER commit directly to `main` branch. All changes MUST go through `develop` or `feature/*` branches.

- **main**: Protected branch, production-only (PR required, direct commits FORBIDDEN)
- **develop**: Primary development branch (work here by default)
- **feature/\***: Feature branches (use for isolated features, PR to develop or main)

### Daily Workflow

1. **ALWAYS** start from `develop` or create a feature branch
2. Run `./setup.sh` to initialize environment
3. Activate venv: `source venv/bin/activate`
4. Run locally: `python run.py`
5. Test endpoints: `curl http://localhost:8080/health`
6. Run `pre-commit run -a` before commit
7. Commit and push to `develop` or `feature/*` branch
8. Create PR from `develop` → `main` OR `feature/*` → `main` when ready to deploy
9. Merge PR triggers CI/CD pipeline and deploys to k8s-pi5-cluster

**Workflow Options:**

- Small changes: Work directly on `develop`, then PR to `main`
- Large features: Create `feature/name` branch, then PR to `main`
- **NEVER**: `git push origin main` or commit directly to main

## Writing Code

### Flask Endpoints

- Always include health (`/health`) and readiness (`/ready`) endpoints
- Use custom spans for business logic: `with tracer.start_as_current_span("name")`
- Set meaningful span attributes: `span.set_attribute("key", "value")`
- Record exceptions: `span.record_exception(e)`

### OpenTelemetry Best Practices

- Use environment variables for configuration (not hardcoded values)
- Set `SERVICE_NAME`, `SERVICE_NAMESPACE`, `deployment.environment`
- Use `BatchSpanProcessor` for production (not `SimpleSpanProcessor`)
- Include trace IDs in log output for correlation

### Logging

- Use structured logging with trace context
- Include `trace_id` and `span_id` in log format
- Never log sensitive data (tokens, passwords, PII)

## Safety Rules (Do Not)

- ⛔ **NEVER commit directly to main branch** - ALWAYS use develop or feature branches
- Do not commit secrets or API keys
- Do not use `latest` Docker tag in deployments
- Do not skip `pre-commit run -a` before commits
- Do not hardcode OTel endpoint URLs (use env vars)
- Do not disable TLS in production configurations

## Docker

```bash
# Build locally
docker build -t otel-demo .

# Run with local OTel collector
docker run -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=host.docker.internal:4317 \
  otel-demo

# Run with New Relic direct (for testing)
docker run -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=otlp.nr-data.net:4317 \
  -e OTEL_EXPORTER_OTLP_HEADERS="api-key=YOUR_KEY" \
  otel-demo
```

## Testing Endpoints

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/health` | Health check | `{"status": "healthy"}` |
| `/ready` | Readiness | `{"status": "ready"}` |
| `/` | Service info | Returns trace ID |
| `/chain` | Nested spans | 3-step demo |
| `/error` | Error demo | Returns 500 |
| `/slow` | Latency demo | 0.5-2s delay |

```bash
# Quick validation
curl -s http://localhost:8080/health | jq
curl -s http://localhost:8080/ | jq
curl -s http://localhost:8080/chain | jq
```

## CI/CD Pipeline

- **lint.yml**: Runs pre-commit hooks on PR
- **docker.yml**: Builds and pushes Docker image on merge to main

## Related Repositories

- [k8s-gitops](https://github.com/stuartshay/k8s-gitops) - K8s deployment manifests
- [homeassistant](https://github.com/stuartshay/homeassistant) - Home automation

## When Unsure

- Check existing code patterns in `app.py`
- Reference OpenTelemetry Python documentation
- Validate with `pre-commit run -a` before asking
- Test endpoints locally before pushing
