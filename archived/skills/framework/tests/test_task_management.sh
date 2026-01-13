#!/usr/bin/env bash
# Integration tests for task management scripts
# Tests task_view.py and task_archive.py with good and bad data
# Created: 2025-11-10
# Spec: bots/skills/framework/specs/task-management-rebuild.md

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

warn_test() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Setup test directory
TEST_DIR="/tmp/task_test_$$"
echo "Setting up test directory: $TEST_DIR"

mkdir -p "$TEST_DIR"/tasks/{inbox,archived}

# Create good task
cat > "$TEST_DIR/tasks/inbox/good-task.md" <<'EOF'
---
title: Good Task
type: task
status: inbox
priority: 1
---
# Good Task
## Context
This task has valid YAML.
EOF

# Create task with YAML error (invalid indentation)
cat > "$TEST_DIR/tasks/inbox/bad-yaml.md" <<'EOF'
---
title: Bad Task
tags:
  - test
  invalid indentation here
priority: 1
---
# Bad Task
EOF

# Create task with missing required field (no title)
cat > "$TEST_DIR/tasks/inbox/missing-field.md" <<'EOF'
---
type: task
priority: 1
---
# No Title Task
EOF

# Create 3 tasks for batch archive test
for i in 1 2 3; do
    cat > "$TEST_DIR/tasks/inbox/batch-$i.md" <<EOF
---
title: Batch Task $i
type: task
status: inbox
---
# Batch Task $i
EOF
done

echo ""
echo "=========================================="
echo "Running Integration Tests"
echo "=========================================="
echo ""

# Test 1: View shows valid tasks and reports errors clearly
echo "TEST 1: View shows valid tasks and reports YAML errors"
if python3 bots/skills/tasks/scripts/task_view.py --data-dir="$TEST_DIR" > "$TEST_DIR/view_output.txt" 2> "$TEST_DIR/errors.log"; then
    # Check if good tasks appear in output
    if grep -q "Good Task" "$TEST_DIR/view_output.txt" && \
       grep -q "Batch Task 1" "$TEST_DIR/view_output.txt" && \
       grep -q "Batch Task 2" "$TEST_DIR/view_output.txt" && \
       grep -q "Batch Task 3" "$TEST_DIR/view_output.txt"; then
        pass_test "View shows valid tasks"
    else
        fail_test "View doesn't show all valid tasks"
        cat "$TEST_DIR/view_output.txt"
    fi

    # Check if bad-yaml error is reported with filename
    if [ -s "$TEST_DIR/errors.log" ]; then
        if grep -q "bad-yaml.md" "$TEST_DIR/errors.log"; then
            pass_test "Error log includes problematic filename"
        else
            fail_test "Error log doesn't include filename"
            cat "$TEST_DIR/errors.log"
        fi
    else
        warn_test "No errors logged for bad YAML (may be silently failing)"
    fi
else
    fail_test "task_view.py crashed instead of handling errors gracefully"
fi

# Test 2: View shows filenames so user knows what to pass to archive
echo ""
echo "TEST 2: View output includes filenames for reference"
if grep -q "good-task.md" "$TEST_DIR/view_output.txt" && \
   grep -q "batch-1.md" "$TEST_DIR/view_output.txt"; then
    pass_test "View shows filenames in output"
else
    fail_test "View doesn't show filenames (user won't know what to pass to archive)"
    echo "View output:"
    cat "$TEST_DIR/view_output.txt"
fi

# Test 3: Archive accepts batch of filenames
echo ""
echo "TEST 3: Archive accepts multiple filenames in one command"
if python3 bots/skills/tasks/scripts/task_archive.py \
    --data-dir="$TEST_DIR" \
    batch-1.md batch-2.md batch-3.md > "$TEST_DIR/archive_output.txt" 2> "$TEST_DIR/archive_errors.log"; then
    pass_test "Archive command accepts multiple files"
else
    fail_test "Archive command doesn't support batch operations"
    cat "$TEST_DIR/archive_errors.log"
fi

# Test 4: Verify files were actually moved
echo ""
echo "TEST 4: Verify batch archive moved files correctly"
if [ -f "$TEST_DIR/tasks/archived/batch-1.md" ] && \
   [ -f "$TEST_DIR/tasks/archived/batch-2.md" ] && \
   [ -f "$TEST_DIR/tasks/archived/batch-3.md" ]; then
    pass_test "Batch tasks moved to archived/"
else
    fail_test "Not all batch tasks were archived"
    echo "Contents of archived/:"
    ls -la "$TEST_DIR/tasks/archived/" || echo "Directory doesn't exist"
fi

if [ ! -f "$TEST_DIR/tasks/inbox/batch-1.md" ] && \
   [ ! -f "$TEST_DIR/tasks/inbox/batch-2.md" ] && \
   [ ! -f "$TEST_DIR/tasks/inbox/batch-3.md" ]; then
    pass_test "Batch tasks removed from inbox/"
else
    fail_test "Batch tasks still in inbox/"
    echo "Contents of inbox/:"
    ls -la "$TEST_DIR/tasks/inbox/"
fi

# Test 5: Good task still in inbox (wasn't accidentally archived)
echo ""
echo "TEST 5: Verify unarchived tasks remain in inbox"
if [ -f "$TEST_DIR/tasks/inbox/good-task.md" ]; then
    pass_test "Good task still in inbox (not accidentally archived)"
else
    fail_test "Good task missing from inbox"
fi

# Test 6: Archive gives clear error if file doesn't exist
echo ""
echo "TEST 6: Archive error handling for nonexistent file"
if python3 bots/skills/tasks/scripts/task_archive.py \
    --data-dir="$TEST_DIR" \
    nonexistent.md > /dev/null 2> "$TEST_DIR/error-nonexistent.log"; then
    warn_test "Archive didn't fail for nonexistent file (should it?)"
else
    # Command failed, check error message
    if grep -q "nonexistent.md" "$TEST_DIR/error-nonexistent.log" && \
       grep -qi "not found\|does not exist" "$TEST_DIR/error-nonexistent.log"; then
        pass_test "Archive gives clear error for nonexistent file"
    else
        fail_test "Archive error message unclear for nonexistent file"
        echo "Error message:"
        cat "$TEST_DIR/error-nonexistent.log"
    fi
fi

# Test 7: Verify error messages include line numbers for YAML errors
echo ""
echo "TEST 7: YAML error messages include line numbers"
if [ -s "$TEST_DIR/errors.log" ]; then
    if grep -qi "line\|:\([0-9]\+\)" "$TEST_DIR/errors.log"; then
        pass_test "Error log includes line number information"
    else
        warn_test "Error log may not include line numbers"
        echo "Error log contents:"
        cat "$TEST_DIR/errors.log"
    fi
else
    warn_test "No error log generated (YAML errors may be silently ignored)"
fi

# Cleanup
echo ""
echo "=========================================="
echo "Cleaning up test directory"
echo "=========================================="
rm -rf "$TEST_DIR"

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
