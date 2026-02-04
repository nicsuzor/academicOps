#!/bin/bash
# Integration test for session knowledge extraction
# Tests end-to-end workflow: session log -> LLM analysis -> knowledge files

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
REPO_ROOT="/home/user/academicOps"
SCRIPT_PATH="$REPO_ROOT/bots/hooks/extract_session_knowledge.py"
TEST_DATA_DIR="/tmp/test_knowledge_extraction_$$"
TEST_SESSION_ID="test-extraction-session-$(date +%s)"
TEST_DATE="2025-11-09"

echo "========================================"
echo "Knowledge Extraction Integration Test"
echo "========================================"
echo ""

# Setup
echo "Setting up test environment..."
mkdir -p "$TEST_DATA_DIR"
mkdir -p "$TEST_DATA_DIR/sessions"
mkdir -p "$TEST_DATA_DIR/knowledge"

# Create mock session log with substantial content
cat > "$TEST_DATA_DIR/sessions/${TEST_DATE}-testabcd.jsonl" <<'EOF'
{"session_id":"test-extraction-session-123","timestamp":"2025-11-09T10:30:00Z","summary":"Extended session; used Read, Edit, Write, Bash; modified 5 file(s)","transcript_summary":{"user_messages":15,"assistant_messages":18,"tools_used":["Read","Edit","Write","Bash","Grep"],"files_modified":["/home/user/academicOps/hooks/session_logger.py","/home/user/academicOps/hooks/log_session_stop.py","/home/user/academicOps/tests/test_session_logging.py"],"errors":[]}}
EOF

echo "✓ Test session log created"

# Test 1: Script exists and is executable
echo ""
echo "Test 1: Checking script exists..."
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}✗ FAIL${NC}: Script not found at $SCRIPT_PATH"
    echo "This is expected on first run (test-first development)"
    rm -rf "$TEST_DATA_DIR"
    exit 1
fi
echo -e "${GREEN}✓ PASS${NC}: Script exists"

# Test 2: Script has correct dependencies
echo ""
echo "Test 2: Checking dependencies..."
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo -e "${YELLOW}⚠ WARNING${NC}: anthropic package not installed"
    echo "Run: uv add anthropic"
    rm -rf "$TEST_DATA_DIR"
    exit 1
fi
echo -e "${GREEN}✓ PASS${NC}: Dependencies available"

# Test 3: Script requires API key (when not in dry-run mode)
echo ""
echo "Test 3: Testing API key requirement..."
unset ANTHROPIC_API_KEY
if python3 "$SCRIPT_PATH" --session-log "$TEST_DATA_DIR/sessions/${TEST_DATE}-testabcd.jsonl" --output-dir "$TEST_DATA_DIR/knowledge" 2>/dev/null; then
    echo -e "${RED}✗ FAIL${NC}: Script should fail without API key"
    rm -rf "$TEST_DATA_DIR"
    exit 1
fi
echo -e "${GREEN}✓ PASS${NC}: Script correctly requires API key"

# Test 4: Dry run mode works
echo ""
echo "Test 4: Testing dry run mode..."
export ANTHROPIC_API_KEY="test-key-for-dry-run"
DRY_RUN_OUTPUT=$(python3 "$SCRIPT_PATH" --session-log "$TEST_DATA_DIR/sessions/${TEST_DATE}-testabcd.jsonl" --output-dir "$TEST_DATA_DIR/knowledge" --dry-run 2>&1)
if echo "$DRY_RUN_OUTPUT" | grep -q "DRY RUN"; then
    echo -e "${GREEN}✓ PASS${NC}: Dry run mode works"
else
    echo -e "${RED}✗ FAIL${NC}: Dry run mode not working"
    echo "Expected 'DRY RUN' in output but didn't find it"
    rm -rf "$TEST_DATA_DIR"
    exit 1
fi

# Test 5: Full extraction (requires real API key)
echo ""
echo "Test 5: Testing full extraction..."
if [ -z "${ANTHROPIC_API_KEY:-}" ] || [ "$ANTHROPIC_API_KEY" = "test-key-for-dry-run" ]; then
    echo -e "${YELLOW}⚠ SKIP${NC}: No real API key available (set ANTHROPIC_API_KEY to test)"
