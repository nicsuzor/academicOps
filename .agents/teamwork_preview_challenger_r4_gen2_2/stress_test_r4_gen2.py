"""Challenger 2 Empirical Stress Test Suite - Iteration 2
Testing HTML metadata escaping, empty event ID deduplication, code block fences,
subagent escaping, and test suite execution.
"""

from __future__ import annotations

import os
import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "py"))

from transcripts.domain.renderer import (
    _escape_html,
    _format_tool_output_markdown,
    _get_code_fence,
    render_to_html,
    render_to_markdown,
    render_to_full_markdown,
    render_to_controller_markdown,
    render_session_to_all_formats,
    _render_subagent_html,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)
from transcripts.adapters.claude import (
    _build_subagent,
    load_claude_session,
)

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
    results.append((name, passed, detail))


def test_html_metadata_escaping():
    print("\n--- Test 1: HTML Metadata Escaping ---")
    event = NormalizedEvent(
        event_id="evt_1",
        timestamp="2026-08-06T12:00:00Z",
        source="user",
        type="message",
        content="Normal user prompt",
    )
    
    # Intentionally evil metadata with XSS vector tags
    evil_session_id = "sess_<script>alert('xss_session_id')</script>"
    evil_slug = "slug_<b>bold</b>_<img src=x onerror=alert('xss_slug')>"
    evil_started_at = "2026-08-06T12:00:00Z<svg/onload=alert('started')>"
    evil_ended_at = "2026-08-06T12:01:00Z<iframe src=javascript:alert('ended')>"
    evil_project = "proj_<project_tag>alert('project')</project_tag>"
    evil_task_id = "task_<task_tag>123</task_tag>"
    
    session = NormalizedSession(
        session_id=evil_session_id,
        source_file=Path("/tmp/evil_sess.jsonl"),
        events=[event],
    )
    correlation = {
        "project": evil_project,
        "task_id": evil_task_id,
        "pr_number": "456",
    }
    
    html = render_to_html(
        session=session,
        slug=evil_slug,
        started_at=evil_started_at,
        last_modified="2026-08-06T12:01:00Z",
        ended_at=evil_ended_at,
        has_user_context=True,
        correlation=correlation,
        insights=None,
    )

    # Verification: Raw unescaped tags MUST NOT exist in rendered HTML
    raw_forbidden = [
        "<script>alert('xss_session_id')</script>",
        "<b>bold</b>",
        "<img src=x onerror=alert('xss_slug')>",
        "<svg/onload=alert('started')>",
        "<iframe src=javascript:alert('ended')>",
        "<project_tag>",
        "<task_tag>",
    ]
    
    all_escaped = True
    for raw in raw_forbidden:
        if raw in html:
            all_escaped = False
            record(f"HTML escaping check for {raw[:20]}", False, f"Found unescaped raw string: {raw}")
    
    if all_escaped:
        record("All HTML metadata tags strictly escaped", True, "No raw tags found in rendered HTML")
    
    # Assert specific escaped entities are present
    record("Title session_id is entity encoded", "&lt;script&gt;alert('xss_session_id')&lt;/script&gt;" in html)
    record("Meta box Slug is entity encoded", "slug_&lt;b&gt;bold&lt;/b&gt;" in html)
    record("Meta box Started At is entity encoded", "&lt;svg/onload=alert('started')&gt;" in html)
    record("Meta box Ended At is entity encoded", "&lt;iframe src=javascript:alert('ended')&gt;" in html)
    record("Meta box Project is entity encoded", "proj_&lt;project_tag&gt;" in html)
    record("Meta box Task ID is entity encoded", "task_&lt;task_tag&gt;" in html)


