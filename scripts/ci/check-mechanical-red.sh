#!/usr/bin/env bash
# check-mechanical-red.sh
#
# Gate decision for the pre-admission mechanical responder
# (specs/workflows/pr-pipeline.md §3.8).
#
# This script is a DETERMINISTIC STATUS CHECK — it reads literal GitHub commit
# status string values (success/failure/pending) and a git commit count; it
# makes NO qualitative judgment about the content of any finding. The qualitative
# judgment ("is this finding mechanical vs. a judgment call?") is made by the LLM
# responder agent at runtime when it reads the review bodies. This script only
# decides "should the responder be dispatched at all?" — the same deterministic
# pattern as review-attestation.sh (§3.7, checks status strings) and
# admit-on-review.sh (§3.2, checks permission strings).
#
# The pre-admission responder fires ONLY when ALL of the following are true:
#
#   (1) At least one of enforcer-status / qa-status is `failure` on HEAD.
#       Source: pr-pipeline.md §3.4 pt 5 — a red verdict is a handoff; the
#       responder is who clears mechanically-fixable red pre-admission.
#       NO-OP-ON-GREEN GUARD: if both are success, exit immediately — this is the
#       P5 pathology guard (PR #1614, pr-pipeline.md §1 table row P5): never burn
#       a runner on a green PR.
#
#   (2) admit-status is NOT `success` (PR is pre-admission).
#       STAGE-2 GUARD: if the PR is already admitted, the post-admission mechanic
#       (pr-pipeline.md §3.3/§3.6, agent-mechanic.yml) handles any remaining red.
#       The pre-admission responder must not run alongside the Stage-2 loop.
#
#   (3) The Responder-By: commit count on the branch has not reached
#       MAX_RESPONDER_RUNS (default 3).
#       CEILING GUARD: mirrors the mechanic's MAX_MECHANIC_RUNS=5 ceiling
#       (pr-pipeline.md §3.6 axis A) but at a tighter budget (3 vs 5) because
#       pre-admission work is on un-blessed changes the maintainer may reject.
#       Counted via: git log "origin/$BASE_BRANCH..HEAD" --grep="^Responder-By:"
#       Source: pr-pipeline.md §3.6 axis A mechanic pattern, adapted for responder.
#
# (4) Stage 1 has converged on this SHA (lint/enforcer/qa ran with no commits).
#     This is enforced by the pipeline's needs: graph before this script runs,
#     not by the script itself. The convergence-guard below is a fail-safe only.
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   has_mechanical_red  — "true" or "false"
#   reason              — human-readable diagnostic string
#
# TESTABILITY: The statuses-JSON approach (STATUSES_JSON env var injecting a file
# path, or live gh api) is identical to review-attestation.sh (scripts/ci/
# review-attestation.sh:50-54) — the decision is a pure function over status
# values, testable without a gh stub. See tests/test_check_mechanical_red.py.
#
# Required env:
#   HEAD_SHA           — exact PR head SHA under evaluation.
#   REPO               — owner/name (e.g. nicsuzor/academicOps).
# Optional env:
#   BASE_BRANCH        — PR base branch for Responder-By: count (default: dev).
#                        Only used in live runs (when STATUSES_JSON is unset).
#   STATUSES_JSON      — path to a file containing the commit-statuses JSON array
#                        for HEAD_SHA (testing / offline). When unset, fetched
#                        live via gh api.
#   RESPONDER_COUNT_JSON
#                      — path to a file containing the integer responder-commit
#                        count (testing only). When unset, computed via git log.
#   MAX_RESPONDER_RUNS — integer cap on Responder-By: commits (default: 3).

set -euo pipefail

HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
REPO="${REPO:?REPO is required}"
MAX_RESPONDER_RUNS="${MAX_RESPONDER_RUNS:-3}"  # allow-fallback: optional config knob; documented default cap in pr-pipeline.md §3.8

# ── Fetch statuses (testable via STATUSES_JSON) ─────────────────────────────
# Pattern from review-attestation.sh:50-54.
if [[ -n "${STATUSES_JSON:-}" ]]; then
  statuses="$(cat "$STATUSES_JSON")"
else
  statuses="$(gh api "repos/${REPO}/commits/${HEAD_SHA}/statuses?per_page=100")"
fi

# Ensure statuses is a valid JSON array, default to empty array if not
if ! jq -e 'type == "array"' <<< \
"${statuses:-}" >/dev/null 2>&1; then
  statuses="[]"
fi

latest_state() {
  local ctx="$1"
  jq -r --arg c "$ctx" \
    '[.[] | select(.context == $c)] | sort_by(.created_at) | last | .state // empty' \
    <<<"$statuses"
}

