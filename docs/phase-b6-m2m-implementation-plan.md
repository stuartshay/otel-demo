# Phase B.6 & M2M Authentication Implementation Plan

This document outlines the implementation plan for auth observability (B.6) and machine-to-machine (M2M) authentication for agents and automated systems.

## Overview

| Component | Repository | Purpose |
|-----------|------------|---------|
| Auth Observability | k8s-gitops | Grafana dashboard for oauth2-proxy metrics |
| Cognito Resource Server | homelab-infrastructure | Define API scopes for M2M access |
| M2M Auth Middleware | otel-demo (new service) | Validate M2M tokens, bypass oauth2-proxy |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Browser Flow (Existing)                              │
│  Browser → Ingress → oauth2-proxy → Cognito Hosted UI → otel-demo           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         M2M/Agent Flow (New)                                 │
│                                                                              │
│  Agent → Get Token (client_credentials) → Cognito Token Endpoint            │
│       → Call API with Bearer token                                           │
│       → Ingress (X-M2M-Token header) → m2m-auth-middleware                  │
│       → Validates JWT → Proxies to otel-demo                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         Observability (New)                                  │
│                                                                              │
│  oauth2-proxy ──metrics──→ Prometheus ──query──→ Grafana Dashboard          │
│  m2m-middleware ──metrics──→ Prometheus ──query──→ Grafana Dashboard        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Auth Observability Dashboard (B.6)

### 1.1 Enable oauth2-proxy Metrics

**Repository:** k8s-gitops

oauth2-proxy exposes Prometheus metrics on port 44180 by default.

```yaml
# infrastructure/auth/oauth2-proxy/deployment.yaml (update)
spec:
  template:
    spec:
      containers:
        - name: oauth2-proxy
          ports:
            - containerPort: 4180
              name: http
            - containerPort: 44180
              name: metrics
```

```yaml
# infrastructure/auth/oauth2-proxy/service.yaml (update)
spec:
  ports:
    - name: http
      port: 4180
      targetPort: http
    - name: metrics
      port: 44180
      targetPort: metrics
```

### 1.2 Create ServiceMonitor

```yaml
# infrastructure/auth/oauth2-proxy/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: oauth2-proxy
  namespace: auth
  labels:
    app.kubernetes.io/name: oauth2-proxy
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: oauth2-proxy
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
  namespaceSelector:
    matchNames:
      - auth
```

### 1.3 Key Metrics to Track

| Metric | Description |
|--------|-------------|
| `oauth2_proxy_requests_total` | Total requests by status code |
| `oauth2_proxy_api_requests_total` | API endpoint requests |
| `oauth2_proxy_auth_success_total` | Successful authentications |
| `oauth2_proxy_auth_failure_total` | Failed authentications |
| `oauth2_proxy_upstream_response_time_seconds` | Backend response latency |

### 1.4 Grafana Dashboard

Create dashboard JSON for auth observability:

```yaml
# infrastructure/observability/grafana/dashboards/oauth2-proxy-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: oauth2-proxy-dashboard
  namespace: observability
  labels:
    grafana_dashboard: "1"
data:
  oauth2-proxy.json: |
    {
      "title": "OAuth2 Proxy - Auth Metrics",
      "uid": "oauth2-proxy-auth",
      "panels": [
        {
          "title": "Auth Success/Failure Rate",
          "type": "timeseries",
          "targets": [
            {
              "expr": "rate(oauth2_proxy_requests_total{code=~\"2..\"}[5m])",
              "legendFormat": "Success (2xx)"
            },
            {
              "expr": "rate(oauth2_proxy_requests_total{code=~\"4..\"}[5m])",
              "legendFormat": "Client Error (4xx)"
            }
          ]
        },
        {
          "title": "Login Events",
          "type": "stat",
          "targets": [
            {
              "expr": "increase(oauth2_proxy_requests_total{path=\"/oauth2/callback\",code=\"302\"}[24h])",
              "legendFormat": "Successful Logins (24h)"
            }
          ]
        },
        {
          "title": "Response Time (p95)",
          "type": "gauge",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, rate(oauth2_proxy_upstream_response_time_seconds_bucket[5m]))"
            }
          ]
        }
      ]
    }
```

### 1.5 Implementation Checklist

