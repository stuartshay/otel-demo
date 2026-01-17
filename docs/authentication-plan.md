# Authentication Rollout Plan (AWS Cognito + oauth2-proxy)

Opinionated plan to protect `otel-demo` with Cognito-backed OIDC and an ingress auth proxy, keeping the Flask app unchanged.

## Implementation Phases

This rollout is split into independent phases that can be executed separately:

| Phase | Scope | Repository | Dependencies |
|-------|-------|------------|--------------|
| **A** | AWS Cognito setup (external IdP) | homelab-infrastructure | None |
| **B** | K8s auth integration (oauth2-proxy) | k8s-gitops | Phase A outputs |
| **C** | Application validation (Swagger) | otel-demo | Phase A + B complete |

## Implementation Checklist

### Phase A: AWS Infrastructure (homelab-infrastructure)

| Step | Task | Status |
|------|------|--------|
| A.1 | Create homelab-infrastructure repo | ❌ Not started |
| A.2 | Bootstrap Terraform state backend (S3 + DynamoDB) | ❌ Not started |
| A.3 | Create Cognito module (User Pool, App Client, domain) | ❌ Not started |
| A.4 | Apply Terraform and capture outputs | ❌ Not started |

### Phase B: Kubernetes Deployment (k8s-gitops)

| Step | Task | Status |
|------|------|--------|
| B.1 | NetworkPolicy (defense-in-depth) | ❌ Not started |
| B.2 | oauth2-proxy manifests (Deployment, Service, ConfigMap) | ❌ Not started |
| B.3 | SealedSecrets (client_id, cookie_secret) | ❌ Not started |
| B.4 | Ingress changes (auth annotations + health bypass) | ❌ Not started |
| B.5 | Application hardening (rate limits, IP allowlist) | ❌ Not started |
| B.6 | Observability (proxy logs/dashboard) | ❌ Not started |
| B.7 | Testing & rollout (dry-run, backout plan) | ❌ Not started |

### Phase C: Application Validation (otel-demo)

| Step | Task | Status |
|------|------|--------|
| C.1 | Token utility (CLI for testing) | ✅ Complete |
| C.2 | Swagger UI auth validation (end-to-end test) | ❌ Not started |

## Project Responsibilities

| Component | Repository | Path |
|-----------|------------|------|
| Terraform state backend | homelab-infrastructure | `terraform/modules/terraform-backend/` |
| Cognito IaC (Terraform) | homelab-infrastructure | `terraform/modules/cognito/` |
| Cognito environment config | homelab-infrastructure | `terraform/environments/prod/` |
| oauth2-proxy manifests | k8s-gitops | `apps/base/otel-demo/` |
| NetworkPolicy | k8s-gitops | `apps/base/otel-demo/networkpolicy.yaml` |
| Ingress (auth annotations) | k8s-gitops | `apps/base/otel-demo/ingress.yaml` |
| Swagger security config | otel-demo | `app/extensions.py` |
| Token CLI | otel-demo | `scripts/token_cli.py` |

## Integration Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    homelab-infrastructure                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  terraform apply                                             │    │
│  │  └── outputs: user_pool_id, client_id, issuer_url, domain   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         Manual or CI/CD bridge
                    (seal outputs into K8s secrets)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         k8s-gitops                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SealedSecret (cognito credentials)                          │    │
│  │  oauth2-proxy Deployment + Service                           │    │
│  │  Ingress with auth annotations                               │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          otel-demo                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  token_cli.py → test token generation                        │    │
│  │  Swagger UI → validate end-to-end auth flow                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Objectives

- Require sign-in for all HTTP traffic; `/health` and `/ready` bypass authentication for K8s probes.
- Keep credentials out of the app; terminate auth at the edge.
- Preserve GitOps (manifests in `k8s-gitops`) and sealed secrets for secrets at rest.
- Separate external cloud infrastructure (AWS) from local K8s deployment.

## Architecture

