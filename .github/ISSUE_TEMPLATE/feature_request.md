---
name: Feature request
about: Suggest an idea for this project
labels: enhancement
---

## Problem / Use case

What are you trying to accomplish? What observability gap does this address?

## Proposed solution

Describe the new endpoint, span, or functionality.

## OpenTelemetry Considerations

- What spans/attributes would be added?
- How does this integrate with existing traces?
- Any new environment variables needed?

## Alternatives considered

Any alternative solutions or features you've considered.

## Example Implementation

```python
# Optional: sketch of the proposed code
@app.route("/new-endpoint")
def new_endpoint():
    with tracer.start_as_current_span("new-operation") as span:
        span.set_attribute("custom.attribute", "value")
        # ...
```

## Pre-submit checklist

- [ ] I read `README.md` and `docs/operations.md`
- [ ] This aligns with OpenTelemetry best practices
- [ ] I considered backward compatibility
