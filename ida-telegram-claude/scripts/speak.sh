#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

if [ "$#" -lt 2 ]; then
    echo "Error: text file argument and output ogg argument required" >&2
    exit 1
fi

exec python3 "$SCRIPT_DIR/speak-gemini.py" "$@"
