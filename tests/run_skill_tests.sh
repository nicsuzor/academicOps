#!/bin/bash
# Run skill script discovery tests
#
# Usage:
#   bash tests/run_skill_tests.sh

set -e

cd "$(dirname "$0")/.."

echo "Running Skill Script Discovery Tests..."
echo "========================================"
echo

python3 tests/integration/test_skill_discovery_standalone.py

echo
echo "To run full pytest suite (requires pytest installed):"
echo "  pytest tests/integration/test_skill_script_discovery.py -v"
