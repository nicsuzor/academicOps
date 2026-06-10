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

# ── API-driven commit statuses ───────────────────────────────────────────────
# These are required status checks that are set via the GitHub Statuses API
# (not by a workflow job). They have no corresponding job name in workflow files
# and must be explicitly listed here to pass validation.
API_DRIVEN_STATUSES=(
  "enforcer-status"      # set by agent-enforcer.yml via GitHub Statuses API (Phase 1 v2 enforcer)
  "qa-status"            # set by agent-qa.yml via GitHub Statuses API (Phase 2 v2 QA / marsha)
  "review-attestation"   # set by pr-pipeline.yml `review-attestation` job (fail-closed liveness; #1450, §3.7)
  "admit-status"         # set by stage2-admission.yml on Environment approval (Phase 4 human gate)
  "merge-prep-status"    # legacy v1 gate (set by agent-merge-prep.yml + Initialize); no longer required
)

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
  # Parse YAML: find all `- context:` lines in the required_status_checks section
  REQUIRED_CHECKS=$(sed -n '/required_status_checks:/,/^  # ─/p' "$RULESET_FILE" \
    | grep "context:" | sed 's/.*context: *//' \
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

# ── Check for workflow files in subdirectories ───────────────────────────────
echo "Checking for workflow files in subdirectories..."
NESTED_YML=$(find "$WORKFLOWS_DIR" -mindepth 2 -name "*.yml" || true)
if [[ -n "$NESTED_YML" ]]; then
  echo "FAILED: GitHub Actions does not support workflow files in subdirectories."
  echo "The following files will be silently ignored by GitHub:"
  echo "$NESTED_YML" | while read -r f; do echo "  - $f"; done
  echo "Fix: Move these files to the root of $WORKFLOWS_DIR."
  exit 1
fi
echo "OK: No nested workflow files found."
echo ""

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
  # Check if this is a known API-driven commit status (not a workflow job name)
  is_api_driven=false
  for api_status in "${API_DRIVEN_STATUSES[@]}"; do
    if [[ "$required" == "$api_status" ]]; then
      is_api_driven=true
      break
    fi
  done

  if [[ "$is_api_driven" == "true" ]]; then
    if [[ "$required" == "enforcer-status" ]]; then
      if ! grep -q "agent-enforcer.yml" "$WORKFLOWS_DIR"/*.yml 2>/dev/null; then
        echo "  ✗ '$required' — API-driven status is required, but no workflow in $WORKFLOWS_DIR calls agent-enforcer.yml!"
        ERRORS=$((ERRORS + 1))
        continue
      fi
    elif [[ "$required" == "qa-status" ]]; then
      if ! grep -q "agent-qa.yml" "$WORKFLOWS_DIR"/*.yml 2>/dev/null; then
        echo "  ✗ '$required' — API-driven status is required, but no workflow in $WORKFLOWS_DIR calls agent-qa.yml!"
        ERRORS=$((ERRORS + 1))
        continue
      fi
    elif [[ "$required" == "review-attestation" ]]; then
      # Set by the pr-pipeline.yml `review-attestation` job (fail-closed liveness;
      # #1450, pr-pipeline.md §3.7). The decision logic is scripts/ci/review-attestation.sh.
      if ! grep -q "review-attestation" "$WORKFLOWS_DIR"/pr-pipeline.yml 2>/dev/null; then
        echo "  ✗ '$required' — API-driven status is required, but $WORKFLOWS_DIR/pr-pipeline.yml does not set review-attestation!"
        ERRORS=$((ERRORS + 1))
        continue
      fi
    elif [[ "$required" == "admit-status" ]]; then
      # Set by the Stage-2 Admission Gate on `pr-fix-loop` Environment approval.
      if ! grep -q "admit-status" "$WORKFLOWS_DIR"/stage2-admission.yml 2>/dev/null; then
        echo "  ✗ '$required' — API-driven status is required, but $WORKFLOWS_DIR/stage2-admission.yml does not set admit-status!"
        ERRORS=$((ERRORS + 1))
        continue
      fi
    elif [[ "$required" == "alignment-status" ]]; then
      if ! grep -q "agent-alignment.yml" "$WORKFLOWS_DIR"/*.yml 2>/dev/null; then
        echo "  ✗ '$required' — API-driven status is required, but no workflow in $WORKFLOWS_DIR calls agent-alignment.yml!"
        ERRORS=$((ERRORS + 1))
        continue
      fi
    fi
    echo "  ✓ '$required' — API-driven commit status (set via GitHub Statuses API, not a job name)"
    continue
  fi

  # GitHub Actions prepends the caller workflow and job ID for reusable workflows
  # e.g., "PR Review Pipeline / lint / Lint". We strip everything up to the last " / "
  # to match against the actual job name defined in the reusable workflow YAML.
  basename_required=$(echo "$required" | sed 's/.* \/ //')

  if echo "$ALL_JOB_NAMES" | grep -qxF "$basename_required"; then
    echo "  ✓ '$required' (as '$basename_required') — found in workflow files"
  else
    echo "  ✗ '$required' (as '$basename_required') — NOT found in any workflow job name!"
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
