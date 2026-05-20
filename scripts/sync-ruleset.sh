#!/usr/bin/env bash
# sync-ruleset.sh
#
# Reads .github/rulesets/pr-review-and-merge.yml and applies the
# API-compatible rules to the live GitHub ruleset.
#
# The YAML file is the single source of truth. This script converts it
# to the JSON payload the GitHub API expects, skipping rule types that
# the API doesn't support (merge_queue, copilot_code_review, etc.).
#
# Usage:
#   ./scripts/sync-ruleset.sh [--dry-run]
#
# Requires: gh CLI (authenticated as repo admin), uv run python with PyYAML

set -euo pipefail

REPO="${REPO:-nicsuzor/academicOps}"
RULESET_ID="${RULESET_ID:-13762049}"
RULESET_FILE="${RULESET_FILE:-.github/rulesets/pr-review-and-merge.yml}"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "DRY RUN: showing payload without applying"
fi

if [[ ! -f "$RULESET_FILE" ]]; then
  echo "ERROR: Ruleset file not found: $RULESET_FILE" >&2
  exit 1
fi

# Rule types the API doesn't support — must be set via GitHub UI
API_UNSUPPORTED=("merge_queue" "copilot_code_review" "copilot_code_review_analysis_tools" "code_quality")

echo "Reading ruleset from $RULESET_FILE..."
echo ""

# Convert YAML -> API JSON payload, stripping unsupported rule types
PAYLOAD=$(uv run python - "$RULESET_FILE" "${API_UNSUPPORTED[@]}" << 'PYTHON_EOF'
import json, sys, yaml

ruleset_file = sys.argv[1]
unsupported = set(sys.argv[2:])

with open(ruleset_file) as f:
    data = yaml.safe_load(f)

api_rules = [r for r in data.get("rules", []) if r["type"] not in unsupported]

payload = {
    "name": data["name"],
    "target": data["target"],
    "enforcement": data["enforcement"],
    "conditions": data["conditions"],
    "bypass_actors": data.get("bypass_actors", []),
    "rules": api_rules,
}

json.dump(payload, sys.stdout, indent=2)
PYTHON_EOF
)

echo "Payload to apply:"
echo "$PAYLOAD" | uv run python -m json.tool
echo ""

# Show diff with current live state
echo "Fetching current live ruleset for comparison..."
if CURRENT=$(gh api "repos/$REPO/rulesets/$RULESET_ID" 2>/dev/null); then
  uv run python - "$CURRENT" "$PAYLOAD" << 'DIFF_EOF'
import json, sys

current = json.loads(sys.argv[1])
desired = json.loads(sys.argv[2])

fields = ["name", "target", "enforcement", "conditions", "bypass_actors", "rules"]
diffs = []
for field in fields:
    c = json.dumps(current.get(field), sort_keys=True)
    d = json.dumps(desired.get(field), sort_keys=True)
    if c != d:
        diffs.append(field)

if diffs:
    print(f"Fields that differ: {', '.join(diffs)}")
else:
    print("No differences detected — live ruleset matches file.")
DIFF_EOF
else
  echo "(could not fetch current ruleset for comparison)"
fi
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN complete. No changes made."
  exit 0
fi

echo "Applying ruleset update..."
set +e
RESULT=$(echo "$PAYLOAD" | gh api "repos/$REPO/rulesets/$RULESET_ID" \
  -X PUT \
  --input - 2>&1)
API_EXIT=$?
set -e

if [[ $API_EXIT -ne 0 ]]; then
  echo "ERROR: gh api PUT failed (exit $API_EXIT):" >&2
  echo "$RESULT" >&2
  echo "" >&2
  echo "Common causes:" >&2
  echo "  - Active gh account lacks admin on $REPO (check: gh api user --jq .login)" >&2
  echo "  - Token missing 'admin:repo' / fine-grained 'Administration: write'" >&2
  exit $API_EXIT
fi

if ! uv run python - "$RESULT" << 'RESULT_EOF'
import json, sys
try:
    d = json.loads(sys.argv[1])
except json.JSONDecodeError as e:
    print(f"ERROR: API returned non-JSON response: {e}", file=sys.stderr)
    print(sys.argv[1], file=sys.stderr)
    sys.exit(1)
if "message" in d and "updated_at" not in d:
    print(f"ERROR: API returned error: {d.get('message')}", file=sys.stderr)
    print(json.dumps(d, indent=2), file=sys.stderr)
    sys.exit(1)
print("Updated successfully at:", d.get("updated_at", "?"))
print("Rules now active:")
for r in d.get("rules", []):
    print(f"  - {r['type']}")
RESULT_EOF
then
  exit 1
fi

echo ""
echo "NOTE: Rules not configurable via API must be verified in GitHub UI:"
echo "  - merge_queue"
echo "  - copilot_code_review / code_quality"
echo "  Settings → Rules → Rulesets → 'PR Review and Merge rules'"
echo ""
echo "Running alignment check..."
bash "$(dirname "$0")/validate-ruleset-alignment.sh"
