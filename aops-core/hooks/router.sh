#!/bin/bash
# Universal Hook Router Wrapper
#
# Two paths to the Python router:
#   1. Fast path — if a pre-built local .venv exists at $HOOK_DIR/.venv
#      (container builds preinstall it), exec its python directly. No uv,
#      no PyPI fetch on first invocation, no cold-cache failures.
#   2. Fallback — bootstrap uv on PATH and use `uv --directory $HOOK_DIR run`.
#      This is the dev / macOS path where the venv isn't pre-built.

HOOK_DIR="$(cd "$(dirname "$(dirname "$0")")" && pwd)"

# 1. Fast path: pre-built local venv.
HOOK_VENV_PYTHON="$HOOK_DIR/.venv/bin/python"
if [ -x "$HOOK_VENV_PYTHON" ]; then
    exec "$HOOK_VENV_PYTHON" "$HOOK_DIR/hooks/router.py" "$@"
fi

# 2. Fallback: bootstrap uv.
SCRIPT_DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

if ! command -v uv &> /dev/null; then
    echo "CRITICAL: 'uv' not found on PATH and no pre-built .venv at $HOOK_DIR/.venv." >&2
    exit 1
fi

# Set UV_CACHE_DIR to avoid Seatbelt permission errors outside the extension path.
# In Docker containers the plugin dir may be root-owned, so fall back to a
# user-specific temp dir. A shared /tmp/uv-cache causes permission errors when
# different UIDs share the same container image cache.
UV_CACHE_CANDIDATE="$HOOK_DIR/.uv-cache"
if mkdir -p "$UV_CACHE_CANDIDATE" 2>/dev/null && [ -w "$UV_CACHE_CANDIDATE" ]; then
    export UV_CACHE_DIR="$UV_CACHE_CANDIDATE"
else
    export UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache-$(id -u)"
fi

exec uv --directory "$HOOK_DIR" run python "$HOOK_DIR/hooks/router.py" "$@"
