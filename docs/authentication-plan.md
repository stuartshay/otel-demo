# Authentication Rollout Plan (AWS Cognito + oauth2-proxy)

Opinionated plan to protect `otel-demo` with Cognito-backed OIDC and an ingress auth proxy, keeping the Flask app unchanged.

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

6) Observability and health
   - Add `oauth2-proxy` logs to your log pipeline; create a simple dashboard for login success/fail counts.
   - Keep existing liveness/readiness probes on the app; add them to the proxy Deployment as well.

7) Testing & rollout
   - Dry-run manifests (`kubeconform` / `kubectl kustomize`) before commit.
   - Deploy to a test namespace or apply a temporary host like `auth-test.lab.informationcart.com` to validate the flow.
   - Verify: login redirect works, cookies set, `/health` behavior as chosen, `/files` and `/db` blocked without auth.
   - Backout plan: remove auth annotations to bypass proxy; rollback image tag via GitOps if proxy is unhealthy.

8) Secrets handling
   - Never commit raw client secrets; seal them with `kubeseal` or encrypt with SOPS before adding to Git.
   - Document secret keys and expected env var names in the new manifests for consistency.

## Deliverables

- New manifests in `k8s-gitops/apps/base/otel-demo/` for `oauth2-proxy` (Deployment, Service, ConfigMap, SealedSecret, NetworkPolicy).
- Updated `ingress.yaml` with auth annotations and `/oauth2` backend.
- (Optional) Split ingress or paths to keep probes open and sensitive endpoints internal.
- README/docs updates describing the auth flow and operations (token expiry, how to add users).
