# otel-worker REST API Integration Plan

**Date**: 2026-01-25
**Status**: Planning
**Estimated Time**: 10-15 hours
**Priority**: P2 - User-facing functionality

## Overview

Add REST API endpoints to otel-demo Flask application to integrate with the otel-worker gRPC service. This provides a web-friendly interface for distance calculations with authentication, async job management, and distributed tracing.

## Goals

1. **gRPC Client Integration** - Connect to otel-worker service from Python
2. **REST API Endpoints** - Expose distance calculation functionality via HTTP
3. **Authentication** - Secure endpoints with Cognito JWT validation
4. **Async Job Management** - Handle long-running calculations gracefully
5. **OpenTelemetry Context Propagation** - Link traces across service boundary
6. **Error Handling** - Provide clear error messages and status codes
7. **API Documentation** - Swagger/OpenAPI integration

## Architecture

```text
otel-ui (React) → HTTPS → otel-demo (Flask) → gRPC → otel-worker (Go)
                           ├── Cognito JWT          ├── PostgreSQL
                           └── OTel Traces          └── CSV Files
```

## Prerequisites

✅ **Completed**:

- otel-worker v1.0.42 deployed and running
- gRPC service available at `otel-worker.otel-worker.svc.cluster.local:50051`
- OpenTelemetry tracing enabled in both services
- otel-demo already has OTel instrumentation
- **Proto definitions published to Buf Registry (v1.0.4)**

❌ **Required**:

- Buf CLI installed (`brew install bufbuild/buf/buf` or download from releases)
- Python gRPC client library
- Cognito JWT validation middleware
- Service-to-service network policy

## Implementation Plan

### Phase 1: gRPC Client Setup (2-3 hours)

#### 1.1 Add Dependencies

**File**: `requirements.txt`

Add:

```text
grpcio==1.62.0
grpcio-tools==1.62.0
protobuf==4.25.3
```

**Action**: Run `pip install -r requirements.txt`

#### 1.2 Generate Python gRPC Stubs (Using Buf)

**Source**: Buf Schema Registry - `buf.build/stuartshay-consulting/otel-worker:1.0.4`

**Why Buf?**

- ✅ No need to copy proto files between repos
- ✅ Versioned proto packages (v1.0.4)
- ✅ Centralized proto definitions
- ✅ Better dependency management
- ✅ Automatic stub generation

**Directory Structure**:

```
otel-demo/
├── buf.gen.yaml              # Buf code generation config
├── app/
│   └── proto/
│       └── distance/
│           └── v1/
│               ├── __init__.py
│               ├── distance_pb2.py       # Generated
│               └── distance_pb2_grpc.py  # Generated
```

**Install Buf CLI**:

```bash
# macOS
brew install bufbuild/buf/buf

# Linux
curl -sSL "https://github.com/bufbuild/buf/releases/download/v1.28.1/buf-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/buf
chmod +x /usr/local/bin/buf

# Verify
buf --version
```

**Create buf.gen.yaml**:

**Note**: This repo currently uses `version: v1` with local plugins (python, grpc_python, pyi) instead of `version: v2` with remote plugins. Both formats work, but the existing buf.gen.yaml uses v1 for consistency with the project setup.

```yaml
# Current format (v1 with local plugins)
version: v1
plugins:
  - plugin: python
    out: app/proto
    opt:
      - paths=source_relative
  - plugin: grpc_python
    out: app/proto
    opt:
      - paths=source_relative
  - plugin: pyi
    out: app/proto
    opt:
      - paths=source_relative
```

Alternative v2 format (not currently used):

```yaml
# Alternative v2 format with remote plugins
version: v2
plugins:
  - remote: buf.build/protocolbuffers/python
    out: app/proto
    opt:
      - paths=source_relative
  - remote: buf.build/grpc/python
    out: app/proto
    opt:
      - paths=source_relative
  - remote: buf.build/protocolbuffers/pyi
    out: app/proto
    opt:
      - paths=source_relative
```

**Generate Code**:

```bash
# Generate from published Buf package
buf generate buf.build/stuartshay-consulting/otel-worker:1.0.4

# Create __init__.py files for Python imports
touch app/proto/__init__.py
touch app/proto/distance/__init__.py
touch app/proto/distance/v1/__init__.py
```

**Makefile Target**:

