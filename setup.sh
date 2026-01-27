#!/usr/bin/env bash
#
# Wrapper script for AcademicOps installation.
# Delegates to scripts/install.py
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AOPS="$SCRIPT_DIR"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required."
    exit 1
fi

# Pass all arguments to python script
python3 "$SCRIPT_DIR/scripts/install.py" "$@"
