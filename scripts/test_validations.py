#!/usr/bin/env python3
"""
Test script to verify validation rules work correctly.
Tests both the simplified .md error message and python -c blocking.
"""

import sys
from pathlib import Path

# Add parent directory to path to import validate_tool
sys.path.insert(0, str(Path(__file__).parent))

from validate_tool import validate_tool_use


def test_md_file_blocking():
    """Test that .md file creation is blocked with simplified message."""
    print("Testing .md file blocking...")

    # Test 1: Regular agent trying to create .md file (should block)
    tool_name = "Write"
    tool_input = {
        "file_path": "docs/README.md",  # Use relative path from project root
        "content": "test content"
    }
    active_agent = "developer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert not allowed, "Should block .md file creation for non-trainer agents"
    assert severity == "block", "Should use 'block' severity"
    assert "All code should be self-documenting; no new documentation allowed" in error, \
        f"Error message should be simplified. Got: {error}"
    print("✓ Test 1 passed: Regular agent blocked from creating .md files")

    # Test 2: Trainer agent creating .md file (should allow)
    active_agent = "trainer"
    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert allowed, "Trainer should be allowed to create .md files"
    print("✓ Test 2 passed: Trainer can create .md files")

    # Test 3: Allowed path (papers/) should be allowed for all agents
    tool_input = {
        "file_path": "/home/nic/src/writing/papers/research.md",
        "content": "research content"
    }
    active_agent = "academic_writer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert allowed, "Should allow .md files in papers/ directory"
    print("✓ Test 3 passed: .md files allowed in papers/ directory")

    # Test 4: Allowed path (bot/agents/) should be allowed for trainer
    tool_input = {
        "file_path": "/home/nic/src/writing/bot/agents/newagent.md",
        "content": "agent instructions"
    }
    active_agent = "trainer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert allowed, "Should allow .md files in bot/agents/ directory for trainer"
    print("✓ Test 4 passed: .md files allowed in bot/agents/ for trainer")

    print("\nAll .md file blocking tests passed!\n")


def test_python_c_blocking():
    """Test that python -c inline execution is blocked for all agents."""
    print("Testing python -c blocking...")

    # Test 1: python -c command (should block)
    tool_name = "Bash"
    tool_input = {
        "command": "python -c 'print(\"hello\")'"
    }
    active_agent = "developer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert not allowed, "Should block python -c execution"
    assert severity == "block", "Should use 'block' severity"
    assert "Inline Python execution (python -c) is prohibited" in error, \
        f"Error message incorrect. Got: {error}"
    assert "Create a proper test file instead" in error, \
        f"Error message should suggest creating test file. Got: {error}"
    print("✓ Test 1 passed: python -c blocked for developer agent")

    # Test 2: python3 -c command (should block)
    tool_input = {
        "command": "python3 -c 'import sys; print(sys.version)'"
    }
    active_agent = "trainer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert not allowed, "Should block python3 -c execution even for trainer"
    assert severity == "block", "Should use 'block' severity"
    print("✓ Test 2 passed: python3 -c blocked even for trainer agent")

    # Test 3: Normal python script execution (should allow)
    tool_input = {
        "command": "python test_script.py"
    }
    active_agent = "developer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    # This should pass the python -c check (but may trigger uv run warning)
    # We're only checking that python -c blocking doesn't interfere
    if not allowed:
        assert "python -c" not in error.lower(), \
            "Normal python script execution should not trigger python -c block"
    print("✓ Test 3 passed: Normal python script execution not blocked by python -c rule")

    # Test 4: Command with python -c in middle of pipeline
    tool_input = {
        "command": "echo 'test' | python -c 'import sys; print(sys.stdin.read())'"
    }
    active_agent = "code-review"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    assert not allowed, "Should block python -c in pipeline"
    assert "Inline Python execution (python -c) is prohibited" in error
    print("✓ Test 4 passed: python -c blocked in pipeline")

    # Test 5: Command with "python-c" as part of filename (should not block)
    tool_input = {
        "command": "cat python-config.txt"
    }
    active_agent = "developer"

    allowed, error, severity = validate_tool_use(tool_name, tool_input, active_agent)

    # Should not trigger python -c block (may trigger other rules)
    if not allowed and error:
        assert "python -c" not in error.lower(), \
            "Should not block commands with 'python-c' as part of other text"
    print("✓ Test 5 passed: 'python-c' in filename not incorrectly blocked")

    print("\nAll python -c blocking tests passed!\n")


def main():
    """Run all validation tests."""
    print("="*70)
    print("Running validation rule tests")
    print("="*70)
    print()

    try:
        test_md_file_blocking()
        test_python_c_blocking()

        print("="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
