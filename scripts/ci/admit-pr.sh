#!/usr/bin/env bash
# admit-pr.sh
#
# Grant admission: POST the required admit-status=success on SHA and arm
# `gh pr merge --auto --squash --delete-branch`. This is the single mechanical
# admission-grant action shared by every admission origin
# (specs/workflows/pr-pipeline.md §5.1) — admit-on-review.yml's approve path
# (§3.2) and conflict-admission-sweep.yml (§3.11) both call this script so the
# write + arm-merge behaviour cannot drift between admission paths.
#
# This script does NOT decide whether to admit — the caller has already made
# that decision (a write-class review approval, or a standing approval plus a
# conflict that needs resolving). It performs the mechanical act only.
#
# This script does NOT resolve SHA — SHA freshness is the CALLER's
# responsibility, not something this script defends against. Each caller has
# its own deliberate resolution policy: admit-on-review.yml re-reads live
# immediately before calling (the PR may have advanced since the review event
# fired); conflict-admission-sweep.yml also re-reads live immediately before
# calling (§5.1 — fixing a latent staleness race where it used to trust a SHA
# snapshotted by an earlier, separate `discover` job). Passing a stale SHA
# here posts the required admit-status check to the wrong commit — that is a
# caller bug, not something this script can detect or correct.
#
# Required env:
#   REPO        owner/name (e.g. nicsuzor/academicOps).
#   PR_NUMBER   the PR to arm auto-merge on.
#   SHA         the commit to post admit-status=success on. Caller-resolved;
#               see above — not derived here.
#   REASON      human-readable admit-status description, distinguishing which
#               admission path granted it (shown on the PR checks tab).
#   GH_TOKEN    must be a token with statuses:write (AOPS_BOT_GH_TOKEN) — no
#               github.token fallback; fails closed if unset (§4.7).
#
# A failed admit-status POST aborts the script (set -e) — unlike the auto-merge
# arm below, this is not tolerated, so a caller can't proceed believing
# admission succeeded when the required check was never actually posted.
# `gh pr merge` failure (already enabled, already merged, etc.) IS tolerated —
# it is not a sign admission failed, just that arming was a no-op.
#
# Emits admitted_sha=$SHA to stdout and $GITHUB_OUTPUT.

set -euo pipefail

REPO="${REPO:?REPO is required}"
PR_NUMBER="${PR_NUMBER:?PR_NUMBER is required}"
SHA="${SHA:?SHA is required}"
REASON="${REASON:?REASON is required}"

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "::error::GH_TOKEN is not set; cannot admit PR." >&2
  exit 1
fi

echo "Admitting PR #$PR_NUMBER at $SHA: $REASON"

gh api "repos/$REPO/statuses/$SHA" \
  -f state="success" \
  -f context="admit-status" \
  -f description="$REASON" \
  -f target_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"

gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash --delete-branch \
  || echo "WARNING: Could not enable auto-merge (may already be enabled, or PR already merged)"

echo "admitted_sha=$SHA"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "admitted_sha=$SHA" >> "$GITHUB_OUTPUT"
fi
