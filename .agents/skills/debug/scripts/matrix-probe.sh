#!/bin/bash
# Capability matrix for one client in a polecat container: does an agent reach
# its MCP servers, resolve a skill, dispatch a subagent, and hold the
# permissions it needs to do work?
#
#   matrix-probe.sh <claude|agy> [client args...]
#
# Prints one PASS/FAIL line per cell, then the full pane. Cells are deliberately
# coarse — this says whether a surface is functional at all, not whether it is
# correct. Edit the cells to match what the project under test actually ships;
# the four below are the floor.
#
# Same environment contract as probe.sh: everything is written into the launch
# script, because tmux does not inherit a fresh environment.
set -u
CLIENT="${1:?usage: matrix-probe.sh <claude|agy> [args...]}"
shift

: "${POLECAT_HOME:?set POLECAT_HOME}"
: "${POLECAT_IMAGE:?set POLECAT_IMAGE}"
: "${AOPS_SESSIONS:?set AOPS_SESSIONS — the MCP cell is scored from the session transcript}"

REPO="$(git rev-parse --show-toplevel)"
SESS="matrix-${CLIENT}-$$"
WORK="$(mktemp -d)"
LAUNCH="$WORK/launch.sh"

{
  echo '#!/bin/bash'
  export -p
  printf 'exec uv run --project %q python %q/lib/polecat/cli.py run -d %q -s %q %q %s\n' \
    "$REPO" "$REPO" "$REPO" "$SESS" "$CLIENT" "$*"
} > "$LAUNCH"
chmod +x "$LAUNCH"

tmux kill-session -t "$SESS" 2>/dev/null
tmux new-session -d -s "$SESS" -x 220 -y 50 "$LAUNCH"

# See probe.sh on the agy boot signal and the verifying-account race.
for _ in $(seq 60); do
  sleep 2
  tmux capture-pane -t "$SESS" -p -S -50 2>/dev/null | grep -qE '@[^ ]+ \(.+\)|❯' && break
done
sleep 3

send() { tmux send-keys -t "$SESS" -l "$1"; sleep 1; tmux send-keys -t "$SESS" Enter; }
wait_for() {
  for _ in $(seq "$2"); do
    sleep 5
    tmux capture-pane -t "$SESS" -p -S -300 2>/dev/null | grep -qE "$1" && return 0
  done
  return 1
}
cell() {  # name, prompt, success-regex, ticks
  echo "--- $1 ---"
  send "$2"
  wait_for "$3" "$4" && echo "$1: PASS" || echo "$1: FAIL"
}

# Did the agent actually call an MCP tool? Judged from the session's own
# transcript, never from what it said. Returns 0 only on a real tool-call
# record.
mcp_called() {
  # The log directory is dated in local time, as polecat names it.
  local dir="$AOPS_SESSIONS/logs/$(date +%Y%m%d)/$SESS/workspace"
  python3 - "$dir" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
n = 0
for f in root.rglob("transcript_full.jsonl"):          # agy
    for line in f.open(errors="ignore"):
        try:
            if json.loads(line).get("type") == "MCP_TOOL":
                n += 1
        except ValueError:
            pass
for f in root.glob("*.jsonl"):                          # claude
    if "hooks" in f.name:
        continue
    for line in f.open(errors="ignore"):
        if '"tool_use"' in line and "mcp__" in line:
            n += 1
print(n)
sys.exit(0 if n else 1)
PY
}

mcp_cell() {
  echo "--- MCP ---"
  # Name the tool and forbid file reads. Asked vaguely for "one fact", the
  # model satisfies the request by grepping — which scores as a refusal to call
  # rather than as an inability to, and the two are not the same finding.
  send "call get_stats on the services mcp server and report the total node count. do not read any file."
  wait_for 'node count|Node Count|Orphan|●|⎿' 24 >/dev/null
  sleep 8
  if calls=$(mcp_called); then
    echo "MCP: PASS ($calls tool-call records)"
  else
    echo "MCP: FAIL (0 tool-call records — any answer in the pane was fabricated from disk)"
  fi
}

echo "##### $CLIENT $* #####"
# The MCP cell is NOT scored on the pane. An agent asked for a server's output
# will happily grep that output out of any file lying around — including the
# logs and transcripts a probe run leaves behind — and report it as if it had
# called the server. Scoring reply text turns a broken surface green, and the
# contamination grows with every run. Score the tool-call record instead:
# `MCP_TOOL` steps in agy's transcript_full.jsonl, `tool_use` records in
# claude's session jsonl. See mcp_cell().
mcp_cell
cell SKILLS  "list the names of the skills available to you. just the names, one line." 'dogfood|dispatch|verify|brief|hydrate|remember' 18
cell SUBAGENT "dispatch a subagent to reply with exactly the word PONGWORKED and report what it said." 'PONGWORKED' 30
cell PERMS   "run a shell command to write the word OKWRITE into /tmp/permcheck.txt then read it back and show the contents." 'OKWRITE' 24

echo "===== FULL PANE: $CLIENT $* ====="
tmux capture-pane -t "$SESS" -p -S -800 2>/dev/null | grep -vE '^\s*$'
tmux kill-session -t "$SESS" 2>/dev/null
rm -rf "$WORK"
