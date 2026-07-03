"""Pause detection & Stop-gate bypass (successor to PR #1998).

A session that yields while it waits on backgrounded work (a subagent/workflow/
monitor, or a scheduled cron) is not claiming "done", so its exit gates
(rbg-review/qa/handover/ida) should not fire. `normalize_input` derives
`is_paused` from the Claude Code 2.1.145+ ``background_tasks`` / ``session_crons``
arrays; `_dispatch_gates` suppresses Stop/SessionEnd gates when it is True.

Ground truth (enumerated from real captured hook payloads — 8107 background_tasks
items across 8650 Stop payloads): observed ``type`` values were
{shell, subagent, workflow} and the only observed ``status`` was "running"
(Claude Code prunes terminal tasks before emitting the array). agy/Gemini carry
NEITHER field (0/4238 payloads). The allowlists in router.py
(``_WAKING_TASK_TYPES`` / ``_ACTIVE_TASK_STATUSES``) make the gate fail SAFE
(fires) on anything unrecognized, rather than silently disarming a chokepoint.
"""

import sys
from pathlib import Path

import pytest

# Setup path to include aops-core
AOPS_CORE_DIR = Path(__file__).parent.parent.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter  # noqa: E402

from tests.hooks.gate_helpers import (  # noqa: E402
    make_gate_trigger_context,
    make_gate_trigger_state,
)


@pytest.fixture
def router(monkeypatch):
    # Mock get_session_data to avoid reading shared PID session map during xdist tests
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _stop_ctx(router, *, background_tasks=None, session_crons=None):
    """Normalize a Claude Stop payload, optionally carrying the pause arrays."""
    raw = {"session_id": "test-session", "hook_event_name": "Stop"}
    if background_tasks is not None:
        raw["background_tasks"] = background_tasks
    if session_crons is not None:
        raw["session_crons"] = session_crons
    return router.normalize_input(raw, client_type="claude")


class TestPauseDetectionTruthTable:
    """`is_paused` derivation over the observed and adversarial payload shapes."""

    def test_empty_arrays_not_paused(self, router):
        ctx = _stop_ctx(router, background_tasks=[], session_crons=[])
        assert ctx.is_paused is False

    def test_fields_absent_not_paused(self, router):
        # Older Claude Code and agy/Gemini carry neither field -> safe no-op.
        ctx = _stop_ctx(router)
        assert ctx.is_paused is False
        assert ctx.background_tasks == []
        assert ctx.session_crons == []

    def test_shell_only_not_paused(self, router):
        # Shell tasks run inline; they do NOT wake the session (core design intent).
        ctx = _stop_ctx(
            router,
            background_tasks=[
                {"id": "b1", "type": "shell", "status": "running", "command": "sleep 1"}
            ],
        )
        assert ctx.is_paused is False

    def test_running_subagent_paused(self, router):
        ctx = _stop_ctx(
            router,
            background_tasks=[
                {"id": "a1", "type": "subagent", "status": "running", "agent_type": "x"}
            ],
        )
        assert ctx.is_paused is True

    def test_running_workflow_paused(self, router):
        ctx = _stop_ctx(
            router,
            background_tasks=[{"id": "w1", "type": "workflow", "status": "running", "name": "wf"}],
        )
        assert ctx.is_paused is True

    def test_mixed_shell_and_subagent_paused(self, router):
        ctx = _stop_ctx(
            router,
            background_tasks=[
                {"id": "b1", "type": "shell", "status": "running"},
                {"id": "a1", "type": "subagent", "status": "running"},
            ],
        )
        assert ctx.is_paused is True

    def test_session_cron_paused(self, router):
        ctx = _stop_ctx(
            router,
            session_crons=[
                {"id": "c1", "schedule": "18 0 * * *", "recurring": False, "prompt": "wake"}
            ],
        )
        assert ctx.is_paused is True


class TestPauseDetectionHardening:
    """The findings the successor PR fixes over the original #1998."""

    def test_completed_subagent_not_paused(self, router):
        # Status-blindness fix (pauli HIGH / marsha case 6): a terminal task
        # lingering in the array must NOT suppress the exit gates indefinitely.
        ctx = _stop_ctx(
            router,
            background_tasks=[
                {"id": "a1", "type": "subagent", "status": "completed", "agent_type": "x"}
            ],
        )
        assert ctx.is_paused is False

    def test_failed_subagent_not_paused(self, router):
        ctx = _stop_ctx(
            router,
            background_tasks=[{"id": "a1", "type": "subagent", "status": "failed"}],
        )
        assert ctx.is_paused is False

    def test_non_dict_items_do_not_crash_and_do_not_pause(self, router):
        # marsha case 7a: a non-dict item used to raise AttributeError and crash
        # the entire Stop hook invocation. It must be skipped, not pause.
        ctx = _stop_ctx(router, background_tasks=["oops", None, 42])
        assert ctx.is_paused is False

    def test_empty_dict_item_not_paused(self, router):
        # marsha case 7b: a degenerate {} item (no type/status) must not pause.
        ctx = _stop_ctx(router, background_tasks=[{}])
        assert ctx.is_paused is False

    def test_unknown_type_not_paused(self, router):
        # Denylist-of-one -> allowlist: an unrecognized future `type` fails SAFE
        # (gate fires) rather than silently suppressing a compliance chokepoint.
        ctx = _stop_ctx(
            router,
            background_tasks=[{"id": "x1", "type": "telemetry", "status": "running"}],
        )
        assert ctx.is_paused is False

    def test_non_list_background_tasks_not_paused(self, router):
        # A malformed non-list value must not crash nor pause.
        ctx = _stop_ctx(router, background_tasks={"unexpected": "shape"})
        assert ctx.is_paused is False


class TestPausedStopGateBypass:
    """`_dispatch_gates` suppresses exit gates only while paused."""

    def test_not_paused_stop_still_fires(self, router):
        state = make_gate_trigger_state("handover")
        ctx = make_gate_trigger_context("handover")  # Stop, is_paused defaults False
        assert ctx.is_paused is False
        assert router._dispatch_gates(ctx, state) is not None

    def test_paused_stop_bypasses_gates(self, router):
        state = make_gate_trigger_state("handover")
        ctx = make_gate_trigger_context("handover").model_copy(update={"is_paused": True})
        assert router._dispatch_gates(ctx, state) is None

    def test_paused_sessionend_bypasses_gates(self, router):
        state = make_gate_trigger_state("handover")
        ctx = make_gate_trigger_context("handover").model_copy(
            update={"hook_event": "SessionEnd", "is_paused": True}
        )
        assert router._dispatch_gates(ctx, state) is None
