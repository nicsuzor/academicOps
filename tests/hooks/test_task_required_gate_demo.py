#!/usr/bin/env python3
"""Demo test proving task_required_gate works correctly.

This test demonstrates the three behaviors:
1. BLOCK: Write operations blocked when gates not satisfied
2. ALLOW: Write operations allowed when all three gates pass
3. BYPASS: Subagent sessions bypass the gate entirely

Run with: pytest tests/hooks/test_task_required_gate_demo.py -v -s
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Paths
AOPS_CORE = Path(__file__).parent.parent.parent
HOOKS_DIR = AOPS_CORE / "hooks"
LIB_DIR = AOPS_CORE / "lib"


def run_gate(
    tool_name: str,
    tool_input: dict,
    session_id: str,
    env_overrides: dict | None = None,
) -> dict:
    """Run the task_required_gate hook and return parsed output.

    Returns dict with:
    - decision: "allow" | "deny" | "allow_empty"
    - message: Additional context (if any)
    - raw_output: Full JSON output
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": session_id,
    }

    env = {
        **os.environ,
        "PYTHONPATH": str(AOPS_CORE),
        "CLAUDE_SESSION_ID": session_id,
        "TASK_GATE_MODE": "block",  # Force block mode for clear demonstration
    }
    # Clear any subagent flag by default
    env.pop("CLAUDE_AGENT_TYPE", None)

    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["python", str(HOOKS_DIR / "task_required_gate.py")],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(HOOKS_DIR),
    )

    # Gate always exits 0 - decision is in JSON output
    assert result.returncode == 0, f"Hook crashed: {result.stderr}"

    if not result.stdout.strip():
        return {"decision": "allow_empty", "message": None, "raw_output": {}}

    output = json.loads(result.stdout)

    if not output:
        return {"decision": "allow_empty", "message": None, "raw_output": {}}

    hook_output = output.get("hookSpecificOutput", {})
    decision = hook_output.get("permissionDecision", "unknown")
    message = hook_output.get("additionalContext", "")

    return {"decision": decision, "message": message, "raw_output": output}


