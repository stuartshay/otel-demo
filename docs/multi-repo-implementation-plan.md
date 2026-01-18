# Multi-Repo Implementation Plan

**Project**: otel-ui and otel-middleware repositories
**Created**: January 18, 2026
**Status**: Planning Phase

## Overview

Expand the otel-demo ecosystem with two new repositories:

- **otel-ui**: React frontend for consuming the otel-demo API
- **otel-middleware**: Python worker agent for background data processing
- **otel-types**: npm package with TypeScript types (generated from otel-demo)

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   otel-ui   │─────▶│  otel-demo   │◀─────│ otel-middleware
│  (React)    │      │  (Flask API) │      │  (Celery Workers)
└─────────────┘      └──────────────┘      └──────────────┘
       │                     │                      │
       │                     │                      │
       ▼                     ▼                      ▼
 @stuartshay/            PostgreSQL             Redis Queue
  otel-types            (owntracks)
  (npm package)         NFS Storage
```

---

## Phase 1: npm Types Package (otel-demo enhancement)

### Objectives

- Generate TypeScript types from Swagger/OpenAPI spec
- Publish types to npm as `@stuartshay/otel-types`
- Sync package version with Docker image version
- Auto-publish on schema changes

### Tasks

#### 1.1: Create Package Structure

- [ ] Create `otel-demo/packages/otel-types/` directory
- [ ] Add `package.json` with metadata
  - Package name: `@stuartshay/otel-types`
  - Version: synced from Docker build (`1.0.x`)
  - Description: "TypeScript types for otel-demo API"
  - License: MIT
- [ ] Add `.npmignore` for clean package
- [ ] Add README.md with usage instructions

#### 1.2: Type Generation Script

- [ ] Add script to fetch `/apispec.json` from running container
- [ ] Install `openapi-typescript` as dev dependency
- [ ] Create generation script: `scripts/generate-types.sh`
- [ ] Output types to `packages/otel-types/index.d.ts`
- [ ] Validate generated types with TypeScript compiler

#### 1.3: npm Token Setup

- [ ] Generate granular access token at npmjs.com
  - Token type: Granular Access Token
  - Expiration: 1 year (custom date)
  - Permissions: Read and write
  - Packages: `@stuartshay/otel-types`
  - IP Ranges: Empty (GitHub Actions)
- [ ] Add `NPM_TOKEN` to GitHub repository secrets
- [ ] Document token rotation in `docs/operations.md`

#### 1.4: GitHub Actions Integration

- [ ] Extend `.github/workflows/docker.yml` with schema detection
  - Add job: `detect-schema-changes`
  - Use `git diff HEAD~1 HEAD -- app/blueprints/ app/extensions.py`
  - Trigger on: releases, schema file changes, manual dispatch
- [ ] Add job: `publish-types` (runs after schema changes detected)
  - Start otel-demo container
  - Fetch `/apispec.json`
  - Generate types with `openapi-typescript`
  - Update `package.json` version
  - Publish to npm with `NPM_TOKEN`
- [ ] Add manual trigger option: `[schema-change]` in commit message

**Deliverables**:

- `packages/otel-types/package.json`
- `scripts/generate-types.sh`
- Updated `.github/workflows/docker.yml`
- `@stuartshay/otel-types` published to npm

---

## Phase 2: otel-ui Repository

### Objectives

- Create React frontend consuming otel-demo API
- Implement OAuth2 authentication with Cognito
- Display trace IDs for observability
- Deploy to K8s with GitOps

### Tasks

#### 2.1: Repository Setup

- [ ] Create new GitHub repository: `stuartshay/otel-ui`
- [ ] Initialize with Vite + React + TypeScript

  ```bash
  npm create vite@latest otel-ui -- --template react-ts
  ```

- [ ] Copy standard files from otel-demo:
  - `.github/workflows/lint.yml` (adapted for Node.js)
  - `.github/workflows/docker.yml` (nginx container)
  - `.pre-commit-config.yaml` (ESLint, Prettier)
  - `.gitignore` (Node.js template)
  - `AGENTS.md` → `.github/copilot-instructions.md`
  - `renovate.json` (dependency updates)

#### 2.2: Development Environment

- [ ] Create `setup.sh` script (Node.js version)
  - Check Node.js/npm installation (recommend nvm)
  - Install dependencies: `npm install`
  - Setup pre-commit hooks
  - Create `.env.example`
- [ ] Add development dependencies:
  - ESLint + TypeScript plugin
  - Prettier
  - Vitest (testing)

#### 2.3: Type Package Integration

- [ ] Add dependency: `@stuartshay/otel-types@~1.0.0`
- [ ] Configure TypeScript to use generated types
- [ ] Create API client wrapper using types
  - Base URL from environment
  - Axios/fetch with interceptors
  - Error handling with trace IDs

#### 2.4: Authentication Implementation

- [ ] Install `oidc-client-ts` for OAuth2/PKCE
- [ ] Configure Cognito settings (from environment):
  - Domain: `homelab-auth.auth.us-east-1.amazoncognito.com`
  - Client ID: `5j475mtdcm4qevh7q115qf1sfj`
  - Redirect URI: `https://ui.lab.informationcart.com/callback`
