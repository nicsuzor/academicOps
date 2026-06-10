#!/usr/bin/env bash
# reconcile-enforcer-reviews.sh
#
# Idempotent single-verdict guarantee for the enforcer (aops-1adfd28d).
#
# Invariant enforced: AT MOST ONE enforcer verdict review stands per SHA. After
# the agent attempt(s) complete, this dismisses every standing enforcer verdict
# review for HEAD_SHA except the newest, so the merge gate (which reads the PR
# review state and the enforcer-status commit status derived from it) can never
# observe TWO standing enforcer verdicts on one diff.
#
# SCOPE — what this does and does NOT guarantee:
#   - Guarantees (and is unit-tested for): never two standing verdicts. This
#     holds regardless of how many times an agent posts (e.g. the silent-replay
#     duplicate, run 27250704371) and is idempotent on re-run.
#   - Does NOT by itself guarantee correct ordering. A "zombie" first attempt
#     can post asynchronously at any wall-clock time, so no post-hoc
#     timestamp/id heuristic can prove which standing review is the authoritative
#     one. Ordering correctness (the authoritative verdict is the one that
#     stands) is provided by reap-agent-processes.sh, which kills the cancelled
#     attempt BEFORE the retry so the stale verdict is never posted at all. This
#     script is the single-standing safety net for the residual case where a
#     reap misses the real process.
#
# The gh read is isolated behind REVIEWS_JSON so the decision (which review ids
# to keep / dismiss) is a pure function over the reviews array and is unit-tested
# without a gh stub (tests/test_reconcile_enforcer_reviews.py), mirroring
# scripts/ci/review-attestation.sh.
#
# Required env:
#   REPO       owner/name.
#   PR_NUMBER  pull request number.
#   HEAD_SHA   exact PR head SHA whose verdicts are being reconciled.
# Optional env:
#   ENFORCER_MARKER  body substring that identifies an enforcer verdict review
#                    (default "Enforcer Review", per enforcer.agent.md §5).
#   REVIEWS_JSON     path to a file with the PR reviews JSON array (testing /
#                    offline). When set, the script computes and prints the
#                    keep/dismiss decision and performs NO gh calls.
#   DRY_RUN          when non-empty (and REVIEWS_JSON unset), fetch live but only
#                    print the decision; perform no dismissals.

set -euo pipefail

REPO="${REPO:?REPO is required}"
PR_NUMBER="${PR_NUMBER:?PR_NUMBER is required}"
HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
MARKER="${ENFORCER_MARKER:-Enforcer Review}"  # allow-fallback: configurable verdict-body marker; default matches enforcer.agent.md §5

if [[ -n "${REVIEWS_JSON:-}" ]]; then
  reviews="$(cat "$REVIEWS_JSON")"
else
  reviews="$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews?per_page=100")"
fi

# Standing enforcer verdict reviews on THIS exact SHA, ordered oldest→newest by
# review id (monotonic). "Standing" = state APPROVED or CHANGES_REQUESTED;
# already-DISMISSED reviews are inert and excluded (so the script is idempotent —
# a second run sees only the one it kept).
ids_sorted="$(jq -r --arg sha "$HEAD_SHA" --arg marker "$MARKER" '
  [ .[]
    | select(.commit_id == $sha)
    | select((.body // "") | test($marker))
    | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")
  ] | sort_by(.id) | .[].id' <<<"$reviews")"

keep=""
dismiss=""
if [[ -n "$ids_sorted" ]]; then
  keep="$(tail -n1 <<<"$ids_sorted")"
  # Every standing enforcer review for this SHA except the newest.
  dismiss="$(sed '$d' <<<"$ids_sorted" | tr '\n' ' ')"
  dismiss="$(echo "$dismiss" | xargs 2>/dev/null || true)"  # allow-fallback: trim/normalise whitespace only; empty stays empty
fi

echo "keep=${keep}"
echo "dismiss=${dismiss}"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "keep=${keep}"
    echo "dismiss=${dismiss}"
  } >> "$GITHUB_OUTPUT"
fi

# Decision-only modes: injected reviews (tests) or explicit dry-run.
if [[ -n "${REVIEWS_JSON:-}" || -n "${DRY_RUN:-}" ]]; then
  exit 0
fi

for rid in $dismiss; do
  [[ -n "$rid" ]] || continue
  echo "reconcile: dismissing superseded enforcer review ${rid}"
  gh api -X PUT "repos/${REPO}/pulls/${PR_NUMBER}/reviews/${rid}/dismissals" \
    -f message="Superseded — exactly one enforcer verdict stands per SHA (aops-1adfd28d)" \
    >/dev/null || echo "::warning::failed to dismiss enforcer review ${rid} (continuing)"
done
