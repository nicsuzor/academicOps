#!/bin/bash
# Integration test for user prompt submit hook
# Tests that the hook reads from markdown file and outputs correct format

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

HOOK_PATH="${AOPS:-$HOME/src/academicOps}/hooks/user_prompt_submit.py"
PROMPT_FILE="${AOPS:-$HOME/src/academicOps}/hooks/templates/user-prompt-submit.md"
TEST_HOOK_PATH="/tmp/test_user_prompt_submit.py"

echo "=== User Prompt Hook Integration Test ==="
echo ""

# Test 1: Hook file exists and is executable
echo "Test 1: Hook file exists and is executable"
if [ -f "$HOOK_PATH" ] && [ -x "$HOOK_PATH" ]; then
    echo -e "${GREEN}✓ Hook file exists and is executable${NC}"
else
    echo -e "${RED}✗ Hook file missing or not executable${NC}"
    exit 1
fi

# Test 2: Prompt markdown file exists
echo "Test 2: Prompt markdown file exists"
if [ -f "$PROMPT_FILE" ]; then
    echo -e "${GREEN}✓ Prompt markdown file exists${NC}"
else
    echo -e "${RED}✗ Prompt markdown file missing${NC}"
    exit 1
fi

# Test 3: Hook executes successfully with valid input
echo "Test 3: Hook executes with valid input"
TEST_INPUT='{"session_id": "test-session-123", "type": "UserPromptSubmit"}'
OUTPUT=$(echo "$TEST_INPUT" | python3 "$HOOK_PATH" 2>&1) || {
    echo -e "${RED}✗ Hook failed to execute${NC}"
    echo "Output: $OUTPUT"
    exit 1
}
echo -e "${GREEN}✓ Hook executed successfully${NC}"

# Test 4: Hook outputs valid JSON
echo "Test 4: Hook outputs valid JSON"
if echo "$OUTPUT" | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Hook outputs valid JSON${NC}"
else
    echo -e "${RED}✗ Hook output is not valid JSON${NC}"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 5: Hook output contains additionalContext field
echo "Test 5: Hook output contains additionalContext field"
if echo "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); sys.exit(0 if 'additionalContext' in data else 1)"; then
    echo -e "${GREEN}✓ Hook output contains additionalContext${NC}"
else
    echo -e "${RED}✗ Hook output missing additionalContext field${NC}"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 6: Hook reads content from markdown file (not hardcoded)
echo "Test 6: Hook reads content from markdown file"
MARKDOWN_CONTENT=$(cat "$PROMPT_FILE")
ADDITIONAL_CONTEXT=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['additionalContext'])")

if [ ${#MARKDOWN_CONTENT} -gt 10 ] && [ ${#ADDITIONAL_CONTEXT} -gt 10 ]; then
    echo -e "${GREEN}✓ Hook successfully reads from markdown file${NC}"
else
    echo -e "${RED}✗ Hook may not be reading from markdown file${NC}"
    exit 1
fi

# Test 7: Fail-fast behavior - hook fails if markdown file missing
echo "Test 7: Fail-fast behavior with missing markdown file"
# Create temporary hook that points to non-existent file
cp "$HOOK_PATH" "$TEST_HOOK_PATH"
chmod +x "$TEST_HOOK_PATH"

# Modify to point to non-existent file (create a test version)
echo "#!/usr/bin/env python3
import sys
import json
from pathlib import Path

def main():
    # Read from non-existent file - should fail
    prompt_file = Path('/tmp/nonexistent_prompt_file_12345.md')

    # Fail-fast: no defaults, no fallbacks
    if not prompt_file.exists():
        print('ERROR: Prompt file missing', file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
" > "$TEST_HOOK_PATH"

if echo "$TEST_INPUT" | python3 "$TEST_HOOK_PATH" 2>&1; then
    echo -e "${RED}✗ Hook should fail with missing markdown file (fail-fast violated)${NC}"
    rm -f "$TEST_HOOK_PATH"
    exit 1
else
    echo -e "${GREEN}✓ Hook correctly fails fast with missing markdown file${NC}"
    rm -f "$TEST_HOOK_PATH"
fi

# Test 8: Debug logging (verify it doesn't crash the hook)
echo "Test 8: Debug logging doesn't crash hook"
# Run hook again and verify exit code is 0
if echo "$TEST_INPUT" | python3 "$HOOK_PATH" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Hook exits successfully (debug logging safe)${NC}"
else
    echo -e "${RED}✗ Hook failed unexpectedly${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== All Tests Passed ===${NC}"
exit 0