else
    echo "Running extraction with real API..."

    python3 "$SCRIPT_PATH" \
        --session-log "$TEST_DATA_DIR/sessions/${TEST_DATE}-testabcd.jsonl" \
        --output-dir "$TEST_DATA_DIR/knowledge" \
        --verbose

    # Check knowledge files were created
    if [ ! -f "$TEST_DATA_DIR/knowledge/index.jsonl" ]; then
        echo -e "${RED}✗ FAIL${NC}: index.jsonl not created"
        rm -rf "$TEST_DATA_DIR"
        exit 1
    fi

    # Check at least one category file was created
    KNOWLEDGE_FILES=$(find "$TEST_DATA_DIR/knowledge" -type f -name "*.md" | wc -l)
    if [ "$KNOWLEDGE_FILES" -eq 0 ]; then
        echo -e "${YELLOW}⚠ WARNING${NC}: No knowledge files created (session may not have extractable knowledge)"
    else
        echo -e "${GREEN}✓ PASS${NC}: Created $KNOWLEDGE_FILES knowledge file(s)"

        # Verify markdown format
        FIRST_MD=$(find "$TEST_DATA_DIR/knowledge" -type f -name "*.md" | head -1)
        if [ -n "$FIRST_MD" ]; then
            echo "Sample knowledge file:"
            head -20 "$FIRST_MD"

            # Check required fields
            if ! grep -q "^# " "$FIRST_MD"; then
                echo -e "${RED}✗ FAIL${NC}: Missing title in markdown"
                rm -rf "$TEST_DATA_DIR"
                exit 1
            fi

            if ! grep -q "^\*\*Date\*\*:" "$FIRST_MD"; then
                echo -e "${RED}✗ FAIL${NC}: Missing date in markdown"
                rm -rf "$TEST_DATA_DIR"
                exit 1
            fi

            if ! grep -q "^\*\*Session\*\*:" "$FIRST_MD"; then
                echo -e "${RED}✗ FAIL${NC}: Missing session provenance in markdown"
                rm -rf "$TEST_DATA_DIR"
                exit 1
            fi
        fi
    fi

    # Verify index format
    if ! python3 -c "import json; [json.loads(line) for line in open('$TEST_DATA_DIR/knowledge/index.jsonl')]" 2>/dev/null; then
        echo -e "${RED}✗ FAIL${NC}: index.jsonl is not valid JSONL"
        rm -rf "$TEST_DATA_DIR"
        exit 1
    fi

    echo -e "${GREEN}✓ PASS${NC}: Full extraction completed successfully"
fi

# Test 6: Batch processing multiple sessions
echo ""
echo "Test 6: Testing batch processing..."

# Create second session log
cat > "$TEST_DATA_DIR/sessions/2025-11-08-testxyz.jsonl" <<'EOF'
{"session_id":"test-batch-session-456","timestamp":"2025-11-08T14:20:00Z","summary":"Short session; used Grep, Read; modified 1 file(s)","transcript_summary":{"user_messages":3,"assistant_messages":4,"tools_used":["Grep","Read"],"files_modified":["/home/user/academicOps/README.md"],"errors":[]}}
EOF

if [ -n "${ANTHROPIC_API_KEY:-}" ] && [ "$ANTHROPIC_API_KEY" != "test-key-for-dry-run" ]; then
    python3 "$SCRIPT_PATH" \
        --sessions-dir "$TEST_DATA_DIR/sessions" \
        --output-dir "$TEST_DATA_DIR/knowledge" \
        --verbose

    echo -e "${GREEN}✓ PASS${NC}: Batch processing works"
else
    echo -e "${YELLOW}⚠ SKIP${NC}: No real API key available"
fi

# Cleanup
echo ""
echo "Cleaning up test environment..."
rm -rf "$TEST_DATA_DIR"
echo "✓ Cleanup complete"

echo ""
echo "========================================"
echo -e "${GREEN}All tests passed!${NC}"
echo "========================================"
exit 0
