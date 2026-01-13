## Summary

- Describe the change and why it's needed.

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update
- [ ] Infrastructure/CI change

## Checklist

- [ ] Read `README.md` and `docs/operations.md`
- [ ] Code follows OpenTelemetry best practices
- [ ] No secrets or API keys committed
- [ ] Environment variables used for configuration (not hardcoded)
- [ ] Ran `pre-commit run -a` locally (hooks passing)
- [ ] Tested endpoints locally with `curl`

## Testing

```bash
# Commands used to validate changes
curl http://localhost:8080/health
curl http://localhost:8080/
```

## OpenTelemetry Considerations

- [ ] Custom spans have meaningful names and attributes
- [ ] Errors are properly recorded with `span.record_exception()`
- [ ] Trace context is propagated correctly
- [ ] No sensitive data in span attributes or logs

## Docker

- [ ] `docker build -t otel-demo .` succeeds
- [ ] Container runs and responds to health checks

## Notes

- Any additional context or screenshots.
