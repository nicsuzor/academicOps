#!/bin/bash
# Universal Hook Router Wrapper
#
# Bootstraps the environment to ensure 'uv' and 'python' are available
# before delegating to the Python router.

# 1. Detect uv binary
if ! command -v uv &> /dev/null; then
    # Try common installation paths
    COMMON_PATHS=(
        "$HOME/.local/bin"
        "/usr/local/bin"
        "/opt/homebrew/bin"
        "/usr/bin"
    )
    for p in "${COMMON_PATHS[@]}"; do
        if [[ -x "$p/uv" ]]; then
            export PATH="$p:$PATH"
            break
        fi
    done
fi

# 2. Final check
if ! command -v uv &> /dev/null; then
    echo "CRITICAL: 'uv' not found on PATH and not in common locations." >&2
    exit 1
fi

# 3. Delegate to the Python router
# Use 'uv --directory' with PLUGIN_DIR to ensure
# correct environment resolution within the extension runtime.
HOOK_DIR="$(cd "$(dirname "$(dirname "$0")")" && pwd)"

exec uv --directory "$HOOK_DIR" run python "$HOOK_DIR/hooks/router.py" "$@"
