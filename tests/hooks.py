#!/usr/bin/env python3
"""
Helpers for validation hook system
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# Helper Functions
# ============================================================================


def run_hook(
    script_path: Path, hook_input: dict[str, Any], timeout: int = 10
) -> tuple[int, str, str]:
    """
    Run a hook script with JSON input and return exit code, stdout, stderr.

    Args:
        script_path: Path to the hook script
        hook_input: Dictionary to pass as JSON stdin
        timeout: Timeout in seconds

    Returns:
        (exit_code, stdout, stderr)
    """
    result = subprocess.run(
        ["uv", "run", "python", str(script_path)],
        check=False,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def parse_hook_output(stdout: str) -> dict[str, Any]:
    """
    Parse hook JSON output from stdout.

    Claude Code hooks output JSON to stdout per the specification.
    This function handles both pure JSON and JSON with surrounding text.
    """
    # Try to find JSON in stdout
    stdout = stdout.strip()

    # Check if stdout starts with {
    if stdout.startswith("{"):
        return json.loads(stdout)

    # Try to find JSON block in stdout
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            # Found start of JSON, extract until end
            json_lines = []
            brace_count = 0
            for j in range(i, len(lines)):
                json_lines.append(lines[j])
                brace_count += lines[j].count("{") - lines[j].count("}")
                if brace_count == 0:
                    break
            json_str = "\n".join(json_lines)
            return json.loads(json_str)

    msg = f"No JSON found in stdout: {stdout}"
    raise ValueError(msg)
