#!/usr/bin/env bash
# Thin tmux control wrapper around `polecat crew`, wired to the dev-only
# `aops-crew:dev` image + `aops-dev` polecat.yaml profile (see
# scripts/gen_dev_polecat_config.py and tests/harness/README.md §
# "Dev-loop"). Wraps the existing tmux interactive-control recipe
# (tests/harness/README.md) — it is not a new framework.
#
# Usage:
#   scripts/dev-crew.sh start <claude|antigravity> [name]
#   scripts/dev-crew.sh send <name> "<text>"
#   scripts/dev-crew.sh watch <name> [--once]
#   scripts/dev-crew.sh logs <name>
#   scripts/dev-crew.sh stop <name>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_CONFIG="$HOME/.polecat-dev/polecat.yaml"
PROJECT_SLUG="aops-dev"

# tmux's default shell is /bin/sh, so aliases like `polecat`/`pc` don't
# resolve — always invoke the CLI by full path (tests/harness/README.md
# gotcha). Runs THIS worktree's polecat/cli.py (unmodified by this dev loop).
polecat_cmd() {
    echo "AOPS_POLECAT_CONFIG=$DEV_CONFIG uv run --project $REPO_ROOT $REPO_ROOT/polecat/cli.py $*"
}

cmd_start() {
    local client="${1:?usage: dev-crew.sh start <claude|antigravity> [name]}"
    local name="${2:-dev-$RANDOM}"

    echo "Regenerating dev polecat.yaml..." >&2
    mkdir -p "$(dirname "$DEV_CONFIG")"
    uv run --project "$REPO_ROOT" "$REPO_ROOT/scripts/gen_dev_polecat_config.py" --out "$DEV_CONFIG" >&2

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
    # Mirrors polecat/cli.py's _get_sessions_base() fallback chain
    # ($AOPS_SESSIONS, else $POLECAT_HOME/sessions, else ~/.polecat/sessions).
    local sessions_base="${AOPS_SESSIONS:-${POLECAT_HOME:-$HOME/.polecat}/sessions}"
    local session_dir="$sessions_base/crew/$name/$PROJECT_SLUG"
    if [ ! -d "$session_dir" ]; then
        echo "No session dir found at $session_dir yet (session may still be starting, or ended without a clean /exit)." >&2
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
