"""Adversarial stress tests for Milestone R4 Iteration 3 HTML rendering and quote escaping.

This test file stress-tests _escape_html and all HTML attribute/element context renderings in
lib/py/transcripts/domain/renderer.py against adversarial payloads including quote breakouts,
HTML injection, null bytes, unicode quotes, multi-line breakouts, and non-string inputs.
"""

from __future__ import annotations

from pathlib import Path

from transcripts.domain.renderer import (
    _escape_html,
    render_to_html,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)


class TestEscapeHtmlAdversarial:
    """Direct unit tests for _escape_html with adversarial payloads."""

    def test_basic_quote_and_xml_escaping(self):
        raw = '<script>alert("XSS & \'breakout\'")</script>'
        escaped = _escape_html(raw)
        assert "<" not in escaped
        assert ">" not in escaped
        assert '"' not in escaped
        assert "'" not in escaped
        assert escaped == '&lt;script&gt;alert(&quot;XSS &amp; &#x27;breakout&#x27;&quot;)&lt;/script&gt;'

    def test_double_quotes(self):
        raw = 'attr="value" title="hello"'
        escaped = _escape_html(raw)
        assert '"' not in escaped
        assert "&quot;" in escaped

    def test_single_quotes(self):
        raw = "attr='value' title='hello'"
        escaped = _escape_html(raw)
        assert "'" not in escaped
        assert "&#x27;" in escaped

    def test_mixed_quotes_and_ampersands(self):
        raw = 'a="1" & b=\'2\' & c=<3>'
        escaped = _escape_html(raw)
        assert '"' not in escaped
        assert "'" not in escaped
        assert "<" not in escaped
        assert ">" not in escaped
        assert escaped == 'a=&quot;1&quot; &amp; b=&#x27;2&#x27; &amp; c=&lt;3&gt;'

    def test_backticks(self):
        raw = "`backticks` standard HTML attribute string"
        escaped = _escape_html(raw)
        assert "`backticks` standard HTML attribute string" == escaped

    def test_null_bytes(self):
        raw = "hello\x00world\"'<&>"
        escaped = _escape_html(raw)
        assert '"' not in escaped
        assert "'" not in escaped
        assert "<" not in escaped
        assert ">" not in escaped
        assert escaped == "hello\x00world&quot;&#x27;&lt;&amp;&gt;"

    def test_unicode_quotes(self):
        # Curly/smart quotes
        raw = '“smart double” ‘smart single’'
        escaped = _escape_html(raw)
        assert escaped == '“smart double” ‘smart single’'

    def test_multiline_quote_breakouts(self):
        raw = "\"\n> <script>alert('breakout')</script>\n\""
        escaped = _escape_html(raw)
        assert '"' not in escaped
        assert "<" not in escaped
        assert ">" not in escaped
        assert "'" not in escaped

    def test_non_string_types(self):
        assert _escape_html(123) == "123"
        assert _escape_html(45.67) == "45.67"
        assert _escape_html(True) == "True"
        assert _escape_html(None) == "None"
        assert _escape_html(["<tag>"]) == "[&#x27;&lt;tag&gt;&#x27;]"


