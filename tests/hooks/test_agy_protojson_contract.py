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

from tests.hooks.agy_accept_contract import PreToolHookResult, is_accepted_by_agy
from tests.hooks.gate_helpers import run_router_agy

# NOTE (aops_4c2949d9): the former test_agy_deny_uses_top_level_allow_tool and
# test_agy_deny_survives_protojson_strict_roundtrip seeded a DENY via the
# retired turn-based `rbg` PreToolUse gate to exercise the agy protojson
# DENY-shape contract (top-level allowTool=false + denyReason). That gate —
# and PreToolUse gating generally — is deleted entirely (nothing fires
# mid-session on any surface any more; GATE_CONFIGS carries no PreToolUse
# policy at all). The scenario these tests drove is now structurally
# unreachable through the real router: no gate can produce a PreToolUse DENY
# any more, on any client, so there is nothing left to seed. Removed rather
# than kept as a synthetic/unreachable reproduction — the ALLOW and
# PostToolUse round-trip tests below remain live coverage of the same
# protojson accept-contract for the events that DO still fire.


def test_agy_allow_survives_protojson_strict_roundtrip():
    """A PreToolUse ALLOW must be accepted AND parse as an explicit allow.

    Two distinct checks, because acceptance alone is the blindspot that shipped
    aops-1e68682a:

      1. UNKNOWN-FIELD axis (``is_accepted_by_agy``): no Claude/Gemini-schema
         field leaks. This is necessary but NOT sufficient — the buggy empty
         object ``{}`` passes it trivially.
      2. SEMANTIC axis: the emitted dict, parsed as ``PreToolHookResult`` (the
         message agy unmarshals stdout into), must yield ``allowTool == True``.
         agy's protojson defaults an OMITTED bool to ``false``, so a ``{}`` allow
         is read as ``allowTool=false, denyReason=""`` — a DENY with empty reason
         that blocked EVERY tool call on the agy client (live: session 22b4caa2).

    The router must emit ``{"allowTool": true}`` end-to-end through the real
    ``--client agy`` subprocess path, not ``{}``.
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
        f"output on unknown field(s): {offending}. stderr: {stderr}"
    )
    # SEMANTIC roundtrip: the allow must read back as allowTool=True, not the
    # protojson omitted-bool default. This is the assertion the old test lacked.
    parsed = PreToolHookResult.model_validate(output)
    assert parsed.allowTool is True, (
        f"PreToolUse ALLOW must parse as allowTool=True (agy protojson defaults an "
        f"omitted bool to false → DENY). Got {output!r}. stderr: {stderr}"
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
