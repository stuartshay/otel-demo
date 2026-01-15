# Authentication Implementation Quick Reference

This document provides a quick reference companion to `authentication-plan.md` for implementing AWS Cognito + oauth2-proxy authentication.

## Status

**Planning Phase** - The authentication system is not yet implemented. This is a future enhancement.

## Prerequisites Checklist

Before starting implementation:

- [ ] AWS account with permissions to create Cognito resources
- [ ] Access to k8s-gitops repository for manifest updates
- [ ] kubectl/kubeseal/SOPS tooling configured
- [ ] NGINX Ingress Controller deployed in cluster
- [ ] SSL/TLS certificate configured for `otel-demo.lab.informationcart.com`

## Quick Implementation Path

### Phase 1: AWS Cognito Setup (30 mins)

1. Create User Pool in AWS Console
2. Enable email sign-in + hosted UI
3. Create App Client with PKCE (no client secret for browser flow)
4. Configure domain prefix
5. Set callback URL: `https://otel-demo.lab.informationcart.com/oauth2/callback`
6. Note down: User Pool ID, Client ID, Region

### Phase 2: oauth2-proxy Deployment (1 hour)

**Key values to configure:**

```yaml
# In k8s-gitops/apps/base/otel-demo/oauth2-proxy-configmap.yaml
OIDC_ISSUER_URL: "https://cognito-idp.<region>.amazonaws.com/<user-pool-id>"
OAUTH2_PROXY_CLIENT_ID: "<client-id-from-cognito>"
OAUTH2_PROXY_REDIRECT_URL: "https://otel-demo.lab.informationcart.com/oauth2/callback"
OAUTH2_PROXY_UPSTREAMS: "http://otel-demo:8080"
OAUTH2_PROXY_EMAIL_DOMAINS: "*"  # or restrict to specific domains
```

**Required secrets (SealedSecret):**

```yaml
# Seal these values before committing
OAUTH2_PROXY_CLIENT_SECRET: "<from-cognito-if-using-confidential-client>"
OAUTH2_PROXY_COOKIE_SECRET: "<random-32-byte-base64-string>"
```

Generate cookie secret:

```bash
python -c 'import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())'
```

### Phase 3: Ingress Configuration (30 mins)

Add to existing `ingress.yaml`:

```yaml
annotations:
  nginx.ingress.kubernetes.io/auth-url: "https://$host/oauth2/auth"
  nginx.ingress.kubernetes.io/auth-signin: "https://$host/oauth2/start?rd=$escaped_request_uri"
```

Add oauth2-proxy backend:

```yaml
- path: /oauth2
  pathType: Prefix
  backend:
    service:
      name: oauth2-proxy
      port:
        number: 4180
```

### Phase 4: Health Endpoints (Optional)

If keeping `/health` and `/ready` unauthenticated:

```yaml
annotations:
  nginx.ingress.kubernetes.io/configuration-snippet: |
    location ~* ^/(health|ready)$ {
      auth_request off;
      proxy_pass http://otel-demo.otel-demo.svc.cluster.local:8080;
    }
```

## Testing the Implementation

### 1. Test oauth2-proxy is running

```bash
kubectl get pods -n otel-demo -l app=oauth2-proxy
kubectl logs -n otel-demo -l app=oauth2-proxy --tail=50
```

### 2. Test the authentication flow

```bash
# Should redirect to Cognito login
curl -I https://otel-demo.lab.informationcart.com/

# After successful login, should reach the app
curl -b cookies.txt -c cookies.txt -L https://otel-demo.lab.informationcart.com/
```

### 3. Verify protected endpoints

```bash
# Should be protected
curl -I https://otel-demo.lab.informationcart.com/files
curl -I https://otel-demo.lab.informationcart.com/db/status

# If configured to be open
curl -I https://otel-demo.lab.informationcart.com/health  # Should return 200
```

### 4. Test API access with token