enforcer_state="$(latest_state "enforcer-status")"
qa_state="$(latest_state "qa-status")"
admit_state="$(latest_state "admit-status")"

emit() {
  printf 'has_mechanical_red=%s\n' "$1"
  printf 'reason=%s\n' "$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      printf 'has_mechanical_red=%s\n' "$1"
      printf 'reason=%s\n' "$2"
    } >>"$GITHUB_OUTPUT"
  fi
}

# ── Guard 1: No-op-on-green ──────────────────────────────────────────────────
# Source: pr-pipeline.md §3.8 constraint "MUST only fire when there is actually
# mechanically-fixable red to clear — never on a green PR".
# Both success → nothing for the responder to do.
if [[ "$enforcer_state" == "success" && "$qa_state" == "success" ]]; then
  emit "false" "No-op-on-green: enforcer-status=success, qa-status=success — no red to respond to"
  exit 0
fi

# ── Guard 2: Convergence guard ───────────────────────────────────────────────
# A pending or absent status means Stage 1 hasn't posted a terminal verdict yet.
# The pipeline needs: graph ensures convergence before this script runs, but we
# fail-safe here: we cannot meaningfully classify "pending" as red.
if [[ -z "$enforcer_state" || "$enforcer_state" == "pending" ]]; then
  emit "false" "Convergence guard: enforcer-status not yet terminal (${enforcer_state:-absent}) — Stage 1 not converged"  # allow-fallback: display-only; empty enforcer_state is already guarded by -z check above
  exit 0
fi
if [[ -z "$qa_state" || "$qa_state" == "pending" ]]; then
  emit "false" "Convergence guard: qa-status not yet terminal (${qa_state:-absent}) — Stage 1 not converged"  # allow-fallback: display-only; empty qa_state is already guarded by -z check above
  exit 0
fi

# ── Guard 3: Stage-2 guard ───────────────────────────────────────────────────
# Source: pr-pipeline.md §3.8 constraint "Stage-2 guard: if already admitted,
# the post-admission mechanic handles it."
if [[ "$admit_state" == "success" ]]; then
  emit "false" "Stage-2 guard: PR is already admitted (admit-status=success) — Stage-2 mechanic handles red"
  exit 0
fi

# ── Guard 4: Ceiling guard ───────────────────────────────────────────────────
# Source: pr-pipeline.md §3.8 / §3.6 axis A pattern — count Responder-By:
# commits since the PR diverged from the base.
if [[ -n "${RESPONDER_COUNT_JSON:-}" ]]; then
  responder_count="$(cat "$RESPONDER_COUNT_JSON")"
else
  BASE_BRANCH="${BASE_BRANCH:-dev}"  # allow-fallback: optional; pr-pipeline.yml always passes BASE_BRANCH; dev is the safe live fallback
  # FAIL-CLOSED: if we cannot fetch the base or count Responder-By: commits, we
  # must NOT silently treat the count as 0 — that would let the responder run
  # past MAX_RESPONDER_RUNS and burn runner budget. A failure to measure the
  # budget is treated as budget-exhausted: no-op and surface to a human.
  if ! git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null; then
    emit "false" "Ceiling guard (fail-closed): could not fetch origin/${BASE_BRANCH} to count Responder-By: commits — surfacing to human"
    exit 0
  fi
  if ! responder_count=$(git log "origin/$BASE_BRANCH..HEAD" --grep="^Responder-By:" --oneline 2>/dev/null | wc -l | tr -d '[:space:]'); then
    emit "false" "Ceiling guard (fail-closed): could not count Responder-By: commits on origin/${BASE_BRANCH}..HEAD — surfacing to human"
    exit 0
  fi
fi

# Guard against a non-numeric/empty count from a malformed RESPONDER_COUNT_JSON:
# fail closed (treat as at-ceiling) rather than defaulting to 0.
if ! [[ "$responder_count" =~ ^[0-9]+$ ]]; then
  emit "false" "Ceiling guard (fail-closed): responder_count '${responder_count}' is not a non-negative integer — surfacing to human"
  exit 0
fi

if [[ "$responder_count" -ge "$MAX_RESPONDER_RUNS" ]]; then
  emit "false" "Ceiling guard: Responder-By: count (${responder_count}) >= MAX_RESPONDER_RUNS (${MAX_RESPONDER_RUNS}) — pre-admission budget exhausted; surfacing to human"
  exit 0
fi

# ── All guards passed: mechanical red exists pre-admission ───────────────────
emit "true" "Pre-admission mechanical red: enforcer=${enforcer_state}, qa=${qa_state}, admit=${admit_state:-absent}, responder_runs=${responder_count:-0}/${MAX_RESPONDER_RUNS} — dispatching responder"  # allow-fallback: display-only; both values are already set/guarded by blocks above