- **IdP**: AWS Cognito User Pool + App Client (PKCE) + hosted UI.
- **Auth proxy**: `oauth2-proxy` Deployment + Service in `otel-demo` namespace.
- **Ingress**: NGINX Ingress enforces `oauth2-proxy` via auth annotations; TLS already terminates at ingress.
- **Secrets**: Cognito client ID/secret and cookie secret stored as SealedSecrets/SOPS.
- **App**: Remains HTTP-only inside cluster; no JWT parsing in Flask.

---

## Phase A: AWS Infrastructure (homelab-infrastructure)

### A.1) Create homelab-infrastructure repository

New repository for external cloud infrastructure that the homelab consumes:

```
homelab-infrastructure/
├── README.md
├── AGENTS.md
├── .github/
│   └── copilot-instructions.md
├── .gitignore
├── .pre-commit-config.yaml
├── terraform/
│   ├── modules/
│   │   ├── terraform-backend/     # S3 + DynamoDB for state (bootstrap)
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── cognito/               # User pools, app clients
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── dns/                   # Route53 (future)
│   └── environments/
│       └── prod/
│           ├── main.tf            # Module instantiation
│           ├── backend.tf         # S3 backend config
│           ├── providers.tf       # AWS provider
│           ├── outputs.tf
│           └── terraform.tfvars   # Variable values (gitignored secrets)
├── scripts/
│   └── bootstrap.sh               # One-time state backend setup
└── docs/
    └── cognito-setup.md
```

**Why separate repo:**

- Different lifecycle (Terraform plan/apply vs GitOps sync)
- Different credentials (AWS IAM vs K8s RBAC)
- Reusable across multiple apps (not just otel-demo)
- Clean separation: external services vs internal K8s resources

### A.2) Bootstrap Terraform state backend

One-time setup for remote state storage:

```hcl
# terraform/modules/terraform-backend/main.tf
resource "aws_s3_bucket" "terraform_state" {
  bucket = "homelab-terraform-state"

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name      = "Terraform State"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "homelab-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name      = "Terraform Lock Table"
    ManagedBy = "terraform"
  }
}
```

**Bootstrap process:**

```bash
# First run uses local state to create the backend
cd terraform/modules/terraform-backend
terraform init
terraform apply

# Then migrate to remote state
cd ../../environments/prod
terraform init -backend-config="bucket=homelab-terraform-state"
```

### A.3) Create Cognito module

```hcl
# terraform/modules/cognito/main.tf
resource "aws_cognito_user_pool" "main" {
  name = var.user_pool_name

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

# Browser flow client (PKCE, no secret)
resource "aws_cognito_user_pool_client" "browser" {
  name         = "${var.user_pool_name}-browser"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

# Server-to-server client (with secret for token_cli.py)
resource "aws_cognito_user_pool_client" "server" {
  name         = "${var.user_pool_name}-server"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true

  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}
```

```hcl
# terraform/modules/cognito/outputs.tf
output "user_pool_id" {
  value       = aws_cognito_user_pool.main.id
  description = "Cognito User Pool ID"
}

output "user_pool_arn" {
  value       = aws_cognito_user_pool.main.arn
  description = "Cognito User Pool ARN"
}

output "issuer_url" {
  value       = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  description = "OIDC Issuer URL for oauth2-proxy"
}

output "domain" {
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
  description = "Cognito hosted UI domain"
}

output "browser_client_id" {
  value       = aws_cognito_user_pool_client.browser.id
  description = "Browser client ID (PKCE, no secret)"
}

output "server_client_id" {
  value       = aws_cognito_user_pool_client.server.id
  description = "Server client ID (with secret)"
}

output "server_client_secret" {
  value       = aws_cognito_user_pool_client.server.client_secret
  sensitive   = true
  description = "Server client secret (for token_cli.py)"
}

data "aws_region" "current" {}
```

### A.4) Apply Terraform and capture outputs

