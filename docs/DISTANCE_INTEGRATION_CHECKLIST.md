# Distance API Integration - Implementation Checklist

Quick reference for implementing REST API integration with otel-worker.

## Phase 1: gRPC Client Setup ✅ Ready

### 1.1 Dependencies

```bash
cd /home/ubuntu/git/otel-demo
echo "grpcio==1.62.0" >> requirements.txt
echo "grpcio-tools==1.62.0" >> requirements.txt
echo "protobuf==4.25.3" >> requirements.txt
pip install -r requirements.txt
```

### 1.2 Generate Python Stubs

```bash
# Add to Makefile
cat >> Makefile << 'EOF'

.PHONY: proto
proto: ## Generate gRPC Python stubs from otel-worker
 @echo "Generating gRPC stubs..."
 @mkdir -p app/proto/distance/v1
 @touch app/proto/__init__.py
 @touch app/proto/distance/__init__.py
 @touch app/proto/distance/v1/__init__.py
 python -m grpc_tools.protoc \
  -I../otel-worker/proto \
  --python_out=app/proto \
  --grpc_python_out=app/proto \
  --pyi_out=app/proto \
  ../otel-worker/proto/distance/v1/distance.proto
 @echo "✓ Stubs generated in app/proto"
EOF

make proto
```

### 1.3 Create gRPC Client Service

- [ ] Create `app/services/distance_client.py`
- [ ] Add `DistanceClient` class with connection pooling
- [ ] Implement `calculate_distance(date, device_id)` method
- [ ] Implement `get_job_status(job_id)` method
- [ ] Implement `list_jobs(...)` method
- [ ] Add OTel instrumentation with `GrpcInstrumentorClient`
- [ ] Add retry logic with exponential backoff
- [ ] Handle gRPC errors (UNAVAILABLE, INVALID_ARGUMENT, etc.)

**Test**: `pytest tests/services/test_distance_client.py -v`

---

## Phase 2: REST API Endpoints ✅ Ready

### 2.1 Create Distance Blueprint

- [ ] Create `app/blueprints/distance.py`
- [ ] Implement `POST /api/distance/calculate`
  - Validate date format (YYYY-MM-DD)
  - Validate date not in future
  - Call gRPC `CalculateDistanceFromHome`
  - Return 202 Accepted with job_id
- [ ] Implement `GET /api/distance/jobs/<job_id>`
  - Call gRPC `GetJobStatus`
  - Transform response to REST format
  - Add CSV download URL if completed
- [ ] Implement `GET /api/distance/jobs`
  - Parse query parameters (status, limit, offset, date, device_id)
  - Call gRPC `ListJobs`
  - Add pagination next_offset
- [ ] Implement `GET /api/distance/download/<filename>`
  - Validate filename (prevent path traversal)
  - Stream CSV from `/data/csv/` directory
  - Set Content-Disposition header

### 2.2 Register Blueprint

```python
# app/__init__.py
from app.blueprints.distance import distance_bp

def create_app(config=None):
    # ... existing code ...
    app.register_blueprint(distance_bp)
    return app
```

**Test**: `pytest tests/blueprints/test_distance.py -v`

---

## Phase 3: Authentication ✅ Ready

### 3.1 Add Dependencies

```bash
echo "PyJWT==2.8.0" >> requirements.txt
echo "cryptography==42.0.0" >> requirements.txt
pip install -r requirements.txt
```

### 3.2 Create Auth Middleware

- [ ] Create `app/middleware/auth.py`
- [ ] Add `CognitoAuth` class
  - Initialize with JWKS URL
  - Implement `verify_token(token)` method
  - Cache JWKS keys
- [ ] Add `@require_auth` decorator
  - Extract Bearer token from Authorization header
  - Verify JWT signature
  - Check expiration
  - Attach claims to `request.user_claims`

### 3.3 Environment Variables

```bash
cat >> .env << EOF
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_ZL7M5Qa7K
COGNITO_CLIENT_ID=5j475mtdcm4qevh7q115qf1sfj
EOF
```

