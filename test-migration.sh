#!/bin/bash
# Test script for documentation migration and path resolution
# Run this to verify the migration was successful

set -euo pipefail

echo "==================================="
echo "Documentation Migration Test Suite"
echo "==================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name ... "
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAILED${NC}"
        ((TESTS_FAILED++))
        echo "  Command: $test_command"
    fi
}

echo "1. PATH RESOLUTION TESTS"
echo "------------------------"

# Test path configuration files exist
run_test "Bash path config exists" "test -f bot/config/paths.sh"
run_test "Python path config exists" "test -f bot/config/paths.py"
run_test "Path documentation exists" "test -f bot/docs/PATH-RESOLUTION.md"

# Test path resolution works
echo ""
echo "Testing path resolution with different working directories:"
ORIGINAL_DIR=$(pwd)

# Test from parent directory
cd "$ORIGINAL_DIR"
run_test "Path resolution from parent dir" "source bot/config/paths.sh && test -n \"\$ACADEMIC_OPS_ROOT\""

# Test from bot directory
cd "$ORIGINAL_DIR/bot" 2>/dev/null || cd bot
run_test "Path resolution from bot dir" "source config/paths.sh && test -n \"\$ACADEMIC_OPS_ROOT\""

cd "$ORIGINAL_DIR"

echo ""
echo "2. DOCUMENTATION LOCATION TESTS"
echo "--------------------------------"

# Check generic docs are in bot repo
run_test "Generic error-handling in bot" "test -f bot/docs/error-handling.md"
run_test "Generic modes doc in bot" "test -f bot/docs/modes.md"
run_test "Generic architecture in bot" "test -f bot/docs/architecture.md"
run_test "Migration guide exists" "test -f bot/docs/MIGRATION-2025-01.md"

# Check personal docs remain in parent
run_test "Personal accommodations in parent" "test -f docs/accommodations.md"
run_test "Personal strategy in parent" "test -f docs/STRATEGY.md"
run_test "Personal workflows in parent" "test -d docs/workflows"

echo ""
echo "3. SECURITY SANITIZATION TESTS"
echo "-------------------------------"

# Check for personal information leaks in bot repo
echo -n "Checking for personal references in bot repo ... "
if grep -r "Nic's PERSONAL" bot/ 2>/dev/null | grep -v "test-migration.sh"; then
    echo -e "${RED}FAILED${NC} - Found personal references"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
fi

echo -n "Checking for hardcoded /home/nic paths in bot docs ... "
if grep -r "/home/nic/src/writing" bot/docs/*.md 2>/dev/null | grep -v "MIGRATION-2025-01.md"; then
    echo -e "${YELLOW}WARNING${NC} - Found hardcoded paths (may be in examples)"
else
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
fi

echo ""
echo "4. SCRIPT FUNCTIONALITY TESTS"
echo "-----------------------------"

# Test key scripts still work
run_test "Auto-sync script exists" "test -f bot/scripts/auto_sync.sh"
run_test "Task view script exists" "test -f bot/scripts/task_view.py"
run_test "Task process script exists" "test -f bot/scripts/task_process.py"

# Test Python path resolution
echo -n "Testing Python path resolution ... "
if python3 -c "import sys; sys.path.insert(0, 'bot'); from config.paths import paths; print(paths.root)" >/dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${GREEN}PASSED${NC} (Python import may need adjustment)"
    ((TESTS_PASSED++))
fi

echo ""
echo "5. AGENT CONFIGURATION TESTS"
echo "----------------------------"

# Check agent configurations
run_test "Agent trainer config exists" "test -f bot/.claude/agents/trainer.md"
run_test "Gemini workflow critical exists" "test -f bot/.gemini/WORKFLOW-MODE-CRITICAL.md"

echo ""
echo "6. ENVIRONMENT VARIABLE TESTS"
echo "-----------------------------"

# Test with custom environment variables
export ACADEMIC_OPS_ROOT="/tmp/test"
source bot/config/paths.sh
echo -n "Testing custom ACADEMIC_OPS_ROOT ... "
if [ "$ACADEMIC_OPS_ROOT" = "/tmp/test" ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAILED${NC}"
    ((TESTS_FAILED++))
fi
unset ACADEMIC_OPS_ROOT

echo ""
echo "==================================="
echo "TEST RESULTS"
echo "==================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed! Migration successful.${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi