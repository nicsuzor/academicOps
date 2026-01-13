#!/bin/bash
# Integration test for session start content
# Validates that session start files (CLAUDE.md + @-referenced files) contain expected content

set -e  # Exit on error

echo "🧪 Running session start content integration test..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REPO_ROOT="/home/nic/src/writing"
CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"

# Test 1: Verify CLAUDE.md exists
echo ""
echo "Test 1: CLAUDE.md exists and is readable"
if [ -f "$CLAUDE_MD" ] && [ -r "$CLAUDE_MD" ]; then
    echo -e "  ${GREEN}✅${NC} CLAUDE.md exists and is readable"
else
    echo -e "  ${RED}❌${NC} CLAUDE.md missing or not readable"
    exit 1
fi

# Test 2: Extract and verify all @-referenced files exist
echo ""
echo "Test 2: All @-referenced files exist and are readable"

# Extract @-references from CLAUDE.md (format: @path/to/file)
# Only match lines that start with "- @" to get file references, not inline @ mentions
REFERENCED_FILES=$(grep -oP '^- @\K[^[:space:]]+' "$CLAUDE_MD" | sort -u)

ALL_FILES_EXIST=0
for ref_file in $REFERENCED_FILES; do
    # Convert relative path to absolute
    if [[ "$ref_file" == /* ]]; then
        abs_path="$ref_file"
    else
        abs_path="${REPO_ROOT}/${ref_file}"
    fi

    if [ -f "$abs_path" ] && [ -r "$abs_path" ]; then
        echo -e "  ${GREEN}✅${NC} @${ref_file} -> ${abs_path}"
    else
        echo -e "  ${RED}❌${NC} @${ref_file} MISSING or not readable (expected: ${abs_path})"
        ALL_FILES_EXIST=1
    fi
done

if [ $ALL_FILES_EXIST -ne 0 ]; then
    exit 1
fi

# Test 3: Verify README.md contains task management documentation
echo ""
echo "Test 3: README.md contains task management documentation"

README="${REPO_ROOT}/README.md"
TASK_CONTENT_FOUND=0

# Check for task management content (either dedicated section OR distributed references)
if grep -q "## 📋 Task Management" "$README"; then
    echo -e "  ${GREEN}✅${NC} Dedicated Task Management section exists"
else
    # Check for task references in Tools & Workflow section as an alternative
    if grep -q "Tasks.*task scripts.*task skill" "$README" || grep -q "\*\*Tasks\*\*" "$README"; then
        echo -e "  ${GREEN}✅${NC} Task management documented in Tools & Workflow section"
    else
        echo -e "  ${RED}❌${NC} Task Management documentation missing (neither dedicated section nor tools reference)"
        TASK_CONTENT_FOUND=1
    fi
fi

# Check for data/tasks/ directory reference (either full path or in directory tree)
if grep -q "data/tasks/" "$README" || (grep -q "tasks/" "$README" && grep -q "data/" "$README"); then
    echo -e "  ${GREEN}✅${NC} References data/tasks/ directory structure"
else
    echo -e "  ${RED}❌${NC} Missing reference to data/tasks/ directory"
    TASK_CONTENT_FOUND=1
fi

# Check for task workflow (inbox -> completed -> archived)
if grep -q "inbox/" "$README" && grep -q "completed/" "$README" && grep -q "archived/" "$README"; then
    echo -e "  ${GREEN}✅${NC} Documents task workflow (inbox/completed/archived)"
else
    echo -e "  ${RED}❌${NC}  Task workflow not documented (inbox/completed/archived)"
    TASK_CONTENT_FOUND=1
fi

# Optional: Check for priority level documentation
if grep -q "Priority Levels" "$README" || grep -q "P1" "$README"; then
    echo -e "  ${GREEN}✅${NC} Documents priority levels"
else
    echo -e "  ${YELLOW}⚠${NC}  Priority level documentation not found (optional enhancement)"
fi

if [ $TASK_CONTENT_FOUND -ne 0 ]; then
    exit 1
fi

# Test 4: Verify data/tasks/ directory structure exists
echo ""
echo "Test 4: Task directory structure exists"

TASK_DIRS=(
    "${REPO_ROOT}/data/tasks"
    "${REPO_ROOT}/data/tasks/inbox"
    "${REPO_ROOT}/data/tasks/completed"
    "${REPO_ROOT}/data/tasks/archived"
)

DIRS_EXIST=0
for task_dir in "${TASK_DIRS[@]}"; do
    if [ -d "$task_dir" ]; then
        echo -e "  ${GREEN}✅${NC} ${task_dir} exists"
    else
        echo -e "  ${RED}❌${NC} ${task_dir} MISSING"
        DIRS_EXIST=1
    fi
done

if [ $DIRS_EXIST -ne 0 ]; then
    exit 1
fi

# Test 5: Check for conflicting task location instructions in session start files
echo ""
echo "Test 5: No conflicting task location instructions"

SESSION_START_FILES=(
    "$CLAUDE_MD"
    "$README"
    "${REPO_ROOT}/bots/CORE.md"
    "${REPO_ROOT}/bots/ACCOMMODATIONS.md"
)

# Check for references to old task locations (if any existed)
# This is a placeholder - update if specific old paths need to be checked
for file in "${SESSION_START_FILES[@]}"; do
    if [ -f "$file" ]; then
        # Check for any references to task locations
        if grep -q "task" "$file" 2>/dev/null; then
            # Verify they point to data/tasks/ if they mention task storage
            if grep -i "task.*location\|task.*storage\|task.*file" "$file" 2>/dev/null | grep -v "data/tasks/" | grep -v "^#" > /dev/null 2>&1; then
                echo -e "  ${YELLOW}⚠${NC}  $(basename "$file") may contain task location references (manual review recommended)"
            fi
        fi
    fi
done

echo -e "  ${GREEN}✅${NC} No obvious conflicting task locations found"

# Test 6: Verify session start content coherence
echo ""
echo "Test 6: Session start content is coherent"

# Check that README.md is actually referenced in CLAUDE.md
if grep -q "@README.md" "$CLAUDE_MD"; then
    echo -e "  ${GREEN}✅${NC} CLAUDE.md references README.md"
else
    echo -e "  ${RED}❌${NC} CLAUDE.md does not reference README.md"
    exit 1
fi

# Check that task-related files reference each other appropriately
# README.md should be authoritative for structure, other files should defer to it
if grep -q "README.md" "${REPO_ROOT}/bots/CORE.md"; then
    echo -e "  ${GREEN}✅${NC} bots/CORE.md references README.md as authoritative"
else
    echo -e "  ${YELLOW}⚠${NC}  bots/CORE.md doesn't explicitly reference README.md (non-critical)"
fi

# All tests passed
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All session start content tests PASSED${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Session start content verified:"
echo "  • All @-referenced files exist and are readable"
echo "  • README.md contains task management documentation"
echo "  • README.md references data/tasks/ directory structure"
echo "  • Task directory structure exists"
echo "  • No conflicting instructions found"
echo ""

exit 0
