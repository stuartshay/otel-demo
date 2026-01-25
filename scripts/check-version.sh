#!/bin/bash
# Script to check version consistency across otel-demo and otel-ui projects

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OTEL_DEMO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OTEL_UI_ROOT="${OTEL_DEMO_ROOT}/../otel-ui"
K8S_GITOPS_ROOT="${OTEL_DEMO_ROOT}/../k8s-gitops"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Version Consistency Check ===${NC}"
echo ""

check_project() {
  local project_name="$1"
  local project_root="$2"
  local k8s_path="$3"

  echo -e "${YELLOW}Checking ${project_name}...${NC}"

  # Check if project exists
  if [ ! -d "${project_root}" ]; then
    echo -e "${RED}✗ ${project_name} directory not found: ${project_root}${NC}"
    return 1
  fi

  # Get VERSION from project
  if [ -f "${project_root}/VERSION" ]; then
    local app_version
    app_version=$(cat "${project_root}/VERSION" | tr -d '\n')
    echo "  App VERSION file: ${app_version}"
  else
    echo -e "${RED}✗ VERSION file not found in ${project_root}${NC}"
    app_version=""
  fi

  # Check k8s-gitops VERSION
  if [ -f "${k8s_path}/VERSION" ]; then
    local k8s_version
    k8s_version=$(cat "${k8s_path}/VERSION" | tr -d '\n')
    echo "  K8s VERSION file: ${k8s_version}"

    # Compare versions
    if [ -n "${app_version}" ] && [ "${app_version}" != "${k8s_version}" ]; then
      echo -e "${RED}✗ Version mismatch! App: ${app_version}, K8s: ${k8s_version}${NC}"
      return 1
    fi
  else
    echo -e "${YELLOW}⚠ K8s VERSION file not found: ${k8s_path}/VERSION${NC}"
  fi

  # Check deployment.yaml
  if [ -f "${k8s_path}/deployment.yaml" ]; then
    local deployment_version
    deployment_version=$(grep "image:.*stuartshay/${project_name}" "${k8s_path}/deployment.yaml" | grep -oP ':\K[0-9]+\.[0-9]+\.[0-9]+')
    echo "  K8s deployment.yaml: ${deployment_version}"

    if [ -n "${app_version}" ] && [ "${app_version}" != "${deployment_version}" ]; then
      echo -e "${RED}✗ Version mismatch! App: ${app_version}, Deployment: ${deployment_version}${NC}"
      return 1
    fi
  fi

  echo -e "${GREEN}✓ ${project_name} versions are consistent${NC}"
  echo ""
  return 0
}

# Check both projects
otel_demo_ok=0
otel_ui_ok=0

check_project "otel-demo" "${OTEL_DEMO_ROOT}" "${K8S_GITOPS_ROOT}/apps/base/otel-demo" || otel_demo_ok=$?
check_project "otel-ui" "${OTEL_UI_ROOT}" "${K8S_GITOPS_ROOT}/apps/base/otel-ui" || otel_ui_ok=$?

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
if [ ${otel_demo_ok} -eq 0 ] && [ ${otel_ui_ok} -eq 0 ]; then
  echo -e "${GREEN}✓ All versions are consistent across projects${NC}"
  exit 0
else
  echo -e "${RED}✗ Version inconsistencies detected${NC}"
  echo ""
  echo "To fix:"
  echo "  - otel-demo: cd ${OTEL_DEMO_ROOT} && ./scripts/update-version.sh <version>"
  echo "  - otel-ui: cd ${OTEL_UI_ROOT} && make version VERSION=<version>"
  exit 1
fi
