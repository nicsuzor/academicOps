#!/usr/bin/env bash
# Thin tmux control wrapper around `polecat crew`, wired to the dev-only
# `aops-crew:dev` image via tests/harness/dev-polecat.yaml (see
# tests/harness/README.md § "Dev-loop"). Wraps the existing tmux
# interactive-control recipe (tests/harness/README.md) — it is not a new
# framework, and it does not touch $AOPS_SESSIONS/polecat.yaml or :latest.
#
# Unlike the pre-restructuring version of this script, there is no live
# bind-mount and no config generator: edit source, `make build-dev &&
# make build-docker-dev`, then `start` again to pick up the change.
#
# Usage:
#   scripts/dev-crew.sh start <claude|antigravity> [name]
#   scripts/dev-crew.sh send <name> "<text>"
#   scripts/dev-crew.sh watch <name> [--once]
#   scripts/dev-crew.sh logs <name>
#   scripts/dev-crew.sh stop <name>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_CONFIG="$REPO_ROOT/tests/harness/dev-polecat.yaml"
PROJECT_SLUG="aops-dev"

# tmux's default shell is /bin/sh, so aliases like `polecat`/`pc` don't
# resolve — always invoke the CLI by full path (tests/harness/README.md
# gotcha). Runs THIS worktree's aops/polecat/cli.py.
polecat_cmd() {
    echo "AOPS_POLECAT_CONFIG=$DEV_CONFIG uv run --project $REPO_ROOT $REPO_ROOT/aops/polecat/cli.py $*"
}

cmd_start() {
    local client="${1:?usage: dev-crew.sh start <claude|antigravity> [name]}"
    local name="${2:-dev-$RANDOM}"

    local launch
    launch="$(polecat_cmd crew --model "$client" --name "$name" "$PROJECT_SLUG")"
    tmux new-session -d -s "$name" -x 220 -y 50 "$launch"
    echo "$name"
}

cmd_send() {
    local name="${1:?usage: dev-crew.sh send <name> \"<text>\"}"
    local text="${2:?usage: dev-crew.sh send <name> \"<text>\"}"
    tmux send-keys -t "$name" -l "$text"
    tmux send-keys -t "$name" Enter
}

cmd_watch() {
    local name="${1:?usage: dev-crew.sh watch <name> [--once]}"
    local once="${2:-}"
    if [ "$once" = "--once" ]; then
        tmux capture-pane -t "$name" -p -S -2000
    else
        tmux attach -t "$name" -r
    fi
}

cmd_logs() {
    local name="${1:?usage: dev-crew.sh logs <name>}"
    # Mirrors aops-jr/polecat/cli.py's session dir resolution: $AOPS_SESSIONS
    # (else $POLECAT_HOME/sessions, else ~/.polecat-dev/sessions), then
    # logs/<YYYYMMDD>/<name>/<project>. Glob the date since we don't know
    # which day the session started on; take the most recent match.
    local sessions_base="${AOPS_SESSIONS:-${POLECAT_HOME:-$HOME/.polecat-dev}/sessions}"
    local session_dir
    session_dir="$(ls -d "$sessions_base"/logs/*/"$name"/"$PROJECT_SLUG" 2>/dev/null | sort | tail -1)"
    if [ -z "$session_dir" ] || [ ! -d "$session_dir" ]; then
        echo "No session dir found under $sessions_base/logs/*/$name/$PROJECT_SLUG yet (session may still be starting, or ended without a clean /exit)." >&2
        exit 1
    fi
    echo "Session dir: $session_dir" >&2
    for f in "$session_dir"/*-hooks.jsonl; do
        [ -e "$f" ] || continue
        echo "--- $f ---"
        tail -n 100 "$f"
    done
    for f in "$session_dir"/session-*.json; do
        [ -e "$f" ] || continue
        echo "--- transcript: $f ---"
    done
}

cmd_stop() {
    local name="${1:?usage: dev-crew.sh stop <name>}"
    tmux send-keys -t "$name" -l "/exit"
    tmux send-keys -t "$name" Enter
    sleep 2
    tmux kill-session -t "$name" 2>/dev/null || true
}

case "${1:-}" in
    start) shift; cmd_start "$@" ;;
    send)  shift; cmd_send "$@" ;;
    watch) shift; cmd_watch "$@" ;;
    logs)  shift; cmd_logs "$@" ;;
    stop)  shift; cmd_stop "$@" ;;
    *)
        echo "usage: $0 {start|send|watch|logs|stop} ..." >&2
        exit 1
        ;;
esac