- [ ] Implement auth provider/context
- [ ] Add login/logout flow
- [ ] Token refresh logic

#### 2.5: Core Components

- [ ] Dashboard layout with navigation
- [ ] API status component (calls `/info`)
- [ ] Owntracks locations viewer (calls `/db/locations`)
  - Table with pagination
  - Filters (user, device, date range)
  - Map view (optional)
- [ ] File browser (calls `/files`)
  - Directory listing
  - File upload/download
  - Delete operations
- [ ] Trace ID display component
  - Show in header
  - Link to New Relic (if available)
  - Copy to clipboard

#### 2.6: Docker Configuration

- [ ] Create multi-stage Dockerfile
  - Build stage: `node:20-alpine` + `npm run build`
  - Runtime stage: `nginx:alpine`
  - Copy build output to nginx html
- [ ] Add nginx.conf with SPA routing
  - Route all requests to index.html
  - Proxy `/api` to otel-demo (if needed)
- [ ] GitHub Actions for Docker build
  - Build on main branch
  - Push to Docker Hub: `stuartshay/otel-ui`
  - Version sync with semantic versioning

**Deliverables**:

- GitHub repository: `stuartshay/otel-ui`
- Docker image: `stuartshay/otel-ui:1.0.x`
- Local development environment
- Working authentication flow

---

## Phase 3: otel-middleware Repository

### Objectives

- Create Python worker agent for background processing
- Process data from otel-demo (PostgreSQL, NFS)
- Implement task queue with Celery + Redis
- Full OpenTelemetry instrumentation

### Tasks

#### 3.1: Repository Setup

- [ ] Create new GitHub repository: `stuartshay/otel-middleware`
- [ ] Mirror otel-demo structure:

  ```
  otel-middleware/
  ├── app/
  │   ├── __init__.py
  │   ├── config.py
  │   ├── celery_app.py
  │   ├── telemetry.py
  │   ├── workers/
  │   │   ├── __init__.py
  │   │   ├── data_transform.py
  │   │   ├── file_processor.py
  │   │   └── cleanup.py
  │   └── api/
  │       ├── __init__.py
  │       └── tasks.py (optional API)
  ├── scripts/
  ├── tests/
  ├── requirements.txt
  ├── Dockerfile
  └── setup.sh
  ```

- [ ] Copy standard files from otel-demo:
  - `pyproject.toml` (Ruff config)
  - `.pre-commit-config.yaml`
  - `.github/workflows/` (lint, docker)
  - `AGENTS.md` → `.github/copilot-instructions.md`

#### 3.2: Core Dependencies

- [ ] Python 3.12 base
- [ ] Celery 5.x (task queue)
- [ ] Redis client (celery broker/backend)
- [ ] psycopg2 (PostgreSQL access)
- [ ] OpenTelemetry instrumentation:
  - `opentelemetry-instrumentation-celery`
  - `opentelemetry-instrumentation-redis`
  - `opentelemetry-instrumentation-psycopg2`
- [ ] Optional: FastAPI (for HTTP task submission API)

#### 3.3: Worker Tasks

- [ ] **Data Transformation Worker**
  - Read from owntracks database
  - Aggregate location data
  - Calculate statistics (distance, time)
  - Store results back to DB or cache
- [ ] **File Processor Worker**
  - Process files from NFS storage
  - Image resizing/optimization
  - Format conversions
  - Generate thumbnails
- [ ] **Cleanup Worker**
  - Purge old location data (90+ days)
  - Remove orphaned files
  - Database vacuum/analyze
- [ ] **Scheduled Tasks** (Celery Beat)
  - Daily cleanup: 2 AM
  - Hourly aggregation
  - Health check ping

#### 3.4: Configuration

- [ ] Database connection (reuse otel-demo credentials)
  - Host: `192.168.1.175:6432` (PgBouncer)
  - Database: `owntracks`
- [ ] Redis configuration
  - Broker URL: `redis://redis:6379/0`
  - Result backend: `redis://redis:6379/1`