| Step | Task | Status |
|------|------|--------|
| 1.1 | Add metrics port to oauth2-proxy deployment | ❌ Not started |
| 1.2 | Update oauth2-proxy service with metrics port | ❌ Not started |
| 1.3 | Create ServiceMonitor for Prometheus scraping | ❌ Not started |
| 1.4 | Create Grafana dashboard ConfigMap | ❌ Not started |
| 1.5 | Verify metrics in Prometheus targets | ❌ Not started |
| 1.6 | Import and test dashboard in Grafana | ❌ Not started |

---

## Part 2: M2M Authentication Middleware

### 2.1 Cognito Resource Server (homelab-infrastructure)

Create a Resource Server to define API scopes for M2M access:

```hcl
# terraform/modules/cognito/resource_server.tf
resource "aws_cognito_resource_server" "api" {
  identifier   = "https://api.lab.informationcart.com"
  name         = "Homelab API"
  user_pool_id = aws_cognito_user_pool.main.id

  scope {
    scope_name        = "read"
    scope_description = "Read access to API resources"
  }

  scope {
    scope_name        = "write"
    scope_description = "Write access to API resources"
  }

  scope {
    scope_name        = "admin"
    scope_description = "Administrative access"
  }
}
```

### 2.2 M2M App Client (homelab-infrastructure)

```hcl
# terraform/modules/cognito/m2m_client.tf
resource "aws_cognito_user_pool_client" "m2m" {
  name         = "${var.user_pool_name}-m2m"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true

  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_flows_user_pool_client = true

  # Use Resource Server scopes
  allowed_oauth_scopes = [
    "${aws_cognito_resource_server.api.identifier}/read",
    "${aws_cognito_resource_server.api.identifier}/write",
  ]

  supported_identity_providers = ["COGNITO"]

  # M2M tokens: shorter access token, no refresh
  access_token_validity  = 1  # 1 hour
  token_validity_units {
    access_token = "hours"
  }
}

output "m2m_client_id" {
  value       = aws_cognito_user_pool_client.m2m.id
  description = "M2M client ID for agents"
}

output "m2m_client_secret" {
  value       = aws_cognito_user_pool_client.m2m.client_secret
  sensitive   = true
  description = "M2M client secret"
}
```

### 2.3 M2M Auth Middleware Service

**Repository:** New service in k8s-gitops or as part of otel-demo

#### Option A: Standalone Python Middleware (Recommended)

```
m2m-auth-middleware/
├── Dockerfile
├── requirements.txt
├── app.py              # FastAPI app
├── auth/
│   ├── __init__.py
│   ├── cognito.py      # JWT validation
│   └── middleware.py   # Request handling
└── tests/
    └── test_auth.py
```

**Core Logic (app.py):**

```python
"""M2M Auth Middleware - Validates Cognito JWT tokens for agent access."""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import Response
import httpx
import jwt
from jwt import PyJWKClient
from functools import lru_cache
import os

app = FastAPI(title="M2M Auth Middleware")

# Configuration
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"
UPSTREAM_URL = os.getenv("UPSTREAM_URL", "http://otel-demo.otel-demo.svc.cluster.local:8080")

# JWKS client with caching
@lru_cache()
def get_jwks_client():
    return PyJWKClient(JWKS_URL, cache_keys=True)


async def validate_m2m_token(request: Request) -> dict:
    """Validate M2M Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER,
            options={"verify_aud": False}  # M2M tokens don't have aud claim
        )

        # Verify it's a client_credentials token (no 'sub' with user ID)
        if "client_id" not in payload:
            raise HTTPException(status_code=403, detail="Not an M2M token")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(
    request: Request,
    path: str,
    token_payload: dict = Depends(validate_m2m_token)
):
    """Proxy validated requests to upstream otel-demo service."""

    # Build upstream URL
    upstream_url = f"{UPSTREAM_URL}/{path}"
    if request.query_params:
        upstream_url += f"?{request.query_params}"

    # Forward request
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=upstream_url,
            headers={
                "X-M2M-Client-ID": token_payload.get("client_id", ""),
                "X-M2M-Scope": " ".join(token_payload.get("scope", "").split()),
                "Content-Type": request.headers.get("Content-Type", "application/json"),
            },
            content=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None,
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )


@app.get("/health")
async def health():
    """Health check endpoint (no auth required)."""
    return {"status": "healthy", "service": "m2m-auth-middleware"}
```

### 2.4 Kubernetes Manifests (k8s-gitops)

