#!/bin/bash
# scripts/verify-docker-env.sh - Multi-client environment verification
#
# Verifies:
#   1. Docker build success
#   2. Tool availability (uv, python, node, gh)
#   3. Client availability (claude, gemini)
#   4. Framework compliance (P#93: Run Python via uv)

set -e

IMAGE_NAME="aops-env-test"
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Ensure cleanup runs on script exit
cleanup() {
    echo -e "\n--- Cleaning up test image ---"
    docker rmi "$IMAGE_NAME" &>/dev/null || true
}
trap cleanup EXIT

echo "--- Building aops environment image ---"
docker build -t "$IMAGE_NAME" .

echo -e "\n--- Running Environment Checks ---"

run_check() {
    local label=$1
    local cmd=$2
    echo -n "Check: $label... "
    if docker run --rm "$IMAGE_NAME" bash -c "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        return 1
    fi
}

# 1. System Tools
run_check "uv installed" "uv --version"
run_check "Python 3.12" "python3 --version | grep '3.12'"
run_check "Node.js 22" "node --version | grep 'v22'"
run_check "Git installed" "git --version"
run_check "GH CLI installed" "gh --version"

# 2. AI Clients
run_check "Claude Code CLI" "claude --version"
run_check "Gemini CLI" "gemini --version"

# 3. Framework Compliance (P#93)
run_check "uv run python" "uv run python --version"

# 4. Workspace Integrity
run_check "AOPS env var" "echo \$AOPS | grep '/app'"
run_check "ACA_DATA env var" "echo \$ACA_DATA | grep '/data'"

echo -e "\n${GREEN}Verification Complete! Environment is multi-client ready.${NC}"
