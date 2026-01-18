# Phase 1 Setup Instructions

This document contains the manual setup steps required to complete Phase 1 (npm types package).

## Overview

Phase 1 implementation is complete and committed to the `develop` branch. The following manual steps are required to enable automatic npm publishing:

1. Create npm granular access token
2. Add NPM_TOKEN to GitHub repository secrets
3. Merge to main branch and verify workflow
4. Document token rotation procedure

---

## Step 1: Create npm Granular Access Token

### Prerequisites

- npm account: You're using your free account at <https://www.npmjs.com>
- Package name: `@stuartshay/otel-types`

### Instructions

1. **Log in to npm**:
   - Go to <https://www.npmjs.com>
   - Click "Sign In" (or go directly to <https://www.npmjs.com/login>)

2. **Navigate to Access Tokens**:
   - Click your profile icon (top right)
   - Select "Access Tokens"
   - Or go directly to: <https://www.npmjs.com/settings/~/tokens>

3. **Generate New Token**:
   - Click "Generate New Token"
   - Select **"Granular Access Token"** (NOT Classic Token)

4. **Configure Token**:
   - **Token Name**: `github-actions-otel-types`
   - **Expiration**: Custom → Set to **1 year from today**
     - Example: If today is January 18, 2025, set to January 18, 2026
     - Note: You'll need to rotate this token annually (see Step 4)
   - **Packages and scopes**:
     - Select: **"Read and write"** permission
     - Scope: **Only select packages** → Choose `@stuartshay/otel-types`
     - (If package doesn't exist yet, you may need to publish manually first - see below)

5. **Generate and Copy Token**:
   - Click "Generate Token"
   - **IMPORTANT**: Copy the token immediately and save it securely
   - You won't be able to see it again!

### If Package Doesn't Exist Yet

If `@stuartshay/otel-types` doesn't appear in the package list:

```bash
# On your local machine:
cd /home/ubuntu/git/otel-demo/packages/otel-types

# Login to npm (one-time)
npm login

# Publish initial version
npm publish --access public
```

Then go back and create the granular access token with the package selected.

---

## Step 2: Add NPM_TOKEN to GitHub Secrets

### Instructions

1. **Navigate to Repository Settings**:
   - Go to: <https://github.com/stuartshay/otel-demo>
   - Click "Settings" tab
   - In left sidebar, click "Secrets and variables" → "Actions"
   - Or go directly to: <https://github.com/stuartshay/otel-demo/settings/secrets/actions>

2. **Create New Secret**:
   - Click "New repository secret"
   - **Name**: `NPM_TOKEN` (MUST be exactly this name)
   - **Secret**: Paste the token you copied from npm
   - Click "Add secret"

3. **Verify Secret**:
   - You should see `NPM_TOKEN` in the list of repository secrets
   - The value will be hidden (shown as asterisks)

---

## Step 3: Test Workflow End-to-End

### Instructions

1. **Merge to Main Branch**:

   ```bash
   cd /home/ubuntu/git/otel-demo
   git checkout main
   git pull origin main
   git merge develop
   git push origin main
   ```

2. **Monitor GitHub Actions**:
   - Go to: <https://github.com/stuartshay/otel-demo/actions>
   - You should see a new workflow run triggered by the push to main
   - The workflow has 3 jobs:
     1. **Build and Push** (builds Docker image)
     2. **Check API Schema Changes** (generates types, detects changes)
     3. **Publish Types to npm** (publishes if schema changed)

3. **Verify Each Job**:

   **Job 1: Build and Push**
   - Should succeed (this already works)
   - Check that Docker image is pushed to Docker Hub
   - Version should be `1.0.<build_number>`

   **Job 2: Check API Schema Changes**
   - Should succeed
   - Check logs for:
     - "Step 1: Fetching spec ✓"
     - "Step 3: Converted to OpenAPI 3.0 ✓"
     - "Step 4: Types generated successfully ✓"
   - Should output `schema_changed=true` (since this is the first run)

   **Job 3: Publish Types to npm**
   - Should succeed
   - Check logs for: "npm publish --access public"
   - Should show package published successfully

4. **Verify npm Package**:
   - Go to: <https://www.npmjs.com/package/@stuartshay/otel-types>
   - You should see the newly published version (1.0.<build_number>)
   - Download and inspect the package:

     ```bash
     npm info @stuartshay/otel-types
     npm view @stuartshay/otel-types versions
     ```

5. **Test Type Installation**:

   ```bash
   # Create test directory
   mkdir -p /tmp/test-types && cd /tmp/test-types
   npm init -y

   # Install the published types
   npm install @stuartshay/otel-types

   # Verify types are available
   cat node_modules/@stuartshay/otel-types/index.d.ts | head -50
   ```

### Troubleshooting

**If Job 2 (schema-check) fails:**

- Check that /apispec.json is accessible: `curl -I https://otel.lab.informationcart.com/apispec.json`
- Verify swagger2openapi is installed: Check job logs for "Installing swagger2openapi"
- Check for conversion errors in logs

**If Job 3 (publish-types) fails:**

- Verify NPM_TOKEN secret is set correctly
- Check npm token permissions (must have "Read and write" for @stuartshay/otel-types)
- Verify token hasn't expired
- Check for version conflicts (package.json version must be unique)

**If npm publish fails with "version already exists":**

- This is expected on subsequent runs without schema changes
- The version is auto-incremented with each build number
- If you need to republish the same version, increment the version manually in package.json

---

## Step 4: Document Token Rotation

### Add to docs/operations.md

Add the following section to `docs/operations.md`:

```markdown
## npm Token Rotation

The `@stuartshay/otel-types` package is published automatically via GitHub Actions.
The NPM_TOKEN secret must be rotated annually.

### Rotation Schedule

- **Current expiration**: [INSERT DATE FROM STEP 1]
- **Next rotation**: [INSERT DATE - 1 YEAR]
- **Calendar reminder**: Set reminder 2 weeks before expiration

### Rotation Procedure

1. **Generate new token** (14 days before expiration):
   - Go to: https://www.npmjs.com/settings/~/tokens
   - Click "Generate New Token" → "Granular Access Token"
   - Token name: `github-actions-otel-types-2026` (increment year)
   - Expiration: 1 year from today
   - Scope: Read and write access to `@stuartshay/otel-types`
   - Generate and copy token

2. **Update GitHub secret**:
   - Go to: https://github.com/stuartshay/otel-demo/settings/secrets/actions
   - Click "NPM_TOKEN" → "Update"
   - Paste new token value
   - Save

3. **Test new token**:
   - Trigger manual workflow: https://github.com/stuartshay/otel-demo/actions/workflows/docker.yml
   - Select "Run workflow" → Run on `main` branch
   - Verify all 3 jobs succeed

4. **Revoke old token**:
   - Go to: https://www.npmjs.com/settings/~/tokens
   - Find old token (e.g., `github-actions-otel-types`)
   - Click "Delete" → Confirm

5. **Update this document**:
   - Update "Current expiration" date
   - Update "Next rotation" date (add 1 year)

### Emergency Rotation

If token is compromised:

1. Immediately revoke compromised token at: https://www.npmjs.com/settings/~/tokens
2. Generate new token using procedure above
3. Update GitHub secret
4. Test workflow
5. Investigate how token was compromised (check logs, audit access)
```

### Instructions

1. Open `docs/operations.md` in your editor
2. Add the above section (customize the dates from Step 1)
3. Commit and push:

   ```bash
   cd /home/ubuntu/git/otel-demo
   git add docs/operations.md
   git commit -m "docs: Add npm token rotation procedure"
   git push origin main
   ```

---

## Phase 1 Completion Checklist

- [ ] npm granular access token created (1-year expiration)
- [ ] NPM_TOKEN added to GitHub repository secrets
- [ ] Merged develop → main
- [ ] GitHub Actions workflow succeeded (all 3 jobs)
- [ ] Package published to npm: <https://www.npmjs.com/package/@stuartshay/otel-types>
- [ ] Types verified in test installation
- [ ] Token rotation procedure documented in docs/operations.md
- [ ] Calendar reminder set for token rotation

---

## Next Steps (Phase 2)

Once Phase 1 is complete and tested, proceed to Phase 2:

- Create `otel-ui` repository (React + Vite + TypeScript)
- Configure Cognito authentication with oidc-client-ts
- Set up development environment
- Create Dockerfile and K8s manifests

See [multi-repo-implementation-plan.md](multi-repo-implementation-plan.md) for full Phase 2 details.

---

## Support

If you encounter issues:

1. Check GitHub Actions logs: <https://github.com/stuartshay/otel-demo/actions>
2. Verify npm token status: <https://www.npmjs.com/settings/~/tokens>
3. Test type generation locally: `bash scripts/generate-types.sh`
4. Check package.json version: `cat packages/otel-types/package.json | jq .version`

For questions, refer to:

- [multi-repo-implementation-plan.md](multi-repo-implementation-plan.md)
- [operations.md](operations.md)
- GitHub Actions workflow: `.github/workflows/docker.yml`
