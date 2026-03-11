#!/usr/bin/env python3
"""Tests that every gate block/warn verdict includes context injection.

Invariant: whenever a gate produces a non-allow verdict (deny, block, warn),
the result MUST include a non-empty context_injection. Without it, the agent
sees "Blocked by hook" with no actionable guidance on what to do.

This is a structural test (gate definitions must have context_key on every
policy) AND a behavioral test (the engine must produce non-empty
context_injection for every block/warn verdict at runtime).
"""

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


def _reinit_gates():
    if "gate_config" in sys.modules:
        importlib.reload(sys.modules["gate_config"])
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture(autouse=True)
def _pin_gate_modes(monkeypatch):
    monkeypatch.setenv("HYDRATION_GATE_MODE", "block")
    monkeypatch.setenv("CUSTODIET_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "block")
    monkeypatch.setenv("COMMIT_GATE_MODE", "deny")
    monkeypatch.setenv("CUSTODIET_TOOL_CALL_THRESHOLD", "50")
    _reinit_gates()
    yield
    _reinit_gates()


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


# ===========================================================================
# STRUCTURAL: Every non-allow policy must declare a context_key
# ===========================================================================


class TestEveryPolicyHasContextKey:
    """Every GatePolicy with a non-allow verdict MUST have a context_key.

    Without context_key, the agent sees "Blocked by hook" with no guidance.
    """

    def test_all_blocking_policies_have_context_key(self):
        from lib.gates.definitions import GATE_CONFIGS

        missing = []
        for config in GATE_CONFIGS:
            for policy in config.policies:
                if policy.verdict not in ("allow",):
                    if not policy.context_key:
                        missing.append(
                            f"{config.name}: verdict={policy.verdict!r}, "
                            f"message_key={policy.message_key!r}, "
                            f"context_key={policy.context_key!r}"
                        )

        assert not missing, (
            "The following policies can block/warn but have no context_key. "
            "Agents see 'Blocked by hook' with no actionable guidance.\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


class TestEveryContextKeyResolvesToTemplate:
    """Every context_key referenced in a policy must exist in TemplateRegistry."""

    def test_all_context_keys_resolve(self):
        from lib.gates.definitions import GATE_CONFIGS

        registry = TemplateRegistry.instance()
        missing = []
        for config in GATE_CONFIGS:
            for policy in config.policies:
                if policy.context_key:
                    try:
                        registry.get_spec(policy.context_key)
                    except KeyError:
                        missing.append(
                            f"{config.name}: context_key={policy.context_key!r} "
                            f"not found in TemplateRegistry"
                        )

        assert not missing, "Context keys reference missing templates:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


class TestEveryContextKeyTemplateFileExists:
    """Every context_key's template file must exist on disk."""

    def test_all_template_files_exist(self):
        from lib.gates.definitions import GATE_CONFIGS

        registry = TemplateRegistry.instance()
        templates_dir = AOPS_CORE / "hooks" / "templates"
        missing = []
        for config in GATE_CONFIGS:
            for policy in config.policies:
                if policy.context_key:
                    try:
                        spec = registry.get_spec(policy.context_key)
                        template_path = templates_dir / spec.filename
                        if not template_path.exists():
                            missing.append(
                                f"{config.name}: {policy.context_key} -> "
                                f"{spec.filename} not found at {template_path}"
                            )
                    except KeyError:
                        pass  # Covered by TestEveryContextKeyResolvesToTemplate

        assert not missing, "Template files missing on disk:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


# ===========================================================================
# BEHAVIORAL: Every block/warn verdict at runtime has context_injection
# ===========================================================================


class TestStopBlockHasContextInjection:
    """Stop hook blocks must always produce non-empty context_injection.

    Tests each gate that can block Stop independently.
    """

    def test_handover_stop_block_has_context(self, router):
        """Handover gate blocking Stop must include context_injection."""
        state = SessionState.create("test-stop-ctx")
        state.gates["handover"].status = GateStatus.CLOSED

        ctx = HookContext(
            session_id="test-stop-ctx",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Handover gate should block Stop when closed"
        assert result.verdict != GateVerdict.ALLOW
        assert result.context_injection and len(result.context_injection) > 0, (
            f"Handover stop block has no context_injection. "
            f"Agent sees 'Blocked by hook' with no guidance. "
            f"verdict={result.verdict.value}, "
            f"system_message={result.system_message!r}, "
            f"context_injection={result.context_injection!r}"
        )

    def test_qa_stop_block_has_context(self, router):
        """QA gate blocking Stop must include context_injection."""
        state = SessionState.create("test-stop-ctx")
        state.close_gate("qa")
        # Provide temp_path so the qa.policy_context template can render
        state.gates["qa"].metrics["temp_path"] = "/tmp/qa-review.md"
        # Open handover so only QA fires
        state.gates["handover"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id="test-stop-ctx",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "QA gate should block Stop when closed"
        assert result.verdict != GateVerdict.ALLOW
        assert result.context_injection and len(result.context_injection) > 0, (
            f"QA stop block has no context_injection. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )

    def test_commit_stop_block_has_context(self, router, monkeypatch):
        """Commit gate blocking Stop must include context_injection."""
        state = SessionState.create("test-stop-ctx")
        # Open handover so only commit fires
        state.gates["handover"].status = GateStatus.OPEN

        # Mock has_uncommitted_work to return True
        monkeypatch.setattr(
            "lib.gates.custom_conditions.check_custom_condition",
            lambda name, ctx, state, ss: name == "has_uncommitted_work",
        )

        ctx = HookContext(
            session_id="test-stop-ctx",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Commit gate should block Stop with uncommitted work"
        assert result.verdict != GateVerdict.ALLOW
        assert result.context_injection and len(result.context_injection) > 0, (
            f"Commit stop block has no context_injection. "
            f"Agent sees 'Blocked by hook' with no guidance on what to commit. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )

    def test_commit_stop_warn_has_context(self, router, monkeypatch):
        """Commit gate warning Stop (unpushed commits) must include context_injection."""
        state = SessionState.create("test-stop-ctx")
        # Open handover so only commit fires
        state.gates["handover"].status = GateStatus.OPEN

        # Mock needs_commit_reminder to return True, has_uncommitted_work to False
        monkeypatch.setattr(
            "lib.gates.custom_conditions.check_custom_condition",
            lambda name, ctx, state, ss: name == "needs_commit_reminder",
        )

        ctx = HookContext(
            session_id="test-stop-ctx",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Commit gate should warn Stop with unpushed commits"
        assert result.verdict == GateVerdict.WARN
        assert result.context_injection and len(result.context_injection) > 0, (
            f"Commit stop warn has no context_injection. "
            f"Agent sees 'Blocked by hook' with no guidance on what to push. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )


class TestPreToolUseBlockHasContextInjection:
    """PreToolUse blocks must always produce non-empty context_injection."""

    def test_hydration_block_has_context(self, router):
        """Hydration gate blocking a write tool must include context_injection."""
        state = SessionState.create("test-ptu-ctx")
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/hydration.md"

        ctx = HookContext(
            session_id="test-ptu-ctx",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict != GateVerdict.ALLOW
        assert result.context_injection and len(result.context_injection) > 0, (
            f"Hydration block has no context_injection. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )

    def test_custodiet_block_has_context(self, router):
        """Custodiet gate blocking at threshold must include context_injection."""
        state = SessionState.create("test-ptu-ctx")
        state.gates["hydration"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 75

        ctx = HookContext(
            session_id="test-ptu-ctx",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "echo hello"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict != GateVerdict.ALLOW
        assert result.context_injection and len(result.context_injection) > 0, (
            f"Custodiet block has no context_injection. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )
