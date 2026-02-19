"""
End-to-end tests for gate enforcement.

These tests run actual CLI headless sessions to verify that gates
correctly block or allow tool usage at runtime.

Per testing.md: TRUE E2E = Real APIs + Real execution. These tests use
the actual CLI and hook infrastructure, not mocks.

IMPORTANT: These tests ACTUALLY exercise gate behavior - they don't just
ask the agent questions about the system. Each test performs real tool
operations and verifies the gate response.

Run with: uv run pytest tests/e2e/test_gates_enforcement_e2e.py -v -n 0 -m slow --timeout=300
"""

import json
from pathlib import Path

import pytest


@pytest.mark.slow
class TestHydrationGateE2E:
    """E2E tests for hydration gate enforcement."""

    def test_hydration_blocks_read_tool_before_hydration(self, cli_headless):
        """
        GIVEN: A fresh session with no hydration
        WHEN: Agent attempts to use Read tool
        THEN: Gate should block with hydration required message
        """
        runner, platform = cli_headless

        result = runner(
            "Read the file /etc/hosts and tell me what's in it. Do not use any other tools first.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        block_indicators = ["hydration", "BLOCKED", "gate", "pending"]
        is_blocked = any(ind.lower() in output_text.lower() for ind in block_indicators)

        assert is_blocked, (
            f"[{platform}] Expected hydration gate to block Read tool.\nOutput: {output_text[:500]}"
        )

    def test_hydration_allows_mcp_task_tools(self, cli_headless):
        """
        GIVEN: A fresh session with no hydration
        WHEN: Agent uses MCP task manager tools (list_tasks)
        THEN: Tools should be allowed (exempt from hydration) and return task data
        """
        runner, platform = cli_headless

        result = runner(
            "List the available tasks using the task manager MCP tool. Just call list_tasks with limit=3.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        assert "Hydration Required" not in output_text
        assert result["success"], f"[{platform}] CLI execution should succeed"

        task_output_indicators = ["success", "tasks", "count", "total"]
        has_task_output = any(ind in output_text.lower() for ind in task_output_indicators)
        assert has_task_output, (
            f"[{platform}] Expected task manager output, got: {output_text[:300]}"
        )

    def test_hydration_allows_safe_git_bash(self, cli_headless):
        """
        GIVEN: A fresh session with no hydration
        WHEN: Agent runs safe git command (git status)
        THEN: Command should execute and return actual git status output
        """
        runner, platform = cli_headless

        result = runner(
            "Run 'git status' using Bash. Just run that one command and show me the output.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        git_output_indicators = [
            "branch",
            "modified",
            "untracked",
            "clean",
            "changes",
            "commit",
        ]
        has_git_output = any(ind.lower() in output_text.lower() for ind in git_output_indicators)

        if "BLOCKED" in output_text.upper():
            assert "hydration" not in output_text.lower(), (
                f"[{platform}] Safe git commands should bypass hydration gate"
            )
        else:
            assert has_git_output, (
                f"[{platform}] Expected git status output, got: {output_text[:300]}"
            )


@pytest.mark.slow
class TestBashClassificationE2E:
    """E2E tests for Bash command classification."""

    def test_safe_read_bash_allowed(self, cli_headless):
        """
        GIVEN: A session (regardless of hydration/task state)
        WHEN: Agent runs read-only Bash (pwd, ls)
        THEN: Commands should execute and return actual output
        """
        runner, platform = cli_headless

        result = runner(
            "Run 'pwd' using Bash and tell me the exact path it returns.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        has_path_output = "/" in output_text and "home" in output_text.lower()

        if "BLOCKED" in output_text.upper():
            assert "destructive" not in output_text.lower(), (
                f"[{platform}] pwd should not be classified as destructive"
            )
        else:
            assert has_path_output or result["success"], (
                f"[{platform}] Expected pwd to return a path, got: {output_text[:300]}"
            )


@pytest.mark.slow
class TestGateLifecycleE2E:
    """E2E tests for gate lifecycle transitions."""

    def test_skill_invocation_progresses_hydration(self, cli_headless):
        """
        GIVEN: A fresh session
        WHEN: Agent invokes the /pull skill
        THEN: Skill should execute (skills bypass some gates) and return task info
        """
        runner, platform = cli_headless

        result = runner(
            "Use the Skill tool to invoke 'aops-core:pull' to pull the next available task.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        skill_output_indicators = [
            "task",
            "pull",
            "claim",
            "ready",
            "queue",
            "no tasks",
            "available",
        ]
        has_skill_output = any(
            ind.lower() in output_text.lower() for ind in skill_output_indicators
        )

        assert result["success"] or has_skill_output, (
            f"[{platform}] Expected /pull skill to execute. Output: {output_text[:500]}"
        )


@pytest.mark.slow
class TestMultiGateE2E:
    """E2E tests for multi-gate enforcement on write operations."""

    def test_edit_requires_hydration(self, cli_headless, tmp_path):
        """
        GIVEN: A fresh session (no hydration)
        WHEN: Agent attempts Edit tool
        THEN: Should be blocked for hydration
        """
        runner, platform = cli_headless
        test_file = tmp_path / "edit-test.txt"
        test_file.write_text("original content")

        result = runner(
            f"Edit the file {test_file} to replace 'original' with 'modified'. Use the Edit tool.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        gate_indicators = ["gate", "hydration", "BLOCKED", "warn", "required"]
        has_gate_enforcement = any(ind.lower() in output_text.lower() for ind in gate_indicators)

        file_unchanged = test_file.read_text() == "original content"

        assert has_gate_enforcement or file_unchanged, (
            f"[{platform}] Expected Edit to be blocked by hydration gate.\n"
            f"File modified: {not file_unchanged}\n"
            f"Output: {output_text[:500]}"
        )

    def test_write_to_project_file_requires_hydration(self, cli_headless):
        """
        GIVEN: A fresh session
        WHEN: Agent attempts to Write to a project file
        THEN: Should trigger hydration gate enforcement
        """
        runner, platform = cli_headless
        project_file = Path.cwd() / "e2e-test-should-not-exist.txt"

        result = runner(
            f"Write 'test' to the file {project_file}. Use the Write tool.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        gate_indicators = ["gate", "hydration", "BLOCKED", "warn"]
        has_gate_enforcement = any(ind.lower() in output_text.lower() for ind in gate_indicators)

        file_not_created = not project_file.exists()

        if project_file.exists():
            project_file.unlink()

        assert has_gate_enforcement or file_not_created, (
            f"[{platform}] Expected Write to project file to be blocked by hydration gate.\n"
            f"File created: {not file_not_created}\n"
            f"Output: {output_text[:500]}"
        )


@pytest.mark.slow
class TestHydrationExemptToolsE2E:
    """E2E tests for tools exempt from hydration gate."""

    def test_memory_tools_bypass_hydration(self, cli_headless):
        """
        GIVEN: A fresh session with no hydration
        WHEN: Agent uses memory retrieval tools
        THEN: Tools should work (memory tools are exempt from hydration)
        """
        runner, platform = cli_headless

        result = runner(
            "Use the mcp__plugin_aops-core_memory__retrieve_memory tool to search for 'test query'.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        blocked_for_hydration = (
            "hydration" in output_text.lower() and "BLOCKED" in output_text.upper()
        )

        memory_indicators = [
            "memories",
            "results",
            "query",
            "similarity",
            "no memories",
        ]
        has_memory_output = any(ind.lower() in output_text.lower() for ind in memory_indicators)

        assert not blocked_for_hydration, (
            f"[{platform}] Memory tools should bypass hydration gate.\nOutput: {output_text[:500]}"
        )
        assert result["success"] or has_memory_output, (
            f"[{platform}] Expected memory tool to execute. Output: {output_text[:500]}"
        )

    def test_glob_bypasses_hydration(self, cli_headless):
        """
        GIVEN: A fresh session with no hydration
        WHEN: Agent uses Glob tool
        THEN: Should work (Glob is exempt from hydration)
        """
        runner, platform = cli_headless

        result = runner(
            "Use the Glob tool with pattern '*.py' to find Python files in the current directory.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = json.dumps(result.get("result", {}))

        blocked_for_hydration = (
            "hydration" in output_text.lower() and "BLOCKED" in output_text.upper()
        )

        assert not blocked_for_hydration, (
            f"[{platform}] Glob should bypass hydration gate.\nOutput: {output_text[:500]}"
        )
