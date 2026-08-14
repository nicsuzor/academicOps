"""Adversarial stress-test probes for Milestone 2 transcript enhancements.

Tests deep subagent trees, cyclic parent linkages, orphaned subagents,
extreme error messages, unknown models, float precision, HTML injection,
and spec compliance.
"""

from pathlib import Path

from transcripts.domain.renderer import (
    _build_subagent_tree,
    _format_error_block_markdown,
    _is_error_event,
    _render_subagent_index,
    render_to_controller_markdown,
    render_to_html,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    SubagentTranscript,
)


class TestSubagentTreeAdversarial:
    """Stress tests for subagent call tree construction and lineage rendering."""

    def test_deeply_nested_subagent_tree_l5(self):
        """Test $L_5$ nesting depth (main -> sub1 -> sub2 -> sub3 -> sub4 -> sub5)."""
        subs = [
            SubagentTranscript(
                agent_id="sub1",
                source_file=Path("agent-sub1.jsonl"),
                name="agent_l1",
                parent_agent_id="main",
            ),
            SubagentTranscript(
                agent_id="sub2",
                source_file=Path("agent-sub2.jsonl"),
                name="agent_l2",
                parent_agent_id="sub1",
            ),
            SubagentTranscript(
                agent_id="sub3",
                source_file=Path("agent-sub3.jsonl"),
                name="agent_l3",
                parent_agent_id="sub2",
            ),
            SubagentTranscript(
                agent_id="sub4",
                source_file=Path("agent-sub4.jsonl"),
                name="agent_l4",
                parent_agent_id="sub3",
            ),
            SubagentTranscript(
                agent_id="sub5",
                source_file=Path("agent-sub5.jsonl"),
                name="agent_l5",
                parent_agent_id="sub4",
            ),
        ]
        session = NormalizedSession(
            session_id="sess_deep", source_file=Path("trunk.jsonl"), subagents=subs
        )

        tree = _build_subagent_tree(session)
        assert len(tree) == 1
        n1 = tree[0]
        assert n1.level_label == "L1"
        assert n1.call_path == "main/agent_l1"

        n2 = n1.children[0]
        assert n2.level_label == "L2"
        assert n2.call_path == "main/agent_l1/agent_l2"

        n3 = n2.children[0]
        assert n3.level_label == "L3"
        assert n3.call_path == "main/agent_l1/agent_l2/agent_l3"

        n4 = n3.children[0]
        assert n4.level_label == "L4"
        assert n4.call_path == "main/agent_l1/agent_l2/agent_l3/agent_l4"

        n5 = n4.children[0]
        assert n5.level_label == "L5"
        assert n5.call_path == "main/agent_l1/agent_l2/agent_l3/agent_l4/agent_l5"

    def test_direct_cyclic_linkage_two_nodes(self):
        """Test cyclic linkage where subA -> subB -> subA with no root."""
        subA = SubagentTranscript(
            agent_id="subA",
            source_file=Path("agent-subA.jsonl"),
            name="subA",
            parent_agent_id="subB",
        )
        subB = SubagentTranscript(
            agent_id="subB",
            source_file=Path("agent-subB.jsonl"),
            name="subB",
            parent_agent_id="subA",
        )
        session = NormalizedSession(
            session_id="sess_cycle", source_file=Path("trunk.jsonl"), subagents=[subA, subB]
        )

        _build_subagent_tree(session)
        assert any("cycle_detected" in d for d in session.degraded)
        rendered_index = _render_subagent_index(session, "test_file")
        assert len(rendered_index) > 0

    def test_subtree_cycle(self):
        """Test root -> childA -> childB -> childA (cycle within subtree)."""
        root = SubagentTranscript(
            agent_id="root",
            source_file=Path("agent-root.jsonl"),
            name="root_agent",
            parent_agent_id="main",
        )
        subA = SubagentTranscript(
            agent_id="subA",
            source_file=Path("agent-subA.jsonl"),
            name="subA",
            parent_agent_id="subB",  # Cycle between subA and subB
        )
        subB = SubagentTranscript(
            agent_id="subB",
            source_file=Path("agent-subB.jsonl"),
            name="subB",
            parent_agent_id="subA",
        )

        session = NormalizedSession(
            session_id="sess_sub_cycle",
            source_file=Path("trunk.jsonl"),
            subagents=[root, subA, subB],
        )

        tree = _build_subagent_tree(session)
        # All subagents should be accounted for in tree or degraded
        total_nodes_in_tree = sum(1 for _ in _flatten_nodes(tree))
        assert total_nodes_in_tree == 3, (
            f"Expected 3 nodes in tree index, but got {total_nodes_in_tree}"
        )
        assert any("cycle_detected" in d for d in session.degraded), (
            "Expected cycle_detected in session.degraded"
        )

    def test_orphaned_parent_id(self):
        """Test subagent with parent_agent_id referencing a missing ID."""
        sub_orphan = SubagentTranscript(
            agent_id="sub_orph",
            source_file=Path("agent-orph.jsonl"),
            name="orphan_agent",
            parent_agent_id="nonexistent_parent_id_12345",
        )
        session = NormalizedSession(
            session_id="sess_orph",
            source_file=Path("trunk.jsonl"),
            subagents=[sub_orphan],
        )

        tree = _build_subagent_tree(session)
        assert len(tree) == 1
        node = tree[0]
        assert node.level_label == "L2 (orphaned: nonexist)"
        assert node.call_path == "main/orphaned/orphan_agent"
        assert any("orphaned_subagent_parent" in d for d in session.degraded)

    def test_unlinked_subagent_missing_parent_id(self):
        """Test subagent with empty or None parent_agent_id."""
        sub_unlinked = SubagentTranscript(
            agent_id="sub_unlinked",
            source_file=Path("agent-unlinked.jsonl"),
            name="unlinked_agent",
            parent_agent_id=None,
        )
        session = NormalizedSession(
            session_id="sess_unlinked",
            source_file=Path("trunk.jsonl"),
            subagents=[sub_unlinked],
        )

        tree = _build_subagent_tree(session)
        assert len(tree) == 1
        node = tree[0]
        assert node.level_label == "L1 (unlinked)"
        assert node.call_path == "main/unlinked/unlinked_agent"

    def test_sibling_label_collision_disambiguation(self):
        """Test sibling subagents with identical labels under the same parent."""
        sub1 = SubagentTranscript(
            agent_id="a111111122222222",
            source_file=Path("agent-1.jsonl"),
            name="pauli",
            parent_agent_id="main",
        )
        sub2 = SubagentTranscript(
            agent_id="b333333344444444",
            source_file=Path("agent-2.jsonl"),
            name="pauli",
            parent_agent_id="main",
        )
        session = NormalizedSession(
            session_id="sess_collision",
            source_file=Path("trunk.jsonl"),
            subagents=[sub1, sub2],
        )

        tree = _build_subagent_tree(session)
        assert len(tree) == 2
        assert tree[0].call_path == "main/pauli-a1111111"
        assert tree[1].call_path == "main/pauli-b3333333"