class TestTaskRequiredGateDemo:
    """Demonstration tests proving gate behavior."""

    @pytest.fixture
    def clean_session_id(self) -> str:
        """Generate a unique session ID with no existing state."""
        import uuid
        return f"demo-test-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def session_with_gates(self, clean_session_id: str) -> str:
        """Create session state with all gates satisfied."""
        import sys
        sys.path.insert(0, str(LIB_DIR.parent))

        from lib.session_state import (
            get_or_create_session_state,
            set_current_task,
            set_critic_invoked,
            set_todo_with_handover,
            save_session_state,
        )

        # Create session and satisfy all three gates
        state = get_or_create_session_state(clean_session_id)
        set_current_task(clean_session_id, "demo-task-123", source="test")
        set_critic_invoked(clean_session_id, verdict="PROCEED")
        set_todo_with_handover(clean_session_id, handover_content="Session handover")

        return clean_session_id

    def test_demo_1_blocks_write_without_task(self, clean_session_id: str) -> None:
        """DEMO 1: Gate BLOCKS Write when no task is bound.

        This proves the gate enforces task binding for destructive operations.
        Without a task, the gate denies Write operations in block mode.
        """
        print("\n" + "=" * 60)
        print("DEMO 1: Write blocked without task")
        print("=" * 60)

        result = run_gate(
            tool_name="Write",
            tool_input={"file_path": "/tmp/test.txt", "content": "hello"},
            session_id=clean_session_id,
        )

        print(f"Tool: Write")
        print(f"Session: {clean_session_id} (no gates satisfied)")
        print(f"Decision: {result['decision']}")
        print(f"Message excerpt: {result['message'][:200] if result['message'] else 'None'}...")

        assert result["decision"] == "deny", (
            f"Expected 'deny', got '{result['decision']}'. "
            "Gate should block Write when no task bound!"
        )
        assert "THREE-GATE CHECK" in result["message"], "Block message should mention gate check"

        print("\n✓ PASSED: Gate correctly blocked Write without task binding")

    def test_demo_2_allows_write_with_all_gates(self, session_with_gates: str) -> None:
        """DEMO 2: Gate ALLOWS Write when all three gates pass.

        This proves the gate permits operations when properly authorized:
        - Task bound ✓
        - Critic invoked ✓
        - Todo with handover ✓
        """
        print("\n" + "=" * 60)
        print("DEMO 2: Write allowed with all gates satisfied")
        print("=" * 60)

        result = run_gate(
            tool_name="Write",
            tool_input={"file_path": "/tmp/test.txt", "content": "hello"},
            session_id=session_with_gates,
        )

        print(f"Tool: Write")
        print(f"Session: {session_with_gates} (all gates satisfied)")
        print(f"Decision: {result['decision']}")

        assert result["decision"] == "allow_empty", (
            f"Expected 'allow_empty' (empty JSON = allow), got '{result['decision']}'. "
            "Gate should allow Write when all gates pass!"
        )

        print("\n✓ PASSED: Gate correctly allowed Write with all gates satisfied")

    def test_demo_3_read_always_allowed(self, clean_session_id: str) -> None:
        """DEMO 3: Read operations ALWAYS allowed (no gate check needed).

        This proves read-only operations bypass the gate entirely,
        allowing exploration before task binding.
        """
        print("\n" + "=" * 60)
        print("DEMO 3: Read always allowed (no task needed)")
        print("=" * 60)

        result = run_gate(
            tool_name="Read",
            tool_input={"file_path": "/tmp/test.txt"},
            session_id=clean_session_id,
        )

        print(f"Tool: Read")
        print(f"Session: {clean_session_id} (no gates satisfied)")
        print(f"Decision: {result['decision']}")

        assert result["decision"] == "allow_empty", (
            f"Expected 'allow_empty', got '{result['decision']}'. "
            "Read should always be allowed!"
        )

        print("\n✓ PASSED: Gate correctly allows Read without task binding")

    def test_demo_4_subagent_bypasses_gate(self, clean_session_id: str) -> None:
        """DEMO 4: Subagent sessions BYPASS the gate entirely.

        This proves subagent sessions (CLAUDE_AGENT_TYPE set) can write
        without satisfying gates - they inherit authorization from parent.
        """
        print("\n" + "=" * 60)
        print("DEMO 4: Subagent bypasses gate")
        print("=" * 60)

        result = run_gate(
            tool_name="Write",
            tool_input={"file_path": "/tmp/test.txt", "content": "hello"},
            session_id=clean_session_id,
            env_overrides={"CLAUDE_AGENT_TYPE": "worker"},
        )

        print(f"Tool: Write")
        print(f"Session: {clean_session_id} (no gates satisfied)")
        print(f"Environment: CLAUDE_AGENT_TYPE=worker")
        print(f"Decision: {result['decision']}")

        assert result["decision"] == "allow_empty", (
            f"Expected 'allow_empty', got '{result['decision']}'. "
            "Subagent should bypass gate!"
        )

        print("\n✓ PASSED: Gate correctly bypassed for subagent session")

    def test_demo_5_destructive_bash_blocked(self, clean_session_id: str) -> None:
        """DEMO 5: Destructive Bash commands also blocked.

        This proves the gate checks Bash commands for destructive patterns
        like rm, mv, git commit, etc.
        """
        print("\n" + "=" * 60)
        print("DEMO 5: Destructive Bash blocked without task")
        print("=" * 60)

        result = run_gate(
            tool_name="Bash",
            tool_input={"command": "git commit -m 'test'"},
            session_id=clean_session_id,
        )

        print(f"Tool: Bash")
        print(f"Command: git commit -m 'test'")
        print(f"Session: {clean_session_id} (no gates satisfied)")
        print(f"Decision: {result['decision']}")

        assert result["decision"] == "deny", (
            f"Expected 'deny', got '{result['decision']}'. "
            "Destructive Bash should be blocked!"
        )

        print("\n✓ PASSED: Gate correctly blocked destructive Bash command")

    def test_demo_6_safe_bash_allowed(self, clean_session_id: str) -> None:
        """DEMO 6: Safe Bash commands allowed without task.

        This proves read-only Bash commands like 'git status' are allowed
        even without task binding.
        """
        print("\n" + "=" * 60)
        print("DEMO 6: Safe Bash allowed without task")
        print("=" * 60)

        result = run_gate(
            tool_name="Bash",
            tool_input={"command": "git status"},
            session_id=clean_session_id,
        )

        print(f"Tool: Bash")
        print(f"Command: git status")
        print(f"Session: {clean_session_id} (no gates satisfied)")
        print(f"Decision: {result['decision']}")

        assert result["decision"] == "allow_empty", (
            f"Expected 'allow_empty', got '{result['decision']}'. "
            "Safe Bash should be allowed!"
        )

        print("\n✓ PASSED: Gate correctly allows safe Bash command")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
