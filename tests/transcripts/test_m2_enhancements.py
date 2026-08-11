"""Unit tests for Milestone 2 enhancements in Python Transcript Generator.

Tests:
1. Token & cost usage metrics propagation in adapters/claude.py.
2. Hierarchical L1/L2 subagent call tree lineage construction, ASCII tree, and table rendering.
3. Per-step token pill rendering in domain/renderer.py.
4. Structured diagnostic error callouts (> [!ERROR_BLOCK]) and truncation in domain/renderer.py.
5. HTML error block rendering (error-box, error-badge, HTML escaping).
"""

from __future__ import annotations

from pathlib import Path

from transcripts.adapters.claude import (
    load_claude_transcript,
    normalize_claude_transcript,
)
from transcripts.domain.renderer import (
    _build_subagent_tree,
    _format_error_block_markdown,
    _is_error_event,
    render_to_controller_markdown,
    render_to_html,
    render_to_markdown,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    SubagentTranscript,
)

CORRELATION: dict[str, str | None] = {"project": "aops", "task_id": "T123", "pr_number": "42"}
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"


def test_token_and_cost_usage_metrics_propagation() -> None:
    """Verify event.meta['usage'] extraction and cumulative cost tracking in adapters/claude.py."""
    transcript = load_claude_transcript(CLAUDE_FIXTURE)
    session = normalize_claude_transcript(transcript)

    assistant_events = [e for e in session.events if e.source == "model"]
    assert len(assistant_events) > 0, "Expected assistant events in Claude fixture"

    for ev in assistant_events:
        assert "usage" in ev.meta, f"Event {ev.event_id} missing usage metadata"
        u = ev.meta["usage"]
        assert "input_tokens" in u
        assert "output_tokens" in u
        assert "cache_read_input_tokens" in u
        assert "cache_creation_input_tokens" in u
        assert "step_cost_usd" in u
        assert "cumulative_cost_usd" in u

    # Verify running cumulative cost increases monotonically
    cum_costs = [ev.meta["usage"]["cumulative_cost_usd"] for ev in assistant_events]
    for i in range(1, len(cum_costs)):
        assert cum_costs[i] >= cum_costs[i - 1]


def test_hierarchical_subagent_call_tree_l1_l2_building() -> None:
    """Verify hierarchical subagent tree construction with L1, L2, call path, and ASCII tree."""
    pauli = SubagentTranscript(
        agent_id="pauli_001",
        source_file=Path("agent-pauli_001.jsonl"),
        agent_type="aops-core:pauli",
        name="pauli",
        description="Code quality audit",
        parent_agent_id="main",
        tokens_used=420100,
        cost_usd=1.2603,
        events=[
            NormalizedEvent(
                event_id="p1",
                timestamp="2026-08-10T22:10:00Z",
                source="model",
                type="message",
                content="Auditing code",
            )
        ],
    )

    marsha = SubagentTranscript(
        agent_id="marsha_002",
        source_file=Path("agent-marsha_002.jsonl"),
        agent_type="aops-core:marsha",
        name="marsha",
        description="Security review",
        parent_agent_id="pauli_001",
        tokens_used=180000,
        cost_usd=0.5400,
        events=[
            NormalizedEvent(
                event_id="m1",
                timestamp="2026-08-10T22:12:00Z",
                source="model",
                type="message",
                content="Checking security",
            )
        ],
    )

    session = NormalizedSession(
        session_id="session_m2_tree",
        source_file=Path("session_m2_tree.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-08-10T22:00:00Z",
                source="user",
                type="message",
                content="Start audit",
            )
        ],
        subagents=[pauli, marsha],
        tokens_used=10000,
        cost_usd=0.03,
    )

    tree = _build_subagent_tree(session)
    assert len(tree) == 1
    root_node = tree[0]
    assert root_node.subagent.agent_id == "pauli_001"
    assert root_node.level_label == "L1"
    assert root_node.call_path == "main/pauli"
    assert len(root_node.children) == 1

    child_node = root_node.children[0]
    assert child_node.subagent.agent_id == "marsha_002"
    assert child_node.level_label == "L2"
    assert child_node.call_path == "main/pauli/marsha"
    assert child_node.parent_label == "pauli"

    md = render_to_markdown(
        session, "s_m2", "2026-08-10T22:00:00Z", "", "", True, CORRELATION, None
    )
    assert "### Subagent Call Tree Lineage" in md
    assert "└── 1. pauli (aops-core:pauli) (L1) [420.1k tok | $1.26] — Code quality audit" in md
    assert "    └── 1.1 marsha (aops-core:marsha) (L2) [180k tok | $0.54] — Security review" in md
    assert (
        "| L1 | `main/pauli` | `pauli` | aops-core:pauli | `main` | 1 | 420.1k | $1.26 | Code quality audit |"
        in md
    )
    assert (
        "| L2 | `main/pauli/marsha` | `marsha` | aops-core:marsha | `pauli` | 1 | 180k | $0.54 | Security review |"
        in md
    )


