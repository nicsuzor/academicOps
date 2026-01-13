#!/usr/bin/env python3
"""
PreToolUse hook: Block Edit/Write/Bash until criteria gate passed.

Gate file: /tmp/claude-criteria-gate-{cwd_hash}
- Project-specific (uses cwd hash, not session_id)
- Created by agent after completing /do Phase 1
- Contains ISO timestamp of when criteria were defined
- Expires after 30 minutes (stale gate protection)

NOTE: Uses cwd (project directory) instead of session_id because:
- Subagents get their own session_id (no parent_session_id available)
- We want the gate to be shared across main session AND subagents
- cwd is stable across all agents within the same project

Exit codes:
    0: Allow
    2: Block (stderr message shown to Claude)

Failure mode: FAIL-CLOSED (block on any error)
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

GATE_DIR = Path("/tmp")
GATE_PREFIX = "claude-criteria-gate-"
GATE_EXPIRY_MINUTES = 30
GATED_TOOLS = {"Edit", "Write", "Bash"}

# EXPLICIT allowlist - no patterns, exact prefixes only
# These are read-only commands that can run without gate
BASH_ALLOWLIST = [
    "ls",
    "cat",
    "head",
    "tail",
    "wc",  # file reading
    "find",
    "grep",
    "rg",  # searching
    "git status",
    "git diff",
    "git log",  # git info
    "git branch",
    "git show",
    "git rev-parse",  # more git info
    'echo "$(date',  # gate file creation
    "pwd",
    "which",
    "type",
    "file",  # system info
    "uv run python -c",  # quick python checks
    "stat",
    "test",
    "cd ",  # navigation/info
]


def get_cwd_hash(cwd: str) -> str:
    """Generate a short hash from cwd for gate file naming."""
    return hashlib.sha256(cwd.encode()).hexdigest()[:12]


def get_gate_file(cwd: str) -> Path:
    """Get project-specific gate file path (based on cwd hash)."""
    cwd_hash = get_cwd_hash(cwd)
    return GATE_DIR / f"{GATE_PREFIX}{cwd_hash}"


def is_allowed_bash(command: str) -> bool:
    """Check if Bash command is in explicit allowlist."""
    cmd = command.strip()

    # Block any command with chain operators (could hide destructive ops)
    # Exception: pipes allowed for read-only commands like `git diff | head`
    if any(op in cmd for op in ["&&", "||", ";"]):
        return False

    # Check explicit allowlist
    return any(cmd.startswith(prefix) for prefix in BASH_ALLOWLIST)


def is_gate_valid(cwd: str) -> bool:
    """Check if gate file exists and is not expired."""
    gate_file = get_gate_file(cwd)
    if not gate_file.exists():
        return False

    try:
        content = gate_file.read_text().strip()
        gate_time = datetime.fromisoformat(content)
        expiry = gate_time + timedelta(minutes=GATE_EXPIRY_MINUTES)
        return datetime.now(gate_time.tzinfo) < expiry
    except (ValueError, OSError):
        # Corrupted or unreadable - treat as invalid
        return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # FAIL-CLOSED: block on parse error
        print("⛔ BLOCKED: Hook input error (fail-closed)", file=sys.stderr)
        sys.exit(2)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    cwd = input_data.get("cwd", "")

    # FAIL-CLOSED: require cwd
    if not cwd:
        print("⛔ BLOCKED: No cwd in hook input (fail-closed)", file=sys.stderr)
        sys.exit(2)

    # Not a gated tool - allow
    if tool_name not in GATED_TOOLS:
        print(json.dumps({}))
        sys.exit(0)

    # Bash: allow explicit read-only commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if is_allowed_bash(command):
            print(json.dumps({}))
            sys.exit(0)

    # Check gate file (with expiry)
    if is_gate_valid(cwd):
        print(json.dumps({}))
        sys.exit(0)

    # BLOCK - gate not passed or expired
    # Provide exact gate file path so agent knows what to create
    gate_file = get_gate_file(cwd)
    print(
        f"⛔ BLOCKED: Criteria gate not passed.\n\n"
        f"Before using Edit/Write/Bash, you MUST:\n"
        f"1. Define acceptance criteria (user outcomes)\n"
        f"2. Invoke critic to review criteria\n"
        f"3. Create TodoWrite with CHECKPOINT items\n"
        f"4. Run: echo \"$(date -Iseconds)\" > {gate_file}\n\n"
        f"Gate expires after 30 minutes. See /do command Phase 1.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