```hcl
# terraform/environments/prod/main.tf
module "cognito" {
  source = "../../modules/cognito"

  user_pool_name = "homelab-users"
  domain_prefix  = "homelab-auth"

  callback_urls = [
    "https://otel-demo.lab.informationcart.com/oauth2/callback",
  ]

  logout_urls = [
    "https://otel-demo.lab.informationcart.com/",
  ]

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Project     = "homelab-infrastructure"
  }
}

output "cognito_issuer_url" {
  value = module.cognito.issuer_url
}

output "cognito_domain" {
  value = module.cognito.domain
}

output "cognito_browser_client_id" {
  value = module.cognito.browser_client_id
}

output "cognito_server_client_id" {
  value = module.cognito.server_client_id
}

output "cognito_server_client_secret" {
  value     = module.cognito.server_client_secret
  sensitive = true
}
```

**Apply and capture:**

```bash
cd terraform/environments/prod
terraform apply

# Capture outputs for Phase B
terraform output -json > /tmp/cognito-outputs.json

# Or export for immediate use
export COGNITO_ISSUER_URL=$(terraform output -raw cognito_issuer_url)
export COGNITO_CLIENT_ID=$(terraform output -raw cognito_browser_client_id)
```

---

## Phase B: Kubernetes Deployment (k8s-gitops)

### B.1) NetworkPolicy (defense-in-depth)

Deploy NetworkPolicy **before** oauth2-proxy to establish baseline traffic restrictions:

```yaml
# k8s-gitops/apps/base/otel-demo/networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: otel-demo-ingress-only
  namespace: otel-demo
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: otel-demo
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from ingress-nginx only
    - from:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Allow DNS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
    # Allow to OTel Collector
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: observability
      ports:
        - protocol: TCP
          port: 4317
```

**Validation:**

```bash
kubectl describe networkpolicy -n otel-demo
# Test direct pod access is blocked (should fail from non-ingress pod):
kubectl run test --rm -it --image=alpine -- wget -qO- http://otel-demo.otel-demo.svc:8080/health
```

Update `kustomization.yaml` to include `networkpolicy.yaml`. After oauth2-proxy is added, update NetworkPolicy to allow ingress → oauth2-proxy → otel-demo chain.

### B.2) oauth2-proxy manifests

- Add `oauth2-proxy` Deployment + Service (small resources; mount no volumes; readiness probe enabled).
- Add ConfigMap for proxy static config (issuer URL, redirect URL, scopes, email-domain allowlist).

### B.3) SealedSecrets

Create SealedSecret from Phase A outputs:

```bash
# Generate cookie secret
COOKIE_SECRET=$(openssl rand -base64 32 | head -c 32)

# Create K8s secret (not committed)
kubectl create secret generic oauth2-proxy-secrets \
  --namespace=otel-demo \
  --from-literal=client-id="$COGNITO_CLIENT_ID" \
  --from-literal=cookie-secret="$COOKIE_SECRET" \
  --dry-run=client -o yaml | kubeseal --format yaml \
  > k8s-gitops/apps/base/otel-demo/oauth2-proxy-sealed-secret.yaml
```

### B.4) Ingress changes

- Update `ingress.yaml` to route `/oauth2/*` to `oauth2-proxy`.
- Add NGINX auth annotations pointing to the proxy.

**Health/Ready Bypass (required for K8s probes):**

```yaml
# Add to ingress.yaml annotations
metadata:
  annotations:
    nginx.ingress.kubernetes.io/auth-url: "http://oauth2-proxy.otel-demo.svc.cluster.local/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://otel-demo.lab.informationcart.com/oauth2/start?rd=$escaped_request_uri"
    nginx.ingress.kubernetes.io/auth-snippet: |
      # Bypass auth for health and ready endpoints (K8s probes)
      if ($request_uri ~* "^/(health|ready)$") {
        return 200;
      }
```

This ensures `/health` and `/ready` remain unauthenticated for liveness/readiness probes while all other endpoints require authentication.

### B.5) Application hardening (optional but recommended)

- Restrict `/files` and `/db` endpoints to authenticated traffic only by ingress rules; consider IP allowlist for `/db`.
- If public exposure is unnecessary, create an internal-only ingress (no external host) for those paths and drop them from the public ingress.
- Add rate limits at ingress (`nginx.ingress.kubernetes.io/limit-*`) to reduce brute-force noise.

### B.6) Observability and health