class TestErrorBlockAdversarial:
    """Adversarial testing for diagnostic error blocks."""

    def test_huge_error_output_with_html_injection(self):
        """Test truncation and HTML tag escaping in large error output."""
        evil_content = "Error occurred!\n" + "</details><script>alert('pwned')</script>\n" * 20
        event = NormalizedEvent(
            event_id="err1",
            timestamp="2026-08-11T10:00:00Z",
            source="tool",
            type="tool_output",
            content=evil_content,
            meta={"is_error": True, "tool_name": "Bash", "tool_use_id": "call_123"},
        )

        lines = _format_error_block_markdown(event)
        rendered_md = "\n".join(lines)
        assert "> [!ERROR_BLOCK]" in rendered_md
        assert "<details><summary>Full Error Output</summary>" in rendered_md

        # Test HTML tier rendering for safety
        session = NormalizedSession(session_id="s_err", source_file=Path("t.jsonl"), events=[event])
        html = render_to_html(
            session,
            "slug",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            True,
            {},
            None,
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_error_detection_exit_code_0_and_1_conflict(self):
        """Test tool output containing both 'exit code: 0' and 'exit code: 1'."""
        content = "Step 1: exit code: 0\nStep 2: exit code: 1\nFAILED"
        event = NormalizedEvent(
            event_id="err_mixed",
            timestamp="2026-08-11T10:00:00Z",
            source="tool",
            type="tool_output",
            content=content,
            meta={},
        )
        is_err = _is_error_event(event)
        assert is_err is True, (
            "Event with 'exit code: 1' was missed because 'exit code: 0' also appeared in text!"
        )

    def test_error_block_code_fence_inside_large_error(self):
        """Test large error message containing triple backticks."""
        content = "```python\ndef foo():\n    raise ValueError('boom')\n```\n" + "extra line\n" * 15
        event = NormalizedEvent(
            event_id="err_fence",
            timestamp="2026-08-11T10:00:00Z",
            source="tool",
            type="tool_output",
            content=content,
            meta={"is_error": True, "tool_name": "Python"},
        )
        lines = _format_error_block_markdown(event)
        rendered_md = "\n".join(lines)
        assert "````" in rendered_md

    def test_org_spend_limit_cutoff_formatting(self):
        """Test system event representing org spend limit cutoff."""
        event = NormalizedEvent(
            event_id="sys_cutoff",
            timestamp="2026-08-11T10:00:00Z",
            source="system",
            type="system",
            content="Organization spend limit reached during subagent execution.",
            meta={"is_cutoff": True, "limit_usd": 45.0},
        )
        lines = _format_error_block_markdown(event, cumulative_cost_usd=45.1205)
        rendered_md = "\n".join(lines)
        assert "Org Spend Limit Cutoff" in rendered_md
        assert "Session Termination" in rendered_md
        assert "Limit Exceeded ($45.1205 / $45.0000)" in rendered_md
        assert "Session terminated immediately. Subagent calls aborted." in rendered_md


class TestTokenAccountingAdversarial:
    """Adversarial testing for token pills, cost headers, and model rate cards."""

    def test_unknown_model_pill_and_degraded_notice(self):
        """Test token pill and degraded list when model is unlisted in MODEL_RATE_CARD."""
        event = NormalizedEvent(
            event_id="asst_unk",
            timestamp="2026-08-11T10:00:00Z",
            source="model",
            type="message",
            content="Hello world",
            meta={
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "cache_read_input_tokens": 500,
                    "cache_creation_input_tokens": 0,
                    "step_cost_usd": 0.0,
                    "cumulative_cost_usd": 0.0,
                },
                "unknown_model": "custom-model-v99",
            },
        )
        session = NormalizedSession(
            session_id="sess_unk",
            source_file=Path("t.jsonl"),
            events=[event],
        )

        controller_md = render_to_controller_markdown(
            session,
            "slug",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            True,
            {},
            None,
        )
        assert "N/A (unknown model: custom-model-v99)" in controller_md

    def test_zero_total_tokens_omits_token_pill(self):
        """Test assistant turn with zero tokens omits token pill header line."""
        event = NormalizedEvent(
            event_id="asst_zero",
            timestamp="2026-08-11T10:00:00Z",
            source="model",
            type="message",
            content="No tokens used",
            meta={
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "step_cost_usd": 0.0,
                    "cumulative_cost_usd": 0.0,
                }
            },
        )
        session = NormalizedSession(
            session_id="sess_zero", source_file=Path("t.jsonl"), events=[event]
        )
        controller_md = render_to_controller_markdown(
            session,
            "slug",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            "2026-08-11T10:00:00Z",
            True,
            {},
            None,
        )
        assert "> **Tokens:**" not in controller_md


def _flatten_nodes(nodes):
    res = []
    for n in nodes:
        res.append(n)
        res.extend(_flatten_nodes(n.children))
    return res
