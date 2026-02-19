#!/usr/bin/env bash
# sync-ruleset.sh
#
# Applies the API-compatible portions of .github/rulesets/pr-review-and-merge.yml
# to the live GitHub ruleset.
#
# Rules NOT applied by this script (API doesn't support them):
#   - merge_queue       → set via GitHub UI
#   - code_quality      → set via GitHub UI (also: survives API updates if already set)
#
# Usage:
#   ./scripts/sync-ruleset.sh [--dry-run]
#
# Requires: gh CLI, authenticated as repo admin

set -euo pipefail

REPO="${REPO:-qut-dmrc/academicOps}"
RULESET_ID="${RULESET_ID:-12723813}"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "DRY RUN: showing payload without applying"
fi

echo "Syncing ruleset $RULESET_ID for $REPO..."
echo ""

# Fetch current state to show diff
CURRENT=$(gh api "repos/$REPO/rulesets/$RULESET_ID" 2>/dev/null)
CURRENT_METHODS=$(echo "$CURRENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('rules', []):
    if r['type'] == 'pull_request':
        print('allowed_merge_methods:', r['parameters']['allowed_merge_methods'])
" 2>/dev/null || echo "(could not parse)")

echo "Current state: $CURRENT_METHODS"
echo ""

# Build the payload (API-compatible rules only)
PAYLOAD=$(cat <<'PAYLOAD_EOF'
{
  "name": "PR Review and Merge rules",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": ["~DEFAULT_BRANCH"]
    }
  },
  "bypass_actors": [
    {
      "actor_id": 5,
      "actor_type": "RepositoryRole",
      "bypass_mode": "always"
    }
  ],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["rebase"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {"context": "Lint"}
        ]
      }
    },
    {
      "type": "code_quality",
      "parameters": {
        "severity": "errors"
      }
    }
  ]
}
PAYLOAD_EOF
)

echo "Payload to apply:"
echo "$PAYLOAD" | python3 -m json.tool
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN complete. No changes made."
  exit 0
fi

echo "Applying ruleset update..."
RESULT=$(echo "$PAYLOAD" | gh api "repos/$REPO/rulesets/$RULESET_ID" \
  -X PUT \
  --input - 2>&1)

echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Updated successfully at:', d.get('updated_at', '?'))
    print('Rules now active:')
    for r in d.get('rules', []):
        print(f'  - {r[\"type\"]}')
except:
    print(sys.stdin.read())
" || echo "$RESULT"

echo ""
echo "NOTE: code_quality and merge_queue rules must be verified in GitHub UI."
echo "  Settings → Rules → Rulesets → 'PR Review and Merge rules'"
echo ""
echo "Running alignment check..."
bash "$(dirname "$0")/validate-ruleset-alignment.sh"