### 3.4 Apply to Endpoints

```python
@distance_bp.route("/api/distance/calculate", methods=["POST"])
@require_auth
def calculate_distance():
    user = request.user_claims
    # ... implementation
```

**Test**: `pytest tests/middleware/test_auth.py -v`

---

## Phase 4: OpenTelemetry Context Propagation ✅ Ready

### 4.1 Update gRPC Client

```python
# app/services/distance_client.py
from opentelemetry import trace
from opentelemetry.propagate import inject

def calculate_distance(self, date: str, device_id: str = ""):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("grpc-calculate-distance") as span:
        span.set_attribute("distance.date", date)

        # Inject trace context into metadata
        metadata = {}
        inject(metadata)

        response = self.stub.CalculateDistanceFromHome(
            request,
            metadata=list(metadata.items())
        )

        return response
```

### 4.2 Verify Trace Hierarchy

```bash
# Make request
curl -X POST http://localhost:8080/api/distance/calculate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"date":"2026-01-25","device_id":"iphone_stuart"}'

# Check New Relic for trace:
# HTTP POST /api/distance/calculate
#   └── grpc-calculate-distance
#       └── CalculateDistanceFromHome (otel-worker)
#           └── GetLocationsByDate (database)
```

---

## Phase 5: Testing 🔄 In Progress

### 5.1 Unit Tests

```bash
# Create test files
touch tests/blueprints/test_distance.py
touch tests/services/test_distance_client.py
touch tests/middleware/test_auth.py

# Run tests
pytest tests/ -v --cov=app --cov-report=term-missing
```

### 5.2 Integration Tests

```bash
# Requires Docker Compose with otel-worker + PostgreSQL
docker-compose -f tests/docker-compose.test.yml up -d
pytest tests/integration/ -v
docker-compose -f tests/docker-compose.test.yml down
```

### 5.3 Manual Testing

```bash
# Start otel-demo
make start

# Test endpoints
curl http://localhost:8080/api/distance/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"date":"2026-01-25","device_id":"iphone_stuart"}'

# Check status
curl http://localhost:8080/api/distance/jobs/<job_id> \
  -H "Authorization: Bearer <token>"

# List jobs
curl "http://localhost:8080/api/distance/jobs?status=completed&limit=10" \
  -H "Authorization: Bearer <token>"

# Download CSV
curl http://localhost:8080/api/distance/download/distance_20260125.csv \
  -H "Authorization: Bearer <token>" \
  -o distance.csv
```

---

## Phase 6: Kubernetes Deployment 🔄 In Progress

### 6.1 Update ConfigMap

```yaml
# k8s-gitops/apps/base/otel-demo/configmap.yaml
data:
  DISTANCE_SERVICE_ENDPOINT: "otel-worker.otel-worker.svc.cluster.local:50051"
  DISTANCE_SERVICE_TIMEOUT: "30"
  RATE_LIMIT_CALCULATE: "10"
  RATE_LIMIT_STATUS: "100"
```

### 6.2 Create Cognito Secret

```yaml
# k8s-gitops/apps/base/otel-demo/cognito-secret.yaml
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

```bash
# Encrypt with SOPS
sops -e cognito-secret.yaml > cognito-secret.enc.yaml
```

### 6.3 Mount CSV PVC

```yaml
# k8s-gitops/apps/base/otel-demo/deployment.yaml
spec:
  template:
    spec:
      containers:
        - name: otel-demo
          volumeMounts:
            - name: csv-storage
              mountPath: /data/csv
              readOnly: true
      volumes:
        - name: csv-storage
          persistentVolumeClaim:
            claimName: otel-worker-csv
```

### 6.4 Create Network Policy

```yaml
# k8s-gitops/apps/base/otel-demo/networkpolicy.yaml
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

### 6.5 Deploy

