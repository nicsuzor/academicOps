"""Tests for token tracking in transcript parser."""

from lib.transcript_parser import (
    ConversationTurn,
    Entry,
    SessionProcessor,
    TimingInfo,
    UsageStats,
    _estimate_tokens,
    _format_token_count,
)


class TestTokenExtraction:
    """Test token extraction from JSONL entries."""

    def test_extract_input_tokens(self):
        """Test extracting input_tokens from message.usage."""
        data = {
            "type": "assistant",
            "message": {"usage": {"input_tokens": 1250, "output_tokens": 820}},
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 1250
        assert entry.output_tokens == 820

    def test_extract_output_tokens(self):
        """Test extracting output_tokens from message.usage."""
        data = {
            "type": "assistant",
            "message": {"usage": {"input_tokens": 500, "output_tokens": 1200}},
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 500
        assert entry.output_tokens == 1200

    def test_missing_usage_defaults_to_none(self):
        """Test that missing usage dict defaults tokens to None."""
        data = {"type": "assistant", "message": {}}
        entry = Entry.from_dict(data)
        assert entry.input_tokens is None
        assert entry.output_tokens is None

    def test_missing_usage_key_entirely(self):
        """Test that message without usage key defaults tokens to None."""
        data = {
            "type": "user",
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens is None
        assert entry.output_tokens is None

    def test_partial_usage_data(self):
        """Test that partial usage data is handled correctly."""
        data = {"type": "assistant", "message": {"usage": {"input_tokens": 1000}}}
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 1000
        assert entry.output_tokens is None

    def test_zero_tokens(self):
        """Test that zero token values are preserved."""
        data = {
            "type": "assistant",
            "message": {"usage": {"input_tokens": 0, "output_tokens": 0}},
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 0
        assert entry.output_tokens == 0

    def test_large_token_counts(self):
        """Test handling large token counts."""
        data = {
            "type": "assistant",
            "message": {"usage": {"input_tokens": 100000, "output_tokens": 50000}},
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 100000
        assert entry.output_tokens == 50000


class TestTimingInfoTokenFields:
    """Test TimingInfo token tracking fields."""

    def test_timing_info_default_total_tokens_none(self):
        """Test that total_tokens defaults to None."""
        timing = TimingInfo()
        assert timing.total_tokens is None
        assert timing.estimated_tokens is False

    def test_timing_info_set_total_tokens(self):
        """Test setting total_tokens on TimingInfo."""
        timing = TimingInfo(total_tokens=2070, estimated_tokens=False)
        assert timing.total_tokens == 2070
        assert timing.estimated_tokens is False

    def test_timing_info_estimated_tokens_flag(self):
        """Test estimated_tokens flag on TimingInfo."""
        timing = TimingInfo(total_tokens=2000, estimated_tokens=True)
        assert timing.total_tokens == 2000
        assert timing.estimated_tokens is True


class TestConversationTurnTokenFields:
    """Test ConversationTurn token tracking fields."""

    def test_conversation_turn_tool_timings_default(self):
        """Test that tool_timings defaults to empty dict."""
        turn = ConversationTurn()
        assert turn.tool_timings == {}
        assert isinstance(turn.tool_timings, dict)

    def test_conversation_turn_tool_timings_populated(self):
        """Test populating tool_timings dict."""
        tool_timings = {
            "Read": {"duration": 0.5, "count": 1},
            "Bash": {"duration": 1.2, "count": 1},
        }
        turn = ConversationTurn(tool_timings=tool_timings)
        assert turn.tool_timings == tool_timings
        assert turn.tool_timings["Read"]["duration"] == 0.5
        assert turn.tool_timings["Bash"]["count"] == 1

    def test_conversation_turn_tool_timings_isolation(self):
        """Test that tool_timings dicts are isolated between instances."""
        turn1 = ConversationTurn()
        turn2 = ConversationTurn()
        turn1.tool_timings["Test"] = {"data": "value"}
        assert "Test" not in turn2.tool_timings


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing code."""

    def test_entry_creation_without_tokens(self):
        """Test creating Entry without token fields still works."""
        entry = Entry(type="user")
        assert entry.input_tokens is None
        assert entry.output_tokens is None

    def test_entry_from_dict_legacy_data(self):
        """Test that legacy JSONL data without tokens works."""
        legacy_data = {
            "type": "user",
            "uuid": "abc-123",
            "message": {"content": "Hello"},
        }
        entry = Entry.from_dict(legacy_data)
        assert entry.type == "user"
        assert entry.uuid == "abc-123"
        assert entry.input_tokens is None
        assert entry.output_tokens is None

    def test_timing_info_legacy_initialization(self):
        """Test that legacy TimingInfo creation still works."""
        timing = TimingInfo(is_first=True, offset_from_start="+00:30", duration="30s")
        assert timing.is_first is True
        assert timing.offset_from_start == "+00:30"
        assert timing.duration == "30s"
        assert timing.total_tokens is None

    def test_conversation_turn_legacy_fields(self):
        """Test that legacy ConversationTurn fields still work."""
        turn = ConversationTurn(user_message="Test", timing_info=TimingInfo())
        assert turn.user_message == "Test"
        assert turn.timing_info is not None
        assert turn.tool_timings == {}


class TestPerTurnTokensInTranscript:
    """Test per-turn token display in transcript markdown output."""

    def test_per_turn_tokens_displayed_in_markdown(self, tmp_path):
        """Verify per-turn tokens appear in transcript output.

        This tests the full flow:
        1. JSONL entries with message.usage tokens
        2. Entry.from_dict extracts tokens
        3. group_entries_into_turns aggregates tokens per turn
        4. format_session_as_markdown displays tokens
        """
        import json

        from lib.session_reader import SessionProcessor

        session_file = tmp_path / "session.jsonl"

        # Create entries with token usage in assistant messages
        entries = [
            {
                "type": "user",
                "uuid": "user-1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "Hello"}]},
            },
            {
                "type": "assistant",
                "uuid": "assistant-1",
                "timestamp": "2026-01-15T10:00:05Z",
                "message": {
                    "content": [{"type": "text", "text": "Hi there!"}],
                    "usage": {
                        "input_tokens": 1500,
                        "output_tokens": 250,
                        "cache_read_input_tokens": 800,
                        "cache_creation_input_tokens": 200,
                    },
                },
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Verify per-turn token counts appear in output
        assert "1,500 in" in markdown, "Input tokens should appear in transcript"
        assert "250 out" in markdown, "Output tokens should appear in transcript"
        assert "Token" in markdown, "Token label should appear"

    def test_per_turn_cache_tokens_displayed(self, tmp_path):
        """Verify cache tokens (read and create) are displayed per turn."""
        import json

        from lib.session_reader import SessionProcessor

        session_file = tmp_path / "session.jsonl"

        entries = [
            {
                "type": "user",
                "uuid": "user-1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "Test cache tokens"}]},
            },
            {
                "type": "assistant",
                "uuid": "assistant-1",
                "timestamp": "2026-01-15T10:00:05Z",
                "message": {
                    "content": [{"type": "text", "text": "Response"}],
                    "usage": {
                        "input_tokens": 2000,
                        "output_tokens": 500,
                        "cache_read_input_tokens": 1500,
                        "cache_creation_input_tokens": 300,
                    },
                },
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Verify cache tokens appear with arrows
        assert "1,500 cache↓" in markdown, "Cache read tokens should appear with ↓"
        assert "300 cache↑" in markdown, "Cache create tokens should appear with ↑"

    def test_multi_turn_tokens_aggregated_separately(self, tmp_path):
        """Verify each turn shows its own token totals, not cumulative."""
        import json

        from lib.session_reader import SessionProcessor

        session_file = tmp_path / "session.jsonl"

        entries = [
            # Turn 1
            {
                "type": "user",
                "uuid": "user-1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "First question"}]},
            },
            {
                "type": "assistant",
                "uuid": "assistant-1",
                "timestamp": "2026-01-15T10:00:05Z",
                "message": {
                    "content": [{"type": "text", "text": "First response"}],
                    "usage": {"input_tokens": 1000, "output_tokens": 200},
                },
            },
            # Turn 2
            {
                "type": "user",
                "uuid": "user-2",
                "timestamp": "2026-01-15T10:00:10Z",
                "message": {"content": [{"type": "text", "text": "Second question"}]},
            },
            {
                "type": "assistant",
                "uuid": "assistant-2",
                "timestamp": "2026-01-15T10:00:15Z",
                "message": {
                    "content": [{"type": "text", "text": "Second response"}],
                    "usage": {"input_tokens": 2000, "output_tokens": 400},
                },
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Both turn token counts should appear separately
        assert "1,000 in" in markdown, "Turn 1 input tokens should appear"
        assert "200 out" in markdown, "Turn 1 output tokens should appear"
        assert "2,000 in" in markdown, "Turn 2 input tokens should appear"
        assert "400 out" in markdown, "Turn 2 output tokens should appear"

    def test_multi_assistant_entry_turn_aggregates_tokens(self, tmp_path):
        """Verify tokens from multiple assistant entries in one turn are summed."""
        import json

        from lib.session_reader import SessionProcessor

        session_file = tmp_path / "session.jsonl"

        # Single turn with multiple assistant messages (e.g., tool use flow)
        entries = [
            {
                "type": "user",
                "uuid": "user-1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "Do something"}]},
            },
            {
                "type": "assistant",
                "uuid": "assistant-1",
                "timestamp": "2026-01-15T10:00:05Z",
                "message": {
                    "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}],
                    "usage": {"input_tokens": 500, "output_tokens": 100},
                },
            },
            {
                "type": "user",
                "uuid": "tool-result-1",
                "timestamp": "2026-01-15T10:00:06Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "result",
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "uuid": "assistant-2",
                "timestamp": "2026-01-15T10:00:10Z",
                "message": {
                    "content": [{"type": "text", "text": "Done!"}],
                    "usage": {"input_tokens": 700, "output_tokens": 150},
                },
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Tokens should be aggregated: 500+700=1200 in, 100+150=250 out
        assert "1,200 in" in markdown, "Aggregated input tokens should appear"
        assert "250 out" in markdown, "Aggregated output tokens should appear"


class TestAttentionCounters:
    """Attention counters: user_messages and mid_session_corrections.

    These are emitted on `to_token_metrics()['attention']` and computed by
    `SessionProcessor._aggregate_session_usage` over the main entries list.
    """

    @staticmethod
    def _processor() -> SessionProcessor:
        return SessionProcessor.__new__(SessionProcessor)

    def test_to_token_metrics_surfaces_attention(self):
        stats = UsageStats()
        stats.user_messages = 5
        stats.mid_session_corrections = 2
        metrics = stats.to_token_metrics()
        assert metrics["attention"] == {
            "user_messages": 5,
            "mid_session_corrections": 2,
        }

    def test_dispatch_then_corrections(self):
        entries = [
            Entry(type="user", message={"content": [{"type": "text", "text": "go"}]}),
            Entry(
                type="assistant",
                message={"content": [{"type": "tool_use", "name": "Read"}]},
            ),
            # tool_result wrapper — not a real user message
            Entry(type="user", message={"content": [{"type": "tool_result"}]}),
            Entry(
                type="user",
                message={"content": [{"type": "text", "text": "wait, change tack"}]},
            ),
            Entry(type="user", message={"content": "another correction"}),
        ]
        stats = self._processor()._aggregate_session_usage(entries)
        assert stats.user_messages == 3
        assert stats.mid_session_corrections == 2

    def test_pre_tool_use_user_msgs_are_not_corrections(self):
        entries = [
            Entry(type="user", message={"content": [{"type": "text", "text": "hi"}]}),
            Entry(
                type="assistant",
                message={"content": [{"type": "text", "text": "ok"}]},
            ),
            Entry(
                type="user",
                message={"content": [{"type": "text", "text": "still pre-tool"}]},
            ),
        ]
        stats = self._processor()._aggregate_session_usage(entries)
        assert stats.user_messages == 2
        assert stats.mid_session_corrections == 0

    def test_pure_tool_result_entries_ignored(self):
        entries = [
            Entry(type="user", message={"content": [{"type": "text", "text": "go"}]}),
            Entry(
                type="assistant",
                message={"content": [{"type": "tool_use", "name": "Read"}]},
            ),
            Entry(
                type="user",
                message={"content": [{"type": "tool_result"}, {"type": "tool_result"}]},
            ),
        ]
        stats = self._processor()._aggregate_session_usage(entries)
        assert stats.user_messages == 1
        assert stats.mid_session_corrections == 0

    def test_meta_and_sidechain_user_entries_ignored(self):
        entries = [
            Entry(
                type="user",
                is_meta=True,
                message={"content": [{"type": "text", "text": "meta"}]},
            ),
            Entry(
                type="user",
                is_sidechain=True,
                message={"content": [{"type": "text", "text": "sub"}]},
            ),
            Entry(type="user", message={"content": [{"type": "text", "text": "real"}]}),
        ]
        stats = self._processor()._aggregate_session_usage(entries)
        assert stats.user_messages == 1
        assert stats.mid_session_corrections == 0

    def test_empty_string_user_content_ignored(self):
        entries = [
            Entry(type="user", message={"content": ""}),
            Entry(type="user", message={"content": "   "}),
            Entry(type="user", message={"content": [{"type": "text", "text": "x"}]}),
        ]
        stats = self._processor()._aggregate_session_usage(entries)
        assert stats.user_messages == 1


class TestPerToolResultTokens:
    """Each tool call's result payload gets an approximate token annotation
    appended to its rendered line in the transcript. The estimate is
    ``len(content) // 4``; the rendering uses ``[~N tok]`` to mark it
    as approximate.
    """

    def test_estimate_tokens_basic(self):
        # 100 chars → ~25 tokens
        assert _estimate_tokens("a" * 100) == 25
        assert _estimate_tokens("") == 0
        # Tiny non-empty floors at 1 to make the annotation visible
        assert _estimate_tokens("ab") == 1

    def test_format_token_count_compact(self):
        assert _format_token_count(0) == "0"
        assert _format_token_count(87) == "87"
        assert _format_token_count(1234) == "1.2k"
        assert _format_token_count(12345) == "12k"
        assert _format_token_count(1_234_567) == "1.2M"

    def test_tool_line_carries_token_annotation(self, tmp_path):
        """A session with one Read tool call surfaces ``[~N tok]`` in the
        rendered tool line."""
        import json

        session_file = tmp_path / "session.jsonl"
        big_result = "x" * 4000  # → ~1000 tokens
        records = [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "read it"}]},
            },
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "2026-01-15T10:00:01Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu1",
                            "name": "Read",
                            "input": {"file_path": "/tmp/x"},
                        }
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            },
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-15T10:00:02Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tu1",
                            "content": big_result,
                        }
                    ]
                },
            },
        ]
        with session_file.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)
        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )
        # The annotation must be the approximate form, not a billed count.
        assert "[~1.0k tok]" in markdown, f"Expected token annotation in:\n{markdown}"

    def test_tiny_result_has_no_annotation(self, tmp_path):
        """Empty/tiny results don't deserve a noisy ``[~0 tok]`` tag."""
        import json

        session_file = tmp_path / "session.jsonl"
        records = [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-15T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "do it"}]},
            },
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "2026-01-15T10:00:01Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu1",
                            "name": "Bash",
                            "input": {"command": "true"},
                        }
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            },
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-15T10:00:02Z",
                "message": {
                    "content": [{"type": "tool_result", "tool_use_id": "tu1", "content": ""}]
                },
            },
        ]
        with session_file.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(session_file)
        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )
        assert "[~" not in markdown