```bash
# Get a token using the CLI tool
export COGNITO_TOKEN_URL="https://<domain>.auth.<region>.amazoncognito.com/oauth2/token"
export COGNITO_CLIENT_ID="<client-id>"
export COGNITO_CLIENT_SECRET="<client-secret>"
export COGNITO_SCOPE="openid email profile"

python scripts/token_cli.py --output header

# Use the token
curl -H "Authorization: Bearer <token>" https://otel-demo.lab.informationcart.com/db/status
```

## Swagger UI Options

### Option A: Proxy-based (Simplest)

Users authenticate once via oauth2-proxy, then can use all Swagger endpoints.

- ✅ Simple to implement
- ✅ No app code changes
- ❌ Can't test API directly with tokens

### Option B: OAuth2 in Swagger UI

Users click "Authorize" button in Swagger, complete OAuth2 flow.

- ✅ Native OAuth2 experience
- ✅ Can test APIs directly
- ❌ Requires app code changes
- ❌ More complex configuration

**Required changes:**

1. Update `app/extensions.py` to add `securityDefinitions`:

```python
swagger_template = {
    # ... existing config ...
    "securityDefinitions": {
        "OAuth2": {
            "type": "oauth2",
            "flow": "authorizationCode",
            "authorizationUrl": "https://<domain>.auth.<region>.amazoncognito.com/oauth2/authorize",
            "tokenUrl": "https://<domain>.auth.<region>.amazoncognito.com/oauth2/token",
            "scopes": {
                "openid": "OpenID",
                "email": "Email",
                "profile": "Profile"
            }
        }
    },
    "security": [{"OAuth2": ["openid", "email", "profile"]}]
}
```

2. Update `app/config.py` to add OAuth2 settings
3. Configure ingress to allow `/apidocs/o2c.html` (OAuth callback)

### Option C: Bearer Token (Testing-friendly)

Users paste JWT tokens into Swagger UI manually.

- ✅ Simple to implement
- ✅ Good for testing with `token_cli.py`
- ❌ Manual token management

**Required changes:**

```python
swagger_template = {
    # ... existing config ...
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter: Bearer <token>"
        }
    },
    "security": [{"Bearer": []}]
}
```

## Rollback Plan

If authentication causes issues:

1. **Quick rollback** - Remove auth annotations from ingress:

```bash
kubectl patch ingress otel-demo -n otel-demo --type=json \
  -p='[{"op": "remove", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1auth-url"}]'
```

2. **Full rollback** - Revert k8s-gitops commit and re-sync

## Security Checklist

- [ ] Secrets sealed with kubeseal or encrypted with SOPS
- [ ] Callback URLs match exactly (no trailing slashes)
- [ ] Email domain restrictions configured appropriately
- [ ] TLS enabled on ingress
- [ ] Cookie secret is strong (32 bytes minimum)
- [ ] `/files` and `/db` endpoints protected
- [ ] Health endpoints accessibility decided and configured
- [ ] Rate limiting configured on ingress
- [ ] Logs being collected from oauth2-proxy

## Common Issues

### Issue: Redirect loop

**Cause**: Misconfigured auth-url or auth-signin annotations

**Fix**: Verify annotations use `$host` not hardcoded hostname

### Issue: 401 Unauthorized

**Cause**: Cookie not being set or expired

**Fix**: Check cookie domain settings, verify cookie secret matches

### Issue: Cognito "invalid redirect_uri"

**Cause**: Callback URL mismatch

**Fix**: Ensure exact match in Cognito console (no trailing slash)

### Issue: Can't access health endpoints

**Cause**: Auth protecting all paths

**Fix**: Add configuration-snippet to bypass auth for specific paths

## References

- Main plan: [authentication-plan.md](./authentication-plan.md)
- Token CLI tool: [scripts/token_cli.py](../scripts/token_cli.py)
- k8s-gitops repo: <https://github.com/stuartshay/k8s-gitops>
- oauth2-proxy docs: <https://oauth2-proxy.github.io/oauth2-proxy/>
- AWS Cognito docs: <https://docs.aws.amazon.com/cognito/>
- Flasgger OAuth2: <https://github.com/flasgger/flasgger>
