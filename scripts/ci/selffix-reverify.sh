#!/usr/bin/env bash
# selffix-reverify.sh
#
# Decides whether a PRE-ADMISSION `synchronize` should RE-DISPATCH the named
# reviewers (enforcer + qa) because the branch tip is a BOT SELF-FIX commit
# (specs/workflows/pr-pipeline.md §3.4 pt 6 / §3.1; epic aops-262def9f WI5).
#
# THE BUG THIS FIXES (root-cause table row 6, the "(d)" leg). When the enforcer
# (or the pre-admission responder, or lint autofix) self-commits a fix, that fix
# fires a fresh `synchronize`. The §3.1 fire-once gate skips the reviewers on any
# pre-admission `synchronize` (admitted != 'true'), so the fix SHA never gets a
# fresh enforcer/qa verdict pre-admission — the promised re-review on the new SHA
# (pr-pipeline.yml qa-job comment, "an enforcer fix changes the SHA → the new
# SHA's run re-reviews") is UNREACHABLE. Net effect: the only content-quality bot
# (qa) is sequenced AFTER the human admit gate, so the human always pays the first
# quality read (PR #2096). enforcer-terminal-status.sh already SHORT-CIRCUITS a
# committed pass to `success` on the OLD SHA on the same promise — so without this
# re-dispatch, a committed enforcer fix leaves BOTH SHAs without a live qa verdict.
#
# THE FIX. On a pre-admission `synchronize` whose HEAD commit is a bot self-fix,
# re-fire the reviewers on that SHA (this script returns `reverify=true`; the
# pr-pipeline.yml enforcer gate ORs it into its fire condition, and qa cascades).
# This is a NARROWING of the fire-once rule, not a repeal: a HUMAN pre-admission
# push has a non-self-fix HEAD → `reverify=false` → the reviewers still skip
# (fire-once preserved). Discrimination is on the COMMIT's own trailer, never on
# author identity (the author heuristic the pipeline deliberately abandoned —
# pr-pipeline.yml `initialize` §5 note about the `botnicbot` misclassification).
#
# LOOP CEILING (brief: "do not create an infinite re-dispatch loop"). An enforcer
# self-fix can beget another enforcer self-fix, so the re-dispatch is bounded by
# MAX_SELFFIX_REVERIFY (default 5, mirroring MAX_MECHANIC_RUNS): once the branch
# carries that many loop-capable self-fix commits (Enforcer-By: / Responder-By:),
# stop auto-re-firing pre-admission and let the human admission boundary
# (admit-on-review.yml admit-enforcer/admit-qa) re-verify instead — a safe
# degradation, since review-attestation still fail-closes the merge gate. Lint
# autofix is a TRIGGER (its fixed SHA needs a fresh verdict too) but is NOT
# counted toward the ceiling: ruff --fix is idempotent and cannot oscillate, so
# counting it would only prematurely exhaust the budget.
#
# This is a DETERMINISTIC decision — it reads a commit message and a commit count,
# no qualitative judgment — matching the review-attestation.sh / check-mechanical-
# red.sh pattern, and is unit-tested as a pure function via injected env
# (tests/test_selffix_reverify.py) with no gh stub.
#
# Required env:
#   REPO       owner/name (only used for the live gh api fetches).
#   HEAD_SHA   the exact PR head SHA under evaluation (the synchronize tip).
# Optional env:
#   BASE_BRANCH            PR base branch for the ceiling count (default: dev).
#   MAX_SELFFIX_REVERIFY   integer cap on loop-capable self-fix commits (default 5).
#   HEAD_MESSAGE           the HEAD commit message (testing; skips the gh fetch).
#   HEAD_MESSAGE_FILE      path to a file with the HEAD commit message (testing).
#   COMPARE_JSON           path to a file with the base...head compare JSON
#                          (testing; skips the gh fetch for the ceiling count).
#   SELFFIX_COUNT          integer loop-capable self-fix count (testing; wins over
#                          COMPARE_JSON and the live fetch).
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   reverify   "true"  — HEAD is a bot self-fix under the ceiling → re-dispatch.
#              "false" — not a self-fix, ceiling reached, or fetch error
#                        (fail-closed: never re-fire on uncertainty).

set -euo pipefail

REPO="${REPO:?REPO is required}"
HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
BASE_BRANCH="${BASE_BRANCH:-dev}"  # allow-fallback: pr-pipeline.yml always passes the PR base ref; dev is the safe live default.
MAX_SELFFIX_REVERIFY="${MAX_SELFFIX_REVERIFY:-5}"  # allow-fallback: documented default cap, mirrors MAX_MECHANIC_RUNS.

emit() {
  printf 'reverify=%s\n' "$1"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf 'reverify=%s\n' "$1" >>"$GITHUB_OUTPUT"
  fi
}

# ── Resolve the HEAD commit message (self-fix TRIGGER test) ──────────────────
if [[ -n "${HEAD_MESSAGE:-}" ]]; then
  head_message="$HEAD_MESSAGE"
elif [[ -n "${HEAD_MESSAGE_FILE:-}" ]]; then
  head_message="$(cat "$HEAD_MESSAGE_FILE")"
elif ! head_message="$(gh api "repos/${REPO}/commits/${HEAD_SHA}" --jq '.commit.message' 2>/dev/null)"; then
  # Fail-closed: cannot read the tip → do not re-fire (admission boundary re-verifies).
  emit "false"
  exit 0
fi

# TRIGGER set: a loop-capable bot self-fix (Enforcer-By:/Responder-By: trailer on
# any line) OR a deterministic lint autofix (its fixed SHA still needs a verdict).
head_is_selffix="false"
if grep -qE '^(Enforcer-By|Responder-By):' <<<"$head_message" \
  || grep -qE '^style: autofix lint' <<<"$head_message"; then
  head_is_selffix="true"
fi

if [[ "$head_is_selffix" != "true" ]]; then
  # A human (or any non-self-fix) push — fire-once preserved, reviewers skip.
  emit "false"
  exit 0
fi

# ── Ceiling count: loop-capable self-fix commits on base..head ───────────────
# Only Enforcer-By:/Responder-By: are counted — the ones that can re-beget a
# self-fix and thus a re-dispatch loop. Lint autofix is idempotent; excluded.
if [[ -n "${SELFFIX_COUNT:-}" ]]; then
  count="$SELFFIX_COUNT"
elif [[ -n "${COMPARE_JSON:-}" ]]; then
  count="$(jq '[.commits[]? | select((.commit.message // "") | test("(^|\n)(Enforcer-By|Responder-By):"))] | length' "$COMPARE_JSON")"
elif ! count="$(gh api "repos/${REPO}/compare/${BASE_BRANCH}...${HEAD_SHA}" \
  --jq '[.commits[]? | select((.commit.message // "") | test("(^|\n)(Enforcer-By|Responder-By):"))] | length' 2>/dev/null)"; then
  # Fail-closed: cannot measure the budget → do not re-fire.
  emit "false"
  exit 0
fi

# Guard against a non-numeric count (malformed injection): fail closed.
if ! [[ "$count" =~ ^[0-9]+$ ]]; then
  emit "false"
  exit 0
fi

if [[ "$count" -ge "$MAX_SELFFIX_REVERIFY" ]]; then
  # Budget exhausted — stop auto-re-firing; the admission boundary re-verifies.
  emit "false"
  exit 0
fi

emit "true"