class TestCondensedHookHeader:
    """The session-level Hook header collapses event + checkmark + verdict
    + (intro to any system message) into a single line. The body of the
    system message follows as a fenced block; the verdose intermediary
    lines (`**Verdict:** \\`x\\``, `ℹ️ Hook message:`) are removed, as is
    the `_Triggered after assistant message:_` literal under Stop hooks.
    """

    def test_stop_with_warn_verdict_and_message_collapses_to_one_line(self, tmp_path):
        import json

        from lib.transcript_parser import SessionSummary

        hook_file = tmp_path / "stop-hook.jsonl"
        record = {
            "session_id": "sess-stop",
            "hook_event": "Stop",
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 0,
            "output": {
                "system_message": "Halted — review pending.",
                "verdict": "warn",
                "metadata": {},
            },
            "raw_input": {"last_assistant_message": "I'm stopping here."},
        }
        with hook_file.open("w") as f:
            f.write(json.dumps(record) + "\n")

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)
        session = SessionSummary(uuid="sess-stop", summary="t")
        markdown = processor.format_session_as_markdown(
            session, entries, agent_entries=None, variant="full"
        )

        # Single-line condensed header: event + checkmark + verdict + intro.
        assert "### Hook: Stop ✓ — verdict `warn` — ℹ️ Hook message:" in markdown
        # Removed: the standalone `**Verdict:** ...` line that used to follow
        # the heading. (The string matches must be on its own line — i.e.
        # surrounded by newlines — to distinguish from the inline form.)
        assert "\n**Verdict:** `warn`\n" not in markdown
        # Removed: the standalone `ℹ️ Hook message:` paragraph above the
        # fenced body (still allowed as a tail of the condensed header).
        assert "\n\nℹ️ Hook message:\n\n```" not in markdown
        # Removed the "Triggered after" literal — quoted block stands alone.
        assert "_Triggered after assistant message:_" not in markdown
        # The body still appears.
        assert "Halted — review pending." in markdown
        assert "I'm stopping here." in markdown

    def test_stop_with_no_message_only_header_line(self, tmp_path):
        import json

        from lib.transcript_parser import SessionSummary

        hook_file = tmp_path / "stop-hook.jsonl"
        record = {
            "session_id": "sess-stop2",
            "hook_event": "Stop",
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 0,
            "output": {"system_message": None, "verdict": "allow", "metadata": {}},
        }
        with hook_file.open("w") as f:
            f.write(json.dumps(record) + "\n")

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)
        session = SessionSummary(uuid="sess-stop2", summary="t")
        markdown = processor.format_session_as_markdown(
            session, entries, agent_entries=None, variant="full"
        )
        # Default Stop verdict surfaces as `allow`, no intro since no message.
        assert "### Hook: Stop ✓ — verdict `allow`" in markdown
        assert "Hook message" not in markdown
