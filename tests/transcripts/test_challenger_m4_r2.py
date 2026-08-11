"""Empirical Challenger Stress-Tests for M4 Re-Verification (Iteration 2).

Covers:
1. Tree building logic in renderer.py with cyclic parent IDs and orphaned subagents.
2. Token pill header formatting and [!ERROR_BLOCK] callout generation on error events.
3. Stop gate hook continuation in lib/hooks/dispatch.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from transcripts.domain.renderer import (
    SubagentTreeNode,
    _build_subagent_tree,
    _format_error_block_markdown,
    _is_error_event,
    _render_events_markdown,
    _render_subagent_index,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    SubagentTranscript,
)

# Import dispatch module directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "hooks"))
import dispatch  # noqa: E402


class TestSubagentTreeBuildingStress:
    """Empirical stress tests for _build_subagent_tree in renderer.py."""

    def test_direct_two_node_cycle(self):
        """subA -> subB -> subA (cyclic loop with no root)."""
        subA = SubagentTranscript(
            agent_id="subA_id_12345",
            source_file=Path("subA.jsonl"),
            name="subA",
            parent_agent_id="subB_id_12345",
        )
        subB = SubagentTranscript(
            agent_id="subB_id_12345",
            source_file=Path("subB.jsonl"),
            name="subB",
            parent_agent_id="subA_id_12345",
        )
        session = NormalizedSession(
            session_id="sess_cycle_2",
            source_file=Path("trunk.jsonl"),
            subagents=[subA, subB],
        )

        tree = _build_subagent_tree(session)

        # Must not infinite loop; all subagents accounted for
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 2
        agent_ids = {n.subagent.agent_id for n in flat_tree}
        assert agent_ids == {"subA_id_12345", "subB_id_12345"}
        assert any("cycle_detected_subagent" in d for d in session.degraded)

    def test_self_cycle(self):
        """subA -> subA (self cycle)."""
        subA = SubagentTranscript(
            agent_id="subSelf_id_1",
            source_file=Path("subSelf.jsonl"),
            name="subSelf",
            parent_agent_id="subSelf_id_1",
        )
        session = NormalizedSession(
            session_id="sess_self_cycle",
            source_file=Path("trunk.jsonl"),
            subagents=[subA],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 1
        assert flat_tree[0].subagent.agent_id == "subSelf_id_1"
        assert any("cycle_detected_subagent" in d for d in session.degraded)

    def test_three_node_indirect_cycle(self):
        """sub1 -> sub2 -> sub3 -> sub1."""
        sub1 = SubagentTranscript(
            agent_id="id1", source_file=Path("1.jsonl"), name="sub1", parent_agent_id="id3"
        )
        sub2 = SubagentTranscript(
            agent_id="id2", source_file=Path("2.jsonl"), name="sub2", parent_agent_id="id1"
        )
        sub3 = SubagentTranscript(
            agent_id="id3", source_file=Path("3.jsonl"), name="sub3", parent_agent_id="id2"
        )
        session = NormalizedSession(
            session_id="sess_cycle_3",
            source_file=Path("trunk.jsonl"),
            subagents=[sub1, sub2, sub3],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 3
        agent_ids = {n.subagent.agent_id for n in flat_tree}
        assert agent_ids == {"id1", "id2", "id3"}
        assert any("cycle_detected_subagent" in d for d in session.degraded)

    def test_multiple_disjoint_cycles(self):
        """(A -> B -> A) and (C -> D -> C)."""
        subA = SubagentTranscript(
            agent_id="a1", source_file=Path("a.jsonl"), name="subA", parent_agent_id="b1"
        )
        subB = SubagentTranscript(
            agent_id="b1", source_file=Path("b.jsonl"), name="subB", parent_agent_id="a1"
        )
        subC = SubagentTranscript(
            agent_id="c1", source_file=Path("c.jsonl"), name="subC", parent_agent_id="d1"
        )
        subD = SubagentTranscript(
            agent_id="d1", source_file=Path("d.jsonl"), name="subD", parent_agent_id="c1"
        )
        session = NormalizedSession(
            session_id="sess_disjoint",
            source_file=Path("trunk.jsonl"),
            subagents=[subA, subB, subC, subD],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 4
        agent_ids = {n.subagent.agent_id for n in flat_tree}
        assert agent_ids == {"a1", "b1", "c1", "d1"}
        assert len([d for d in session.degraded if "cycle_detected" in d]) >= 2

    def test_orphaned_subagents_various_parents(self):
        """Orphans referencing non-existent parent IDs."""
        orph1 = SubagentTranscript(
            agent_id="o1", source_file=Path("o1.jsonl"), name="orph1", parent_agent_id="missing_p1"
        )
        orph2 = SubagentTranscript(
            agent_id="o2", source_file=Path("o2.jsonl"), name="orph2", parent_agent_id="missing_p2"
        )
        orph3 = SubagentTranscript(
            agent_id="o3", source_file=Path("o3.jsonl"), name="orph3", parent_agent_id="missing_p1"
        )
        session = NormalizedSession(
            session_id="sess_orphans",
            source_file=Path("trunk.jsonl"),
            subagents=[orph1, orph2, orph3],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 3

        # Check call paths and level labels
        paths = [n.call_path for n in flat_tree]
        assert "main/orphaned/orph1" in paths
        assert "main/orphaned/orph2" in paths
        assert "main/orphaned/orph3" in paths

        # Degraded checks
        degraded_parents = [d for d in session.degraded if "orphaned_subagent_parent" in d]
        assert len(degraded_parents) >= 2
        assert any("missing_p1" in d for d in degraded_parents)
        assert any("missing_p2" in d for d in degraded_parents)

    def test_orphan_chain(self):
        """Orphan root spawning children: missing -> orph_root -> child1 -> child2."""
        orph_root = SubagentTranscript(
            agent_id="or1",
            source_file=Path("or1.jsonl"),
            name="orph_root",
            parent_agent_id="nonexistent",
        )
        child1 = SubagentTranscript(
            agent_id="c1", source_file=Path("c1.jsonl"), name="child1", parent_agent_id="or1"
        )
        child2 = SubagentTranscript(
            agent_id="c2", source_file=Path("c2.jsonl"), name="child2", parent_agent_id="c1"
        )
        session = NormalizedSession(
            session_id="sess_orph_chain",
            source_file=Path("trunk.jsonl"),
            subagents=[orph_root, child1, child2],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 3

        # orph_root is top-level orphan
        assert tree[0].subagent.agent_id == "or1"
        assert tree[0].level_label == "L2 (orphaned: nonexist)"
        # child1 is child of orph_root
        assert tree[0].children[0].subagent.agent_id == "c1"
        # child2 is child of child1
        assert tree[0].children[0].children[0].subagent.agent_id == "c2"

    def test_complex_mixture_roots_cycles_orphans(self):
        """Mix of normal root, unlinked, orphan, cycle under root, cycle without root."""
        root = SubagentTranscript(
            agent_id="r1", source_file=Path("r1.jsonl"), name="root1", parent_agent_id="main"
        )
        unlinked = SubagentTranscript(
            agent_id="u1", source_file=Path("u1.jsonl"), name="unlinked1", parent_agent_id=None
        )
        orphan = SubagentTranscript(
            agent_id="o1", source_file=Path("o1.jsonl"), name="orphan1", parent_agent_id="ghost"
        )
        cyc1 = SubagentTranscript(
            agent_id="cy1", source_file=Path("cy1.jsonl"), name="cyc1", parent_agent_id="cy2"
        )
        cyc2 = SubagentTranscript(
            agent_id="cy2", source_file=Path("cy2.jsonl"), name="cyc2", parent_agent_id="cy1"
        )

        session = NormalizedSession(
            session_id="sess_mix",
            source_file=Path("trunk.jsonl"),
            subagents=[root, unlinked, orphan, cyc1, cyc2],
        )

        tree = _build_subagent_tree(session)
        flat_tree = self._flatten_tree(tree)
        assert len(flat_tree) == 5
        agent_ids = {n.subagent.agent_id for n in flat_tree}
        assert agent_ids == {"r1", "u1", "o1", "cy1", "cy2"}

        # Verify index table rendering executes cleanly
        index_lines = _render_subagent_index(session, "test_mix")
        assert len(index_lines) > 0

    def _flatten_tree(self, nodes: list[SubagentTreeNode]) -> list[SubagentTreeNode]:
        res = []
        for n in nodes:
            res.append(n)
            res.extend(self._flatten_tree(n.children))
        return res


class TestTokenPillAndErrorBlockFormatting:
    """Empirical stress tests for token pills and diagnostic error blocks."""

    def test_token_pill_large_counts_and_cache_split(self):
        """Token pill formatting with high numbers, cache read + write."""
        event = NormalizedEvent(
            event_id="e_pill_large",
            timestamp="2026-08-11T10:00:00Z",
            source="model",
            type="message",
            content="Heavy calculation turn",
            meta={
                "usage": {
                    "input_tokens": 15000000,
                    "output_tokens": 250000,
                    "cache_read_input_tokens": 12000000,
                    "cache_creation_input_tokens": 3000000,
                    "step_cost_usd": 45.1234,
                    "cumulative_cost_usd": 120.5678,
                }
            },
        )
        rendered_lines = _render_events_markdown([event])
        rendered_text = "\n".join(rendered_lines)

        assert (
            "> **Tokens:** `15,000,000` in (`12,000,000` cache read, `3,000,000` cache write) | `250,000` out | **Step Cost:** `$45.1234` | **Cumulative:** `$120.5678`"
            in rendered_text
        )

    def test_token_pill_unknown_model_handling(self):
        """Token pill when unknown_model is present."""
        event = NormalizedEvent(
            event_id="e_pill_unk",
            timestamp="2026-08-11T10:00:00Z",
            source="model",
            type="message",
            content="Unknown model response",
            meta={
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 100,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "step_cost_usd": 0.0,
                    "cumulative_cost_usd": 0.05,
                },
                "unknown_model": "claude-4-hyper-future",
            },
        )
        rendered_lines = _render_events_markdown([event])
        rendered_text = "\n".join(rendered_lines)

        assert "Step Cost:** N/A (unknown model: claude-4-hyper-future)" in rendered_text

    def test_error_block_org_spend_limit(self):
        """System spend limit cutoff error block."""
        event = NormalizedEvent(
            event_id="e_spend_limit",
            timestamp="2026-08-11T10:00:00Z",
            source="system",
            type="system",
            content="Organization spend limit of $50.00 reached.",
            meta={
                "is_cutoff": True,
                "limit_usd": 50.0,
                "is_error": True,
            },
        )
        blocks = _format_error_block_markdown(event, cumulative_cost_usd=50.0432)
        text = "\n".join(blocks)

        assert "> [!ERROR_BLOCK]" in text
        assert "> **Error Type:** `Org Spend Limit Cutoff`" in text
        assert "> **Source Event / Tool:** `Session Termination`" in text
        assert "> **Status / Exit Code:** `Limit Exceeded ($50.0432 / $50.0000)`" in text
        assert "> **Impact:** Session terminated immediately. Subagent calls aborted." in text

    def test_error_block_tool_command_not_found(self):
        """Tool execution failure command not found."""
        event = NormalizedEvent(
            event_id="e_cmd_not_found",
            timestamp="2026-08-11T10:00:00Z",
            source="tool",
            type="tool_output",
            content="bash: foo_bar_baz_cmd: command not found\nexit code: 127",
            meta={
                "tool_use_id": "call_99",
            },
        )
        tool_call_names = {"call_99": "RunTerminalCommand"}
        blocks = _format_error_block_markdown(event, tool_call_names=tool_call_names)
        text = "\n".join(blocks)

        assert "> [!ERROR_BLOCK]" in text
        assert "> **Error Type:** `Tool Execution Failure`" in text
        assert "> **Source Event / Tool:** `RunTerminalCommand` (`call_99`)" in text
        assert "> **Status / Exit Code:** `127`" in text

    def test_error_block_code_fence_escalation(self):
        """Large error output containing 3 backticks forces 4 backticks code fence."""
        content = "Line 1\n```python\nprint('hello')\n```\n" + "Line extra\n" * 12
        event = NormalizedEvent(
            event_id="e_fence",
            timestamp="2026-08-11T10:00:00Z",
            source="tool",
            type="tool_output",
            content=content,
            meta={"is_error": True},
        )
        blocks = _format_error_block_markdown(event)
        text = "\n".join(blocks)

        assert "````" in text

    def test_error_event_detection_variations(self):
        """Test _is_error_event on various event shapes."""
        # 1. meta is_error = True
        ev1 = NormalizedEvent("1", "ts", "tool", "tool_output", "OK", meta={"is_error": True})
        assert _is_error_event(ev1) is True

        # 2. exit_code != 0
        ev2 = NormalizedEvent("2", "ts", "tool", "tool_output", "FAILED", meta={"exit_code": 1})
        assert _is_error_event(ev2) is True

        # 3. exit_code == 0
        ev3 = NormalizedEvent("3", "ts", "tool", "tool_output", "SUCCESS", meta={"exit_code": 0})
        assert _is_error_event(ev3) is False

        # 4. content contains exit code: 2
        ev4 = NormalizedEvent(
            "4", "ts", "tool", "tool_output", "Process failed with exit code: 2", meta={}
        )
        assert _is_error_event(ev4) is True


class TestStopGateHookContinuationStress:
    """Empirical stress tests for stop gate continuation in lib/hooks/dispatch.py."""

    def test_is_continuation_matrix(self):
        """Verify is_continuation across events and stop_hook_active values."""
        # Continuation events with stop_hook_active = True
        for ev in ("Stop", "SubagentStop", "PostToolBatch"):
            assert dispatch.is_continuation(ev, {"stop_hook_active": True}) is True
            assert dispatch.is_continuation(ev, {"stop_hook_active": 1}) is True
            assert dispatch.is_continuation(ev, {"stop_hook_active": "yes"}) is True

        # Continuation events with stop_hook_active = False / missing
        for ev in ("Stop", "SubagentStop", "PostToolBatch"):
            assert dispatch.is_continuation(ev, {"stop_hook_active": False}) is False
            assert dispatch.is_continuation(ev, {}) is False
            assert dispatch.is_continuation(ev, {"stop_hook_active": None}) is False

        # Non-continuation events even if stop_hook_active = True
        for ev in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "SessionStart"):
            assert dispatch.is_continuation(ev, {"stop_hook_active": True}) is False

    def test_dispatch_main_continuation_early_exit(self):
        """When stop_hook_active=True on Stop event, dispatch.main returns 0 without output."""
        argv = ["dispatch.py", "claude", "Stop"]
        input_data = json.dumps({"stop_hook_active": True, "session_id": "test_sess"})

        # Run main logic
        old_stdin = sys.stdin
        try:
            import io

            sys.stdin = io.StringIO(input_data)
            ret = dispatch.main(argv)
            assert ret == 0
        finally:
            sys.stdin = old_stdin

    def test_block_disposition_rendering_claude_vs_agy(self):
        """Verify _render_claude and _render_agy on BLOCK / REFUSE / ADVISE."""
        res_block = dispatch.block("Stop block reason", user_text="User notice")

        # Claude on Stop -> top-level decision: block
        claude_stop = dispatch._render_claude(res_block, "Stop")
        assert claude_stop == {
            "decision": "block",
            "reason": "Stop block reason",
            "systemMessage": "User notice",
        }

        # Claude on SubagentStop -> top-level decision: block
        claude_substop = dispatch._render_claude(res_block, "SubagentStop")
        assert claude_substop == {
            "decision": "block",
            "reason": "Stop block reason",
            "systemMessage": "User notice",
        }

        # Claude on PreToolUse (illegal block) -> degrades to advisory
        claude_pretool = dispatch._render_claude(res_block, "PreToolUse")
        assert "hookSpecificOutput" in claude_pretool
        assert (
            claude_pretool["hookSpecificOutput"]["permissionDecisionReason"]
            if "permissionDecisionReason" in claude_pretool["hookSpecificOutput"]
            else claude_pretool["hookSpecificOutput"]["additionalContext"] == "Stop block reason"
        )

        # agy on block -> degrades to ephemeral injectSteps
        agy_block = dispatch._render_agy(res_block)
        assert agy_block == {"injectSteps": [{"ephemeralMessage": "Stop block reason"}]}

    def test_disposition_merging_precedence(self):
        """_merge prefers REFUSE over BLOCK over ADVISE."""
        r_adv = dispatch.warn("Advise message")
        r_blk = dispatch.block("Block message")
        r_ref = dispatch.refuse("Refuse message")

        assert dispatch._merge([r_adv, r_blk]) == r_blk
        assert dispatch._merge([r_adv, r_blk, r_ref]) == r_ref
        assert dispatch._merge([r_adv]) == r_adv
        assert dispatch._merge([]) is None
