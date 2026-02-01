# Version Management Guide

This document describes how version management works for otel-demo.

## Overview

otel-demo uses **manual semantic versioning** with a `VERSION` file as the single source of truth. The CI workflow reads this file to tag Docker images consistently across branches.

## Version Format

Versions follow **semantic versioning** (semver):

```
MAJOR.MINOR.PATCH
```

Example: `1.0.84`

- **MAJOR**: Breaking changes (currently fixed at 1)
- **MINOR**: New features (incremented for minor releases)
- **PATCH**: Bug fixes and patches (incremented for each release)

## Current Workflow

### Automated (CI)

When you push to `main`:

1. GitHub Actions reads `VERSION` file
2. Validates semver format (`x.y.z`)
3. Builds Docker image with version tag
4. Pushes to Docker Hub: `stuartshay/otel-demo:x.y.z` and `:latest`

### Manual Version Bump

**IMPORTANT**: Always use the provided script to update versions.

```bash
# Update otel-demo version
cd /home/ubuntu/git/otel-demo
./scripts/update-version.sh 1.0.85

# Review changes
git diff

# Commit and push (from develop or feature branch)
git add -A
git commit -m "chore: Bump version to 1.0.85"
git push origin HEAD

# Create PR to main for release
```

The script updates:

- `VERSION` file
- `pyproject.toml` (version field)
- `.env` (APP_VERSION)

## Branch Release Strategy

### Feature Release (Normal Workflow)

1. Work on `develop` or `feature/*` branch
2. When ready to release, bump version:

   ```bash
   ./scripts/update-version.sh 1.0.85
   ```

3. Commit and push to your branch
4. Create PR to `main`
5. Merge PR triggers Docker build with new version
6. Update k8s-gitops deployment manifests

### Hotfix Release (Emergency)

1. Create `hotfix/*` branch from `main`
2. Make urgent fixes
3. Bump patch version:

   ```bash
   ./scripts/update-version.sh 1.0.85
   ```

4. PR to `main` for immediate release
5. Backport to `develop` if needed

## Deployment Workflow

After version bump is merged to `main`:

1. **Docker Image** - Built automatically by GitHub Actions
   - Wait for workflow to complete
   - Verify image: `docker pull stuartshay/otel-demo:1.0.85`

2. **Update k8s-gitops** - Deploy to cluster

   ```bash
   cd /home/ubuntu/git/k8s-gitops/apps/base/otel-demo
   ./update-version.sh 1.0.85
   git add -A
   git commit -m "chore: Update otel-demo to 1.0.85"
   git push origin master
   ```

3. **Argo CD Sync** - Automatic deployment
   - Argo CD detects changes in k8s-gitops
   - Syncs new version to cluster
   - Monitor: `kubectl get pods -n otel-demo`

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.84 | 2026-01-29 | Distance service integration complete |
| 1.0.71 | 2026-01-21 | gRPC client for otel-worker |

## Troubleshooting

### Version Mismatch

If deployed version doesn't match repo:

```bash
# Check deployed version
kubectl get deployment otel-demo -n otel-demo -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check repo version
cat /home/ubuntu/git/otel-demo/VERSION

# Check k8s-gitops manifests
grep "image:" /home/ubuntu/git/k8s-gitops/apps/base/otel-demo/deployment.yaml
```

### Docker Build Failed

1. Check GitHub Actions workflow logs
2. Verify VERSION file format (must be `x.y.z`)
3. Ensure Docker Hub credentials are valid

### Argo CD Not Syncing

```bash
# Manual sync
kubectl patch application otel-demo -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"normal"}}}'

# Or use Argo CD CLI
argocd app sync otel-demo --prune
```

## Best Practices

✅ **DO:**

- Always use `./scripts/update-version.sh` to bump versions
- Follow semver conventions
- Update k8s-gitops after Docker image is built
- Test new versions in staging before production

❌ **DON'T:**

- Manually edit VERSION file without using the script
- Skip version bumps for releases
- Use the same version for different code
- Commit directly to `main` (use PRs)

## Related Documentation

- [Operations Guide](operations.md)
- [Multi-Repo Implementation Plan](multi-repo-implementation-plan.md)
- [Distance Integration](DISTANCE_INTEGRATION_PLAN.md)
