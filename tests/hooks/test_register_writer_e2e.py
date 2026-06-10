#!/usr/bin/env python3
"""End-to-end proof of the AOPS_SESSION_REGISTER *writer* (task aops-75a0f4da).

PR #1471 shipped the register-scaling READER + engine enforcement, but nothing
in the repo *wrote* AOPS_SESSION_REGISTER, so get_session_register() always
resolved to 'working' and the capture/personal register was unreachable — the
feature was dormant. This suite proves the activation half end-to-end:

    polecat launcher writer            in-container reader + engine
    (cli._apply_gate_env)   ─env─▶     (gate_config + GenericGate)

A single call to the production writer ``cli._apply_gate_env(env, session_cfg)``
stamps the whole posture (gate modes + AOPS_SESSION_REGISTER) onto an env dict —
exactly as it does before forwarding into the container. We load that env into
os.environ and drive the REAL gate engine with REAL GateConfig definitions,
proving that a capture-register session actually drops the review-grade gates
(enforcer / ida / qa) while the safety gates (sentinel / handover) still fire.

This is the writer-driven companion to test_gate_hygiene_engine.py, which proves
the same engine behaviour from a hand-set env var. Here the env var is produced
by the writer under test, closing the loop the task targets.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for sub in ("aops-core", "polecat"):
    p = str(REPO_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import cli  # polecat/cli.py — the launcher that owns the writer
from hooks.schemas import HookContext
from lib.gate_types import GateStatus
from lib.gates.definitions import GATE_CONFIGS
from lib.gates.engine import GenericGate
from lib.polecat_config import GatesConfig, SessionDefaults
from lib.session_state import SessionState

_CONFIGS = {c.name: c for c in GATE_CONFIGS}

# Gate modes used for every session_cfg below. enforcer/qa/ida are set to a
# mode that WOULD fire (block/warn) so that suppression is the only thing that
# can stop them — a no-op mode would make the capture assertions vacuous.
_FIRING_GATES = GatesConfig(
    handover="block",
    qa="warn",
    enforcer="block",
    hydration="off",
    ida="warn",
    enforcer_threshold=50,
)


def _session_cfg(register: str | None) -> SessionDefaults:
    """A resolved session config with the given register (None = unset)."""
    return SessionDefaults(
        hooks_enabled=True,
        claude_model="claude-sonnet-4-6",
        gemini_model="gemini-3.1-pro-preview",
        antigravity_model="agy",
        debug=False,
        gates=_FIRING_GATES,
        register=register,
    )


def _write_posture_to_env(monkeypatch, register: str | None) -> dict[str, str]:
    """Run the production WRITER, then load its output into os.environ.

    Returns the env dict the writer produced so callers can assert on it.
    Anything the writer omits (e.g. AOPS_SESSION_REGISTER when register is
    unset) is explicitly cleared from os.environ so a stale value can't leak in.
    """
    env: dict[str, str] = {}
    cli._apply_gate_env(env, _session_cfg(register))  # the writer under test
    monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


def _ctx(tool_name, hook_event="PreToolUse", tool_input=None):
    return HookContext(
        session_id="register-writer-e2e",
        client_type="claude",
        trace_id=None,
        hook_event=hook_event,
        tool_name=tool_name,
        tool_input=tool_input or {},
        is_subagent=False,
        raw_input={},
    )


def _verdict(result):
    return None if result is None else getattr(result.verdict, "value", result.verdict)


# ---------------------------------------------------------------------------
# The writer itself
# ---------------------------------------------------------------------------


def test_writer_stamps_register_when_set(monkeypatch):
    """register set ⇒ the writer stamps AOPS_SESSION_REGISTER into the env."""
    env = _write_posture_to_env(monkeypatch, "capture")
    assert env["AOPS_SESSION_REGISTER"] == "capture"


def test_writer_omits_register_when_unset(monkeypatch):
    """register unset ⇒ the writer does NOT stamp the var (reader → 'working').

    Fail-closed contract: an absent var can only ever buy MORE ceremony.
    """
    env = _write_posture_to_env(monkeypatch, None)
    assert "AOPS_SESSION_REGISTER" not in env


def test_writer_does_not_inherit_launcher_register(monkeypatch):
    """register unset ⇒ the writer POPS any inherited AOPS_SESSION_REGISTER.

    A polecat run must not inherit the launching session's register; its stakes
    are its own. The writer pops a pre-existing value so it cannot leak in.
    """
    env = {"AOPS_SESSION_REGISTER": "capture"}  # simulate inherited value
    cli._apply_gate_env(env, _session_cfg(None))
    assert "AOPS_SESSION_REGISTER" not in env


# ---------------------------------------------------------------------------
# Writer → engine: review-grade gates DROP in the capture register
# ---------------------------------------------------------------------------


def _enforcer_overdue_state():
    state = SessionState.create("register-writer-e2e", client_type="claude")
    state.main_agent.current_task = "task-x"
    state.gates["enforcer"].status = GateStatus.OPEN
    state.gates["enforcer"].ops_since_open = 999
    return state


def test_capture_register_drops_enforcer_via_writer(monkeypatch):
    """capture register (written by the launcher) suppresses the enforcer block."""
    _write_posture_to_env(monkeypatch, "capture")
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("Write"), _enforcer_overdue_state())
    assert _verdict(result) != "deny"


def test_working_register_keeps_enforcer_via_writer(monkeypatch):
    """Control: unset register (writer omits var) ⇒ enforcer block fires."""
    _write_posture_to_env(monkeypatch, None)
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("Write"), _enforcer_overdue_state())
    assert _verdict(result) == "deny"


def _stop_state_with_gate_closed(gate_name, *, did_work=False):
    state = SessionState.create("register-writer-e2e", client_type="claude")
    state.main_agent.current_task = "task-x"
    # The Stop policies match only when the gate is CLOSED (armed but unmet).
    state.gates[gate_name].status = GateStatus.CLOSED
    state.session_did_work = did_work
    return state


def test_capture_register_drops_ida_via_writer(monkeypatch):
    """capture register suppresses the ida honesty reminder on Stop."""
    _write_posture_to_env(monkeypatch, "capture")
    gate = GenericGate(_CONFIGS["ida"])
    result = gate.on_stop(_ctx(None, hook_event="Stop"), _stop_state_with_gate_closed("ida"))
    assert _verdict(result) not in ("deny", "warn")


def test_working_register_keeps_ida_via_writer(monkeypatch):
    """Control: unset register ⇒ the ida reminder fires on Stop."""
    _write_posture_to_env(monkeypatch, None)
    gate = GenericGate(_CONFIGS["ida"])
    result = gate.on_stop(_ctx(None, hook_event="Stop"), _stop_state_with_gate_closed("ida"))
    assert _verdict(result) == "warn"


def test_capture_register_drops_qa_via_writer(monkeypatch):
    """capture register suppresses the qa verification reminder on Stop."""
    _write_posture_to_env(monkeypatch, "capture")
    gate = GenericGate(_CONFIGS["qa"])
    result = gate.on_stop(_ctx(None, hook_event="Stop"), _stop_state_with_gate_closed("qa"))
    assert _verdict(result) not in ("deny", "warn")


def test_working_register_keeps_qa_via_writer(monkeypatch):
    """Control: unset register ⇒ the qa reminder fires on Stop."""
    _write_posture_to_env(monkeypatch, None)
    gate = GenericGate(_CONFIGS["qa"])
    result = gate.on_stop(_ctx(None, hook_event="Stop"), _stop_state_with_gate_closed("qa"))
    assert _verdict(result) == "warn"


# ---------------------------------------------------------------------------
# Writer → engine: safety gates STILL fire in the capture register
# ---------------------------------------------------------------------------


def test_capture_register_keeps_sentinel_via_writer(monkeypatch):
    """register-scaling drops ceremony, NOT safety: sentinel still blocks."""
    _write_posture_to_env(monkeypatch, "capture")
    monkeypatch.setenv("SENTINEL_GATE_MODE", "block")  # not part of GatesConfig
    gate = GenericGate(_CONFIGS["sentinel"])
    result = gate.check(
        _ctx("Bash", tool_input={"command": "rm -rf ~/.claude/plugins"}),
        SessionState.create("register-writer-e2e"),
    )
    assert _verdict(result) == "deny"


def test_capture_register_keeps_handover_via_writer(monkeypatch):
    """The handover (work-loss) gate still fires in the capture register."""
    _write_posture_to_env(monkeypatch, "capture")
    gate = GenericGate(_CONFIGS["handover"])
    result = gate.on_stop(
        _ctx(None, hook_event="Stop"),
        _stop_state_with_gate_closed("handover", did_work=True),
    )
    assert _verdict(result) == "deny"