```bash
cd /home/ubuntu/git/k8s-gitops
git add apps/base/otel-demo/
git commit -m "feat(otel-demo): Add distance API integration"
git push origin master

# Wait for Argo CD sync
kubectl rollout status deployment -n otel-demo otel-demo

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://otel-demo.otel-demo.svc.cluster.local:8080/health
```

---

## Verification Checklist

### Development

- [ ] gRPC stubs generated without errors
- [ ] Endpoints respond with expected status codes
- [ ] JWT validation works
- [ ] Rate limiting enforces limits
- [ ] OTel traces show complete hierarchy
- [ ] Unit tests pass (80%+ coverage)

### Staging

- [ ] Deployment successful to k8s-pi5-cluster
- [ ] Pods healthy (2/2 Running)
- [ ] gRPC connectivity to otel-worker works
- [ ] Network policy allows traffic
- [ ] Cognito JWT validation works end-to-end
- [ ] CSV downloads work
- [ ] Traces appear in New Relic
- [ ] No errors in logs for 24 hours

### Production

- [ ] Feature flag enabled
- [ ] Load testing passed
- [ ] Monitoring alerts configured
- [ ] Documentation updated
- [ ] Runbook created

---

## Quick Commands

```bash
# Generate stubs
make proto

# Run dev server
make start

# Run tests
pytest tests/ -v --cov

# Check logs
make logs

# Deploy to k8s
cd /home/ubuntu/git/k8s-gitops
git add . && git commit -m "feat: distance API" && git push

# Check k8s pods
kubectl get pods -n otel-demo
kubectl logs -n otel-demo -l app.kubernetes.io/name=otel-demo --tail=50

# Test gRPC from otel-demo pod
kubectl exec -n otel-demo deploy/otel-demo -- \
  python -c "import grpc; print('gRPC available')"
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app.proto'"

```bash
# Regenerate stubs
make proto
# Verify __init__.py files exist
ls -la app/proto/
ls -la app/proto/distance/
ls -la app/proto/distance/v1/
```

### "grpc.RpcError: StatusCode.UNAVAILABLE"

```bash
# Check service is running
kubectl get svc -n otel-worker otel-worker
# Test DNS resolution
kubectl exec -n otel-demo deploy/otel-demo -- \
  nslookup otel-worker.otel-worker.svc.cluster.local
# Check network policy
kubectl get networkpolicy -n otel-demo
```

### "401 Unauthorized"

```bash
# Check JWT token expiry
# Decode at jwt.io
# Verify COGNITO_USER_POOL_ID and CLIENT_ID match
kubectl get secret -n otel-demo cognito-config -o yaml
```

### "CSV file not found"

```bash
# Check PVC is mounted
kubectl describe pod -n otel-demo <pod-name>
# Check PVC exists
kubectl get pvc -n otel-worker otel-worker-csv
# Check file exists in otel-worker
kubectl exec -n otel-worker deploy/otel-worker -- ls -la /data/csv/
```

---

## Timeline Estimate

| Phase | Time | Status |
|-------|------|--------|
| 1. gRPC Client Setup | 2-3h | ⏳ Ready to start |
| 2. REST Endpoints | 3-4h | ⏳ Depends on Phase 1 |
| 3. Authentication | 2-3h | ⏳ Depends on Phase 2 |
| 4. OTel Propagation | 1-2h | ⏳ Depends on Phase 2 |
| 5. Testing | 2-3h | ⏳ Depends on all phases |
| 6. K8s Deployment | 1-2h | ⏳ Depends on all phases |
| **Total** | **11-17h** | |

**Recommended**: 2-3 days with testing buffer

---

## Next Action

**Start with Phase 1.1**: Add gRPC dependencies to `requirements.txt`

```bash
cd /home/ubuntu/git/otel-demo
echo -e "\n# gRPC dependencies for distance-worker integration" >> requirements.txt
echo "grpcio==1.62.0" >> requirements.txt
echo "grpcio-tools==1.62.0" >> requirements.txt
echo "protobuf==4.25.3" >> requirements.txt
pip install -r requirements.txt
```
