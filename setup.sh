#!/usr/bin/env bash
#
# TOMBSTONE (epic-267fe017): setup.sh is no longer the install entry point.
#
# The single authoritative local-install path is now:
#
#     make install-dev        # orchestrator (build + install via scripts/install.py)
#   or, equivalently, run the installer directly:
#     uv run python scripts/install.py
#
# This wrapper previously built extensions and then delegated to
# scripts/install.py, while `make install-dev` hand-rolled a *different* subset
# of the install (the "install split-brain"). Both now route through
# scripts/install.py so there is exactly one install code path.
#
# This stub is retained only to redirect anything that still invokes setup.sh.
# It forwards to the authoritative installer; it does not duplicate any logic.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "⚠️  setup.sh is deprecated (epic-267fe017)." >&2
echo "    Use 'make install-dev' or 'uv run python scripts/install.py'." >&2
echo "    Forwarding to scripts/install.py ..." >&2

if ! command -v uv &> /dev/null; then
    echo "Error: uv is required." >&2
    exit 1
fi

export AOPS="$SCRIPT_DIR"
exec uv run python "$SCRIPT_DIR/scripts/install.py" "$@"
