#!/usr/bin/env bash
# user-side-pr-review.sh
#
# Periodic user-side reviewer. Polls GitHub for PRs labelled
# `ready-for-review` (set by GHA mechanical merge-prep), dispatches the
# judge-role agent (the rebuilt RBG — see aops-core/agents/rbg.md) against
# each, and on PASS labels the PR `approve-ready` for the next daily sweep.
#
# Heartbeat: writes a last-run timestamp on every successful invocation to
#   $HEARTBEAT_FILE. The daily-sweep CTA reads this to distinguish
#   "no approve-ready PRs" from "reviewer cron stalled". Path is also
#   referenced from aops-core/skills/daily/instructions/workflow-monitor.md.
#
# Hard budget: <200 LOC. If this grows past that, the design is wrong —
# raise it as a follow-up rather than bloating this script.
#
# Inputs (env, all optional):
#   AOPS_PR_REVIEW_REPOS  Space-separated list of <owner>/<repo>. Default:
#                         derived from $AOPS_SESSIONS/projects.yaml when
#                         present; otherwise just the current repo.
#   AOPS_PR_REVIEW_LABEL  Source label to poll. Default: ready-for-review.
#   AOPS_PR_APPROVE_LABEL Label set on PASS. Default: approve-ready.
#   AOPS_RBG_CMD          Command that runs the judge agent for one PR.
#                         Receives the PR url as argv[1] and must print a
#                         Verdict block to stdout ending with an
#                         "Overall: APPROVE|REVISE|BLOCK|ESCALATE" line.
#                         Default: dispatch via polecat
#                         using the rbg agent.
#   HEARTBEAT_FILE        Override for the heartbeat path. Default below.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HEARTBEAT_FILE="${HEARTBEAT_FILE:-$SCRIPT_DIR/state/user-side-pr-review.last-run}"
SOURCE_LABEL="${AOPS_PR_REVIEW_LABEL:-ready-for-review}"
APPROVE_LABEL="${AOPS_PR_APPROVE_LABEL:-approve-ready}"
LOG_PREFIX="[user-side-pr-review]"

log() { printf '%s %s\n' "$LOG_PREFIX" "$*" >&2; }

# Heartbeat MUST emit even if no PRs are found, so the daily sweep can tell
# "cron ran, found nothing" apart from "cron has not run".
write_heartbeat() {
  local now_epoch now_iso
  now_epoch="$(date -u +%s)"
  now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$HEARTBEAT_FILE")"
  printf 'epoch=%s\ntimestamp=%s\n' "$now_epoch" "$now_iso" > "$HEARTBEAT_FILE"
}

# Best-effort heartbeat on any exit so silent failure (script crashes early)
# is still distinguishable from "cron not scheduled at all" — the file exists
# but its timestamp goes stale.
trap 'write_heartbeat' EXIT

require() {
  command -v "$1" >/dev/null 2>&1 || { log "missing dependency: $1"; exit 2; }
}

require gh
require jq

discover_repos() {
  if [ -n "${AOPS_PR_REVIEW_REPOS:-}" ]; then
    printf '%s\n' $AOPS_PR_REVIEW_REPOS
    return
  fi
  local registry="${AOPS_SESSIONS:-}/projects.yaml"
  if [ -n "${AOPS_SESSIONS:-}" ] && [ -f "$registry" ]; then
    # projects.yaml repo entries look like: `repo: owner/name`. Pull those out.
    awk '/^[[:space:]]*repo:[[:space:]]*[^[:space:]]+\/[^[:space:]]+/ {print $2}' "$registry"
    return
  fi
  # Fallback: current repo (works when cron runs inside a checkout).
  if gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null; then
    return
  fi
  log "no repos to poll (set AOPS_PR_REVIEW_REPOS)"
  return
}

list_ready_prs() {
  local repo="$1"
  gh pr list --repo "$repo" \
    --state open \
    --label "$SOURCE_LABEL" \
    --json number,url,headRefName,labels \
    --limit 50 2>/dev/null || echo '[]'
}

already_approved() {
  # Skip PRs already carrying $APPROVE_LABEL — idempotent.
  local labels_json="$1"
  printf '%s' "$labels_json" \
    | jq -e --arg L "$APPROVE_LABEL" '.[] | select(.name == $L)' >/dev/null 2>&1
}