```makefile
.PHONY: proto
proto: ## Generate gRPC Python stubs from Buf Registry
 @echo "Generating gRPC stubs from buf.build/stuartshay-consulting/otel-worker:1.0.4..."
 @buf generate buf.build/stuartshay-consulting/otel-worker:1.0.4
 @touch app/proto/__init__.py
 @touch app/proto/distance/__init__.py
 @touch app/proto/distance/v1/__init__.py
 @echo "✓ Stubs generated in app/proto"
```

**Test**: Verify imports work:

```python
from app.proto.distance.v1 import distance_pb2, distance_pb2_grpc
```

**Version Pinning**: To upgrade to a new otel-worker proto version:

```bash
# Update to v1.0.5 (example)
buf generate buf.build/stuartshay-consulting/otel-worker:1.0.5
```

#### 1.3 Create gRPC Client Service

**File**: `app/services/distance_client.py`

**Features**:

- Singleton gRPC channel with connection pooling
- OpenTelemetry interceptor for distributed tracing
- Retry logic with exponential backoff
- Health check method
- Environment-based configuration

**Interface**:

```python
class DistanceClient:
    def __init__(self, endpoint: str):
        """Initialize gRPC client with OTel instrumentation."""

    async def calculate_distance(
        self, date: str, device_id: str = ""
    ) -> CalculateDistanceResponse:
        """Start async distance calculation job."""

    async def get_job_status(self, job_id: str) -> GetJobStatusResponse:
        """Poll job status and retrieve results."""

    async def list_jobs(
        self,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
        date: str = "",
        device_id: str = ""
    ) -> ListJobsResponse:
        """List jobs with filtering."""

    def health_check(self) -> bool:
        """Check gRPC connection health."""
```

**Environment Variables**:

```bash
DISTANCE_SERVICE_ENDPOINT=otel-worker.otel-worker.svc.cluster.local:50051
DISTANCE_SERVICE_TIMEOUT=30  # seconds
```

**OTel Integration**:

```python
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

GrpcInstrumentorClient().instrument()
```

**Error Handling**:

```python
from grpc import StatusCode

try:
    response = stub.CalculateDistanceFromHome(request)
except grpc.RpcError as e:
    if e.code() == StatusCode.UNAVAILABLE:
        raise ServiceUnavailableError("Distance service unreachable")
    elif e.code() == StatusCode.INVALID_ARGUMENT:
        raise ValidationError(e.details())
    raise
```

**Testing**:

```python
# tests/services/test_distance_client.py
def test_calculate_distance_success(mock_grpc_stub):
    client = DistanceClient("localhost:50051")
    response = client.calculate_distance("2026-01-25", "iphone_stuart")
    assert response.job_id
    assert response.status == "queued"

def test_connection_error(mock_grpc_stub):
    mock_grpc_stub.side_effect = grpc.RpcError(StatusCode.UNAVAILABLE)
    client = DistanceClient("localhost:50051")
    with pytest.raises(ServiceUnavailableError):
        client.calculate_distance("2026-01-25", "iphone_stuart")
```

---

### Phase 2: REST API Endpoints (3-4 hours)

#### 2.1 Create Distance Blueprint

**File**: `app/blueprints/distance.py`

**Endpoints**:

##### POST /api/distance/calculate

**Purpose**: Start async distance calculation

**Request**:

```json
{
  "date": "2026-01-25",
  "device_id": "iphone_stuart"  // optional
}
```

**Response** (202 Accepted):

```json
{
  "job_id": "b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
  "status": "queued",
  "queued_at": "2026-01-25T15:24:54.545Z",
  "status_url": "/api/distance/jobs/b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

**Validations**:

- Date format: YYYY-MM-DD
- Date not in future
- Device ID alphanumeric + underscore

**Swagger**:

```python
@distance_bp.route("/api/distance/calculate", methods=["POST"])
def calculate_distance():
    """Calculate distance from home.
    ---
    tags:
      - Distance
    summary: Start distance calculation job
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - date
          properties:
            date:
              type: string
              format: date
              example: "2026-01-25"
            device_id:
              type: string
              example: "iphone_stuart"
    responses:
      202:
        description: Job created successfully
      400:
        description: Invalid request parameters
      401:
        description: Unauthorized (missing/invalid JWT)
      503:
        description: Distance service unavailable
    security:
      - Bearer: []
    """
