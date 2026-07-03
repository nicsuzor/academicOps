#!/usr/bin/env bash
# enforcer-terminal-status.sh
#
# Decides the terminal `enforcer-status` (state + description) for a single
# agent-enforcer.yml pass, and whether the job should hard-fail.
#
# THE BUG THIS FIXES (aops-89d55ef5 — closed via dashboard in 2026-06 with no
# code change; the bug was still live until this script). `gh pr review`
# attaches a posted review to the PR's CURRENT head SHA at submission time,
# not the SHA the job started on. enforcer.agent.md has the agent fix
# mechanical violations and push BEFORE posting its verdict (§3 then §5), so
# when it commits mid-run, the PR head has already advanced by the time it
# calls `gh pr review`. The old inline logic matched strictly on
# `commit_id == HEAD_SHA`, found nothing for the now-superseded HEAD_SHA, and
# posted a false `failure` ("no verdict posted") on a pass that actually
# succeeded — found a violation, fixed it, pushed it. See
# specs/workflows/pr-pipeline.md §3.4 pt 6.
#
# THE FIX: a pushed commit (COMMITTED=true, from the workflow's git-verified
# check-commit step) is checked FIRST, before any review lookup, and is
# decisive — it is strictly stronger evidence than a review match, since it
# is verified via git rather than self-reported by the action, and it is
# exactly the thing that makes a review-match race in the first place. A
# committed pass is always a `success` handoff for the SHA it ran on:
# whatever the agent found there, it fixed and handed off. Nothing is lost —
# the review the agent just posted (APPROVE or REQUEST_CHANGES) is attached
# to the NEW sha and is read by that SHA's own pass via the ordinary §10
# SHA-skip check, so a genuinely remaining violation still reddens the
# correct (new) SHA one pass later. A problem the agent could not fix is
# still red; a problem it fixed inline and committed never was.
#
# Required env:
#   HEAD_SHA        exact PR head SHA this job started on (the pre-commit SHA).
#   COMMITTED       "true" if the agent pushed a commit this pass (the
#                   workflow's check-commit step output), "false" otherwise.
#                   Fails fast if unset — silently defaulting this exact
#                   variable is what would reintroduce the bug this script
#                   fixes (a wiring mistake dropping COMMITTED would silently
#                   fall through to the review-match path this script exists
#                   to bypass).
#   REVIEW_OUTCOME  outcome of the primary "Run Enforcer Review" step
#                   (success/failure/cancelled/skipped/"" — GHA step outcome
#                   vocabulary).
# Optional env:
#   RETRY_OUTCOME   outcome of the one-shot retry step, same vocabulary; ""
#                   when the retry never ran.
#   REPO, PR_NUMBER required for the live review lookup; not read when
#                   REVIEWS_JSON is set, and NEVER read on the committed path
#                   (no live call is made when COMMITTED=true).
#   REVIEWS_JSON    path to a file with the PR reviews JSON array (testing /
#                   offline). When set, no gh calls are made.
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   state        success|failure
#   description  short human string for the commit-status description
#   failed       true|false — whether the calling job should exit 1

set -euo pipefail

HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
COMMITTED="${COMMITTED:?COMMITTED is required}"
REVIEW_OUTCOME="${REVIEW_OUTCOME:-}"
RETRY_OUTCOME="${RETRY_OUTCOME:-}"

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

# ── Committed short-circuit — see header. Checked before any review lookup,
#    and before REPO/PR_NUMBER are required, so a committed pass never makes
#    a live API call here at all. ────────────────────────────────────────────
if [[ "$COMMITTED" == "true" ]]; then
  emit "success" "Fixed inline — commit pushed; enforcer re-verifies the new SHA" "false"
  exit 0
fi

# ── No commit this pass: HEAD_SHA is still the PR's actual head, so a posted
#    review's commit_id (if any) unambiguously targets it. ──────────────────
if [[ -n "${REVIEWS_JSON:-}" ]]; then
  reviews="$(cat "$REVIEWS_JSON")"
else
  reviews="$(gh api "repos/${REPO:?REPO is required}/pulls/${PR_NUMBER:?PR_NUMBER is required}/reviews?per_page=100" 2>/dev/null || echo "[]")"
fi

review_state="$(jq -r --arg sha "$HEAD_SHA" '
  [.[] | select(.commit_id == $sha) | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")]
  | last | .state // ""' <<<"$reviews")"

case "$review_state" in
  APPROVED)
    emit "success" "Axiom-clean" "false"
    exit 0
    ;;
  CHANGES_REQUESTED)
    emit "failure" "Violations found — see review" "true"
    exit 0
    ;;
esac

# No genuine verdict review found for HEAD_SHA. Distinguish infra failure
# from agent-completed-but-silent so the description is actionable.
if [[ -z "$REVIEW_OUTCOME" ]]; then
  emit "failure" "Enforcer failed: early pipeline failure (review step never ran) — see run logs" "true"
  exit 0
fi

if [[ "$REVIEW_OUTCOME" != "success" ]]; then
  case "$RETRY_OUTCOME" in
    failure | cancelled)
      emit "failure" "Enforcer action step failed in both attempts (see run logs)" "true"
      ;;
    success)
      emit "failure" "Enforcer retry succeeded but posted no verdict review (see run logs)" "true"
      ;;
    *)
      emit "failure" "Enforcer first attempt did not succeed (${REVIEW_OUTCOME}); retry did not execute — see run logs" "true"
      ;;
  esac
  exit 0
fi

emit "failure" "Enforcer posted no APPROVED/CHANGES_REQUESTED review" "true"
exit 0