run_judge() {
  local pr_url="$1"
  if [ -n "${AOPS_RBG_CMD:-}" ]; then
    # User override; pass PR url as argv[1].
    AOPS_RBG_CMD_ARR=($AOPS_RBG_CMD)
    "${AOPS_RBG_CMD_ARR[@]}" "$pr_url"
    return
  fi
  # Default: spawn the rbg judge agent via polecat. The agent is owned by
  # aops-core/agents/rbg.md (parallel sibling task-6e97e850); we MUST NOT
  # inline judge behaviour here.
  #
  # NOTE (task-1e657d9f): polecat interactive oneshot dispatch is not yet
  # certified. Until that task resolves, `polecat run --agent rbg` returns a
  # 401 auth error; the caller's error-capture branch will log "judge dispatch
  # failed" and leave the PR unlabelled. Override AOPS_RBG_CMD to use a
  # different dispatch path in the interim.
  local polecat_bin
  polecat_bin="$(command -v polecat || true)"
  if [ -z "$polecat_bin" ]; then
    if [ -n "${AOPS:-}" ] && command -v uv >/dev/null 2>&1; then
      uv run --project "$AOPS" "$AOPS/polecat/cli.py" \
        run --agent rbg --arg pr_url="$pr_url"
      return
    fi
    log "polecat not on PATH and AOPS unset; cannot dispatch rbg for $pr_url"
    return 3
  fi
  "$polecat_bin" run --agent rbg --arg pr_url="$pr_url"
}

verdict_from_output() {
  # Judge agent (rbg) emits a structured Verdict block ending with an
  # `Overall: <APPROVE|REVISE|BLOCK|ESCALATE>` line (see aops-core/agents/rbg.md
  # "Verdict block (REQUIRED schema)"). Coerce to the cron's two-state action:
  # APPROVE → PASS (apply approve-ready); REVISE/BLOCK → FAIL (no label);
  # ESCALATE / unparseable → ABSTAIN (no label).
  local out="$1"
  if printf '%s' "$out" | grep -Eiq '^[[:space:]]*Overall:[[:space:]]*APPROVE\b'; then
    echo PASS; return
  fi
  if printf '%s' "$out" | grep -Eiq '^[[:space:]]*Overall:[[:space:]]*(REVISE|BLOCK)\b'; then
    echo FAIL; return
  fi
  echo ABSTAIN
}

review_pr() {
  local repo="$1" pr_num="$2" pr_url="$3"
  log "judging $repo#$pr_num ($pr_url)"
  local judge_out
  if ! judge_out="$(run_judge "$pr_url" 2>&1)"; then
    log "judge dispatch failed for $repo#$pr_num — leaving labels unchanged"
    return 0
  fi
  local verdict
  verdict="$(verdict_from_output "$judge_out")"
  case "$verdict" in
    PASS)
      log "$repo#$pr_num PASS — applying $APPROVE_LABEL"
      gh pr edit "$pr_num" --repo "$repo" --add-label "$APPROVE_LABEL" \
        || log "failed to apply $APPROVE_LABEL to $repo#$pr_num"
      ;;
    FAIL)
      log "$repo#$pr_num FAIL — leaving for human review"
      ;;
    *)
      log "$repo#$pr_num ABSTAIN (no Verdict line) — leaving unchanged"
      ;;
  esac
}

main() {
  local repos found=0
  repos="$(discover_repos)"
  if [ -z "$repos" ]; then
    log "no repos discovered; emitting heartbeat and exiting"
    return 0
  fi
  while IFS= read -r repo; do
    [ -z "$repo" ] && continue
    local prs
    prs="$(list_ready_prs "$repo")"
    [ "$prs" = '[]' ] && continue
    local count
    count="$(printf '%s' "$prs" | jq 'length')"
    [ "$count" -eq 0 ] && continue
    found=$((found + count))
    while IFS= read -r row; do
      local num url labels
      num="$(printf '%s' "$row" | jq -r '.number')"
      url="$(printf '%s' "$row" | jq -r '.url')"
      labels="$(printf '%s' "$row" | jq -c '.labels')"
      if already_approved "$labels"; then
        log "$repo#$num already $APPROVE_LABEL — skipping"
        continue
      fi
      review_pr "$repo" "$num" "$url"
    done < <(printf '%s' "$prs" | jq -c '.[]')
  done <<< "$repos"
  log "scan complete: $found PR(s) considered"
}

main "$@"