```

##### GET /api/distance/jobs/{job_id}

**Purpose**: Get job status and results

**Response** (200 OK - Completed):

```json
{
  "job_id": "b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
  "status": "completed",
  "queued_at": "2026-01-25T15:24:54.545Z",
  "started_at": "2026-01-25T15:24:54.600Z",
  "completed_at": "2026-01-25T15:24:55.200Z",
  "result": {
    "csv_download_url": "/api/distance/download/distance_20260125_iphone_stuart.csv",
    "total_distance_km": 19.44,
    "total_locations": 1464,
    "max_distance_km": 0.31,
    "min_distance_km": 0.001,
    "processing_time_ms": 600,
    "date": "2026-01-25",
    "device_id": "iphone_stuart"
  },
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

**Response** (200 OK - Processing):

```json
{
  "job_id": "b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
  "status": "processing",
  "queued_at": "2026-01-25T15:24:54.545Z",
  "started_at": "2026-01-25T15:24:54.600Z",
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

**Response** (200 OK - Failed):

```json
{
  "job_id": "b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
  "status": "failed",
  "queued_at": "2026-01-25T15:24:54.545Z",
  "started_at": "2026-01-25T15:24:54.600Z",
  "completed_at": "2026-01-25T15:24:55.000Z",
  "error_message": "No location data found for date 2026-01-25",
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

**Status Codes**:

- 200: Job found (any status)
- 404: Job ID not found
- 401: Unauthorized

##### GET /api/distance/jobs

**Purpose**: List jobs with filtering

**Query Parameters**:

- `status`: Filter by status (queued/processing/completed/failed)
- `limit`: Max results (default 50, max 500)
- `offset`: Pagination offset (default 0)
- `date`: Filter by calculation date (YYYY-MM-DD)
- `device_id`: Filter by device

**Response** (200 OK):

```json
{
  "jobs": [
    {
      "job_id": "b4eaed9f-2b3d-43cb-9cb2-4d7313343369",
      "status": "completed",
      "date": "2026-01-25",
      "device_id": "iphone_stuart",
      "queued_at": "2026-01-25T15:24:54.545Z",
      "completed_at": "2026-01-25T15:24:55.200Z"
    }
  ],
  "total_count": 1,
  "limit": 50,
  "offset": 0,
  "next_offset": null,
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

##### GET /api/distance/download/{filename}

**Purpose**: Download CSV result file

**Response**:

- Content-Type: text/csv
- Content-Disposition: attachment; filename="distance_20260125.csv"
- Body: CSV file content

**Security**:

- Validate filename format
- Prevent path traversal
- Check file exists
- Rate limit downloads

**Implementation Note**:
Since CSV files are in Kubernetes PVC, need to either:

1. Mount same PVC to otel-demo pods (read-only)
2. Stream file content from otel-worker via gRPC
3. Use S3/object storage for shared access

**Recommendation**: Option 1 (shared PVC mount) for simplicity.

#### 2.2 Error Response Format

**Standard Error**:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid date format. Expected YYYY-MM-DD",
    "details": {
      "field": "date",
      "value": "2026-1-25"
    }
  },
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

**Error Codes**:

- `VALIDATION_ERROR`: Invalid input (400)
- `UNAUTHORIZED`: Missing/invalid JWT (401)
- `NOT_FOUND`: Resource not found (404)
- `SERVICE_UNAVAILABLE`: gRPC service down (503)
- `INTERNAL_ERROR`: Unexpected error (500)

#### 2.3 Register Blueprint

**File**: `app/__init__.py`

```python
from app.blueprints.distance import distance_bp

def create_app(config=None):
    # ... existing code ...
    app.register_blueprint(distance_bp)
    return app
```

---

### Phase 3: Authentication (2-3 hours)

#### 3.1 Cognito JWT Validation

**Dependencies**:

```text
PyJWT==2.8.0
cryptography==42.0.0
requests==2.31.0
```

**File**: `app/middleware/auth.py`

**Features**:

- JWT signature verification using Cognito JWKS
- Token expiration checking
- Audience (client_id) validation
- Claims extraction (sub, email, username)
- Caching of JWKS for performance

**Implementation**:

```python
import jwt
from jwt import PyJWKClient
from functools import wraps
from flask import request, jsonify

class CognitoAuth:
    def __init__(self, region: str, user_pool_id: str, client_id: str):
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        self.client_id = client_id
        self.jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)

    def verify_token(self, token: str) -> dict:
        """Verify JWT and return decoded claims."""
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
        )

        return claims

