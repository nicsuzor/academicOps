#!/bin/bash
#
# Manual test script to simulate remote automation environment
#
# This script tests that the framework can bootstrap itself in a clean
# environment where only CLAUDE_PROJECT_DIR is set (simulating CI, remote VM,
# or Claude Code Web scenarios).
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Remote Automation Test ==="
echo "Testing framework bootstrap in clean environment"
echo "Repo: $REPO_ROOT"
echo

# Test 1: Clean environment with only CLAUDE_PROJECT_DIR
echo "Test 1: Session environment setup with CLAUDE_PROJECT_DIR only"
echo "---------------------------------------------------------------"

# Unset AOPS to simulate clean environment
unset AOPS || true
unset ACA_DATA || true

# Set only CLAUDE_PROJECT_DIR (always provided by Claude Code)
export CLAUDE_PROJECT_DIR="$REPO_ROOT"

echo "Environment before hook:"
echo "  AOPS: ${AOPS:-<not set>}"
echo "  CLAUDE_PROJECT_DIR: $CLAUDE_PROJECT_DIR"
echo

# Run session_env_setup.sh hook
echo "Running session_env_setup.sh..."
output=$(bash "$REPO_ROOT/hooks/session_env_setup.sh" 2>&1)
exit_code=$?

echo "Exit code: $exit_code"
echo "Output:"
echo "$output"
echo

if [ $exit_code -ne 0 ]; then
    echo "❌ FAIL: Hook exited with non-zero code"
    exit 1
fi

if ! echo "$output" | grep -q '{"continue": true}'; then
    echo "❌ FAIL: Hook did not output success JSON"
    exit 1
fi

if ! echo "$output" | grep -q "Derived AOPS from CLAUDE_PROJECT_DIR"; then
    echo "❌ FAIL: Hook did not derive AOPS from CLAUDE_PROJECT_DIR"
    exit 1
fi

echo "✓ PASS: Hook successfully derived AOPS"
echo

# Test 2: Verify settings-self.json uses CLAUDE_PROJECT_DIR
echo "Test 2: Verify settings-self.json uses CLAUDE_PROJECT_DIR"
echo "-----------------------------------------------------------"

settings_file="$REPO_ROOT/config/claude/settings-self.json"

if [ ! -f "$settings_file" ]; then
    echo "❌ FAIL: settings-self.json not found"
    exit 1
fi

if ! grep -q '\$CLAUDE_PROJECT_DIR' "$settings_file"; then
    echo "❌ FAIL: settings-self.json does not use CLAUDE_PROJECT_DIR"
    exit 1
fi

if grep -v '^\s*"\$comment"' "$settings_file" | grep -q '\$AOPS'; then
    echo "❌ FAIL: settings-self.json uses AOPS (should use CLAUDE_PROJECT_DIR)"
    exit 1
fi

echo "✓ PASS: settings-self.json correctly uses CLAUDE_PROJECT_DIR"
echo

# Test 3: Verify repo-local .claude/settings.json links to settings-self.json
echo "Test 3: Verify repo-local .claude/ uses settings-self.json"
echo "------------------------------------------------------------"

claude_settings="$REPO_ROOT/.claude/settings.json"

if [ ! -L "$claude_settings" ]; then
    echo "❌ FAIL: .claude/settings.json is not a symlink"
    exit 1
fi

target=$(readlink "$claude_settings")
if [[ ! "$target" =~ settings-self\.json$ ]]; then
    echo "❌ FAIL: .claude/settings.json does not link to settings-self.json (links to: $target)"
    exit 1
fi

echo "✓ PASS: .claude/settings.json correctly links to settings-self.json"
echo

# Test 4: Verify sync_web_bundle.py --self uses settings-self.json
echo "Test 4: Verify sync_web_bundle.py --self uses settings-self.json"
echo "-----------------------------------------------------------------"

sync_output=$(python3 "$REPO_ROOT/scripts/sync_web_bundle.py" --self --dry-run 2>&1)

if ! echo "$sync_output" | grep -q "settings.json -> ../config/claude/settings-self.json"; then
    echo "❌ FAIL: sync_web_bundle.py --self does not use settings-self.json"
    echo "Output:"
    echo "$sync_output"
    exit 1
fi

echo "✓ PASS: sync_web_bundle.py --self correctly uses settings-self.json"
echo

# Test 5: Test with CLAUDE_ENV_FILE (session persistence)
echo "Test 5: Test CLAUDE_ENV_FILE session persistence"
echo "--------------------------------------------------"

temp_env=$(mktemp)
export CLAUDE_ENV_FILE="$temp_env"

# Clear AOPS again for this test
unset AOPS || true

echo "Running hook with CLAUDE_ENV_FILE=$CLAUDE_ENV_FILE..."
bash "$REPO_ROOT/hooks/session_env_setup.sh" > /dev/null 2>&1

if [ ! -f "$CLAUDE_ENV_FILE" ]; then
    echo "❌ FAIL: CLAUDE_ENV_FILE was not created"
    rm -f "$temp_env"
    exit 1
fi

if ! grep -q "export AOPS=" "$CLAUDE_ENV_FILE"; then
    echo "❌ FAIL: AOPS not written to CLAUDE_ENV_FILE"
    cat "$CLAUDE_ENV_FILE"
    rm -f "$temp_env"
    exit 1
fi

if ! grep -q "export PYTHONPATH=" "$CLAUDE_ENV_FILE"; then
    echo "❌ FAIL: PYTHONPATH not written to CLAUDE_ENV_FILE"
    cat "$CLAUDE_ENV_FILE"
    rm -f "$temp_env"
    exit 1
fi

echo "✓ PASS: Environment variables correctly persisted to CLAUDE_ENV_FILE"
echo "Content:"
cat "$CLAUDE_ENV_FILE"
rm -f "$temp_env"
echo

# All tests passed
echo "========================================="
echo "✅ All tests PASSED"
echo "========================================="
echo
echo "Remote automation setup is working correctly!"
echo "The framework can bootstrap itself using only CLAUDE_PROJECT_DIR"
echo "without requiring AOPS to be pre-configured."
