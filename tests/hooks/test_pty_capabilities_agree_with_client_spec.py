"""CI guard: client_spec.py channel capabilities must agree with the
MEASURED cells in tests/hooks/fixtures/pty_capabilities.json (aops_de1fd90a).

WHY THIS EXISTS
---------------
mem-c3317ce8 flagged the gap this closes: "PTY fixture has no CI test
consuming it." GH #2181 is the concrete cost of that gap — the fixture's
asyncRewake-entry-drops-JSON-block cells were measurable 2026-07-08, but
nothing consumed them, so the production defect (a Stop hook entry carrying
`asyncRewake:true` silently discarding exit-0 JSON `decision:block`) shipped
and stayed live in `aops-core/hooks/hooks.json` until a user-visible failure
forced the investigation. This test maps each load-bearing Stop cell to the
`client_spec.py` capability fact it backs, so a re-probed fixture that flips
a cell (a REAL client behavior change, e.g. a Claude Code point release)
fails CI immediately — forcing a `client_spec.py` / spec update instead of
silent drift between the measured client and the SSoT that the router reads
at runtime.

Re-probe with `scripts/pty_hook_probe.py --only <label>` (see its module
docstring) and commit the updated fixture when a cell here legitimately
changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hooks import client_spec as cs

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pty_capabilities.json"


def _load_cells() -> dict[str, dict]:
    data = json.loads(FIXTURE_PATH.read_text())
    return {c["label"]: c for c in data["cells"]}


_CELLS = _load_cells()


def _cell(label: str) -> dict:
    assert label in _CELLS, (
        f"fixture is missing expected cell {label!r} — was it renamed or "
        "removed in scripts/pty_hook_probe.py without updating this test?"
    )
    return _CELLS[label]


class TestClaudeStopCapabilitiesAgreeWithFixture:
    """Each test here is one (client_spec field, fixture cell) pairing. If
    the measured client behavior ever disagrees with the SSoT capability
    table, exactly one of these fails — pinpointing which cell moved.
    """

    def test_can_block_agrees_with_measured_jsonblock_plain(self):
        spec = cs.channel_spec("claude", "Stop")
        cell = _cell("stop-jsonblock-plain")
        measured_can_block = bool(cell["agent_ctx_a"] and cell["user_saw_a"])
        assert spec.can_block == measured_can_block, (
            f"client_spec.channel_spec('claude','Stop').can_block "
            f"({spec.can_block}) disagrees with the measured "
            f"stop-jsonblock-plain cell ({measured_can_block}). Re-probe with "
            "scripts/pty_hook_probe.py and update client_spec.py / "
            "CLIENT-TRANSLATION.md / ENFORCEMENT-MAP.md to match."
        )

    def test_agent_context_without_block_agrees_with_measured_additionalcontext(self):
        spec = cs.channel_spec("claude", "Stop")
        cell = _cell("stop-additionalcontext-warn")
        measured = bool(cell["agent_ctx_a"] and cell["user_saw_a"])
        assert spec.agent_context_without_block == measured, (
            "client_spec.channel_spec('claude','Stop').agent_context_without_block "
            f"({spec.agent_context_without_block}) disagrees with the measured "
            f"stop-additionalcontext-warn cell ({measured}). Re-probe with "
            "scripts/pty_hook_probe.py and update client_spec.py / specs to match."
        )

    def test_no_client_event_claims_the_retired_asyncrewake_quiet_split(self):
        """GH #2181 fix direction B: agent_full_user_summary must stay False
        everywhere post-retirement (mirrors tests/hooks/test_client_spec.py's
        guard, re-asserted here against the fixture's own asyncrewake-split
        cell so this file is self-contained evidence of the retirement).
        """
        spec = cs.channel_spec("claude", "Stop")
        assert spec.agent_full_user_summary is False, (
            "asyncRewake quiet-split was retired 2026-07-08 (GH #2181) — "
            "agent_full_user_summary must be False; do not re-enable it "
            "without also re-adding a per-entry channel-selection mechanism "
            "(fix direction A on #2181) that keeps block-mode JSON delivery "
            "safe on the SAME hooks.json Stop entry."
        )

    @pytest.mark.parametrize("agent_pin_suffix", ["", "-agentpin"])
    def test_asyncrewake_entry_still_discards_json_block_gh2181(self, agent_pin_suffix):
        """Regression guard for the GH #2181 root cause. If Claude Code ever
        FIXES this (an asyncRewake:true entry starts honoring its own exit-0
        JSON decision:block), this test FAILS. That failure is GOOD NEWS, not
        a bug in the test: (1) re-probe to confirm, (2) reconsider whether
        hooks.json should reintroduce asyncRewake for a future quiet-split
        need (fix direction A becomes viable again), (3) update this test's
        expectation once confirmed.
        """
        cell = _cell(f"stop-jsonblock-asyncrewake{agent_pin_suffix}")
        control = _cell(f"stop-jsonblock-plain{agent_pin_suffix}")
        # The control (plain entry) must still deliver+block — otherwise
        # something ELSE broke and the asyncrewake comparison is meaningless.
        assert control["agent_ctx_a"] and control["user_saw_a"], (
            f"control cell stop-jsonblock-plain{agent_pin_suffix} no longer "
            "shows delivery — re-probe before trusting the asyncrewake cell "
            "below it; something else regressed first."
        )
        assert not cell["agent_ctx_a"] and not cell["user_saw_a"], (
            f"stop-jsonblock-asyncrewake{agent_pin_suffix} now shows delivery "
            "on BOTH surfaces — Claude Code may have FIXED the asyncRewake "
            "JSON-drop bug (GH #2181). See this test's docstring before "
            "treating this failure as a regression."
        )

    def test_agent_pin_does_not_change_jsonblock_delivery(self):
        """GH #2181's `is_subagent` misclassification hypothesis, EXONERATED:
        a project-pinned `agent:` setting must not change whether a plain
        Stop entry's JSON decision:block delivers.
        """
        unpinned = _cell("stop-jsonblock-plain")
        pinned = _cell("stop-jsonblock-plain-agentpin")
        assert (unpinned["agent_ctx_a"], unpinned["user_saw_a"]) == (
            pinned["agent_ctx_a"],
            pinned["user_saw_a"],
        ), (
            "agent-pinning changed JSON decision:block delivery — the "
            "is_subagent misclassification hypothesis from GH #2181 may no "
            "longer be exonerated; re-open the investigation."
        )

    def test_warn_mode_stop_channel_precondition_holds(self):
        """router._resolve_policy_for_claude_stop (aops-core/hooks/router.py)
        gates every warn-mode Stop gate's non-blocking delivery (qa, handover,
        rbg-review, ida) on agent_context_without_block. This must stay True
        for warn-mode gates to deliver non-blockingly — if it ever measures
        False, warn-mode advisories would silently upgrade to a blocking
        decision on Claude, with no test elsewhere catching it (the
        router-level unit tests mock the channel_spec answer rather than
        re-measuring it).
        """
        spec = cs.channel_spec("claude", "Stop")
        assert spec.agent_context_without_block is True, (
            "warn-mode Stop gates require agent_context_without_block=True "
            "to deliver non-blockingly — if this capability is ever measured "
            "False, warn-mode advisories silently upgrade to a blocking "
            "decision on Claude. Re-probe stop-additionalcontext-warn before "
            "assuming this is stale."
        )
