#!/usr/bin/env bash
# reap-agent-processes.sh
#
# Reap "zombie" agent processes left behind by a cancelled first attempt, so a
# retry never runs concurrently with the attempt it is supposed to replace
# (aops-1adfd28d).
#
# Problem this defends against: `anthropics/claude-code-action` surfaces a
# `rate_limit_event` as a step `cancelled`. GitHub marks the STEP cancelled, but
# the underlying `claude` process can survive on the runner and keep working in
# the background. The enforcer workflow's one-shot retry (aops-221211fa) then
# launches a SECOND agent, so two enforcer agents run concurrently in one job
# and both post `## Enforcer Review` verdicts — observed on run 27250704371
# leaving three reviews (two dismissed) on a single SHA, with an unordered race
# that could leave a STALE verdict standing last.
#
# This script is the cleanup mechanism for that cancellation path: before the
# retry launches, reap any agent process group matching $PATTERN that is NOT in
# this script's own process group. Killing by process GROUP (not just the
# matched PID) takes down the whole `claude` subtree (node/bun launcher + CLI +
# any tool subprocesses), not just the leader.
#
# The claude-code-action runs as a third-party `uses:` step, so a `trap` cannot
# be installed inside it; reaping from the next step (which runs on the same
# runner, same user, and can see processes a prior step detached) is the
# reachable cleanup boundary.
#
# Usage:
#   reap-agent-processes.sh [PATTERN]
#     PATTERN  pgrep -f command-line pattern of the agent to reap.
#              Default: env REAP_PATTERN, else "claude".
# Env:
#   REAP_PATTERN     default pattern when no arg is given.
#   REAP_GRACE_SECS  seconds to wait after SIGTERM before SIGKILL (default 3).
#
# Best-effort by design: never aborts the job (no `set -e`). Exit 0 always —
# the retry must proceed whether or not a zombie was present.

set -uo pipefail  # allow-fallback: intentionally NOT -e — reaping is best-effort cleanup that must never abort the caller's retry path

PATTERN="${1:-${REAP_PATTERN:-claude}}"  # allow-fallback: configurable match target; default "claude" is the agent CLI this workflow runs
GRACE="${REAP_GRACE_SECS:-3}"            # allow-fallback: SIGTERM→SIGKILL grace window, tunable for slow shutdowns

self_pid=$$
self_pgid="$(ps -o pgid= -p "$self_pid" 2>/dev/null | tr -d ' ')"

# Candidate PIDs whose full command line matches PATTERN. pgrep excludes its own
# PID; we additionally exclude this script's entire process group below, so the
# reaper can never kill itself, its parent step shell, or the test runner that
# launched it (whose argv may legitimately contain PATTERN).
mapfile -t pids < <(pgrep -f -- "$PATTERN" 2>/dev/null || true)

declare -A pgids=()
for pid in "${pids[@]}"; do
  [ -n "$pid" ] || continue
  [ "$pid" = "$self_pid" ] && continue
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')"
  [ -n "$pgid" ] || continue
  [ "$pgid" = "$self_pgid" ] && continue   # never reap our own group
  pgids["$pgid"]=1
done

if [ "${#pgids[@]}" -eq 0 ]; then
  echo "reap: no surviving processes match '$PATTERN'"
  exit 0
fi

for pgid in "${!pgids[@]}"; do
  echo "reap: SIGTERM process group $pgid (matched '$PATTERN')"
  kill -TERM -- "-$pgid" 2>/dev/null || true
done

sleep "$GRACE"

reaped=""
for pgid in "${!pgids[@]}"; do
  if kill -0 -- "-$pgid" 2>/dev/null; then
    echo "reap: SIGKILL process group $pgid (survived SIGTERM)"
    kill -KILL -- "-$pgid" 2>/dev/null || true
  fi
  reaped="$reaped $pgid"
done

echo "reaped_pgids=${reaped# }"
exit 0
