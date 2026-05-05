#!/bin/bash
# Universal Hook Router Wrapper
#
# Bootstraps the environment to ensure 'uv' and 'python' are available
# before delegating to the Python router.

# 0. Vanilla-crew bypass: skip all framework hooks when AOPS_HOOKS_OFF=1.
# Set by polecat when launching crew containers in vanilla trial mode
# (POLECAT_VANILLA_CREW=1). Exit 0 with no stdout = continue normally.
if [ "$AOPS_HOOKS_OFF" = "1" ]; then
    exit 0
fi

# 1. Ensure uv/uvx are on PATH (shared with run-mcp.sh)
SCRIPT_DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

# 2. Final check
if ! command -v uv &> /dev/null; then
    echo "CRITICAL: 'uv' not found on PATH and not in common locations." >&2
    exit 1
fi

# 3. Delegate to the Python router
# Use 'uv --directory' with PLUGIN_DIR to ensure
# correct environment resolution within the extension runtime.
HOOK_DIR="$(cd "$(dirname "$(dirname "$0")")" && pwd)"

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
