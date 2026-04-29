#!/usr/bin/env python3
"""Tests for orchestrator boundary enforcement.

Covers:
1. prompt_classifier / dispositor reminder injection (Level 2 hydrator)
2. is_project_source_write path classification
3. orchestrator_boundary gate PostToolUse warn verdict (Level 4 detection)

See `specs/orchestrator-boundary.md` and `aops-core/HEURISTICS.md#P122`.
"""

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from hooks.schemas import CanonicalHookOutput, HookContext
from lib.gate_model import GateVerdict
from lib.gates.registry import GateRegistry
from lib.orchestrator_boundary import (
    classify_prompt,
    is_framework_path,
    is_orchestrator_session,
    is_project_source_write,
    should_inject_dispositor_reminder,
)
from lib.session_state import SessionState


def _reinit_gates():
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture(autouse=True)
def _gate_modes(monkeypatch):
    monkeypatch.setenv("HYDRATION_GATE_MODE", "off")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    monkeypatch.setenv("ORCHESTRATOR_BOUNDARY_GATE_MODE", "warn")
    # Force orchestrator session for tests unless a test overrides it
    monkeypatch.delenv("POLECAT_SESSION_TYPE", raising=False)
    _reinit_gates()
    yield
    _reinit_gates()


# ===========================================================================
# Unit: classify_prompt
# ===========================================================================


class TestClassifyPrompt:
    def test_empty_prompt(self):
        assert classify_prompt("") == "empty"
        assert classify_prompt("   \n") == "empty"

    def test_slash_command(self):
        assert classify_prompt("/daily") == "slash-command"
        assert classify_prompt("/q implement foo bar baz") == "slash-command"

    def test_task_notification(self):
        assert (
            classify_prompt("<task-notification>job-42 completed</task-notification>")
            == "task-notification"
        )

    def test_short_question(self):
        assert classify_prompt("what time is it?") == "question"
        assert classify_prompt("How does hydration work?") == "question"

    def test_work_request_plain(self):
        assert (
            classify_prompt("implement login using JWT and store tokens in redis") == "work-request"
        )
        assert (
            classify_prompt("refactor the task manager so that subtasks inherit tags")
            == "work-request"
        )

    def test_long_question_counts_as_work_request(self):
        # Long questions may still describe work — be conservative and inject.
        long_q = " ".join(["why"] * 20) + "?"
        assert classify_prompt(long_q) == "work-request"

    def test_non_string(self):
        assert classify_prompt(None) == "empty"
        assert classify_prompt(12345) == "empty"


# ===========================================================================
# Unit: is_framework_path
# ===========================================================================


class TestIsFrameworkPath:
    @pytest.mark.parametrize(
        "file_path,expected",
        [
            ("aops-core/hooks/router.py", True),
            ("specs/enforcement.md", True),
            (".agents/context-map.json", True),
            ("docs/VISION.md", True),
            ("tests/hooks/test_x.py", True),
            ("scripts/install.sh", True),
            # Non-framework
            ("src/app.py", False),
            ("README.md", False),
            ("paper/draft.md", False),
            # Leading dot-slash
            ("./aops-core/foo.py", True),
            ("./src/app.py", False),
        ],
    )
    def test_relative_paths(self, file_path, expected):
        assert is_framework_path(file_path) is expected

    def test_absolute_inside_cwd(self, tmp_path):
        cwd = tmp_path
        (cwd / "aops-core").mkdir()
        (cwd / "aops-core" / "foo.py").write_text("# framework")
        (cwd / "src").mkdir()
        (cwd / "src" / "app.py").write_text("# project")

        assert is_framework_path(str(cwd / "aops-core" / "foo.py"), cwd=str(cwd)) is True
        assert is_framework_path(str(cwd / "src" / "app.py"), cwd=str(cwd)) is False

    def test_absolute_outside_cwd(self, tmp_path):
        # Files outside cwd are not project writes — treat as "not framework"
        # (the detection further up returns False in that case)
        other = tmp_path / "other"
        other.mkdir()
        (other / "file.py").write_text("")
        assert is_framework_path(str(other / "file.py"), cwd=str(tmp_path / "proj")) is False

    def test_empty_path(self):
        assert is_framework_path("") is False


# ===========================================================================
# Unit: is_project_source_write
# ===========================================================================


