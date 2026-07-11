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
from lib.gate_model import GateVerdict
from lib.gates.registry import GateRegistry
from lib.hook_context import HookContext
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
def _reinit_gates_fixture():
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
    All block and warn policies (QA, handover, Ida) use context_key so the
    advisory reaches the agent via the warn+ctx_inj → decision=block upgrade
    path in output_for_claude(). message_key is a separate, short user-facing
    summary routed to stopReason/systemMessage only.
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

    exit_reflection (aops_4c2949d9) consolidates the former rbg-review + qa +
    handover trio into one Stop gate; both tiers are exercised here.
    """

    def test_exit_reflection_full_tier_stop_block_has_context(self, router, monkeypatch):
        """exit_reflection FULL tier blocking Stop in block mode must include
        context_injection."""
        from tests.hooks.gate_helpers import make_gate_trigger_state, set_gate_modes

        set_gate_modes(monkeypatch, exit_reflection="block")
        state = make_gate_trigger_state("exit_reflection")  # task-bound, did work

        ctx = HookContext(
            session_id="test-gate-mode",
            client_type="claude",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "exit_reflection FULL tier should block Stop when closed"
        assert result.verdict == GateVerdict.DENY
        assert result.context_injection and len(result.context_injection) > 0, (
            f"exit_reflection FULL-tier stop block has no context_injection. "
            f"Agent sees 'Blocked by hook' with no guidance. "
            f"verdict={result.verdict.value}, "
            f"system_message={result.system_message!r}, "
            f"context_injection={result.context_injection!r}"
        )

    def test_exit_reflection_lite_tier_stop_warn_has_context(self, router, monkeypatch):
        """exit_reflection LITE tier (no bound task) warning at Stop must
        include context_injection too — the reminder IS the context."""
        from tests.hooks.gate_helpers import make_gate_trigger_state, set_gate_modes

        set_gate_modes(monkeypatch, exit_reflection="block")
        state = make_gate_trigger_state("exit_reflection", full_tier=False)

        ctx = HookContext(
            session_id="test-gate-mode",
            client_type="claude",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "exit_reflection LITE tier should warn at Stop when closed"
        assert result.verdict == GateVerdict.WARN
        assert result.context_injection and len(result.context_injection) > 0, (
            f"exit_reflection LITE-tier stop warn has no context_injection. "
            f"verdict={result.verdict.value}, "
            f"context_injection={result.context_injection!r}"
        )


class TestSubagentStartContextInjectionDoesNotCrash:
    """End-to-end regression: a SubagentStart-triggered context_injection must
    not crash output_for_claude.

    Formerly reproduced via the retired `rbg` gate's SubagentStart reset
    trigger (aops_4c2949d9 — the whole gate is deleted). The router-level
    invariant under test — Claude has no additionalContext channel on
    SubagentStart, so the advisory must be DROPPED, never raised — is generic
    to the engine, not gate-specific, so it is reproduced here with a
    synthetic gate (mirrors test_gate_hygiene_engine.py's never-block probe)
    rather than depending on any one gate's trigger shape.
    """

    def test_subagent_start_context_injection_does_not_crash_router(self, router, monkeypatch):
        from lib.gate_types import GateCondition, GateConfig, GateTransition, GateTrigger
        from lib.gates.engine import GenericGate
        from lib.gates.registry import GateRegistry

        probe = GateConfig(
            name="ws7_subagent_start_ctx_probe",
            description="test-only gate that emits context_injection on SubagentStart",
            triggers=[
                GateTrigger(
                    condition=GateCondition(hook_event="SubagentStart"),
                    transition=GateTransition(context_template="probe context injection"),
                )
            ],
        )
        GateRegistry.register(GenericGate(probe))
        try:
            state = SessionState.create("test-subagent-start", client_type="claude")

            ctx = HookContext(
                session_id="test-subagent-start",
                client_type="claude",
                hook_event="SubagentStart",
                subagent_type="aops-core:rbg",
                tool_name=None,
                tool_input={},
            )

            result = router._dispatch_gates(ctx, state)

            assert result is not None, "probe trigger should fire on SubagentStart"
            assert result.context_injection, "expected the probe context_injection"

            canonical = router._gate_result_to_canonical(result)
            # Must NOT raise — the advisory is dropped (no HSO channel on SubagentStart).
            output = router.output_for_claude(canonical, "SubagentStart")
            payload = output.model_dump_json(exclude_none=True)
            assert "hookSpecificOutput" not in payload
            assert "additionalContext" not in payload
        finally:
            GateRegistry._gates.pop(probe.name, None)
