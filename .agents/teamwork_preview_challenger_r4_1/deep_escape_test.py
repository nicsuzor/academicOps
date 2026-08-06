"""Deep investigation of escaping & formatting vulnerabilities in renderer.py."""

from __future__ import annotations

import sys
sys.path.insert(0, "/workspace/lib/py")

from pathlib import Path
from transcripts.domain.renderer import render_session_to_all_formats
from transcripts.model import NormalizedEvent, NormalizedSession, NormalizedToolCall, SubagentTranscript


def inspect_escaping():
    print("--- Testing Model Message Content Escaping in Markdown ---")
    model_event = NormalizedEvent(
        event_id="m1",
        timestamp="2026-08-06T12:00:00Z",
        source="model",
        type="message",
        content="I am reviewing <file_content> and <USER_REQUEST> for tags <thinking> and <script>alert('model')</script>.",
    )
    session = NormalizedSession(
        session_id="s_model_escape",
        source_file=Path("s_model_escape.jsonl"),
        events=[model_event],
    )
    ctrl_md, full_md, concise_md, html, json_sidecar = render_session_to_all_formats(
        session, "slug_m", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
    )

    print("Model content in controller_md:")
    for line in ctrl_md.splitlines():
        if "I am reviewing" in line:
            print("  RAW LINE:", repr(line))

    print("\nModel content in html:")
    for line in html.splitlines():
        if "I am reviewing" in line:
            print("  RAW HTML LINE:", repr(line))

    print("\n--- Testing Subagent Description Escaping in Markdown Subagent Index ---")
    subagent = SubagentTranscript(
        agent_id="sub_x",
        source_file=Path("agent-sub_x.jsonl"),
        description="Task for <USER_REQUEST> with <script>alert('sub')</script>",
        events=[],
    )
    session_sub = NormalizedSession(
        session_id="s_sub_desc",
        source_file=Path("s_sub_desc.jsonl"),
        subagents=[subagent],
    )
    ctrl_md_sub, _, concise_md_sub, _, _ = render_session_to_all_formats(
        session_sub, "slug_sub", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
    )

    print("Subagent table in controller_md:")
    for line in ctrl_md_sub.splitlines():
        if "sub_x" in line:
            print("  RAW TABLE ROW:", repr(line))

    print("\n--- Testing Tool Output Triple Backticks Breaking Markdown Code Blocks ---")
    tool_event = NormalizedEvent(
        event_id="t1",
        timestamp="2026-08-06T12:00:00Z",
        source="tool",
        type="tool_output",
        content="Output with backticks:\n```python\nprint('<script>alert(1)</script>')\n```\nEnd of output.",
    )
    session_tool = NormalizedSession(
        session_id="s_tool_backticks",
        source_file=Path("s_tool_backticks.jsonl"),
        events=[tool_event],
    )
    ctrl_md_tool, _, _, _, _ = render_session_to_all_formats(
        session_tool, "slug_tool", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z", True, {}, None
    )

    print("Tool output in controller_md:")
    print(ctrl_md_tool)


if __name__ == "__main__":
    inspect_escaping()
