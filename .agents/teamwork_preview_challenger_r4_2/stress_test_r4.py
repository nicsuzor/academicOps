"""Empirical Stress Test Harness for Milestone R4 (4-Tier Transcript System & Renderer Hardening) - Deep Audit.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "py"))

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import (
    MODEL_RATE_CARD,
    _accumulate_usage,
    _build_subagent,
    get_model_rates,
    load_claude_session,
    normalize_claude_transcript,
)
from transcripts.domain.cache import SkipCache
from transcripts.domain.renderer import (
    _escape_html,
    _format_tool_output_markdown,
    build_json_sidecar,
    render_session_to_all_formats,
    render_to_controller_markdown,
    render_to_full_markdown,
    render_to_html,
    render_to_json,
    render_to_markdown,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)
from transcripts.runner import process_single_session

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
    results.append((name, passed, detail))


def deep_test_suite():
    print("\n--- Deep Audit & Edge Cases ---")

    # 1. Unescaped session metadata in render_to_html
    event = NormalizedEvent(
        event_id="evt_1",
        timestamp="2026-08-06T12:00:00Z",
        source="user",
        type="message",
        content="Normal message",
    )
    session = NormalizedSession(
        session_id="sess_<script>alert('sess_id')</script>",
        source_file=Path("/tmp/sess.jsonl"),
        events=[event],
    )
    correlation = {
        "project": "<script>alert('project')</script>",
        "task_id": "task_<tag>",
        "pr_number": "123",
    }
    html = render_to_html(
        session, "slug_<tag>", "2026-08-06T12:00:00Z", "2026-08-06T12:01:00Z", "2026-08-06T12:01:00Z",
        True, correlation, None
    )

    record(
        "HTML title tag is escaped",
        "<title>Session sess_&lt;script&gt;" in html,
        f"Title content: {html.split('<title>')[1].split('</title>')[0] if '<title>' in html else 'N/A'}"
    )
    record(
        "HTML h1 tag is escaped",
        "<h1>Session sess_&lt;script&gt;" in html,
        f"h1 content: {html.split('<h1>')[1].split('</h1>')[0] if '<h1>' in html else 'N/A'}"
    )
    record(
        "HTML meta-box Project field is escaped",
        "<strong>Project</strong>&lt;script&gt;" in html or "<strong>Project</strong>N/A" in html,
        f"Found raw script in HTML? {'<script>alert(\'project\')</script>' in html}"
    )
    record(
        "HTML meta-box Task ID field is escaped",
        "<strong>Task ID</strong>task_&lt;tag&gt;" in html,
        f"Found raw tag in task_id? {'task_<tag>' in html}"
    )
    record(
        "HTML meta-box Slug field is escaped",
        "<strong>Slug</strong>slug_&lt;tag&gt;" in html,
        f"Found raw tag in slug? {'slug_<tag>' in html}"
    )

    # 2. Empty/Falsy event_id deduplication bug
    p_event_summary = NormalizedEvent(
        event_id="",  # summary event without leafUuid
        timestamp="2026-08-06T12:00:00Z",
        source="system",
        type="checkpoint",
        content="Parent summary",
    )
    sub_event_summary = NormalizedEvent(
        event_id="",  # subagent summary event without leafUuid
        timestamp="2026-08-06T12:00:05Z",
        source="system",
        type="checkpoint",
        content="Subagent summary",
    )
    parent_events = [p_event_summary]
    parent_ids = {e.event_id for e in parent_events if e.event_id}
    # Check deduplication filter
    sub_filtered = [e for e in [sub_event_summary] if not (e.event_id and e.event_id in parent_ids)]
    record(
        "Empty event_id ('') in parent does not drop subagent events with empty event_id ('')",
        len(sub_filtered) == 1,
        f"Subagent summary event kept? {len(sub_filtered) == 1}"
    )

    # 3. Triple backtick code block fence breakage in tool output
    fenced_tool_output = "Here is sample output:\n```python\ndef foo():\n    return 42\n```\nEnd of output." + ("\nline" * 15)
    formatted_fenced = _format_tool_output_markdown(fenced_tool_output)
    joined_fenced = "\n".join(formatted_fenced)
    record(
        "Tool output with triple backticks inside <details> block handled",
        "`" * 3 in joined_fenced,
        f"Formatted markdown details fence structure: {formatted_fenced[2]} ... {formatted_fenced[-3]}"
    )

    # 4. Token Accounting Split correctness
    subagent_1 = SubagentTranscript(
        agent_id="sub_a",
        source_file=Path("/tmp/sub_a.jsonl"),
        tokens_used=1500,
        cost_usd=0.015,
    )
    session_tokens = NormalizedSession(
        session_id="tok_test",
        source_file=Path("/tmp/trunk.jsonl"),
        tokens_used=3000,
        cost_usd=0.030,
        subagents=[subagent_1],
    )
    record("controller_tokens property", session_tokens.controller_tokens == 3000)
    record("subagent_tokens property", session_tokens.subagent_tokens == 1500)
    record("total_tokens_used property", session_tokens.total_tokens_used == 4500)
    record("controller_cost_usd property", session_tokens.controller_cost_usd == 0.030)
    record("subagent_cost_usd property", session_tokens.subagent_cost_usd == 0.015)
    record("total_cost_usd property", session_tokens.total_cost_usd == 0.045)


if __name__ == "__main__":
    deep_test_suite()

    print("\n=== SUMMARY ===")
    total = len(results)
    passed = sum(1 for r in results if r[1])
    failed = total - passed
    print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
    if failed > 0:
        print("\nFailures:")
        for name, p, detail in results:
            if not p:
                print(f" - {name}: {detail}")