- Add `oauth2-proxy` logs to your log pipeline; create a simple dashboard for login success/fail counts.
- Keep existing liveness/readiness probes on the app; add them to the proxy Deployment as well.

### B.7) Testing & rollout

- Dry-run manifests (`kubeconform` / `kubectl kustomize`) before commit.
- Deploy to a test namespace or apply a temporary host like `auth-test.lab.informationcart.com` to validate the flow.
- Verify: login redirect works, cookies set, `/health` returns 200 without auth, `/files` and `/db` blocked without auth.

**Rollback procedure:**

1. Remove auth annotations from ingress:

   ```bash
   kubectl annotate ingress otel-demo nginx.ingress.kubernetes.io/auth-url- -n otel-demo
   kubectl annotate ingress otel-demo nginx.ingress.kubernetes.io/auth-signin- -n otel-demo
   ```

2. Scale oauth2-proxy to 0: `kubectl scale deploy oauth2-proxy --replicas=0 -n otel-demo`
3. Commit and push to trigger Argo CD sync.

---

## Phase C: Application Validation (otel-demo)

### C.1) Token utility (manual/testing) ✅ Complete

Use `scripts/token_cli.py` to fetch a Cognito token via client credentials for curl/Swagger testing:

```bash
# Use server client from Phase A outputs
export COGNITO_TOKEN_URL="https://<domain>/oauth2/token"
export COGNITO_CLIENT_ID="<server_client_id>"
export COGNITO_CLIENT_SECRET="<server_client_secret>"
export COGNITO_SCOPE="openid email profile"
python scripts/token_cli.py --output header
```

- Outputs either the raw token, an Authorization header, or the full JSON (`--output token|header|json`).
- Keep the client secret in environment/SealedSecrets; do not commit it or paste into logs. Local development can load these values from your gitignored `.env`.

### C.2) Swagger UI auth validation (final step)

Use Swagger UI as the final validation checkpoint after all auth components are deployed.

**Test OAuth2 flow (browser):**

1. Navigate to `/apidocs/` (should redirect through oauth2-proxy to Cognito login).
2. Complete login with Cognito hosted UI.
3. After redirect, click "Authorize" in Swagger UI.
4. Execute a protected endpoint (e.g., `GET /db/test`) and verify 200 response.

**Test bearer token flow (CLI + Swagger):**

1. Generate token: `python scripts/token_cli.py --output token`
2. In Swagger UI, click "Authorize" → paste token in bearerAuth field.
3. Execute protected endpoints and verify success.

**Validate error cases:**

- Expired token returns 401.
- Missing token returns 401.
- Invalid scope returns 403.

**Swagger security configuration** (add to `app/extensions.py`):

```python
# Add to swagger_template in extensions.py
"securityDefinitions": {
    "oauth2": {
        "type": "oauth2",
        "flow": "authorizationCode",
        "authorizationUrl": "https://<cognito-domain>/oauth2/authorize",
        "tokenUrl": "https://<cognito-domain>/oauth2/token",
        "scopes": {
            "openid": "OpenID Connect scope",
            "email": "Access email address",
            "profile": "Access user profile",
        },
    },
    "bearerAuth": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "description": "Bearer token (e.g., 'Bearer eyJ...')",
    },
},
"security": [{"oauth2": ["openid", "email"]}],
```

Document successful validation in PR before merging auth rollout.

---

## Deliverables

### Phase A (homelab-infrastructure)

- New `homelab-infrastructure` GitHub repository.
- Terraform state backend module (S3 + DynamoDB).
- Cognito module with User Pool, browser client (PKCE), server client (secret).
- Production environment config with outputs.

### Phase B (k8s-gitops)

- New manifests in `apps/base/otel-demo/` for `oauth2-proxy` (Deployment, Service, ConfigMap, SealedSecret, NetworkPolicy).
- Updated `ingress.yaml` with auth annotations, `/oauth2` backend, and health/ready bypass.

### Phase C (otel-demo)

- Swagger security configuration in `app/extensions.py`.
- Token CLI (`scripts/token_cli.py`) — already complete.
- README/docs updates describing the auth flow and operations (token expiry, how to add users).
