#!/bin/bash
# Integration test for feature-dev skill
# Validates the complete feature development workflow

set -e  # Exit on error

echo "🧪 Running feature-dev skill integration test..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect base directory dynamically
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTS_DIR="$(cd "${SCRIPT_PATH}/../../.." && pwd)"
TEST_DIR="/tmp/feature-dev-test-$$"
SKILL_DIR="${BOTS_DIR}/skills/feature-dev"

# Setup test environment
echo ""
echo "Setup: Creating test environment"
mkdir -p "${TEST_DIR}"

# Test 1: Skill file exists and is well-formed
echo ""
echo "Test 1: Skill file structure"
if [ ! -f "${SKILL_DIR}/SKILL.md" ]; then
    echo -e "${RED}❌ SKILL.md not found${NC}"
    exit 1
fi

# Check for required sections
REQUIRED_SECTIONS=(
    "# Feature Development Skill"
    "## Workflow"
    "### Phase 1: User Story Capture"
    "### Phase 4: Test-First Design"
    "## Progress Tracking"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
    if grep -q "$section" "${SKILL_DIR}/SKILL.md"; then
        echo -e "  ${GREEN}✅${NC} Section found: $section"
    else
        echo -e "  ${RED}❌${NC} Section MISSING: $section"
        exit 1
    fi
done

# Test 2: Verify required directories
echo ""
echo "Test 2: Directory structure"
REQUIRED_DIRS=(
    "${SKILL_DIR}/templates"
    "${SKILL_DIR}/tests"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅${NC} $dir exists"
    else
        echo -e "  ${RED}❌${NC} $dir MISSING"
        exit 1
    fi
done

# Test 3: Template files exist
echo ""
echo "Test 3: Template files"
REQUIRED_TEMPLATES=(
    "${SKILL_DIR}/templates/user-story.md"
    "${SKILL_DIR}/templates/experiment-plan.md"
    "${SKILL_DIR}/templates/test-spec.md"
    "${SKILL_DIR}/templates/dev-plan.md"
)

for template in "${REQUIRED_TEMPLATES[@]}"; do
    if [ -f "$template" ]; then
        echo -e "  ${GREEN}✅${NC} $(basename $template) exists"
    else
        echo -e "  ${RED}❌${NC} $(basename $template) MISSING"
        exit 1
    fi
done

# Test 4: Skill follows size limits (500 lines)
echo ""
echo "Test 4: Bloat check for skill file"
lines=$(wc -l < "${SKILL_DIR}/SKILL.md")
if [ "$lines" -gt 500 ]; then
    echo -e "${RED}❌ SKILL.md exceeds 500 line limit ($lines lines)${NC}"
    exit 1
else
    echo -e "${GREEN}✅ SKILL.md within size limit ($lines/500 lines)${NC}"
fi

# Test 5: Documentation integrity
echo ""
echo "Test 5: Documentation references"
# Check that skill references framework docs appropriately
if grep -q "AXIOMS.md\|ACCOMMODATIONS.md" "${SKILL_DIR}/SKILL.md"; then
    echo -e "${GREEN}✅ References framework documentation${NC}"
else
    echo -e "${YELLOW}⚠️  No explicit references to framework docs${NC}"
fi

# Cleanup
rm -rf "${TEST_DIR}"

# All tests passed
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All feature-dev integration tests PASSED${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

exit 0