- [ ] OTel configuration (same as otel-demo)
  - Endpoint: `otel-collector.observability:4317`
  - Service name: `otel-middleware`

#### 3.5: OpenTelemetry Instrumentation

- [ ] Configure tracer in `telemetry.py`
- [ ] Auto-instrument Celery tasks
- [ ] Add custom spans for business logic
- [ ] Propagate trace context between workers
- [ ] Structured logging with trace IDs

#### 3.6: Optional HTTP API

- [ ] FastAPI app for task submission
- [ ] Endpoints:
  - `POST /tasks/transform` - Trigger data transformation
  - `POST /tasks/process-file` - Process specific file
  - `GET /tasks/{task_id}` - Get task status
  - `GET /health` - Worker health check
  - `GET /metrics` - Prometheus metrics
- [ ] Authentication: internal only (no public ingress)

#### 3.7: Docker Configuration

- [ ] Multi-stage Dockerfile
  - Base: `python:3.12-slim`
  - Worker mode: `celery -A app.celery_app worker`
  - Beat mode: `celery -A app.celery_app beat` (scheduler)
  - API mode (optional): `gunicorn app.api:app`
- [ ] GitHub Actions for Docker build
  - Build on main branch
  - Push to Docker Hub: `stuartshay/otel-middleware`

**Deliverables**:

- GitHub repository: `stuartshay/otel-middleware`
- Docker image: `stuartshay/otel-middleware:1.0.x`
- Working Celery workers
- Sample tasks implemented

---

## Phase 4: Kubernetes Deployment (k8s-gitops)

### Objectives

- Deploy otel-ui and otel-middleware to K8s
- Configure ingress and networking
- Integrate with existing infrastructure

### Tasks

#### 4.1: otel-ui Deployment

- [ ] Create manifests in `k8s-gitops/apps/base/otel-ui/`
  - `deployment.yaml` - nginx container with React build
  - `service.yaml` - ClusterIP service (port 80)
  - `ingress.yaml` - HTTPS ingress with oauth2-proxy
  - `configmap.yaml` - API endpoint URL
  - `kustomization.yaml`
- [ ] Ingress configuration:
  - Host: `ui.lab.informationcart.com`
  - TLS: Let's Encrypt (cert-manager)
  - Annotations: oauth2-proxy for authentication
  - Bypass: `/assets/*` (static files)
- [ ] Resources:
  - Requests: 10m CPU, 32Mi memory
  - Limits: 50m CPU, 64Mi memory
- [ ] Replicas: 1 (can scale later)

#### 4.2: otel-middleware Deployment

- [ ] Create Redis StatefulSet (or use existing)
  - Namespace: `otel-demo` or `middleware`
  - PVC: 1Gi for persistence
  - Service: `redis.otel-demo:6379`
- [ ] Create manifests in `k8s-gitops/apps/base/otel-middleware/`
  - `deployment-worker.yaml` - Celery worker pods
  - `deployment-beat.yaml` - Celery Beat scheduler (1 replica)
  - `deployment-api.yaml` (optional) - FastAPI for task submission
  - `service.yaml` (optional) - ClusterIP for API
  - `configmap.yaml` - Redis, DB, OTel config
  - `sealedsecret.yaml` - DB credentials (reuse from otel-demo)
  - `kustomization.yaml`
- [ ] Worker resources:
  - Requests: 50m CPU, 128Mi memory
  - Limits: 200m CPU, 256Mi memory
  - Replicas: 2 (scale based on queue length)
- [ ] No public ingress (internal only)

#### 4.3: DNS Configuration

- [ ] Add DNS record: `ui.lab.informationcart.com` → 192.168.1.100 (MetalLB)
- [ ] Optional: `worker.lab.informationcart.com` (if API exposed)
- [ ] Use Cloudflare DNS skill if available

#### 4.4: Argo CD Integration

- [ ] Add applications to `k8s-gitops/bootstrap/apps-app.yaml`:

  ```yaml
  - name: otel-ui
    path: apps/base/otel-ui
  - name: otel-middleware
    path: apps/base/otel-middleware
  ```

- [ ] Sync policy: Manual (for lab)
- [ ] Manual sync after deployment

#### 4.5: Testing & Validation

- [ ] Verify otel-ui accessibility: `https://ui.lab.informationcart.com`
- [ ] Test OAuth2 login flow
- [ ] Verify API calls to otel-demo
- [ ] Check worker logs: `kubectl logs -n otel-demo -l app=otel-middleware`
- [ ] Submit test task via API or Python script
- [ ] Verify traces in New Relic

**Deliverables**:

- K8s manifests in `k8s-gitops`
- Working ingress with TLS
- Running worker pods
- Argo CD applications configured

