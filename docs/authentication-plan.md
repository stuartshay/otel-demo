# Authentication Rollout Plan (AWS Cognito + oauth2-proxy)

**Status**: Planning document for future implementation

**Quick Start**: See [authentication-quickstart.md](./authentication-quickstart.md) for step-by-step implementation guide.

Opinionated plan to protect `otel-demo` with Cognito-backed OIDC and an ingress auth proxy, keeping the Flask app unchanged.

## Current State

The otel-demo application currently has:

- ✅ Health endpoints (`/health`, `/ready`) - unprotected, suitable for K8s probes
- ✅ Swagger UI (`/apidocs`) - currently open, ready for OAuth2 integration
- ✅ File operations (`/files/*`) - unprotected, will benefit from authentication
- ✅ Database operations (`/db/*`) - unprotected, will benefit from authentication
- ✅ Token CLI utility (`scripts/token_cli.py`) - ready for OAuth2 client credentials flow
- ❌ No authentication layer - this plan adds it at the ingress level

## Objectives

- Require sign-in for all HTTP traffic (health/ready may stay open if desired).
- Keep credentials out of the app; terminate auth at the edge.
- Preserve GitOps (manifests in `k8s-gitops`) and sealed secrets for secrets at rest.

## Architecture

- **IdP**: AWS Cognito User Pool + App Client (PKCE) + hosted UI.
- **Auth proxy**: `oauth2-proxy` Deployment + Service in `otel-demo` namespace.
- **Ingress**: NGINX Ingress enforces `oauth2-proxy` via auth annotations; TLS already terminates at ingress.
- **Secrets**: Cognito client ID/secret and cookie secret stored as SealedSecrets/SOPS.
- **App**: Remains HTTP-only inside cluster; no JWT parsing in Flask.

## Work Plan

1) Cognito setup (AWS Console)
   - Create User Pool; enable email sign-in; enable hosted UI.
   - Create App Client (public) with PKCE, no client secret for browser flow; scopes: `openid`, `email`, `profile`.
   - Configure domain (prefix) and callbacks: `https://otel-demo.lab.informationcart.com/oauth2/callback`. Sign-out URL: `https://otel-demo.lab.informationcart.com/`.
   - (Optional) Create a second App Client with client secret for server-to-server/mTLS paths if needed.

2) Proxy configuration (values to capture)
   - `OIDC_ISSUER_URL`: `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`
   - `OIDC_CLIENT_ID`: from Cognito App Client (PKCE).
   - `COOKIE_SECRET`: 16/24/32-byte base64 string (random).
   - Allowed email domains/user IDs to keep homelab tight.

3) Kubernetes additions (in `k8s-gitops/apps/base/otel-demo/`)
   - Add `oauth2-proxy` Deployment + Service (small resources; mount no volumes; readiness probe enabled).
   - Add SealedSecret for `client_id`, `client_secret` (if using secret-bearing client), `cookie_secret`.
   - Add ConfigMap for proxy static config (issuer URL, redirect URL, scopes, email-domain allowlist).
   - Add NetworkPolicy to allow ingress -> oauth2-proxy -> app only.

4) Ingress changes
   - Update `ingress.yaml` to route `/oauth2/*` to `oauth2-proxy`.
   - Add NGINX auth annotations (e.g., `nginx.ingress.kubernetes.io/auth-url` and `auth-signin`) pointing to the proxy.
   - Decide probe exposure: either keep `/health` and `/ready` unauthenticated with `nginx.ingress.kubernetes.io/auth-snippet` exceptions, or protect everything.

5) Application hardening (optional but recommended)
   - Restrict `/files` and `/db` endpoints to authenticated traffic only by ingress rules; consider IP allowlist for `/db`.
   - If public exposure is unnecessary, create an internal-only ingress (no external host) for those paths and drop them from the public ingress.
   - Add rate limits at ingress (`nginx.ingress.kubernetes.io/limit-*`) to reduce brute-force noise.

6) Swagger UI auth experience
   - Enable OAuth2 authorize button in Swagger UI using Cognito authorization code + PKCE:
     - Add OpenAPI security scheme (type `oauth2`, flow `authorizationCode`) pointing to Cognito authorize/token endpoints, and set default scopes (`openid`, `email`, `profile`).
     - Set `SWAGGER_OAUTH_CLIENT_ID` and `SWAGGER_OAUTH_SCOPE_SEPARATOR` env vars (Flasgger supports forwarding to Swagger UI); use the same callback as the app: `https://otel-demo.lab.informationcart.com/oauth2/callback`.
     - Add a dedicated ingress path `/swagger-callback` (or reuse `/oauth2/callback` if allowed by oauth2-proxy) and permit it through auth annotations so the OAuth handshake completes.
   - If you prefer bearer token entry only: add an `http` bearer security scheme and require it on routes so the “Authorize” modal accepts a pasted JWT (from Cognito or an internal token issuer).
   - Ensure `/apidocs` and `/apispec.json` remain behind oauth2-proxy; only the OAuth callback should bypass auth checks.

7) Observability and health
   - Add `oauth2-proxy` logs to your log pipeline; create a simple dashboard for login success/fail counts.
   - Keep existing liveness/readiness probes on the app; add them to the proxy Deployment as well.

8) Testing & rollout
   - Dry-run manifests (`kubeconform` / `kubectl kustomize`) before commit.
   - Deploy to a test namespace or apply a temporary host like `auth-test.lab.informationcart.com` to validate the flow.
   - Verify: login redirect works, cookies set, `/health` behavior as chosen, `/files` and `/db` blocked without auth.
   - Backout plan: remove auth annotations to bypass proxy; rollback image tag via GitOps if proxy is unhealthy.

9) Secrets handling
   - Never commit raw client secrets; seal them with `kubeseal` or encrypt with SOPS before adding to Git.
   - Document secret keys and expected env var names in the new manifests for consistency.

10) Token utility (manual/testing)
    - Use `scripts/token_cli.py` to fetch a Cognito token via client credentials for curl/Swagger testing:

      ```bash
      export COGNITO_TOKEN_URL="https://<domain>/oauth2/token"
      export COGNITO_CLIENT_ID="..."
      export COGNITO_CLIENT_SECRET="..."
      export COGNITO_SCOPE="openid email profile"
      python scripts/token_cli.py --output header
      ```

    - Outputs either the raw token, an Authorization header, or the full JSON (`--output token|header|json`).
    - Keep the client secret in environment/SealedSecrets; do not commit it or paste into logs. Local development can load these values from your gitignored `.env`.

## Deliverables

- New manifests in `k8s-gitops/apps/base/otel-demo/` for `oauth2-proxy` (Deployment, Service, ConfigMap, SealedSecret, NetworkPolicy).
- Updated `ingress.yaml` with auth annotations and `/oauth2` backend.
- (Optional) Split ingress or paths to keep probes open and sensitive endpoints internal.
- README/docs updates describing the auth flow and operations (token expiry, how to add users).
