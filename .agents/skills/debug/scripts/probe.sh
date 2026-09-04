#!/bin/bash
# One-cell probe: boot a sandbox container on the given client, ask it one
# question, print the verdict verbatim, clean up.
#
#   probe.sh <claude|agy> "<prompt>" "<success-regex>" [client args...]
#
# Exits 0 when the success regex appears in the pane, 1 on timeout or on a
# recognised refusal.
#
# The sandbox runs on a private clone that carries ONLY COMMITTED WORK — it
# cannot see this checkout's working tree. Commit anything the probe depends on
# before running it.
#
# Reads GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL and any variable the server commands
# in your plugins interpolate (e.g. an MCP endpoint) from the calling
# environment — tmux does not inherit a fresh environment, so every one is
# written into the launch script rather than assumed.
set -u
CLIENT="${1:?usage: probe.sh <claude|agy> <prompt> <success-regex> [args...]}"
PROMPT="${2:?missing prompt}"
SUCCESS="${3:?missing success regex}"
shift 3

REPO="$(git rev-parse --show-toplevel)"
SESS="probe-${CLIENT}-$$"
WORK="$(mktemp -d)"
LAUNCH="$WORK/launch.sh"

{
  echo '#!/bin/bash'
  # Forward the whole environment rather than a guessed subset: a variable an
  # MCP server command interpolates is invisible here and fails silently there.
  export -p
  printf 'cd %q\n' "$REPO"
  printf 'exec sbx run --clone --name %q --kit lib/kits/%q --kit lib/kits/aops %q . %s\n' \
    "$SESS" "$CLIENT" "$CLIENT" "${*:+-- $*}"
} > "$LAUNCH"
chmod +x "$LAUNCH"

tmux kill-session -t "$SESS" 2>/dev/null
tmux new-session -d -s "$SESS" -x 220 -y 50 "$LAUNCH"

# Boot signal. For agy that is the plan name beside the account in the header
# block — until it renders, agy is still authenticating and shows
# "⚠ Verifying your account...", a startup race of a second or two that is not
# a failure and must not be scored as one.
for _ in $(seq 60); do
  sleep 2
  tmux capture-pane -t "$SESS" -p -S -50 2>/dev/null | grep -qE '@[^ ]+ \(.+\)|❯' && break
done
sleep 3

tmux send-keys -t "$SESS" -l "$PROMPT"
sleep 1
tmux send-keys -t "$SESS" Enter

RC=1
for _ in $(seq 60); do
  sleep 5
  PANE="$(tmux capture-pane -t "$SESS" -p -S -200 2>/dev/null)"
  if echo "$PANE" | grep -qE "$SUCCESS"; then RC=0; break; fi
  if echo "$PANE" | grep -qiE 'halting|not available|cannot be executed|no such tool'; then break; fi
done

echo "===== VERDICT: $CLIENT $* (rc=$RC) ====="
tmux capture-pane -t "$SESS" -p -S -200 2>/dev/null | grep -vE '^\s*$' | tail -30
tmux kill-session -t "$SESS" 2>/dev/null
sbx rm -f "$SESS" 2>/dev/null
rm -rf "$WORK"
exit $RC
