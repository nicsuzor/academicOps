"""Consumer-side per-client acceptance test for ``--client agy``.

THE GAP THIS CLOSES
-------------------
Commit ``4c73f02a`` ("update agy build", 2026-06-03) routed ``--client agy``
through ``output_for_gemini`` on the assumption that agy speaks Gemini's hook
dialect. It does not: the antigravity harness parses hook stdout as **protojson**
against ``exa.hooks_pb.*Result`` and rejects on the first unknown field, so every
agy hook verdict — including enforcer DENYs — was silently discarded while the
router exited 0 and its own jsonl logged "healthy". CI never caught it because
there was **zero** consumer-side coverage of the agy accept-contract: the
schema-conformance tests are producer-only (claude+gemini), and
``test_subprocess_format.py`` asserts ``"decision" in output`` — the *opposite*
of what agy needs. See task ``aops-27004ffd``; fix epic ``aops-2dc18411``.

This module runs canonical router outputs through the real ``--client agy``
subprocess path (``run_router_agy``) and checks them against the strict
protojson accept-contract in ``agy_accept_contract.py``.

LIFECYCLE (read before editing)
-------------------------------
The behavioural fix — ``output_for_agy()`` emitting ``*Result`` protojson — is
tracked by ``aops-d27d55a0`` and is blocked on live-agy enum discovery
(``aops-939b6c3a``). Until it lands:

  * ``test_current_agy_deny_output_is_rejected_by_harness_contract`` passes — it
    is the deterministic in-CI reproduction of the silent-drop bug (the proof
    that previously lived only in an auto-nuked in-container ``cli.log``).
  * the ``*_survives_protojson_strict_roundtrip`` guards are ``xfail(strict=True)``
    — they encode the contract the fix must satisfy and FAIL today exactly as
    the bug predicts.

When ``output_for_agy()`` lands, the roundtrip guards will XPASS (tripping
strict-xfail) and the reproduction test will fail — both deliberately, to force
whoever lands the fix to update this file and convert the guards into live
regression tests. Do not delete the guards to make them green; flip them.
"""

from __future__ import annotations

import pytest
from lib.gate_types import GateStatus
from lib.session_state import SessionState

from tests.hooks.agy_accept_contract import is_accepted_by_agy
from tests.hooks.gate_helpers import run_router_agy

# Tie every xfail to the implementation task so the reason is greppable.
_FIX_TASK = "aops-d27d55a0: output_for_agy() not implemented — agy folded into the Claude-schema gemini path by 4c73f02a"


def _seed_enforcer_deny(monkeypatch, state_dir, session_id: str) -> None:
    """Seed on-disk session state so a PreToolUse on `session_id` DENYs.

    The subprocess router loads this state by session id; an enforcer gate held
    OPEN and parked above its tool-call threshold produces a canonical
    compliance DENY — the safety-critical verdict the agy harness silently drops.
    """
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", "50")
    state = SessionState.create(session_id, client_type="agy")
    state.gates["enforcer"].status = GateStatus.OPEN
    state.gates["enforcer"].ops_since_open = 100
    state.save()


def _deny_input(session_id: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m x"},
    }


def test_current_agy_deny_output_is_rejected_by_harness_contract(monkeypatch, tmp_path):
    """Deterministic in-CI reproduction of the silent-drop regression.

    A canonical enforcer DENY routed through ``--client agy`` today emits
    Claude-schema JSON; the agy protojson harness rejects it on the first
    unknown field (``systemMessage``), so the deny never blocks. This test
    encodes that failure so it cannot regress un-noticed again.

    NOTE: this assertion inverts once ``output_for_agy()`` lands — see the module
    lifecycle docstring.
    """
    sid = "agy-contract-deny-repro"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy(_deny_input(sid), "PreToolUse")

    assert output.get("decision") == "deny", (
        f"Expected a canonical enforcer DENY to exercise the contract; "
        f"got {output!r}. stderr: {stderr}"
    )
    accepted, offending = is_accepted_by_agy(output, "PreToolUse")
    assert not accepted, (
        "Regression alert: --client agy now emits output the agy protojson "
        "harness accepts. output_for_agy() may have landed — convert the "
        "xfail roundtrip guards in this module into live regression tests and "
        "update this reproduction test."
    )
    assert "systemMessage" in offending, (
        f"Expected the Claude-schema 'systemMessage' field to be the protojson "
        f"rejection point (matching the live cli.log error); offending={offending!r}"
    )


@pytest.mark.xfail(strict=True, reason=_FIX_TASK)
def test_agy_deny_survives_protojson_strict_roundtrip(monkeypatch, tmp_path):
    """A canonical enforcer DENY must survive the agy protojson accept-contract.

    This is the consumer-side acceptance test that would have failed the instant
    4c73f02a landed. A DENY is expressed protojson-side via
    ``permissionOverrides.allowTool=false`` (no enum string required), so this is
    satisfiable ahead of the ``decision`` enum discovery.
    """
    sid = "agy-contract-deny-guard"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy(_deny_input(sid), "PreToolUse")
    assert output.get("decision") == "deny", f"setup: expected DENY, got {output!r}"

    accepted, offending = is_accepted_by_agy(output, "PreToolUse")
    assert accepted, f"agy harness would reject the DENY output on unknown field(s): {offending}"


@pytest.mark.xfail(strict=True, reason=_FIX_TASK)
def test_agy_allow_survives_protojson_strict_roundtrip():
    """A PreToolUse ALLOW must survive the agy protojson accept-contract.

    Allow is the empty ``PreToolHookResult`` ``{}``; the router currently emits
    ``{"decision":"allow","metadata":{}}`` which protojson rejects on ``metadata``.
    """
    output, stderr = run_router_agy(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "agy-contract-allow-guard",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/hostname"},
        },
        "PreToolUse",
    )
    accepted, offending = is_accepted_by_agy(output, "PreToolUse")
    assert accepted, f"agy harness would reject the ALLOW output on unknown field(s): {offending}"


@pytest.mark.xfail(strict=True, reason=_FIX_TASK)
def test_agy_posttool_survives_protojson_strict_roundtrip():
    """A PostToolUse result must survive the agy protojson accept-contract.

    ``PostToolHookResult`` is the empty object ``{}``; the router currently emits
    ``{"decision":"allow","metadata":{}}`` which protojson rejects on ``decision``
    (the verbatim cli.log error in aops-27004ffd).
    """
    output, stderr = run_router_agy(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "agy-contract-posttool-guard",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/hostname"},
        },
        "PostToolUse",
    )
    accepted, offending = is_accepted_by_agy(output, "PostToolUse")
    assert accepted, (
        f"agy harness would reject the PostToolUse output on unknown field(s): {offending}"
    )
