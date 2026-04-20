#!/bin/bash
# Integration test for framework integrity
# Validates documentation consistency and framework structure

set -e  # Exit on error

echo "🧪 Running framework integrity integration test..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

BOTS_DIR="${AOPS:-$HOME/src/academicOps}"

# Test 1: Verify authoritative files exist
echo ""
echo "Test 1: Authoritative files exist"
REQUIRED_FILES=(
    "${BOTS_DIR}/AXIOMS.md"
    "${BOTS_DIR}/CORE.md"
    "${BOTS_DIR}/ACCOMMODATIONS.md"
    "${BOTS_DIR}/README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✅${NC} $file exists"
    else
        echo -e "  ${RED}❌${NC} $file MISSING"
        exit 1
    fi
done

# Test 2: Verify directory structure
echo ""
echo "Test 2: Directory structure"
REQUIRED_DIRS=(
    "${BOTS_DIR}/skills"
    "${BOTS_DIR}/hooks"
    "${BOTS_DIR}/commands"
    "${BOTS_DIR}/tests"
    "${BOTS_DIR}/agents"
    "${BOTS_DIR}/dist"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅${NC} $dir exists"
    else
        echo -e "  ${RED}❌${NC} $dir MISSING"
        exit 1
    fi
done

# Test 3: Check for bloat (file size limits)
echo ""
echo "Test 3: Bloat check (file size limits)"
BLOAT_DETECTED=0

# Check skill files (500 line limit)
while IFS= read -r -d '' file; do
    lines=$(wc -l < "$file")
    if [ "$lines" -gt 500 ]; then
        echo -e "  ${RED}❌${NC} $file exceeds 500 line limit ($lines lines)"
        BLOAT_DETECTED=1
    fi
done < <(find "${BOTS_DIR}/skills" -name "*.md" -type f -print0 2>/dev/null)

# Check doc files (300 line limit for chunks, if they exist)
if [ -d "${BOTS_DIR}/docs/chunks" ]; then
    while IFS= read -r -d '' file; do
        lines=$(wc -l < "$file")
        if [ "$lines" -gt 300 ]; then
            echo -e "  ${RED}❌${NC} $file exceeds 300 line limit ($lines lines)"
            BLOAT_DETECTED=1
        fi
    done < <(find "${BOTS_DIR}/docs/chunks" -name "*.md" -type f -print0 2>/dev/null)
fi

if [ $BLOAT_DETECTED -eq 0 ]; then
    echo -e "${GREEN}✅ No bloat detected${NC}"
else
    echo -e "${RED}❌ Bloat detected - files exceed size limits${NC}"
    exit 1
fi

# All tests passed
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All framework integrity tests PASSED${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

exit 0