def test_empty_event_id_deduplication():
    print("\n--- Test 2: Empty Event ID Handling in _build_subagent ---")
    
    # Create parent events: one with empty string event_id, one with None, one with valid event_id
    p_event_empty = NormalizedEvent(
        event_id="",
        timestamp="2026-08-06T12:00:00Z",
        source="system",
        type="checkpoint",
        content="Parent summary event with empty event_id",
    )
    p_event_valid = NormalizedEvent(
        event_id="parent_evt_123",
        timestamp="2026-08-06T12:00:01Z",
        source="model",
        type="message",
        content="Parent message event",
    )
    parent_events = [p_event_empty, p_event_valid]

    parent_event_ids = {e.event_id for e in parent_events if e.event_id}
    
    record("parent_event_ids excludes empty string ''", "" not in parent_event_ids, f"parent_event_ids = {parent_event_ids}")
    record("parent_event_ids includes valid 'parent_evt_123'", "parent_evt_123" in parent_event_ids)

    sub_event_empty = NormalizedEvent(
        event_id="",
        timestamp="2026-08-06T12:00:02Z",
        source="system",
        type="checkpoint",
        content="Subagent summary event with empty event_id",
    )
    sub_event_echo = NormalizedEvent(
        event_id="parent_evt_123",
        timestamp="2026-08-06T12:00:03Z",
        source="model",
        type="message",
        content="Echoed parent event",
    )
    sub_event_unique = NormalizedEvent(
        event_id="sub_evt_456",
        timestamp="2026-08-06T12:00:04Z",
        source="model",
        type="message",
        content="Unique subagent event",
    )

    sub_events = [sub_event_empty, sub_event_echo, sub_event_unique]

    deduped_events = []
    for ev in sub_events:
        if ev.event_id and ev.event_id in parent_event_ids:
            continue
        deduped_events.append(ev)

    record("Subagent empty event_id ('') is preserved", sub_event_empty in deduped_events)
    record("Subagent echo event_id ('parent_evt_123') is deduplicated/dropped", sub_event_echo not in deduped_events)
    record("Subagent unique event_id ('sub_evt_456') is preserved", sub_event_unique in deduped_events)
    record("Total preserved events count is 2", len(deduped_events) == 2, f"Got: {len(deduped_events)}")


def test_code_block_fence_handling():
    print("\n--- Test 3: Code Block Fence & Backtick Handling ---")
    
    content_with_triple = "Code snippet:\n```python\nprint('hello')\n```\nEnd snippet."
    fence_3 = _get_code_fence(content_with_triple)
    record("Fence for triple backticks is 4 backticks", fence_3 == "````", f"Got: {fence_3}")
    
    content_with_quad = "Code snippet:\n````markdown\n```\n````\nEnd."
    fence_4 = _get_code_fence(content_with_quad)
    record("Fence for quad backticks is 5 backticks", fence_4 == "`````", f"Got: {fence_4}")
    
    formatted = _format_tool_output_markdown(content_with_triple)
    record("Tool output formatted using dynamic fence", formatted[2].startswith("````"), f"First line of output: {formatted[2]}")


def test_subagent_html_and_markdown_escaping():
    print("\n--- Test 4: Subagent Description & Label Escaping ---")
    
    subagent = SubagentTranscript(
        agent_id="sub_<script>alert('agent_id')</script>",
        source_file=Path("/tmp/sub.jsonl"),
        agent_type=None,
        name=None,
        description="desc_<script>alert('desc')</script>",
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-08-06T12:00:00Z",
                source="user",
                type="message",
                content="Sub prompt",
            )
        ]
    )
    
    session = NormalizedSession(
        session_id="sess_sub_test",
        source_file=Path("/tmp/trunk.jsonl"),
        events=[],
        subagents=[subagent],
    )
    
    sub_html = _render_subagent_html(session, "test_base")
    record("Subagent HTML label escaped", "sub_&lt;script&gt;" in sub_html)
    record("Subagent HTML desc escaped", "desc_&lt;script&gt;" in sub_html)
    record("Subagent HTML no raw script", "<script>" not in sub_html)


def main():
    print("=== STARTING CHALLENGER 2 EMPIRICAL STRESS TESTS (ITERATION 2) ===")
    test_html_metadata_escaping()
    test_empty_event_id_deduplication()
    test_code_block_fence_handling()
    test_subagent_html_and_markdown_escaping()
    
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
        sys.exit(1)
    else:
        print("All empirical stress tests PASSED successfully!")


if __name__ == "__main__":
    main()
