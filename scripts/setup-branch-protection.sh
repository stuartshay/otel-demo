#!/bin/bash
set -e

# Branch Protection Setup Script for otel-demo
# This script configures GitHub branch protection rules to enforce:
# - All changes to main must come via Pull Requests
# - Direct commits to main are forbidden
# - CI checks must pass before merging

REPO="stuartshay/otel-demo"
BRANCH="main"

echo "🔒 Setting up branch protection for ${REPO}:${BRANCH}"
echo ""

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Configure branch protection using GitHub CLI
echo "📋 Configuring branch protection rules..."
echo ""

# Main protection rule with all settings
gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/${REPO}/branches/${BRANCH}/protection" \
    -f required_status_checks='{"strict":true,"contexts":["lint"]}' \
    -f enforce_admins=true \
    -f required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":0}' \
    -F allow_force_pushes=false \
    -F allow_deletions=false \
    -f restrictions=null \
    -f required_linear_history=false \
    -f allow_fork_syncing=true

echo ""
echo "✅ Branch protection configured successfully!"
echo ""
echo "📋 Protection Rules Applied:"
echo "   ✓ Require pull request before merging (0 approvals required)"
echo "   ✓ Dismiss stale PR approvals when new commits pushed"
echo "   ✓ Require status checks: lint"
echo "   ✓ Require branches to be up to date before merging"
echo "   ✓ Include administrators (no one can bypass)"
echo "   ✓ Disable force pushes"
echo "   ✓ Disable branch deletion"
echo ""
echo "🎯 Result: Direct commits to main are now FORBIDDEN"
echo "   All changes must go through PRs from develop or feature/* branches"
echo ""

# Verify the setup
echo "🔍 Verifying configuration..."
gh api "/repos/${REPO}/branches/${BRANCH}/protection" \
    --jq '{
        "required_pull_request_reviews": .required_pull_request_reviews.required_approving_review_count,
        "required_status_checks": .required_status_checks.contexts,
        "enforce_admins": .enforce_admins.enabled,
        "allow_force_pushes": .allow_force_pushes.enabled,
        "allow_deletions": .allow_deletions.enabled
    }'

echo ""
echo "✅ Setup complete! Branch protection is active."
echo ""
echo "📖 View protection settings:"
echo "   https://github.com/${REPO}/settings/branches"
