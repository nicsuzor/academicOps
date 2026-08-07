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

echo "##### $CLIENT $* #####"
cell MCP     "ask the pkb mcp server for its status and return the entire reply only." 'build_profile|version' 24
cell SKILLS  "list the names of the skills available to you. just the names, one line." 'dogfood|dispatch|verify|brief|hydrate|remember' 18
cell SUBAGENT "dispatch a subagent to reply with exactly the word PONGWORKED and report what it said." 'PONGWORKED' 30
cell PERMS   "run a shell command to write the word OKWRITE into /tmp/permcheck.txt then read it back and show the contents." 'OKWRITE' 24

echo "===== FULL PANE: $CLIENT $* ====="
tmux capture-pane -t "$SESS" -p -S -800 2>/dev/null | grep -vE '^\s*$'
tmux kill-session -t "$SESS" 2>/dev/null
rm -rf "$WORK"