def require_auth(f):
    """Decorator to require valid Cognito JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            auth = current_app.config["COGNITO_AUTH"]
            claims = auth.verify_token(token)
            request.user_claims = claims  # Attach to request context
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    return decorated
```

**Environment Variables**:

```bash
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_ZL7M5Qa7K
COGNITO_CLIENT_ID=5j475mtdcm4qevh7q115qf1sfj
```

**Usage**:

```python
@distance_bp.route("/api/distance/calculate", methods=["POST"])
@require_auth
def calculate_distance():
    user = request.user_claims
    logger.info(f"User {user['sub']} starting calculation")
    # ... implementation
```

#### 3.2 Rate Limiting

**File**: `app/middleware/rate_limit.py`

**Strategy**: Token bucket per user (sub claim)

**Limits**:

- 10 calculations per minute per user
- 100 job status checks per minute per user

**Implementation**:

```python
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    def check_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if request is under rate limit."""
        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, window)
        return current <= limit

def rate_limit(limit: int, window: int):
    """Decorator for rate limiting."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_sub = request.user_claims["sub"]
            key = f"rate_limit:{f.__name__}:{user_sub}"

            if not limiter.check_limit(key, limit, window):
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": window
                }), 429

            return f(*args, **kwargs)
        return decorated
    return decorator
```

**Usage**:

```python
@distance_bp.route("/api/distance/calculate", methods=["POST"])
@require_auth
@rate_limit(limit=10, window=60)  # 10 per minute
def calculate_distance():
    # ... implementation
```

---

### Phase 4: OpenTelemetry Context Propagation (1-2 hours)

#### 4.1 gRPC Metadata Injection

**File**: `app/services/distance_client.py`

**Goal**: Propagate trace context from Flask HTTP request to gRPC call

**Implementation**:

```python
from opentelemetry import trace, context
from opentelemetry.propagate import inject

class DistanceClient:
    def calculate_distance(self, date: str, device_id: str = ""):
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("grpc-calculate-distance") as span:
            span.set_attribute("distance.date", date)
            span.set_attribute("distance.device_id", device_id)

            # Inject trace context into gRPC metadata
            metadata = {}
            inject(metadata)

            request = distance_pb2.CalculateDistanceRequest(
                date=date,
                device_id=device_id
            )

            response = self.stub.CalculateDistanceFromHome(
                request,
                metadata=list(metadata.items())
            )

            span.set_attribute("distance.job_id", response.job_id)

            return response
```

**Expected Trace Hierarchy**:

```text
HTTP POST /api/distance/calculate (Flask - automatic)
├── rpc.service: distance.v1.DistanceService
├── rpc.method: POST
├── service.name: otel-demo
└── grpc-calculate-distance (custom span)
    ├── distance.date: 2026-01-25
    ├── distance.device_id: iphone_stuart
    ├── distance.job_id: b4eaed9f...
    └── CalculateDistanceFromHome (otel-worker - automatic)
        └── GetLocationsByDate (otel-worker - custom)
            ├── db.system: postgresql
            └── db.result_count: 1464
```

#### 4.2 Add Custom Span Attributes

**Best Practices**:

```python
# DO: Add business-relevant attributes
span.set_attribute("distance.date", date)
span.set_attribute("distance.device_id", device_id)
span.set_attribute("job.status", status)
span.set_attribute("user.tenant", user_claims.get("tenant"))

# DON'T: Add high-cardinality attributes
# span.set_attribute("user.email", email)  # PII + high cardinality
# span.set_attribute("job.id", job_id)     # Unique per request
```

---

### Phase 5: Testing (2-3 hours)

#### 5.1 Unit Tests

**File**: `tests/blueprints/test_distance.py`

**Coverage**:

- Valid calculation request
- Invalid date format
- Missing required fields
- Authentication failures
- Rate limit enforcement
- gRPC service unavailable
- Completed job result retrieval
- Failed job error handling

**Example**:

```python
def test_calculate_distance_success(client, mock_distance_client, auth_headers):
    mock_distance_client.calculate_distance.return_value = Mock(
        job_id="test-job-id",
        status="queued"
    )

    response = client.post(
        "/api/distance/calculate",
        json={"date": "2026-01-25", "device_id": "iphone_stuart"},
        headers=auth_headers
    )

    assert response.status_code == 202
    data = response.get_json()
    assert data["job_id"] == "test-job-id"
    assert data["status"] == "queued"
    assert "status_url" in data
```

#### 5.2 Integration Tests

**File**: `tests/integration/test_distance_integration.py`

**Setup**:

- Use testcontainers for otel-worker (or mock gRPC server)
- Real PostgreSQL database with test data
- Cognito mock (or use test user pool)

**Test Scenarios**:

1. End-to-end calculation flow
2. Job polling until completion
3. CSV download after completion
4. Multiple concurrent calculations
5. Error recovery and retries

#### 5.3 Load Testing

**File**: `tests/load/test_distance_load.py`

**Tool**: Locust or k6

**Scenarios**:

- 10 concurrent users, 100 calculations each
- Measure: response time, success rate, gRPC connection pool behavior

---

### Phase 6: Documentation (1-2 hours)

#### 6.1 API Documentation

**Update**: `README.md`

Add table:

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/distance/calculate` | POST | Start distance calculation | Required |
| `/api/distance/jobs/{id}` | GET | Get job status | Required |
| `/api/distance/jobs` | GET | List jobs | Required |
| `/api/distance/download/{file}` | GET | Download CSV | Required |

#### 6.2 Swagger Integration

Endpoints automatically appear in `/apidocs` with decorators.

#### 6.3 Developer Guide

**File**: `docs/DISTANCE_API.md`

**Contents**:

- Quick start examples (curl, Python, JavaScript)
- Authentication setup
- Error handling
- Rate limits
- Polling best practices
- CSV format documentation

---

## Configuration

### Environment Variables

**New Variables**:

```bash
# Distance Service
DISTANCE_SERVICE_ENDPOINT=otel-worker.otel-worker.svc.cluster.local:50051
DISTANCE_SERVICE_TIMEOUT=30

# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_ZL7M5Qa7K
COGNITO_CLIENT_ID=5j475mtdcm4qevh7q115qf1sfj

# Rate Limiting
RATE_LIMIT_CALCULATE=10  # per minute
RATE_LIMIT_STATUS=100    # per minute

# CSV Storage (if using shared PVC)
CSV_STORAGE_PATH=/data/csv
```

### Kubernetes Deployment

**Updates Required**:

**File**: `k8s-gitops/apps/base/otel-demo/deployment.yaml`

1. **Add ConfigMap entries**:

```yaml
data:
  DISTANCE_SERVICE_ENDPOINT: "otel-worker.otel-worker.svc.cluster.local:50051"
  DISTANCE_SERVICE_TIMEOUT: "30"
  RATE_LIMIT_CALCULATE: "10"
  RATE_LIMIT_STATUS: "100"
```

2. **Add Secret for Cognito** (via SOPS):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cognito-config
  namespace: otel-demo
type: Opaque
stringData:
  COGNITO_USER_POOL_ID: us-east-1_ZL7M5Qa7K
  COGNITO_CLIENT_ID: 5j475mtdcm4qevh7q115qf1sfj
```

3. **Mount CSV PVC** (read-only):

```yaml
volumeMounts:
  - name: csv-storage
    mountPath: /data/csv
    readOnly: true
volumes:
  - name: csv-storage
    persistentVolumeClaim:
      claimName: otel-worker-csv  # Same PVC as otel-worker
```

4. **Network Policy** (allow otel-demo → otel-worker):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: otel-demo-egress
  namespace: otel-demo
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: otel-demo
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: otel-worker
      ports:
        - protocol: TCP
          port: 50051
```

---

## Testing Plan

### Manual Testing Checklist

#### Development (Local)

- [ ] Generate gRPC stubs successfully
- [ ] Import stubs without errors
- [ ] Mock gRPC server responds correctly
- [ ] Flask endpoints return expected responses
- [ ] JWT validation works with valid token
- [ ] JWT validation rejects expired token
- [ ] Rate limiting kicks in after threshold
- [ ] OTel traces show gRPC spans
- [ ] Error responses include trace IDs

#### Staging (k8s-pi5-cluster)

- [ ] otel-demo can reach otel-worker via gRPC
- [ ] DNS resolution works (service discovery)
- [ ] Network policy allows traffic
- [ ] Cognito JWT validation works
- [ ] Job creation returns valid job_id
- [ ] Job polling returns correct status
- [ ] Completed job returns CSV path
- [ ] CSV download works from shared PVC
- [ ] Traces propagate end-to-end (UI → Flask → gRPC → DB)
- [ ] New Relic shows distributed traces
- [ ] Errors are logged with trace correlation

### Automated Testing

#### Unit Tests (pytest)

```bash
pytest tests/blueprints/test_distance.py -v --cov
pytest tests/services/test_distance_client.py -v --cov
pytest tests/middleware/test_auth.py -v --cov
```

**Target Coverage**: 80%+

#### Integration Tests

```bash
pytest tests/integration/ -v --log-cli-level=INFO
```

**Requirements**:

- Docker Compose with otel-worker + PostgreSQL
- Test database with sample OwnTracks data
- Cognito test user pool (or mock)

#### Load Tests (Locust)

```bash
locust -f tests/load/test_distance_load.py --host=http://localhost:8080
```

**Metrics**:

- 95th percentile response time < 500ms
- Error rate < 1%
- gRPC connection pool stable under load

---

## Rollout Strategy

### Development

1. **Branch**: `feature/distance-api-integration`
2. **Incremental PRs**:
   - PR #1: gRPC client + stubs
   - PR #2: REST endpoints (no auth)
   - PR #3: Cognito authentication
   - PR #4: Rate limiting
   - PR #5: Documentation + tests

### Staging

1. **Deploy**: otel-demo with new endpoints
2. **Verify**: End-to-end flow with Postman/curl
3. **Monitor**: Check logs, traces, metrics for 24 hours
4. **Load Test**: Simulate production traffic

### Production

1. **Feature Flag**: `DISTANCE_API_ENABLED=false` initially
2. **Gradual Rollout**: Enable for beta users first
3. **Monitor**: Latency, error rates, gRPC connection metrics
4. **Full Rollout**: Enable for all users after 48 hours

---

## Success Criteria

- [ ] POST /api/distance/calculate creates job (< 100ms)
- [ ] GET /api/distance/jobs/{id} polls status (< 50ms)
- [ ] Completed jobs return CSV download URL
- [ ] Failed jobs return clear error messages
- [ ] JWT validation rejects invalid tokens
- [ ] Rate limiting prevents abuse
- [ ] End-to-end traces visible in New Relic
- [ ] 80%+ test coverage
- [ ] API documented in Swagger
- [ ] Zero critical bugs in staging for 24 hours

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| gRPC service unavailable | High | Circuit breaker, retries, clear error messages |
| Cognito JWT issues | High | Thorough testing, fallback to API key auth |
| Rate limit too restrictive | Medium | Monitor usage, make configurable |
| CSV file access issues | Medium | Test PVC mounting, consider S3 alternative |
| Performance degradation | Medium | Load testing, gRPC connection pooling |
| Breaking changes in proto | Low | Version API endpoints, pin proto version |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. gRPC Client Setup | 2-3 hours | None |
| 2. REST Endpoints | 3-4 hours | Phase 1 |
| 3. Authentication | 2-3 hours | Phase 2 |
| 4. OTel Propagation | 1-2 hours | Phase 2 |
| 5. Testing | 2-3 hours | All phases |
| 6. Documentation | 1-2 hours | All phases |
| **Total** | **11-17 hours** | |

**Recommended Pace**: 2-3 days with testing buffer

---

## Next Steps

1. **Review Plan**: Get feedback on architecture and approach
2. **Environment Setup**: Ensure Cognito user pool is configured
3. **Start Development**: Begin with Phase 1 (gRPC client)
4. **Incremental PRs**: Small, focused pull requests for easy review
5. **Testing**: Test each phase before moving to next
6. **Documentation**: Update docs as features are completed

---

## References

- **[Buf Package - otel-worker v1.0.4](https://buf.build/stuartshay-consulting/otel-worker/docs/1.0.4)** - Official proto definitions
- [Buf Documentation](https://buf.build/docs/) - Buf Schema Registry guide
- [gRPC Python Quick Start](https://grpc.io/docs/languages/python/quickstart/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [OpenTelemetry gRPC Instrumentation](https://opentelemetry-python.readthedocs.io/en/latest/instrumentation/grpc/grpc.html)
- [Flask Blueprint Best Practices](https://flask.palletsprojects.com/en/2.3.x/blueprints/)
- [AWS Cognito JWT Verification](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html)

---

## Questions for Stakeholders

1. **Cognito Setup**: Is the user pool already configured, or do we need to create it?
2. **CSV Storage**: Prefer shared PVC mount or S3/object storage?
3. **Rate Limits**: Are 10 calculations/min and 100 status checks/min reasonable?
4. **API Versioning**: Should we version the API as `/api/v1/distance/calculate`?
5. **Error Reporting**: Should we integrate with Sentry or rely on New Relic?
6. **Beta Users**: Who should get early access for testing?

---

**Status**: Ready for review and approval to begin implementation.