---

## Phase 5: Documentation & Operations

### Tasks

#### 5.1: Update otel-demo Documentation

- [ ] Update `README.md` with ecosystem overview
- [ ] Document schema change workflow in `docs/operations.md`
- [ ] Add npm package publishing process
- [ ] Document breaking change policy

#### 5.2: otel-ui Documentation

- [ ] Create `README.md` with:
  - Project overview
  - Local development setup
  - Build and deployment
  - Environment variables
  - Authentication configuration
- [ ] Add `docs/operations.md`:
  - Troubleshooting
  - Common issues
  - Type package updates

#### 5.3: otel-middleware Documentation

- [ ] Create `README.md` with:
  - Worker architecture
  - Task descriptions
  - Configuration options
  - Local development with Redis
- [ ] Add `docs/operations.md`:
  - Task submission examples
  - Monitoring workers
  - Celery troubleshooting
  - Scaling guidelines

#### 5.4: k8s-gitops Documentation

- [ ] Update `k8s-gitops/README.md` with new apps
- [ ] Document deployment process
- [ ] Add troubleshooting for oauth2-proxy issues

**Deliverables**:

- Comprehensive README files
- Operations guides
- Troubleshooting documentation

---

## Success Criteria

### otel-demo (Phase 1)

- [x] otel-demo API is production-ready
- [ ] npm package `@stuartshay/otel-types` published
- [ ] Schema changes auto-trigger type republishing
- [ ] Types match current API spec

### otel-ui (Phase 2)

- [ ] React app builds successfully
- [ ] OAuth2 authentication works
- [ ] Can fetch data from otel-demo API
- [ ] Trace IDs displayed in UI
- [ ] Deployed to K8s with HTTPS ingress

### otel-middleware (Phase 3)

- [ ] Celery workers running in K8s
- [ ] Redis connection established
- [ ] Can access otel-demo database
- [ ] Sample tasks execute successfully
- [ ] Traces appear in New Relic

### Integration (Phase 4)

- [ ] All three services communicating
- [ ] End-to-end flow working:
  - User logs into otel-ui
  - Submits task via UI
  - Worker processes task
  - Results visible in UI
- [ ] Distributed tracing across all services

---

## Timeline Estimates

| Phase | Estimated Time | Complexity |
|-------|----------------|------------|
| Phase 1: npm Types | 4-6 hours | Medium |
| Phase 2: otel-ui | 12-16 hours | High |
| Phase 3: otel-middleware | 10-14 hours | High |
| Phase 4: K8s Deployment | 6-8 hours | Medium |
| Phase 5: Documentation | 4-6 hours | Low |
| **Total** | **36-50 hours** | - |

---

## Risks & Mitigation

### Risk 1: Schema Drift

**Impact**: Frontend uses outdated types, API calls fail
**Mitigation**:

- Auto-publish types on schema changes
- Add pre-commit hook to detect schema modifications
- Version pinning with semver ranges

### Risk 2: Worker Failure

**Impact**: Tasks stuck in queue, data not processed
**Mitigation**:

- Celery task retries (3x with exponential backoff)
- Dead letter queue for failed tasks
- Monitoring with Prometheus/Grafana
- Alerting on queue length > 100

### Risk 3: Authentication Issues

**Impact**: Users can't access otel-ui
**Mitigation**:

- Test OAuth2 flow thoroughly in dev
- Document Cognito troubleshooting
- Health checks bypass authentication
- Fallback to token-based auth for testing

### Risk 4: Database Connection Pool Exhaustion

**Impact**: Workers and API compete for connections
**Mitigation**:

- Use PgBouncer (already configured)
- Separate connection pools for API vs workers
- Monitor connection usage
- Scale PgBouncer if needed

---

## Next Steps

1. **Review this plan** with stakeholder
2. **Decide starting point**:
   - Option A: Start with Phase 1 (types package) - builds foundation
   - Option B: Start with Phase 2 (otel-ui) - delivers user value first
   - Option C: Start with Phase 3 (otel-middleware) - backend-first approach
3. **Setup repositories** in GitHub
4. **Configure npm account** for package publishing
5. **Begin implementation** phase by phase

---

## References

- [otel-demo Repository](https://github.com/stuartshay/otel-demo)
- [k8s-gitops Repository](https://github.com/stuartshay/k8s-gitops)
- [homelab-infrastructure Repository](https://github.com/stuartshay/homelab-infrastructure)
- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [oidc-client-ts](https://github.com/authts/oidc-client-ts)
- [openapi-typescript](https://github.com/drwpow/openapi-typescript)
