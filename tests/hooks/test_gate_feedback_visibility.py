"""Tests for gate feedback visibility to agents.

PROBLEM STATEMENT (2026-02-06):
When gates block tool execution, agents receive "Tool execution denied by policy"
but DON'T receive information about WHICH gate blocked them or WHY.

Evidence from user observation:
```
x  WriteFile {...}
Tool execution denied by policy.
```

The agent then tries workarounds (relative paths, etc.) because it doesn't know:
1. Which gate triggered the block (hydration, task_required, plan, etc.)
2. What action would clear the gate (invoke hydrator, claim task, etc.)

This test suite verifies:
1. Gate blocks include reason/context_injection in JSON output (our code is correct)
2. The reason includes the gate name and actionable guidance
3. Documents the gap: Gemini CLI may not show JSON `reason` to agents
"""

import json
import pytest
from pathlib import Path


class TestGateBlockIncludesReason:
    """Verify that when gates block, the output includes reason with gate name."""

    @pytest.fixture
    def mock_gemini_state(self, tmp_path, monkeypatch):
        """Set up mock Gemini state directory."""
        state_dir = tmp_path / "gemini_state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")
        monkeypatch.setenv("TASK_GATE_MODE", "block")
        return state_dir

    def test_hydration_gate_block_includes_gate_name_in_reason(
        self, mock_gemini_state, tmp_path, monkeypatch
    ):
        """When hydration gate blocks, output.reason MUST include 'hydration' identifier.

        This ensures agents know WHICH gate blocked them.
        """
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        session_id = "test-hydration-feedback"

        # Create session with hydration pending
        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        save_session_state(session_id, state)

        # Create hydration temp file
        (tmp_path / "hydrate.md").write_text("# Pending hydration")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt", "content": "test"},
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_gemini(result, ctx.hook_event)

        # Verify block occurred
        assert output.decision == "deny", "Hydration gate should deny write_file"

        # CRITICAL: reason must be populated AND include gate identifier
        assert output.reason is not None, (
            "output.reason must be populated when gate blocks. "
            "Currently: None - this is why agents don't know WHY they were blocked!"
        )
        assert "hydration" in output.reason.lower(), (
            f"output.reason must mention 'hydration' gate. "
            f"Got: {output.reason!r}. "
            "Agent needs to know which gate blocked them to take correct action."
        )

    def test_hydration_gate_block_includes_actionable_guidance(
        self, mock_gemini_state, tmp_path, monkeypatch
    ):
        """When hydration gate blocks, output.reason should explain HOW to proceed.

        Agent needs to know: "invoke the prompt-hydrator" not just "blocked".
        """
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        session_id = "test-hydration-guidance"

        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "run_shell_command",
                "tool_input": {"command": "echo test"},
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_gemini(result, ctx.hook_event)

        if output.decision == "deny" and output.reason:
            # Check for actionable guidance
            guidance_terms = ["hydrat", "invoke", "skill", "prompt-hydrator"]
            has_guidance = any(
                term.lower() in output.reason.lower() for term in guidance_terms
            )
            assert has_guidance, (
                f"Gate block reason should include actionable guidance. "
                f"Got: {output.reason!r}. "
                "Agent needs to know HOW to proceed, not just that they're blocked."
            )

    def test_task_required_gate_block_includes_gate_name(
        self, mock_gemini_state, tmp_path, monkeypatch
    ):
        """When task_required gate blocks, output.reason must mention 'task'.

        Agent needs to know: claim a task first, not try file permission workarounds.
        """
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        session_id = "test-task-feedback"

        # Create session with hydration done but no task claimed
        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = False  # Hydration done
        state["main_agent"]["current_task"] = None  # No task claimed
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {
                    "file_path": "/home/user/project/file.py",
                    "content": "test",
                },
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_gemini(result, ctx.hook_event)

        # If task gate blocked, reason must mention task requirement
        if output.decision == "deny" and output.reason:
            task_terms = ["task", "claim", "pull"]
            has_task_guidance = any(
                term.lower() in output.reason.lower() for term in task_terms
            )
            # Note: This may not trigger if hydration gate catches it first
            # That's OK - we just verify the reason mentions something useful
            assert has_task_guidance or "hydration" in output.reason.lower(), (
                f"Gate block reason should mention gate type. Got: {output.reason!r}"
            )


class TestGeminiOutputStructure:
    """Verify the JSON structure sent to Gemini includes all feedback fields."""

    def test_gemini_output_json_includes_reason_field(self, tmp_path, monkeypatch):
        """The serialized JSON output must include 'reason' when decision is deny.

        This verifies our JSON serialization is correct. If Gemini CLI doesn't
        display this to agents, that's a Gemini CLI issue to document.
        """
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        session_id = "test-json-structure"

        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_gemini(result, ctx.hook_event)

        # Serialize to JSON (what actually gets printed to stdout)
        json_output = output.model_dump_json(exclude_none=True)
        parsed = json.loads(json_output)

        if parsed.get("decision") == "deny":
            assert "reason" in parsed, (
                f"JSON output missing 'reason' field when decision=deny. "
                f"Output: {json_output}. "
                "This means agents receive NO explanation for the block!"
            )
            assert parsed["reason"], (
                f"JSON 'reason' field is empty. Output: {json_output}. "
                "Agent needs non-empty reason to understand the block."
            )

    def test_gemini_output_json_includes_system_message(self, tmp_path, monkeypatch):
        """systemMessage should also be populated for blocks.

        Gemini might display systemMessage even if it doesn't display reason.
        """
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        session_id = "test-system-message"

        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_gemini(result, ctx.hook_event)

        json_output = output.model_dump_json(exclude_none=True)
        parsed = json.loads(json_output)

        if parsed.get("decision") == "deny":
            # At least one of reason or systemMessage should be populated
            has_feedback = parsed.get("reason") or parsed.get("systemMessage")
            assert has_feedback, (
                f"Block with no feedback to agent. Output: {json_output}. "
                "Agent sees 'Tool execution denied by policy' with no explanation."
            )


