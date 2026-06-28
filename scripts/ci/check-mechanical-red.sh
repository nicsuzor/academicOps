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
#   (1) At least one mechanical-red trigger is present on HEAD:
#         - enforcer-status == `failure`, OR
#         - qa-status == `failure`, OR
#         - the `Pytest` check-run == `failure` AND that failure is attributable
#           to THIS PR's diff (NOT also failing on the base branch — see #1965).
#       Source: pr-pipeline.md §3.4 pt 5 / §3.8 — a red verdict is a handoff; the
#       responder is who clears mechanically-fixable red (including failing CI)
#       pre-admission.
#       NO-OP-ON-GREEN GUARD: if enforcer + qa are both success AND there is no
#       PR-attributable Pytest red, exit immediately — this is the P5 pathology
#       guard (PR #1614, pr-pipeline.md §1 table row P5): never burn a runner on a
#       green PR.
#       BASE-BROKEN PYTEST GUARD (#1965): a test broken on the base branch reddens
#       Pytest on EVERY PR. Dispatching the responder for it would spawn a
#       thundering herd of useless runs — the responder cannot fix a base failure
#       from a PR branch. So a Pytest failure is a trigger ONLY when Pytest is NOT
#       also failing on the base branch. If the base state cannot be verified, we
#       fail closed (no dispatch) and surface to a human.
#
#       NOTE ON WHY PYTEST IS READ DIFFERENTLY: `Pytest` is a GitHub Actions
#       check-run, NOT a commit status, so it never appears in the commit-statuses
#       API this script reads for enforcer/qa/admit. HEAD's Pytest result is passed
#       in deterministically via PYTEST_RESULT (the `needs.pytest.result` of the
#       same pr-pipeline run — check-mechred `needs: [..., pytest]`, so Pytest is
#       always terminal when this script runs; no polling/race). The base branch's
#       Pytest state is queried live from the check-runs API (only when needed).
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
#   PYTEST_RESULT      — HEAD `Pytest` job result from the same pr-pipeline run
#                        (`needs.pytest.result`: success/failure/skipped/...).
#                        Only `failure` is a candidate trigger. Absent → treated
#                        as not-a-trigger.
#   BASE_BRANCH        — PR base branch, used both for the Responder-By: count and
#                        for the base-broken Pytest check (default: dev).
#   STATUSES_JSON      — path to a file containing the commit-statuses JSON array
#                        for HEAD_SHA (testing / offline). When unset, fetched
#                        live via gh api.
#   BASE_CHECK_RUNS_JSON
#                      — path to a file containing the check-runs JSON for the base
#                        branch HEAD (testing). When unset, fetched live via gh api
#                        ONLY when a Pytest failure needs base-attribution.
#   RESPONDER_COUNT_JSON
#                      — path to a file containing the integer responder-commit
#                        count (testing only). When unset, computed via git log.
#   MAX_RESPONDER_RUNS — integer cap on Responder-By: commits (default: 3).

set -euo pipefail

HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
REPO="${REPO:?REPO is required}"
MAX_RESPONDER_RUNS="${MAX_RESPONDER_RUNS:-3}"  # allow-fallback: optional config knob; documented default cap in pr-pipeline.md §3.8
BASE_BRANCH="${BASE_BRANCH:-dev}"  # allow-fallback: optional; pr-pipeline.yml always passes BASE_BRANCH; dev is the safe live fallback. Used for the Responder-By: count AND the base-broken Pytest check.

# HEAD Pytest result. `Pytest` is a check-run, not a commit status, so it is NOT
# in the statuses JSON; it is passed in deterministically as needs.pytest.result
# (terminal because check-mechred needs:[..., pytest]). Only `failure` is a
# candidate trigger; anything else (success/skipped/cancelled/absent) is not.
pytest_state="${PYTEST_RESULT:-}"

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

# ── Base-broken Pytest attribution (#1965) ───────────────────────────────────
# Returns the latest COMPLETED `Pytest` conclusion on the base branch:
#   "failure"      — base is broken; a Pytest red is NOT attributable to the PR.
#   "success"      — base is green; a Pytest red IS attributable to the PR.
#   ""             — no completed base Pytest run found; treat as not-broken.
#   "unverifiable" — could not fetch the base check-runs (live API error); we
#                    fail closed (no dispatch) rather than risk a thundering herd.
base_pytest_conclusion() {
  local json
  if [[ -n "${BASE_CHECK_RUNS_JSON:-}" ]]; then
    json="$(cat "$BASE_CHECK_RUNS_JSON")"
  elif ! json="$(gh api "repos/${REPO}/commits/${BASE_BRANCH}/check-runs?per_page=100" 2>/dev/null)"; then
    printf 'unverifiable'
    return 0
  fi
  # The live check-runs API returns {check_runs:[...]}; injected test JSON may be
  # a bare array. Normalise to an array, default to [] on anything malformed.
  local arr
  arr="$(jq 'if type == "object" and has("check_runs") then .check_runs else . end' <<<"$json" 2>/dev/null || printf '[]')"
  if ! jq -e 'type == "array"' <<<"$arr" >/dev/null 2>&1; then arr="[]"; fi
  jq -r '
    [ .[] | select((.name == "Pytest" or ((.name | tostring) | endswith("Pytest"))) and .status == "completed") ]
    | sort_by(.completed_at // .started_at // "") | last
    | if . == null then ""
      elif (.conclusion == "failure" or .conclusion == "timed_out") then "failure"
      elif (.conclusion == "success") then "success"
      else "" end
  ' <<<"$arr"
}

# ── Guard 1: No-op-on-green (incl. PR-attributable Pytest red, #1965) ─────────
# Source: pr-pipeline.md §3.8 constraint "MUST only fire when there is actually
# mechanically-fixable red to clear — never on a green PR".
# enforcer + qa both success → the only remaining trigger is a Pytest failure
# that is attributable to THIS PR's diff (not also failing on the base branch).
if [[ "$enforcer_state" == "success" && "$qa_state" == "success" ]]; then
  if [[ "$pytest_state" != "failure" ]]; then
    emit "false" "No-op-on-green: enforcer-status=success, qa-status=success, Pytest=${pytest_state:-absent} — no red to respond to"  # allow-fallback: display-only; the trigger test above gated on the exact value, this is just the diagnostic label
    exit 0
  fi
  # Pytest is red on HEAD and is the only candidate trigger. Apply the
  # base-broken guard before dispatching.
  base_pytest_state="$(base_pytest_conclusion)"
  case "$base_pytest_state" in
    failure)
      emit "false" "Base-broken Pytest guard (#1965): Pytest=failure on HEAD but ALSO failing on origin/${BASE_BRANCH} — not attributable to this PR's diff; surfacing to human (the responder cannot fix a base failure from a PR branch)"
      exit 0
      ;;
    unverifiable)
      emit "false" "Base-broken Pytest guard (fail-closed): Pytest=failure on HEAD but base Pytest state on origin/${BASE_BRANCH} could not be verified — surfacing to human rather than risk a herd of useless responder runs"
      exit 0
      ;;
    *)
      : # base green ("success") or no completed base run ("") → Pytest red is
        # PR-attributable → fall through to the remaining guards and dispatch.
      ;;
  esac
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
emit "true" "Pre-admission mechanical red: enforcer=${enforcer_state}, qa=${qa_state}, pytest=${pytest_state:-absent}, admit=${admit_state:-absent}, responder_runs=${responder_count:-0}/${MAX_RESPONDER_RUNS} — dispatching responder"  # allow-fallback: display-only; both values are already set/guarded by blocks above