```yaml
# apps/base/m2m-auth-middleware/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: m2m-auth-middleware
  namespace: otel-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: m2m-auth-middleware
  template:
    metadata:
      labels:
        app.kubernetes.io/name: m2m-auth-middleware
    spec:
      containers:
        - name: m2m-auth-middleware
          image: stuartshay/m2m-auth-middleware:1.0.0
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: COGNITO_REGION
              value: "us-east-1"
            - name: COGNITO_USER_POOL_ID
              valueFrom:
                secretKeyRef:
                  name: cognito-config
                  key: user-pool-id
            - name: UPSTREAM_URL
              value: "http://otel-demo.otel-demo.svc.cluster.local:8080"
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "200m"
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
```

```yaml
# apps/base/m2m-auth-middleware/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: m2m-auth-middleware
  namespace: otel-demo
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-dns01-production
    # NO oauth2-proxy auth - M2M validates its own tokens
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.lab.informationcart.com
      secretName: m2m-api-tls
  rules:
    - host: api.lab.informationcart.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: m2m-auth-middleware
                port:
                  name: http
```

### 2.5 Agent Usage Example

```bash
#!/bin/bash
# scripts/m2m-auth-example.sh

# Get M2M token from Cognito
TOKEN=$(curl -s -X POST \
  "https://homelab-auth.auth.us-east-1.amazoncognito.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "${M2M_CLIENT_ID}:${M2M_CLIENT_SECRET}" \
  -d "grant_type=client_credentials&scope=https://api.lab.informationcart.com/read" \
  | jq -r '.access_token')

# Call API with M2M endpoint
curl -X GET "https://api.lab.informationcart.com/db/locations" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

### 2.6 Implementation Checklist

| Step | Task | Repository | Status |
|------|------|------------|--------|
| 2.1 | Create Cognito Resource Server | homelab-infrastructure | ❌ Not started |
| 2.2 | Create M2M App Client | homelab-infrastructure | ❌ Not started |
| 2.3 | Apply Terraform and capture outputs | homelab-infrastructure | ❌ Not started |
| 2.4 | Create m2m-auth-middleware Python app | New repo or otel-demo | ❌ Not started |
| 2.5 | Build and push Docker image | GitHub Actions | ❌ Not started |
| 2.6 | Create K8s manifests | k8s-gitops | ❌ Not started |
| 2.7 | Create Cloudflare DNS for api.lab.* | k8s-gitops/cloudflare | ❌ Not started |
| 2.8 | Deploy and test M2M flow | Manual | ❌ Not started |
| 2.9 | Add M2M metrics to Grafana dashboard | k8s-gitops | ❌ Not started |
| 2.10 | Document agent onboarding process | otel-demo/docs | ❌ Not started |

---

## Endpoints Summary

| Endpoint | Auth Method | Use Case |
|----------|-------------|----------|
| `otel.lab.informationcart.com` | Browser (oauth2-proxy) | Human users, Swagger UI |
| `api.lab.informationcart.com` | M2M Bearer token | Agents, scripts, CI/CD |

---

## Security Considerations

1. **Token Scope Validation**: M2M middleware should enforce scope requirements per endpoint
2. **Rate Limiting**: Add rate limits to M2M ingress to prevent abuse
3. **Audit Logging**: Log all M2M requests with client_id for traceability
4. **Secret Rotation**: Plan for periodic M2M client secret rotation
5. **Network Policy**: Restrict m2m-middleware to only talk to otel-demo service

---

## Observability Integration

Both oauth2-proxy and m2m-auth-middleware metrics flow to the same Grafana dashboard:

| Panel | Data Source |
|-------|-------------|
| Browser Auth Rate | oauth2-proxy metrics |
| M2M Auth Rate | m2m-middleware metrics |
| Combined Error Rate | Both sources |
| Token Validation Latency | m2m-middleware histogram |
| Active Sessions | oauth2-proxy gauge |

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| B.6 Observability | 2-3 hours | Prometheus + Grafana deployed |
| M2M Cognito Setup | 1 hour | Terraform access |
| M2M Middleware Dev | 4-6 hours | Python/FastAPI |
| M2M K8s Deploy | 2-3 hours | DNS, TLS |
| Testing & Docs | 2-3 hours | All above |

### Total Estimate: 12-16 hours

---

## Next Steps

1. **Start with B.6**: Enable oauth2-proxy metrics and create Grafana dashboard
2. **Then Cognito**: Add Resource Server and M2M client to Terraform
3. **Build Middleware**: Create the m2m-auth-middleware service
4. **Deploy & Test**: K8s manifests, DNS, end-to-end testing