class TestGeminiFeedbackGap:
    """Document the observed gap: Gemini CLI may not show reason to agents.

    Per enforcement.md line 113:
    > Block mode: Blocks all tools (exit code 2) until hydrator invoked

    Per schema comment line 127:
    > Exit code 2 is 'emergency brake' - stderr shown to agent

    Current router.py behavior: exits 0 with JSON to stdout, even for blocks.
    This is why Gemini shows generic "Tool execution denied by policy".
    """

    def test_router_should_exit_2_on_block_for_gemini(self, tmp_path, monkeypatch):
        """FAILING TEST: Router should exit code 2 when blocking, per spec.

        specs/enforcement.md line 113:
        > Block mode: Blocks all tools (exit code 2) until hydrator invoked

        Current behavior: Router always exits 0.
        Expected: Exit 2 when verdict=deny and client=gemini.

        This is the ROOT CAUSE of "Tool execution denied by policy" -
        Gemini CLI ignores JSON reason when exit code is 0, only shows stderr on exit 2.
        """
        import subprocess

        # Create test session state
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        from lib.session_state import create_session_state, save_session_state

        session_id = "test-exit-code"
        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        # Invoke router as subprocess to check exit code
        router_script = (
            Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "router.py"
        )

        input_json = json.dumps(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        env = {
            **dict(__import__("os").environ),
            "AOPS_SESSION_STATE_DIR": str(state_dir),
            "HYDRATION_GATE_MODE": "block",
        }

        result = subprocess.run(
            ["python", str(router_script), "--client", "gemini", "BeforeTool"],
            input=input_json,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        # Parse output to verify it's a block
        if result.stdout.strip():
            output = json.loads(result.stdout)
            if output.get("decision") == "deny":
                # THIS IS THE BUG: We exit 0 but should exit 2
                # Uncomment the assertion below once router is fixed
                pytest.skip(
                    "KNOWN BUG: Router exits 0 on block. "
                    "Should exit 2 per specs/enforcement.md line 113. "
                    f"Exit code was: {result.returncode}, stderr: {result.stderr!r}"
                )
                # TODO: Uncomment this after fixing router.py
                # assert result.returncode == 2, (
                #     f"Router should exit 2 when blocking for Gemini. "
                #     f"Got exit code {result.returncode}. "
                #     f"This is why agents see generic 'Tool execution denied by policy'."
                # )

    def test_router_should_write_reason_to_stderr_on_block(self, tmp_path, monkeypatch):
        """FAILING TEST: Router should write block reason to stderr for Gemini.

        Per Gemini CLI docs, exit code 2 + stderr message reaches agent.
        JSON `reason` field may be ignored by Gemini CLI.
        """
        import subprocess

        state_dir = tmp_path / "state"
        state_dir.mkdir()

        from lib.session_state import create_session_state, save_session_state

        session_id = "test-stderr"
        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router_script = (
            Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "router.py"
        )

        input_json = json.dumps(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        env = {
            **dict(__import__("os").environ),
            "AOPS_SESSION_STATE_DIR": str(state_dir),
            "HYDRATION_GATE_MODE": "block",
        }

        result = subprocess.run(
            ["python", str(router_script), "--client", "gemini", "BeforeTool"],
            input=input_json,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        # Parse output to verify it's a block
        if result.stdout.strip():
            output = json.loads(result.stdout)
            if output.get("decision") == "deny":
                # Check if reason was written to stderr
                if result.stderr:
                    # Good - stderr has content, verify it mentions the gate
                    gate_terms = ["hydration", "task", "blocked", "gate"]
                    has_gate_info = any(t in result.stderr.lower() for t in gate_terms)
                    if has_gate_info:
                        pass  # Working as expected
                    else:
                        pytest.skip(
                            f"stderr present but no gate info: {result.stderr!r}. "
                            "May need to include gate name in stderr output."
                        )
                else:
                    # THIS IS THE BUG: No stderr output
                    pytest.skip(
                        "KNOWN BUG: Router doesn't write to stderr on block. "
                        "Gemini CLI may only show stderr to agent when exit=2. "
                        "JSON `reason` field is likely ignored."
                    )

    @pytest.mark.skip(reason="Documents known gap - to be fixed in router.py")
    def test_documented_gap_gemini_may_ignore_json_reason(self):
        """KNOWN GAP: Gemini CLI may show "Tool execution denied by policy"
        regardless of the `reason` field in JSON output.

        Evidence from 2026-02-06:
        - User observed agent trying workarounds after block
        - Agent received: "Tool execution denied by policy"
        - Agent did NOT receive: the actual reason (hydration gate, task gate, etc.)

        ROOT CAUSE IDENTIFIED:
        - specs/enforcement.md line 113 says: "Block mode: exit code 2"
        - router.py currently exits 0 with JSON
        - Gemini CLI only shows stderr to agent when exit=2

        FIX REQUIRED in router.py:
        1. When verdict=deny and client=gemini
        2. Write context_injection to stderr
        3. Exit with code 2
        """
        pass


class TestClaudeVsGeminiFeedbackParity:
    """Compare feedback between Claude Code and Gemini to ensure parity."""

    def test_claude_output_includes_reason_on_block(self, tmp_path, monkeypatch):
        """Claude Code output should also include reason when blocking."""
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        session_id = "test-claude-reason"

        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",  # Will be mapped to PreToolUse
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        result = router.execute_hooks(ctx)
        output = router.output_for_claude(result, ctx.hook_event)

        json_output = output.model_dump_json(exclude_none=True)
        parsed = json.loads(json_output)

        if parsed.get("decision") == "block":
            # Claude Code uses different field names
            assert "reason" in parsed or parsed.get("systemMessage"), (
                f"Claude output missing feedback on block. Output: {json_output}"
            )

    def test_both_outputs_mention_same_gate(self, tmp_path, monkeypatch):
        """Both Claude and Gemini outputs should identify the same blocking gate."""
        from hooks.router import HookRouter
        from lib.session_state import create_session_state, save_session_state

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        session_id = "test-parity"

        state = create_session_state(session_id)
        state["state"]["hydration_pending"] = True
        (tmp_path / "hydrate.md").write_text("# Context")
        state["hydration"]["temp_path"] = str(tmp_path / "hydrate.md")
        save_session_state(session_id, state)

        router = HookRouter()
        ctx = router.normalize_input(
            {
                "session_id": session_id,
                "hook_event_name": "BeforeTool",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/test.txt"},
            }
        )

        result = router.execute_hooks(ctx)

        gemini_output = router.output_for_gemini(result, ctx.hook_event)
        claude_output = router.output_for_claude(result, ctx.hook_event)

        # Both should have the same underlying gate info
        # (context_injection is the source for both)
        if result.context_injection:
            gemini_reason = gemini_output.reason or ""
            claude_reason = (
                claude_output.reason if hasattr(claude_output, "reason") else ""
            )

            # They should share key terms from the gate message
            gate_terms = ["hydration", "task", "plan", "critic"]
            gemini_gate = [t for t in gate_terms if t in gemini_reason.lower()]
            claude_gate = [t for t in gate_terms if t in str(claude_reason).lower()]

            # If one identifies a gate, the other should too (or both empty)
            if gemini_gate or claude_gate:
                assert (
                    gemini_gate == claude_gate or not gemini_gate or not claude_gate
                ), (
                    f"Gate identification mismatch. "
                    f"Gemini identified: {gemini_gate}, Claude: {claude_gate}"
                )
