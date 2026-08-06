"""Exhaustive empirical test suite for Milestone R4 Iteration 2 Challenger 1."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/workspace/lib/py")

from transcripts.domain.renderer import (
    _escape_html,
    _get_code_fence,
    _format_tool_output_markdown,
    render_session_to_all_formats,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)


def test_html_metadata_escaping():
    print("=== Testing HTML Metadata Header Escaping ===")
    malicious_payloads = [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "'><svg/onload=alert(1)>",
        "&'\"<>",
    ]

    for idx, payload in enumerate(malicious_payloads):
        correlation = {
            "project": f"Project_{payload}",
            "task_id": f"Task_{payload}",
            "pr_number": payload,
        }
        subagent = SubagentTranscript(
            agent_id=f"sub_{idx}_{payload}",
            source_file=Path(f"sub_{idx}.jsonl"),
            agent_type=f"Type_{payload}",
            name=f"Name_{payload}",
            description=f"Desc_{payload}",
            events=[],
        )
        session = NormalizedSession(
            session_id=f"session_{payload}",
            source_file=Path("session_test.jsonl"),
            events=[
                NormalizedEvent(
                    event_id="e1",
                    timestamp="2026-08-06T12:00:00Z",
                    source="user",
                    type="message",
                    content="Hello",
                )
            ],
            subagents=[subagent],
        )

        _, _, _, html, _ = render_session_to_all_formats(
            session,
            f"slug_{payload}",
            f"2026-08-06_{payload}",
            f"2026-08-06_{payload}",
            f"2026-08-06_{payload}",
            True,
            correlation,
            None,
        )

        # Verification checks
        assert "<script>alert(1)</script>" not in html, f"Raw <script> found for payload {payload}"
        assert "<img src=x onerror=alert(1)>" not in html, f"Raw <img> found for payload {payload}"
        assert "<svg/onload=alert(1)>" not in html, f"Raw <svg> found for payload {payload}"
        assert "onerror=" not in html, f"Raw attribute onerror= found in HTML for payload {payload}"

        # Ensure all malicious characters are escaped
        print(f"  [PASS] Payload {idx+1}: {payload!r} rendered safely in HTML")


def test_markdown_model_content_and_backtick_fences():
    print("\n=== Testing Markdown Model Content & Code Fences ===")

    # 1. Backtick fence generator logic
    fence_cases = [
        ("No backticks", 3),
        ("Single ` backtick", 3),
        ("Double `` backticks", 3),
        ("Triple ``` backticks", 4),
        ("Quadruple ```` backticks", 5),
        ("Mixed ``` and ```` and `````", 6),
        ("10 backticks " + "`" * 10, 11),
    ]

    for content, expected_len in fence_cases:
        fence = _get_code_fence(content)
        assert len(fence) == expected_len, f"Expected fence len {expected_len}, got {len(fence)} for {content!r}"
        assert fence == "`" * expected_len
        print(f"  [PASS] Fence for '{content[:20]}...' -> len {len(fence)} ('{fence}')")

    # 2. Model message content escaping in Markdown
    model_content_test = "Assistant output with <script>alert(1)</script> and <thinking>secret</thinking> and `code`."
    event = NormalizedEvent(
        event_id="e_model",
        timestamp="2026-08-06T12:00:00Z",
        source="model",
        type="message",
        content=model_content_test,
    )
    session = NormalizedSession(
        session_id="s_model_test",
        source_file=Path("s_model.jsonl"),
        events=[event],
    )

    ctrl_md, full_md, concise_md, _, _ = render_session_to_all_formats(
        session,
        "slug_model_test",
        "2026-08-06T12:00:00Z",
        "2026-08-06T12:00:00Z",
        "2026-08-06T12:00:00Z",
        True,
        {},
        None,
    )

    assert "<script>" not in ctrl_md, "Unescaped <script> tag in controller_md model content"
    assert "<thinking>" not in ctrl_md, "Unescaped <thinking> tag in controller_md model content"
    assert "&lt;script&gt;" in ctrl_md, "Missing HTML entity &lt;script&gt; in controller_md model content"
    assert "&lt;thinking&gt;" in ctrl_md, "Missing HTML entity &lt;thinking&gt; in controller_md model content"
    print("  [PASS] Model message content properly escaped in Markdown output")


def test_tool_output_fence_formatting():
    print("\n=== Testing Tool Output Code Fence Formatting ===")
    tool_output_with_triple = "```python\nprint('hello')\n```"
    formatted = _format_tool_output_markdown(tool_output_with_triple)
    assert formatted.startswith("````\n"), f"Expected 4 backticks opening fence, got: {formatted[:10]!r}"
    assert formatted.endswith("\n````"), f"Expected 4 backticks closing fence, got: {formatted[-10:]!r}"
    print("  [PASS] Tool output with triple backticks properly enclosed in 4-backtick fence")

    tool_output_with_quad = "````\nCode with 4 backticks\n````"
    formatted_quad = _format_tool_output_markdown(tool_output_with_quad)
    assert formatted_quad.startswith("`````\n"), f"Expected 5 backticks opening fence, got: {formatted_quad[:10]!r}"
    assert formatted_quad.endswith("\n`````"), f"Expected 5 backticks closing fence, got: {formatted_quad[-10:]!r}"
    print("  [PASS] Tool output with 4 backticks properly enclosed in 5-backtick fence")


if __name__ == "__main__":
    test_html_metadata_escaping()
    test_markdown_model_content_and_backtick_fences()
    test_tool_output_fence_formatting()
    print("\nAll targeted challenger tests PASSED successfully!")
