#!/usr/bin/env bash
# validate-ruleset-alignment.sh
#
# Validates that the required status check names in the ruleset match
# the actual job names in the workflow files.
#
# Exit codes:
#   0 - All required checks found in workflow files
#   1 - One or more required checks have no matching workflow job
#
# Usage:
#   ./scripts/validate-ruleset-alignment.sh
#   ./scripts/validate-ruleset-alignment.sh --repo nicsuzor/academicOps  # live from API
#
# Run via CI: see .github/workflows/validate-ruleset.yml

set -euo pipefail

REPO="${REPO:-nicsuzor/academicOps}"
WORKFLOWS_DIR=".github/workflows"
RULESET_FILE=".github/rulesets/pr-review-and-merge.yml"

# ── Extract required check names ────────────────────────────────────────────

if [[ "${1:-}" == "--repo" ]] && [[ -n "${2:-}" ]]; then
  REPO="$2"
  echo "Fetching required checks from live API for $REPO..."
  REQUIRED_CHECKS=$(gh api "repos/$REPO/rulesets" --jq '
    .[].rules[]
    | select(.type == "required_status_checks")
    | .parameters.required_status_checks[]
    | .context
  ' 2>/dev/null | sort)
else
  echo "Extracting required checks from $RULESET_FILE..."
  # Parse YAML: find lines under required_status_checks: that have `- context:`
  REQUIRED_CHECKS=$(grep -A1 "required_status_checks:" "$RULESET_FILE" \
    | grep "context:" \
    | sed 's/.*context: *//' \
    | tr -d '"' \
    | sort)
fi

if [[ -z "$REQUIRED_CHECKS" ]]; then
  echo "WARNING: No required status checks found. Check $RULESET_FILE or API."
  exit 0
fi

echo "Required status checks:"
echo "$REQUIRED_CHECKS" | while read -r check; do echo "  - $check"; done
echo ""

# ── Extract job names from workflow files ────────────────────────────────────

echo "Scanning workflow job names in $WORKFLOWS_DIR..."
ALL_JOB_NAMES=$(grep -rh "^  [a-z].*:$\|^    name:" "$WORKFLOWS_DIR"/*.yml 2>/dev/null \
  | grep "^    name:" \
  | sed 's/.*name: *//' \
  | tr -d '"' \
  | sort -u)

echo "Found job names:"
echo "$ALL_JOB_NAMES" | while read -r name; do echo "  - $name"; done
echo ""

# ── Check alignment ──────────────────────────────────────────────────────────

ERRORS=0
echo "Checking alignment..."

while IFS= read -r required; do
  if echo "$ALL_JOB_NAMES" | grep -qxF "$required"; then
    echo "  ✓ '$required' — found in workflow files"
  else
    echo "  ✗ '$required' — NOT found in any workflow job name!"
    echo "    This will silently block all PRs. Fix: update the ruleset or rename the job."
    ERRORS=$((ERRORS + 1))
  fi
done <<< "$REQUIRED_CHECKS"

echo ""

if [[ $ERRORS -gt 0 ]]; then
  echo "FAILED: $ERRORS required check(s) have no matching workflow job name."
  echo ""
  echo "To fix:"
  echo "  1. Check the job names in .github/workflows/ (look for 'name:' fields)"
  echo "  2. Update .github/rulesets/pr-review-and-merge.yml to match exactly"
  echo "  3. Apply the updated ruleset: scripts/sync-ruleset.sh"
  exit 1
else
  echo "OK: All required checks are aligned with workflow job names."
fi
