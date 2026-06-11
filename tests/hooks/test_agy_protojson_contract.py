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

LIFECYCLE (post-fix — output_for_agy landed, aops-d27d55a0; deny-shape repaired
aops-891c0e36)
------------------------------------------------------------------------------
``output_for_agy()`` now emits ``*Result`` protojson, so the guards below are
asserts (flipped from ``xfail(strict=True)`` per the aops-d27d55a0 brief):

  * ``test_agy_deny_uses_top_level_allow_tool`` — the INVERSION of the original
    silent-drop reproduction: the enforcer DENY is now expressed structurally
    via the TOP-LEVEL ``allowTool=false`` + ``denyReason`` fields of
    ``PreToolHookResult`` (NOT nested under ``permissionOverrides``, which is a
    *repeated* per-tool override list — wrong-nesting it there made live agy's
    protojson parser reject with ``unexpected token {`` and silently drop the
    DENY: aops-891c0e36).
  * the ``*_survives_protojson_strict_roundtrip`` guards assert the PreToolUse
    deny/allow and PostToolUse outputs are accepted by the agy protojson
    accept-contract.

SCOPE OF THE GREEN — READ THIS BEFORE TRUSTING IT
-------------------------------------------------
These asserts verify conformance to the **offline** accept-contract in
``agy_accept_contract.py`` — a strict Pydantic model transcribed from the
``exa.hooks_pb`` binary descriptor (epic aops-2dc18411). They faithfully cover
the UNKNOWN-FIELD axis (the exact failure mode 4c73f02a tripped: the field NAMES
agy's ``*Result`` defines), because field names come from the descriptor. They
do **NOT** prove the live agy harness accepts the output: the descriptor could
be wrong, and protojson is additionally strict about types/oneofs/enum-values
this model does not pin. Live-harness acceptance ("deny actually blocks, Stop
respected on real agy") is UNVERIFIED here and is the downstream build+verify
task **aops-7fa86b45** — green here is necessary, not sufficient. (Live agy could
not be exercised in this session: the binary is present but not logged into
Antigravity, so it hangs on an interactive OAuth flow.)

STILL DEFERRED (blocked on live-agy enum discovery, aops-939b6c3a): the hard
stop-block enum STRINGS — Stop ``decision`` and PostInvocation
``terminationBehavior`` — are not yet emitted (a guessed enum is silently
discarded by agy). ``output_for_agy()`` delivers the Stop/PostInvocation
*advisory* via ``injectSteps`` / ``reason`` but does NOT force-continue. The
unit-level deferral guard lives in ``test_output_for_agy.py``.
"""

from __future__ import annotations

from lib.gate_types import GateStatus
from lib.session_state import SessionState

from tests.hooks.agy_accept_contract import is_accepted_by_agy
from tests.hooks.gate_helpers import run_router_agy


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


def test_agy_deny_uses_top_level_allow_tool(monkeypatch, tmp_path):
    """Post-fix regression: a canonical enforcer DENY uses TOP-LEVEL ``allowTool``.

    This test is the INVERSION of the original silent-drop reproduction (pre-fix
    it asserted ``--client agy`` emitted Claude-schema JSON the protojson harness
    rejected on ``systemMessage``). With ``output_for_agy()`` landed AND the
    deny-shape repair from aops-891c0e36 in place, the enforcer DENY is now
    expressed STRUCTURALLY via the TOP-LEVEL ``allowTool=false`` + ``denyReason``
    fields of ``PreToolHookResult`` — NOT nested under ``permissionOverrides``,
    which is a repeated field that protojson rejected with
    ``unexpected token {`` and which silently dropped every live agy DENY.
    """
    sid = "agy-contract-deny-repro"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy(_deny_input(sid), "PreToolUse")

    # The deny is structural: top-level allowTool=false blocks the tool with no
    # enum string and no nesting under permissionOverrides.
    assert output.get("allowTool") is False, (
        f"Expected a structural DENY via top-level allowTool=false; "
        f"got {output!r}. stderr: {stderr}"
    )
    assert output.get("denyReason"), (
        f"Expected a denyReason on the structural DENY; got {output!r}. stderr: {stderr}"
    )
    # MUST NOT nest under permissionOverrides (the pre-fix shape that live agy
    # rejected with "syntax error … unexpected token {").
    assert "permissionOverrides" not in output, (
        f"Pre-fix wrong-nesting under permissionOverrides leaked back into agy "
        f"output (protojson rejects this with unexpected-token): {output!r}"
    )
    # None of the Claude/Gemini-schema fields that protojson rejects may leak.
    for forbidden in ("decision", "metadata", "systemMessage", "hookSpecificOutput"):
        assert forbidden not in output, (
            f"Claude/Gemini-schema field {forbidden!r} leaked into agy output "
            f"(protojson would reject on it): {output!r}"
        )
    accepted, offending = is_accepted_by_agy(output, "PreToolUse")
    assert accepted, (
        f"agy accept-contract (offline; live agy is aops-7fa86b45) rejects the DENY "
        f"output on unknown field(s): {offending}"
    )


def test_agy_deny_survives_protojson_strict_roundtrip(monkeypatch, tmp_path):
    """A canonical enforcer DENY must survive the agy protojson accept-contract.

    This is the consumer-side acceptance test that would have failed the instant
    4c73f02a landed. A DENY is expressed protojson-side via the TOP-LEVEL
    ``allowTool=false`` + ``denyReason`` fields (no enum string required), so
    this is satisfiable ahead of the ``decision`` enum discovery. Flipped from
    xfail(strict) to a live assert when ``output_for_agy()`` landed
    (aops-d27d55a0); deny-shape repaired aops-891c0e36.
    """
    sid = "agy-contract-deny-guard"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy(_deny_input(sid), "PreToolUse")
    # Post-fix the deny is structural (top-level allowTool=false), not a
    # ``decision`` enum and not nested under permissionOverrides.
    assert output.get("allowTool") is False, (
        f"setup: expected a structural DENY (top-level allowTool=false), got {output!r}"
    )
    assert "permissionOverrides" not in output, (
        f"setup: deny must not be wrong-nested under permissionOverrides "
        f"(the protojson-rejected pre-fix shape), got {output!r}"
    )

    accepted, offending = is_accepted_by_agy(output, "PreToolUse")
    assert accepted, (
        f"agy accept-contract (offline; live agy is aops-7fa86b45) rejects the DENY "
        f"output on unknown field(s): {offending}"
    )


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
    assert accepted, (
        f"agy accept-contract (offline; live agy is aops-7fa86b45) rejects the ALLOW "
        f"output on unknown field(s): {offending}"
    )


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
        f"agy accept-contract (offline; live agy is aops-7fa86b45) rejects the "
        f"PostToolUse output on unknown field(s): {offending}"
    )
