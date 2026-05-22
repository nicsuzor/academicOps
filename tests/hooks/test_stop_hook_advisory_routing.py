"""Regression coverage for Stop-hook RBG advisory routing (aops-d10e7db6).

The Stop hook composes an RBG advisory wrapped in a `<SYSTEM HOOK INSTRUCTION>`
block. That block must reach the agent's context on its next turn — not the
user's chat transcript.

Channel routing for Claude Code Stop hooks:
- `reason` (with `decision="block"`): only Stop channel that feeds text into
  the agent's context (the agent is told it must continue working from this
  reason).
- `stopReason`, `systemMessage`: user-visible only. The agent never sees these
  on its next turn.
- `hookSpecificOutput.additionalContext`: emitted defensively for forward
  compatibility — newer Claude Code may honour it for Stop; older versions
  ignore the unknown field.

Repro session (2026-05-22): the advisory text appeared in the user transcript;
the agent did not see it. Root cause: WARN-on-Stop with `context_injection`
was routed to `systemMessage`/`stopReason` (the user channels). Fix: WARN with
advisory context upgrades to `decision="block"` + `reason=<advisory>` at the
output layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter  # noqa: E402
from hooks.schemas import CanonicalHookOutput, ClaudeStopHookOutput  # noqa: E402

ADVISORY = (
    "<SYSTEM HOOK INSTRUCTION>Watch out, you aren't finished until you: "
    "provide evidence and an indicator of your level of certainty for "
    "EACH of your major claims.</SYSTEM HOOK INSTRUCTION>"
)


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


# ---------------------------------------------------------------------------
# Direct output_for_claude assertions
# ---------------------------------------------------------------------------


class TestStopHookAdvisoryRouting:
    """Stop hook output must route the advisory to agent-visible channels."""

    def test_advisory_reaches_agent_via_reason(self, router):
        """WARN on Stop with advisory → decision=block + reason carries the advisory."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)

        output = router.output_for_claude(canonical, "Stop")

        assert isinstance(output, ClaudeStopHookOutput)
        # The only Stop channel that reaches the agent is decision=block + reason.
        assert output.decision == "block"
        assert output.reason == ADVISORY

    def test_advisory_does_not_leak_to_stop_reason(self, router):
        """Advisory text must not appear in user-visible stopReason."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)

        output = router.output_for_claude(canonical, "Stop")

        assert output.stopReason is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.stopReason or ""
        ), (
            "Advisory leaked into user-visible stopReason — this is the "
            "exact bug from aops-d10e7db6."
        )

    def test_advisory_does_not_leak_to_system_message(self, router):
        """Advisory text must not appear in user-visible systemMessage."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)

        output = router.output_for_claude(canonical, "Stop")

        assert output.systemMessage is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.systemMessage or ""
        ), (
            "Advisory leaked into user-visible systemMessage — this is the "
            "exact bug from aops-d10e7db6."
        )

    def test_forward_compat_additional_context_emitted(self, router):
        """hookSpecificOutput.additionalContext is also emitted for forward-compat."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)

        output = router.output_for_claude(canonical, "Stop")

        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.hookEventName == "Stop"
        assert output.hookSpecificOutput.additionalContext == ADVISORY

    def test_session_end_same_routing(self, router):
        """SessionEnd uses the same routing as Stop."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)

        output = router.output_for_claude(canonical, "SessionEnd")

        assert output.decision == "block"
        assert output.reason == ADVISORY

    def test_approve_when_no_advisory(self, router):
        """Stop without advisory context approves (does not gratuitously block)."""
        canonical = CanonicalHookOutput(
            verdict="warn", context_injection=None, system_message="short note"
        )

        output = router.output_for_claude(canonical, "Stop")

        assert output.decision == "approve"
        # short user-facing note is fine in stopReason
        assert output.stopReason == "short note"

    def test_deny_still_routes_advisory_to_agent(self, router):
        """DENY on Stop: reason carries advisory (agent), stopReason carries summary (user)."""
        canonical = CanonicalHookOutput(
            verdict="deny",
            context_injection=ADVISORY,
            system_message="Handover required before stop",
        )

        output = router.output_for_claude(canonical, "Stop")

        assert output.decision == "block"
        assert output.reason == ADVISORY
        assert output.stopReason == "Handover required before stop"
        assert output.systemMessage == "Handover required before stop"
        # Advisory must not be echoed into user-visible channels.
        assert "SYSTEM HOOK INSTRUCTION" not in (output.stopReason or "")
        assert "SYSTEM HOOK INSTRUCTION" not in (output.systemMessage or "")


# ---------------------------------------------------------------------------
# JSON envelope: stdout from output_for_claude.model_dump_json must not
# contain the bare advisory outside the JSON object, and the JSON must
# place the advisory only in agent channels.
# ---------------------------------------------------------------------------


class TestStopHookJsonEnvelope:
    """End-to-end: the JSON Claude Code parses must carry the advisory in agent channels only."""

    def test_serialised_json_carries_advisory_in_reason_not_stop_reason(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        payload = json.loads(output.model_dump_json(exclude_none=True))

        # Agent-visible channel carries the advisory
        assert payload.get("decision") == "block"
        assert payload.get("reason") == ADVISORY

        # User-visible channels do NOT carry the advisory text
        for user_field in ("stopReason", "systemMessage"):
            value = payload.get(user_field)
            if value is not None:
                assert "SYSTEM HOOK INSTRUCTION" not in value, (
                    f"Advisory leaked into user-visible {user_field!r} of the "
                    f"serialised JSON envelope: {value!r}"
                )

    def test_router_subprocess_does_not_print_advisory_outside_json(self, tmp_path):
        """Invoke the router as a subprocess and confirm stdout is a single JSON object.

        Critically, the bare `<SYSTEM HOOK INSTRUCTION>` text must NOT appear
        OUTSIDE the JSON envelope on stdout. If it did, Claude Code would
        render it directly in the user transcript.
        """
        router_path = AOPS_CORE / "hooks" / "router.py"
        if not router_path.exists():
            pytest.skip(f"router.py not found at {router_path}")

        # Minimal Stop event payload. We can't easily force a WARN+advisory
        # without setting up live session state, so we just assert that
        # whatever stdout produces, it parses as a single JSON object — i.e.
        # the handler never prints raw text alongside JSON.
        payload = {
            "hook_event_name": "Stop",
            "session_id": "test-stop-envelope-d10e7db6",
            "transcript_path": str(tmp_path / "transcript.jsonl"),
            "cwd": str(tmp_path),
        }
        (tmp_path / "transcript.jsonl").write_text("")

        result = subprocess.run(
            [sys.executable, str(router_path), "--client", "claude"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        stdout = result.stdout.strip()
        if not stdout:
            # Empty stdout is acceptable (no output) — what we forbid is
            # mixed JSON+raw text.
            return

        # stdout must be a single JSON object — nothing before/after.
        try:
            json.loads(stdout)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"router stdout is not a single JSON object — raw text leaked "
                f"to the user transcript. stdout={stdout!r}, error={e}"
            )
