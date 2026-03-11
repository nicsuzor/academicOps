#!/usr/bin/env bash
#
# Wrapper script for AcademicOps installation.
# Builds extensions then delegates to scripts/install.py
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AOPS="$SCRIPT_DIR"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is required."
    exit 1
fi

# Check for ACA_DATA (required for build)
if [[ -z "${ACA_DATA:-}" ]]; then
    echo "Error: ACA_DATA environment variable must be set."
    exit 1
fi

# Build extensions first
echo "=== Building extensions ==="
uv run python "$SCRIPT_DIR/scripts/build.py"

# Then install/link
echo ""
echo "=== Installing ==="
uv run python "$SCRIPT_DIR/scripts/install.py" "$@"