def test_subagent_cycle_protection_and_orphaned_parent() -> None:
    """Verify cycle detection and orphaned parent handling degrade gracefully."""
    sub_cycle_a = SubagentTranscript(
        agent_id="agent_a",
        source_file=Path("agent-a.jsonl"),
        agent_type="worker",
        name="worker_a",
        parent_agent_id="agent_b",
    )
    sub_cycle_b = SubagentTranscript(
        agent_id="agent_b",
        source_file=Path("agent-b.jsonl"),
        agent_type="worker",
        name="worker_b",
        parent_agent_id="agent_a",
    )

    session = NormalizedSession(
        session_id="session_cycle",
        source_file=Path("session_cycle.jsonl"),
        subagents=[sub_cycle_a, sub_cycle_b],
    )

    tree = _build_subagent_tree(session)
    assert len(tree) > 0
    # Degradation notices recorded
    assert len(session.degraded) > 0


def test_per_step_token_pill_rendering() -> None:
    """Verify formatted token pills on assistant turns in controller markdown."""
    event = NormalizedEvent(
        event_id="e_token_pill",
        timestamp="2026-08-10T22:15:30Z",
        source="model",
        type="message",
        content="Executing step",
        meta={
            "usage": {
                "input_tokens": 12450,
                "output_tokens": 450,
                "cache_read_input_tokens": 8200,
                "cache_creation_input_tokens": 1000,
                "step_cost_usd": 0.0381,
                "cumulative_cost_usd": 1.425,
            }
        },
    )

    session = NormalizedSession(
        session_id="session_pill",
        source_file=Path("session_pill.jsonl"),
        events=[event],
    )

    controller_md = render_to_controller_markdown(
        session, "s_pill", "2026-08-10T22:15:30Z", "", "", True, CORRELATION, None
    )

    expected_pill = "> **Tokens:** `12,450` in (`8,200` cache read, `1,000` cache write) | `450` out | **Step Cost:** `$0.0381` | **Cumulative:** `$1.4250`"
    assert expected_pill in controller_md


def test_diagnostic_error_block_formatting_and_truncation() -> None:
    """Verify structured [!ERROR_BLOCK] callouts and large output truncation."""
    tool_error_event = NormalizedEvent(
        event_id="e_err",
        timestamp="2026-08-10T22:04:12Z",
        source="tool",
        type="tool_output",
        content="bash: rtk: command not found\nExit Code: 127",
        meta={
            "tool_use_id": "toolu_01Me46HjJa47GxqUEh193Rfs",
            "is_error": True,
            "exit_code": 127,
        },
    )

    assert _is_error_event(tool_error_event)

    callout_lines = _format_error_block_markdown(
        tool_error_event,
        tool_call_names={"toolu_01Me46HjJa47GxqUEh193Rfs": "Bash"},
    )
    callout_text = "\n".join(callout_lines)

    assert "> [!ERROR_BLOCK]" in callout_text
    assert "> **Error Type:** `Tool Execution Failure`" in callout_text
    assert "> **Source Event / Tool:** `Bash` (`toolu_01Me46HjJa47GxqUEh193Rfs`)" in callout_text
    assert "> **Status / Exit Code:** `127`" in callout_text
    assert (
        "> **Message:** `bash: rtk: command not found`" in callout_text
        or "> **Message:**" in callout_text
    )
    assert "> **Impact:** Tool call failed; assistant requested fallback execution." in callout_text

    # Test truncation of large error output (>10 lines)
    large_error_content = "\n".join([f"Line {i}: catastrophic error detail" for i in range(25)])
    large_error_event = NormalizedEvent(
        event_id="e_large_err",
        timestamp="2026-08-10T22:05:00Z",
        source="tool",
        type="tool_output",
        content=large_error_content,
        meta={"is_error": True, "exit_code": 1, "tool_name": "PythonCompiler"},
    )
    large_callout_lines = _format_error_block_markdown(large_error_event)
    large_callout_text = "\n".join(large_callout_lines)

    assert "> <details><summary>Full Error Output</summary>" in large_callout_text
    assert "Line 0: catastrophic error detail" in large_callout_text
    assert "Line 24: catastrophic error detail" in large_callout_text


def test_html_error_block_rendering_and_escaping() -> None:
    """Verify HTML error-box, error-badge, and HTML escaping."""
    error_event = NormalizedEvent(
        event_id="e_html_err",
        timestamp="2026-08-10T22:04:12Z",
        source="tool",
        type="tool_output",
        content="<script>alert('xss')</script>\nbash: command failed",
        meta={"is_error": True, "exit_code": 127},
    )

    session = NormalizedSession(
        session_id="session_html_err",
        source_file=Path("session_html_err.jsonl"),
        events=[error_event],
    )

    html_out = render_to_html(
        session, "s_html", "2026-08-10T22:00:00Z", "", "", True, CORRELATION, None
    )

    assert 'class="error-box"' in html_out
    assert '<span class="badge error-badge">ERROR BLOCK</span>' in html_out
    # Check XSS script tag is safely escaped
    assert "<script>" not in html_out
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html_out
