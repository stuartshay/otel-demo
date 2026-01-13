---
name: Bug report
about: Create a report to help us improve
labels: bug
---

## Describe the bug

A clear and concise description of what the bug is.

## Reproduction

Steps to reproduce the behavior:

1. Run command '...'
2. Call endpoint '...'
3. See error

## Expected behavior

A clear and concise description of what you expected to happen.

## Environment

- OS:
- Python version:
- Docker version (if applicable):
- OTel Collector endpoint:

## Configuration

```bash
# Environment variables used
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=
```

## Trace Information

If applicable, include trace ID from the response:

```json
{
  "trace_id": "..."
}
```

## Pre-submit checklist

- [ ] I read `README.md` and `docs/operations.md`
- [ ] I ran `pre-commit run -a` locally
- [ ] I tested with a fresh virtual environment

## Logs/Output

Paste relevant logs (redact any secrets or API keys).

```
```