class TestHTMLAttributeContexts:
    """Stress tests for HTML attribute and element contexts in rendered HTML output."""

    def test_filename_base_attribute_breakout_prevention(self):
        """Test <a href="./{filename_base}.full.md"> attribute context with breakout payload."""
        adversarial_filename = 'session" onclick="alert(1)" id="hacked'
        subagent = SubagentTranscript(
            agent_id="sub_001",
            source_file=Path("sub.jsonl"),
            agent_type="analyst",
            name="Analyst",
            description='Subagent "description" <script>',
            parent_tool_use_id="toolu_1",
            events=[],
        )
        session = NormalizedSession(
            session_id='sess_"123"',
            source_file=Path("test.jsonl"),
            events=[],
            subagents=[subagent],
        )

        html_out = render_to_html(
            session=session,
            slug=adversarial_filename,
            started_at="2026-08-06",
            ended_at="2026-08-06",
            last_modified="2026-08-06",
            has_user_context=True,
            correlation={"project": 'proj"name', "task_id": "task'<script>"},
            insights="Insights & 'reflections'",
        )

        # Check href attribute context: double quotes are &quot;, so no breakout occurs
        assert 'href="./20260806-00-proj&quot;name-session&quot; onclick=&quot;alert(1)&quot; id=&quot;hacked.full.md"' in html_out
        assert 'onclick="alert(1)"' not in html_out
        assert 'id="hacked' not in html_out

    def test_session_metadata_quote_and_tag_safety(self):
        """Test session metadata fields in HTML header and meta grid."""
        session = NormalizedSession(
            session_id='sess_<script>alert("id")</script>',
            source_file=Path("test.jsonl"),
            events=[],
        )
        html_out = render_to_html(
            session=session,
            slug='slug_"quoted"',
            started_at='2026"onload="alert(1)',
            ended_at="2026",
            last_modified="2026",
            has_user_context=True,
            correlation={"project": 'proj"<script>', "task_id": "task'injection"},
            insights=None,
        )

        assert '<title>Session sess_&lt;script&gt;alert(&quot;id&quot;)&lt;/script&gt;</title>' in html_out
        assert '<h1>Session sess_&lt;script&gt;alert(&quot;id&quot;)&lt;/script&gt;</h1>' in html_out
        assert '<strong>Slug</strong>slug_&quot;quoted&quot;' in html_out
        assert 'proj&quot;&lt;script&gt;' in html_out

    def test_event_prompt_kind_and_source_escaping(self):
        """Stress-test prompt_kind, source, and timestamp in events."""
        event_injected = NormalizedEvent(
            event_id="e1",
            timestamp='2026-08-06',
            source="user",
            type="message",
            content="Injected content",
            meta={
                "is_human": False,
                "prompt_kind": 'system"<script>alert(1)</script>',
                "injected_content": 'Injected context with <script>alert("xss")</script> and "quotes"',
            },
        )
        session = NormalizedSession(
            session_id="s1",
            source_file=Path("s1.jsonl"),
            events=[event_injected],
        )

        html_out = render_to_html(
            session=session,
            slug="s1",
            started_at="2026",
            ended_at="2026",
            last_modified="2026",
            has_user_context=True,
            correlation={},
            insights=None,
        )

        # Check prompt_kind escaping in badge:
        assert 'Injected Context (system&quot;&lt;script&gt;alert(1)&lt;/script&gt;)' in html_out or 'system&quot;&lt;script&gt;' in html_out

    def test_tool_call_args_and_names_escaping(self):
        """Test tool call names and JSON args escaping in HTML."""
        event_tool = NormalizedEvent(
            event_id="e2",
            timestamp="2026-08-06",
            source="model",
            type="message",
            content="Calling tool",
            tool_calls=[
                NormalizedToolCall(
                    name='tool_<script>alert("name")</script>',
                    args={"arg1": 'val"<script>alert("arg")</script>'},
                    call_id="call_1",
                )
            ],
        )
        session = NormalizedSession(
            session_id="s2",
            source_file=Path("s2.jsonl"),
            events=[event_tool],
        )

        html_out = render_to_html(
            session=session,
            slug="s2",
            started_at="2026",
            ended_at="2026",
            last_modified="2026",
            has_user_context=True,
            correlation={},
            insights=None,
        )

        assert 'tool_&lt;script&gt;alert(&quot;name&quot;)&lt;/script&gt;' in html_out
        assert r'val\&quot;&lt;script&gt;alert(\&quot;arg\&quot;)&lt;/script&gt;' in html_out
        assert '<script>alert("name")</script>' not in html_out

    def test_untrusted_header_title_and_source_class_vulnerability(self):
        """Stress-test event.source and event.timestamp for raw unescaped injection in HTML DOM."""
        event_custom = NormalizedEvent(
            event_id="e3",
            timestamp='2026-08-06<script>alert("ts")</script>',
            source='custom"<script>alert("source")</script>',
            type="message",
            content="Custom event content",
        )
        session = NormalizedSession(
            session_id="s3",
            source_file=Path("s3.jsonl"),
            events=[event_custom],
        )

        html_out = render_to_html(
            session=session,
            slug="s3",
            started_at="2026",
            ended_at="2026",
            last_modified="2026",
            has_user_context=True,
            correlation={},
            insights=None,
        )

        # Demonstrate whether event.source and event.timestamp allow raw HTML injection
        has_source_xss = '<script>alert("source")</script>' in html_out
        has_ts_xss = '<script>alert("ts")</script>' in html_out

        # Store finding: event.source and event.timestamp are currently NOT escaped in event headers!
        assert has_source_xss is True or has_ts_xss is True, "Expected to detect unescaped HTML vulnerability in event header/source"
