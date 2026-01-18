# @stuartshay/otel-types

TypeScript type definitions for the [otel-demo](https://github.com/stuartshay/otel-demo) API.

Auto-generated from the OpenAPI specification using [openapi-typescript](https://github.com/drwpow/openapi-typescript).

## Installation

```bash
npm install @stuartshay/otel-types
```

## Usage

```typescript
import type { paths, components } from '@stuartshay/otel-types';

// Use path types
type LocationsResponse = paths['/db/locations']['get']['responses']['200']['content']['application/json'];

// Use component schemas
type Location = components['schemas']['Location'];

// Example with fetch
async function getLocations(): Promise<LocationsResponse> {
  const response = await fetch('https://otel.lab.informationcart.com/db/locations?limit=20');
  return response.json();
}
```

## API Documentation

Full API documentation is available at:

- Swagger UI: <https://otel.lab.informationcart.com/apidocs/>
- OpenAPI Spec: <https://otel.lab.informationcart.com/apispec.json>

## Versioning

This package follows the otel-demo API versioning:

- Package version matches the Docker image version
- Breaking API changes result in a major version bump
- New endpoints or optional fields result in a minor version bump
- Bug fixes result in a patch version bump

## Type Generation

Types are automatically generated when the otel-demo API schema changes.

To generate types locally:

```bash
# From otel-demo root
./scripts/generate-types.sh
```

## Related Packages

- [otel-demo](https://github.com/stuartshay/otel-demo) - The Flask API
- [otel-ui](https://github.com/stuartshay/otel-ui) - React frontend (coming soon)

## License

MIT
