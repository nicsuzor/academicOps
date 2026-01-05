#!/bin/bash
#
# Manual bootstrap script for non-Claude environments (like Gemini)
# Emulates the SessionStart hook behavior
#

set -euo pipefail

# Hardcoded paths for this environment (verified in session)
export AOPS="/home/nic/src/academicOps"
export ACA_DATA="/home/nic/writing/data"
export PYTHONPATH="${AOPS}:${PYTHONPATH:-}"

echo ">> Bootstrapping Agent Session..." >&2
echo ">> AOPS: $AOPS" >&2
echo ">> ACA_DATA: $ACA_DATA" >&2

# Path to the hook script
HOOK_SCRIPT="$AOPS/hooks/sessionstart_load_axioms.py"

if [ ! -f "$HOOK_SCRIPT" ]; then
    echo "FATAL: Hook script not found at $HOOK_SCRIPT" >&2
    exit 1
fi

# Run the hook and capture JSON output
OUTPUT=$(echo "{}" | python3 "$HOOK_SCRIPT")

# Extract additionalContext using python (since jq might not be available or reliable)
echo "$OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('hookSpecificOutput', {}).get('additionalContext', ''))
except Exception as e:
    print(f'Error parsing JSON: {e}', file=sys.stderr)
    sys.exit(1)
"

echo ">> Bootstrap Complete. Context dumped above." >&2
