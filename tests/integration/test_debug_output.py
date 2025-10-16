#!/usr/bin/env python3
"""Debug test to see actual Claude Code output."""

import json
import subprocess

import pytest

# Mark all tests in this file as slow (integration tests invoking Claude CLI)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


def test_see_output():
    """Just print what we get back."""
    result = subprocess.run(
        [
            "claude",
            "-p", "@agent-developer Run this bash command: python -c 'print(1+1)'",
            "--output-format", "json",
            "--permission-mode", "acceptEdits"
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd="/home/nic/src/writing"
    )

    print("\n=== STDOUT ===")
    print(result.stdout)
    print("\n=== STDERR ===")
    print(result.stderr)
    print("\n=== RETURN CODE ===")
    print(result.returncode)

    if result.stdout:
        output = json.loads(result.stdout)
        print("\n=== PARSED OUTPUT ===")
        print(json.dumps(output, indent=2))
        print("\n=== PERMISSION DENIALS ===")
        print(output.get("permission_denials", "NOT FOUND"))


if __name__ == "__main__":
    test_see_output()
