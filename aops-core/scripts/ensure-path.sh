#!/bin/bash
# ensure-path.sh — Ensure common CLI tools (uv, gh, etc.) are on PATH.
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

# Required binaries to find on PATH.
_AOPS_REQUIRED_BINS=(uv gh)

# Common binary directories — covers Homebrew (Apple Silicon + Intel),
# Linux standard, Debian containers, pip --user, Cargo installs.
_AOPS_COMMON_PATHS=(
    "$HOME/.local/bin"
    "$HOME/.cargo/bin"
    "/home/debian/.local/bin"
    "/usr/local/bin"
    "/opt/homebrew/bin"
    "/usr/bin"
)

# Collect unique directories to add (avoids duplicating PATH entries).
_AOPS_DIRS_TO_ADD=""
for _bin in "${_AOPS_REQUIRED_BINS[@]}"; do
    if ! command -v "$_bin" &> /dev/null; then
        for _p in "${_AOPS_COMMON_PATHS[@]}"; do
            if [[ -f "$_p/$_bin" && -x "$_p/$_bin" ]]; then
                # Only add if not already in PATH and not already queued
                case ":$PATH:$_AOPS_DIRS_TO_ADD:" in
                    *":$_p:"*) ;;
                    *) _AOPS_DIRS_TO_ADD="$_p:$_AOPS_DIRS_TO_ADD" ;;
                esac
                break
            fi
        done
    fi
done

if [[ -n "$_AOPS_DIRS_TO_ADD" ]]; then
    if [[ -n "$PATH" ]]; then
        export PATH="${_AOPS_DIRS_TO_ADD%:}:$PATH"
    else
        export PATH="${_AOPS_DIRS_TO_ADD%:}"
    fi
fi

unset _bin _p _AOPS_REQUIRED_BINS _AOPS_COMMON_PATHS _AOPS_DIRS_TO_ADD