class TestIsProjectSourceWrite:
    def test_edit_to_project_source_fires(self):
        assert is_project_source_write("Edit", {"file_path": "src/app.py"}) is True

    def test_write_to_framework_suppressed(self):
        assert is_project_source_write("Write", {"file_path": "aops-core/new_file.py"}) is False
        assert is_project_source_write("Edit", {"file_path": "specs/x.md"}) is False
        assert is_project_source_write("Edit", {"file_path": ".agents/context-map.json"}) is False

    def test_non_write_tool(self):
        assert is_project_source_write("Read", {"file_path": "src/app.py"}) is False
        assert is_project_source_write("Bash", {"command": "rm -rf src/"}) is False

    def test_missing_file_path(self):
        assert is_project_source_write("Edit", {}) is False
        assert is_project_source_write("Edit", None) is False

    def test_non_string_file_path(self):
        assert is_project_source_write("Edit", {"file_path": 123}) is False


# ===========================================================================
# Unit: is_orchestrator_session
# ===========================================================================


class TestIsOrchestratorSession:
    def test_no_env_is_orchestrator(self):
        # Legacy call (no cwd) — falls back to env-only check
        assert is_orchestrator_session({}) is True

    def test_polecat_worker_not_orchestrator(self):
        assert is_orchestrator_session({"POLECAT_SESSION_TYPE": "polecat"}) is False
        assert is_orchestrator_session({"POLECAT_SESSION_TYPE": "crew"}) is False

    def test_unknown_session_type_is_orchestrator(self):
        # Conservative: unknown values fall back to orchestrator
        assert is_orchestrator_session({"POLECAT_SESSION_TYPE": "something-else"}) is True

    def test_cwd_inside_brain_is_orchestrator(self, tmp_path):
        env = {"ACA_DATA": str(tmp_path)}
        assert is_orchestrator_session(env, cwd=str(tmp_path)) is True
        sub = tmp_path / "projects"
        sub.mkdir()
        assert is_orchestrator_session(env, cwd=str(sub)) is True

    def test_cwd_outside_brain_is_not_orchestrator(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        other = tmp_path / "academicOps"
        other.mkdir()
        env = {"ACA_DATA": str(brain)}
        # In academicOps the agent IS the worker — not the orchestrator.
        assert is_orchestrator_session(env, cwd=str(other)) is False

    def test_aca_data_unset_with_cwd_not_orchestrator(self, tmp_path):
        # Without ACA_DATA we cannot identify the brain repo — fail closed.
        assert is_orchestrator_session({}, cwd=str(tmp_path)) is False


# ===========================================================================
# Unit: should_inject_dispositor_reminder
# ===========================================================================


class TestShouldInjectDispositorReminder:
    def test_work_request_in_orchestrator(self):
        # Legacy: no cwd passed — env-only check, defaults to orchestrator.
        assert should_inject_dispositor_reminder("implement login feature", {}) is True

    def test_slash_command_skipped(self):
        assert should_inject_dispositor_reminder("/daily", {}) is False

    def test_short_question_skipped(self):
        assert should_inject_dispositor_reminder("what now?", {}) is False

    def test_polecat_worker_skipped(self):
        assert (
            should_inject_dispositor_reminder(
                "implement login feature", {"POLECAT_SESSION_TYPE": "polecat"}
            )
            is False
        )

    def test_empty_skipped(self):
        assert should_inject_dispositor_reminder("", {}) is False

    def test_work_request_in_brain_cwd_injects(self, tmp_path):
        env = {"ACA_DATA": str(tmp_path)}
        assert (
            should_inject_dispositor_reminder("implement login feature", env, cwd=str(tmp_path))
            is True
        )

    def test_work_request_outside_brain_skipped(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        other = tmp_path / "academicOps"
        other.mkdir()
        env = {"ACA_DATA": str(brain)}
        # In academicOps/, the agent is the worker — no reminder.
        assert (
            should_inject_dispositor_reminder("implement login feature", env, cwd=str(other))
            is False
        )


# ===========================================================================
# Integration: hydrator injects dispositor reminder
# ===========================================================================


class TestHydratorInjection:
    def _make_ctx(self, prompt: str, cwd: str | None = None) -> HookContext:
        return HookContext(
            session_id="test-orch-boundary",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
            is_subagent=False,
            raw_input={"prompt": prompt},
            cwd=cwd,
        )

    def test_work_request_outside_brain_no_injection(self, monkeypatch, tmp_path):
        # Regression: agents working in academicOps/mem/explorations should
        # NOT see dispositor reminders — they ARE the worker for that repo.
        brain = tmp_path / "brain"
        brain.mkdir()
        other = tmp_path / "academicOps"
        other.mkdir()
        monkeypatch.setenv("ACA_DATA", str(brain))
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput()

        ctx = self._make_ctx("implement login with JWT tokens", cwd=str(other))
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is None

    def test_work_request_inside_brain_injects(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ACA_DATA", str(tmp_path))
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput()

        ctx = self._make_ctx("implement login with JWT tokens", cwd=str(tmp_path))
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is not None
        assert "Orchestrator Boundary" in merged.context_injection

    def test_work_request_injects_reminder(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput()

        ctx = self._make_ctx("implement login with JWT tokens")
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is not None
        assert "Orchestrator Boundary" in merged.context_injection
        assert "dispatch" in merged.context_injection.lower()

    def test_slash_command_no_injection(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput()

        ctx = self._make_ctx("/daily")
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is None

    def test_polecat_worker_no_injection(self, monkeypatch):
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "polecat")
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput()

        ctx = self._make_ctx("implement login with JWT tokens")
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is None

    def test_reminder_appended_to_existing_injection(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        merged = CanonicalHookOutput(context_injection="PRIOR_CONTENT")

        ctx = self._make_ctx("refactor the billing module to use decimal precision")
        router._inject_dispositor_reminder(ctx, merged)

        assert merged.context_injection is not None
        assert merged.context_injection.startswith("PRIOR_CONTENT")
        assert "Orchestrator Boundary" in merged.context_injection


# ===========================================================================
# Integration: orchestrator_boundary gate fires WARN on PostToolUse
# ===========================================================================


class TestOrchestratorBoundaryGate:
    def _make_ctx(
        self,
        tool_name: str = "Edit",
        file_path: str = "src/app.py",
        cwd: str = "/workspace",
    ) -> HookContext:
        return HookContext(
            session_id="test-orch-boundary-gate",
            hook_event="PostToolUse",
            tool_name=tool_name,
            tool_input={"file_path": file_path, "old_string": "a", "new_string": "b"},
            is_subagent=False,
            cwd=cwd,
            raw_input={},
        )

    def test_project_source_write_fires_warn(self, monkeypatch):
        # Gate fires only when cwd is inside the brain repo (orchestrator
        # session). Set ACA_DATA to match cwd to simulate a brain session.
        monkeypatch.setenv("ACA_DATA", "/workspace")
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Edit", file_path="src/app.py")

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "orchestrator_boundary gate did not fire"
        assert result.verdict == GateVerdict.WARN, f"Expected WARN, got {result.verdict}"
        assert result.context_injection is not None
        assert "src/app.py" in result.context_injection

    def test_project_source_write_outside_brain_does_not_fire(self, monkeypatch, tmp_path):
        # Regression: agents working in a project source repo (academicOps,
        # mem, explorations) ARE the worker — orchestrator gate must not fire.
        brain = tmp_path / "brain"
        brain.mkdir()
        other = tmp_path / "academicOps"
        other.mkdir()
        monkeypatch.setenv("ACA_DATA", str(brain))
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate-outside")
        ctx = self._make_ctx(tool_name="Edit", file_path="src/app.py", cwd=str(other))

        result = router._dispatch_gates(ctx, state)

        if result is not None and result.system_message:
            assert "Orchestrator boundary" not in result.system_message

    def test_framework_write_does_not_fire(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Write", file_path="aops-core/hooks/foo.py")

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.WARN or (
                result.system_message is None
                or "Orchestrator boundary" not in (result.system_message or "")
            )

    def test_specs_write_does_not_fire(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Edit", file_path="specs/enforcement.md")

        result = router._dispatch_gates(ctx, state)

        # No orchestrator_boundary warn for framework paths
        if result is not None and result.system_message:
            assert "Orchestrator boundary" not in result.system_message

    def test_polecat_worker_does_not_fire(self, monkeypatch):
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "polecat")
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Edit", file_path="src/app.py")

        result = router._dispatch_gates(ctx, state)

        if result is not None and result.system_message:
            assert "Orchestrator boundary" not in result.system_message

    def test_read_tool_does_not_fire(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Read", file_path="src/app.py")

        result = router._dispatch_gates(ctx, state)

        if result is not None and result.system_message:
            assert "Orchestrator boundary" not in result.system_message

    def test_subagent_session_does_not_fire(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Edit", file_path="src/app.py")
        ctx.is_subagent = True

        result = router._dispatch_gates(ctx, state)

        # Subagent sessions bypass gates entirely
        assert result is None

    def test_gate_mode_off_disables(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_BOUNDARY_GATE_MODE", "allow")
        _reinit_gates()
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = SessionState.create("test-orch-boundary-gate")
        ctx = self._make_ctx(tool_name="Edit", file_path="src/app.py")

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.WARN
