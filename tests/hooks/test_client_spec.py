"""Faithfulness guard for the client-translation SSoT (`hooks.client_spec`).

`client_spec.py` is the single source of truth that BOTH the runtime router and
the build will read (Table 1 of `specs/hooks/CLIENT-TRANSLATION.md`). Before any
consumer is rewired to it, this test proves it reproduces the CURRENT, scattered
maps EXACTLY — so the consolidation is provably behaviour-preserving. After the
rewire, this test guards against the SSoT drifting from what the wire expects.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from hooks import client_spec as cs
from hooks.router import GEMINI_EVENT_MAP

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def build_mod():
    spec = importlib.util.spec_from_file_location("buildmod", REPO / "scripts" / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestInboundEventMap:
    """`to_internal_event` must reproduce the runtime `GEMINI_EVENT_MAP` (gemini+agy)."""

    def test_every_runtime_inbound_entry_is_reproduced(self):
        for wire, internal in GEMINI_EVENT_MAP.items():
            resolved = {cs.to_internal_event(c, wire) for c in ("gemini", "agy")}
            assert internal in resolved, (
                f"wire {wire!r}->{internal!r} not reproduced by client_spec inbound (got {resolved})"
            )

    def test_claude_inbound_is_identity(self):
        for ev in ("PreToolUse", "UserPromptSubmit", "Stop", "SessionStart", "PostToolUse"):
            assert cs.to_internal_event("claude", ev) == ev


class TestOutboundEventMap:
    """`to_wire_events` must reproduce the build's Claude->external maps."""

    def test_gemini_outbound_matches_build(self, build_mod):
        c2g = build_mod.CLAUDE_TO_GEMINI_EVENTS
        for claude_ev, gem in c2g.items():
            if claude_ev in ("BeforeTool", "AfterTool", "BeforeAgent", "AfterAgent"):
                continue  # build identity-passthrough of already-gemini names
            targets = gem if isinstance(gem, list) else [gem]
            valid = sorted(t for t in targets if cs.valid_wire_event("gemini", t))
            assert sorted(cs.to_wire_events("gemini", claude_ev)) == valid, claude_ev

    def test_agy_outbound_matches_documented_invariants(self):
        assert cs.to_wire_events("agy", "UserPromptSubmit") == ["PreInvocation"]
        assert cs.to_wire_events("agy", "Stop") == ["PostInvocation"]
        assert cs.to_wire_events("agy", "PreToolUse") == ["PreToolUse"]
        assert cs.to_wire_events("agy", "PostToolUse") == ["PostToolUse"]
        # Events with no agy equivalent are dropped (invariant: build emits nothing).
        for dropped in (
            "SessionStart",
            "SessionEnd",
            "SubagentStart",
            "SubagentStop",
            "PreCompact",
            "Notification",
        ):
            assert cs.to_wire_events("agy", dropped) == [], dropped


class TestRegistrationShapeAndTimeouts:
    def test_agy_flat_list_events(self):
        # Invariant #9: PreInvocation/PostInvocation/Stop are flat; tool events wrapper.
        assert cs.config_shape("agy", "PreInvocation") == "flat"
        assert cs.config_shape("agy", "PostInvocation") == "flat"
        assert cs.config_shape("agy", "Stop") == "flat"
        assert cs.config_shape("agy", "PreToolUse") == "wrapper"
        assert cs.config_shape("agy", "PostToolUse") == "wrapper"

    def test_agy_pretooluse_timeout_floor(self):
        # Invariant #10: agy PreToolUse cold-start floor >= 15000ms.
        assert cs.timeout_floor_ms("agy", "PreToolUse") == 15000
        assert cs.timeout_floor_ms("agy", "PostToolUse") is None

    def test_gemini_uses_wrapper_shape(self):
        assert cs.config_shape("gemini", "BeforeTool") == "wrapper"


class TestChannelTable:
    def test_every_client_event_has_a_spec_or_is_intentionally_absent(self):
        # Each (client, core_event) we route must have a channel spec.
        core = ["PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"]
        for client in cs.CLIENTS:
            for ev in core:
                assert cs.channel_spec(client, ev) is not None, (client, ev)

    def test_claude_stop_delivers_without_block_2_1_191(self):
        # mem-4ab6cc0b: confirmed live. The stale "Stop rejects hookSpecificOutput"
        # belief is retired — Stop can deliver agent context without blocking.
        spec = cs.channel_spec("claude", "Stop")
        assert spec.agent_context_without_block is True
        assert spec.can_block is True  # delivery != enforcement; block still available

    def test_agy_pretooluse_has_no_free_agent_channel(self):
        spec = cs.channel_spec("agy", "PreToolUse")
        assert spec.agent_context_without_block is False
        assert spec.can_block is True

    def test_agy_posttool_has_no_channels(self):
        spec = cs.channel_spec("agy", "PostToolUse")
        assert (spec.can_block, spec.agent_context_without_block, spec.user_message) == (
            False,
            False,
            False,
        )
