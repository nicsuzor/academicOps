"""RBG R2 regression fixture — universal-claim docstring, single-client parametrisation.

This file is an input fixture for dogfood-testing RBG's R2 (class-instance
parameterisation) inference rule. It deliberately contains the R2 violation
pattern: a docstring that makes a universal claim over all router clients, but
tests only parametrised against the ``agy`` client.

EXPECTED RBG VERDICT when reviewed against the updated rbg.md: REVISE, citing R2.

Gold-standard worked case: PR #1802 ``tests/hooks/test_ida_denyreason_1798.py``.
That file's docstring claims "no agy PreToolUse output for a read tool may ever
carry IDA content" — a universal claim over all clients — but every test calls
``run_router_agy`` only, leaving the class {claude, crew, gemini, ...} uncovered.

The fix (follow-up task) is to parametrise the tests over all client types so
that the invariant is verified for the full class the claim asserts over.
"""

from __future__ import annotations


# Synthetic stand-in for the real helper; in the real test suite this
# would be imported from tests.hooks.gate_helpers.
def _run_router(client: str, payload: dict, event: str) -> tuple[dict, str]:
    raise NotImplementedError("fixture stub — not for direct execution")


# ── R2 VIOLATION: universal claim, single-client parametrisation ──────────────


def test_read_tool_pretooluse_never_emits_deny_reason(monkeypatch, tmp_path):
    """A read-only tool PreToolUse MUST NOT emit denyReason on any client.

    This invariant is absolute: no router client may ever return a denyReason
    for a PreToolUse on a read-only tool. The gate pipeline must be unreachable
    for read tools across all client implementations (agy, claude, crew, gemini).

    R2 VIOLATION (detected by updated rbg.md): the docstring claims the class
    {all router clients} but the test only calls ``_run_router("agy", ...)``.
    The remaining class members are untested.
    """
    payload = {"conversationId": "test-sid", "toolCall": {"name": "grep_search", "args": {}}}

    # BUG: only "agy" is tested; the universal claim requires all clients.
    output, _stderr = _run_router("agy", payload, "PreToolUse")

    assert "denyReason" not in output, f"Read tool must never be denied: {output!r}"
