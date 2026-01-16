#!/bin/bash
# Integration test for task management scripts

set -e  # Exit on error

echo "Testing task management scripts..."

# Test 1: task_view.py runs without error
echo "Test 1: task_view.py execution..."
uv run python bots/skills/tasks/scripts/task_view.py --compact > /dev/null
echo "✓ task_view.py runs successfully"

# Test 2: task_archive.py shows help
echo "Test 2: task_archive.py help..."
uv run python bots/skills/tasks/scripts/task_archive.py --help > /dev/null
echo "✓ task_archive.py help works"

# Test 3: task_add.py shows help
echo "Test 3: task_add.py help..."
uv run python bots/skills/tasks/scripts/task_add.py --help > /dev/null
echo "✓ task_add.py help works"

echo ""
echo "All task script tests passed!"
exit 0
