#!/bin/bash
set -e

# Script to update otel-demo version
# Usage: ./scripts/update-version.sh 1.0.71

if [ -z "$1" ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 1.0.71"
  exit 1
fi

NEW_VERSION="$1"

# Validate version format (semantic versioning: MAJOR.MINOR.PATCH)
if ! [[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: invalid version '${NEW_VERSION}'. Expected format: MAJOR.MINOR.PATCH (e.g., 1.0.71)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Updating otel-demo to version ${NEW_VERSION}..."

# Update VERSION file
echo "${NEW_VERSION}" > "${PROJECT_ROOT}/VERSION"

# Update pyproject.toml if it exists
if [ -f "${PROJECT_ROOT}/pyproject.toml" ]; then
  sed -i.bak "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" "${PROJECT_ROOT}/pyproject.toml"
  rm -f "${PROJECT_ROOT}/pyproject.toml.bak"
fi

# Update .env file if it exists
if [ -f "${PROJECT_ROOT}/.env" ]; then
  sed -i.bak "s/^APP_VERSION=.*/APP_VERSION=${NEW_VERSION}/" "${PROJECT_ROOT}/.env"
  rm -f "${PROJECT_ROOT}/.env.bak"
fi

echo "✅ Updated otel-demo to version ${NEW_VERSION}"
echo ""
echo "Files modified:"
echo "  - VERSION"
[ -f "${PROJECT_ROOT}/pyproject.toml" ] && echo "  - pyproject.toml"
[ -f "${PROJECT_ROOT}/.env" ] && echo "  - .env"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Update k8s-gitops manifests: cd ../k8s-gitops/apps/base/otel-demo && ./update-version.sh ${NEW_VERSION}"
echo "  3. Commit: git add -A && git commit -m \"chore: bump version to v${NEW_VERSION}\""
echo "  4. Tag: git tag -a v${NEW_VERSION} -m \"Release v${NEW_VERSION}\""
echo "  5. Push: git push origin develop && git push origin v${NEW_VERSION}"
