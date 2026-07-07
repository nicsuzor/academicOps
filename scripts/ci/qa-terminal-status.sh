#!/usr/bin/env bash
# qa-terminal-status.sh
#
# Decides the terminal `qa-status` (state + description) for a single
# agent-qa.yml pass. Extracted from inline workflow bash — like the sibling
# enforcer-terminal-status.sh — so the decision is unit-tested
# (tests/test_qa_terminal_status.py) rather than living only in YAML where the
# false-green below survived unnoticed.
#
# THE BUG THIS FIXES (aops_e958bd56 — false green live on PR #2135, 2026-07-06).
# When the QA agent fails to run (on #2135 the marsha prompt failed to
# materialise and the agent step exited 1), the terminal-status fallback looked
# up ANY APPROVED/CHANGES_REQUESTED review on the head SHA — NOT scoped to
# marsha's "QA Verification" marker. The ENFORCER's approval
# ("## Enforcer Review — clean") sat on the same SHA, so the unscoped lookup
# accepted the enforcer's verdict as a QA pass and posted qa-status=success
# ("3/3 dimensions pass") even though marsha never ran → silent QA bypass /
# false green on a REQUIRED merge gate.
#
# THE FIX: the review lookup is scoped to marsha's "QA Verification" marker
# (qa.agent.md §Identity: every QA review body begins with `# QA Verification`),
# mirroring how the SHA-skip check and the enforcer's own lookups prove a NAMED
# reviewer ran on the SHA. Fail-closed: absent a genuine QA verdict review on
# the exact HEAD_SHA, qa-status is failure — a missing/absent QA verdict is
# never a pass. Unlike the enforcer there is no COMMITTED short-circuit: QA
# verifies, it never commits (qa.agent.md "Never modify code"), so `gh pr
# review` always attaches to the SHA the job started on.
#
# Required env:
#   HEAD_SHA        exact PR head SHA this job started on.
#   REVIEW_OUTCOME  outcome of the "Run QA Verification" step
#                   (success/failure/cancelled/skipped/"" — GHA step vocabulary).
# Optional env:
#   REPO, PR_NUMBER required for the live review lookup; not read when
#                   REVIEWS_JSON is set.
#   REVIEWS_JSON    path to a file with the PR reviews JSON array (testing /
#                   offline). When set, no gh calls are made.
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   state        success|failure
#   description  short human string for the commit-status description
#   failed       true|false — whether the calling job should exit 1

set -euo pipefail

HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
REVIEW_OUTCOME="${REVIEW_OUTCOME:-}"

emit() {
  printf 'state=%s\n' "$1"
  printf 'description=%s\n' "$2"
  printf 'failed=%s\n' "$3"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      printf 'state=%s\n' "$1"
      printf 'description=%s\n' "$2"
      printf 'failed=%s\n' "$3"
    } >>"$GITHUB_OUTPUT"
  fi
}

if [[ -n "${REVIEWS_JSON:-}" ]]; then
  reviews="$(cat "$REVIEWS_JSON")"
else
  reviews="$(gh api "repos/${REPO:?REPO is required}/pulls/${PR_NUMBER:?PR_NUMBER is required}/reviews?per_page=100" 2>/dev/null || echo "[]")"
fi

# Scope to marsha's "QA Verification" marker — a NAMED-reviewer attestation.
# An enforcer approval ("## Enforcer Review") on the same SHA must NOT count as
# a QA pass; that unscoped match is exactly the aops_e958bd56 false-green.
# Anchored to the START of the body (qa.agent.md §Identity: the body MUST begin
# with `# QA Verification` as the first line) so a review that merely *mentions*
# the phrase in prose cannot leak through — the residual of a bare substring
# match. jq test() is single-line by default, so `^` is the body's start.
review_state="$(jq -r --arg sha "$HEAD_SHA" '
  [.[]
    | select(.commit_id == $sha)
    | select((.body // "") | test("^#+ QA Verification"))
    | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")]
  | last | .state // ""' <<<"$reviews")"

case "$review_state" in
  APPROVED)
    emit "success" "3/3 dimensions pass" "false"
    exit 0
    ;;
  CHANGES_REQUESTED)
    emit "failure" "Verification failed — see review" "true"
    exit 0
    ;;
esac

# No genuine QA verdict review for HEAD_SHA → fail-closed. Distinguish an agent
# that failed to run from one that ran but posted no verdict, for an actionable
# description.
if [[ "$REVIEW_OUTCOME" != "success" ]]; then
  emit "failure" "Agent run failed without a verdict review" "true"
  exit 0
fi

emit "failure" "QA posted no APPROVED/CHANGES_REQUESTED review" "true"
exit 0
