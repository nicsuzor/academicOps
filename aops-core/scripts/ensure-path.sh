#!/bin/bash
# ensure-path.sh — Ensure uv/uvx and common user binaries are on PATH.
#
# Source this file; do not execute it directly.
# Works across macOS (Homebrew), Debian (pip --user), Docker, and cron.
#
# Usage:
#   source "$(dirname "$0")/ensure-path.sh"

# Ensure $USER is set — minimal environments (launchd, Claude Code plugin
# launcher) may omit it, which breaks ~/.env.system-paths paths like
# /opt/$USER/cache/uv.
export USER="${USER:-$(id -un)}"

# Source user's system-paths file if it exists (Homebrew shellenv, Cargo, etc.)
[[ -f "$HOME/.env.system-paths" ]] && source "$HOME/.env.system-paths"

# Probe common binary directories if uv is not already available.
if ! command -v uv &> /dev/null; then
    _AOPS_COMMON_PATHS=(
        "$HOME/.local/bin"
        "/home/debian/.local/bin"
        "/usr/local/bin"
        "/opt/homebrew/bin"
        "/usr/bin"
    )
    for _p in "${_AOPS_COMMON_PATHS[@]}"; do
        if [[ -x "$_p/uv" ]]; then
            export PATH="$_p:$PATH"
            break
        fi
    done
    unset _p _AOPS_COMMON_PATHS
fi
