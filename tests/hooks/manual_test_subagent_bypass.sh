#!/bin/bash
# Manual test to verify subagent bypass in hydration gate
# This simulates a subagent session attempting to use tools while hydration is pending

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_PATH="$SCRIPT_DIR/../../hooks/hydration_gate.py"
AOPS_CORE_DIR="$SCRIPT_DIR/../.."

# Add aops-core to PYTHONPATH so lib module can be found
export PYTHONPATH="$AOPS_CORE_DIR:$PYTHONPATH"

echo "=== Manual Test: Subagent Bypass in Hydration Gate ==="
echo ""

# Test 1: Subagent session should bypass (exit 0)
echo "Test 1: Subagent session with CLAUDE_AGENT_TYPE set"
echo "Expected: Exit code 0 (bypass), no warning/block message"

# Create mock input with hydration pending scenario
INPUT_JSON='{"tool_name":"Read","tool_input":{"file_path":"/test/file.txt"},"session_id":"test-session"}'

# Set CLAUDE_AGENT_TYPE to simulate subagent
export CLAUDE_AGENT_TYPE="worker"

# Run the hook
EXIT_CODE=0
OUTPUT=$(echo "$INPUT_JSON" | python3 "$HOOK_PATH" 2>&1) || EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Output: $OUTPUT"

if [ $EXIT_CODE -eq 0 ] && [ -z "$(echo "$OUTPUT" | grep 'HYDRATION GATE')" ]; then
    echo "✓ PASS: Subagent bypassed the gate"
else
    echo "✗ FAIL: Subagent was blocked or warned"
    exit 1
fi

echo ""

# Test 2: Non-subagent session in warn mode should warn (but still exit 0)
echo "Test 2: Non-subagent session without CLAUDE_AGENT_TYPE"
echo "Expected: Exit code 0 (warn mode), warning message present"

# Unset CLAUDE_AGENT_TYPE
unset CLAUDE_AGENT_TYPE

# Set warn mode
export HYDRATION_GATE_MODE="warn"

# Create session state file to simulate hydration pending
SESSION_STATE_DIR="/tmp/test-claude-sessions"
mkdir -p "$SESSION_STATE_DIR"
echo '{"hydration_pending": "test"}' > "$SESSION_STATE_DIR/test-session.json"

# Mock the session state path
export ACA_DATA="/tmp/test-aca-data"
mkdir -p "$ACA_DATA/sessions"
ln -sf "$SESSION_STATE_DIR/test-session.json" "$ACA_DATA/sessions/test-session.json" 2>/dev/null || true

EXIT_CODE=0
OUTPUT=$(echo "$INPUT_JSON" | python3 "$HOOK_PATH" 2>&1) || EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
if echo "$OUTPUT" | grep -q "HYDRATION GATE"; then
    echo "✓ PASS: Warning message shown for non-subagent"
else
    echo "✗ FAIL: No warning message for non-subagent"
    exit 1
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ PASS: Exit code 0 in warn mode"
else
    echo "✗ FAIL: Exit code $EXIT_CODE (expected 0 in warn mode)"
    exit 1
fi

echo ""

# Clean up
rm -rf "$SESSION_STATE_DIR"
rm -rf "$ACA_DATA"

echo "=== All Tests Passed ==="
echo ""
echo "Summary:"
echo "✓ Subagents bypass the hydration gate when CLAUDE_AGENT_TYPE is set"
echo "✓ Non-subagents trigger warnings when hydration is pending"
echo ""
echo "Conclusion: The hydration gate correctly allows subagents to"
echo "inherit context from their parent without blocking."
