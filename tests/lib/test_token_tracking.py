"""Tests for token tracking in transcript parser."""

from datetime import datetime

import pytest

from lib.transcript_parser import Entry, TimingInfo, ConversationTurn


class TestTokenExtraction:
    """Test token extraction from JSONL entries."""

    def test_extract_input_tokens(self):
        """Test extracting input_tokens from message.usage."""
        data = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 1250,
                    "output_tokens": 820
                }
            }
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 1250
        assert entry.output_tokens == 820

    def test_extract_output_tokens(self):
        """Test extracting output_tokens from message.usage."""
        data = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 1200
                }
            }
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 500
        assert entry.output_tokens == 1200

    def test_missing_usage_defaults_to_none(self):
        """Test that missing usage dict defaults tokens to None."""
        data = {
            "type": "assistant",
            "message": {}
        }
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
        data = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 1000
                }
            }
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 1000
        assert entry.output_tokens is None

    def test_zero_tokens(self):
        """Test that zero token values are preserved."""
        data = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            }
        }
        entry = Entry.from_dict(data)
        assert entry.input_tokens == 0
        assert entry.output_tokens == 0

    def test_large_token_counts(self):
        """Test handling large token counts."""
        data = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 100000,
                    "output_tokens": 50000
                }
            }
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
            "Bash": {"duration": 1.2, "count": 1}
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
            "message": {"content": "Hello"}
        }
        entry = Entry.from_dict(legacy_data)
        assert entry.type == "user"
        assert entry.uuid == "abc-123"
        assert entry.input_tokens is None
        assert entry.output_tokens is None

    def test_timing_info_legacy_initialization(self):
        """Test that legacy TimingInfo creation still works."""
        timing = TimingInfo(
            is_first=True,
            offset_from_start="+00:30",
            duration="30s"
        )
        assert timing.is_first is True
        assert timing.offset_from_start == "+00:30"
        assert timing.duration == "30s"
        assert timing.total_tokens is None

    def test_conversation_turn_legacy_fields(self):
        """Test that legacy ConversationTurn fields still work."""
        turn = ConversationTurn(
            user_message="Test",
            timing_info=TimingInfo()
        )
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
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Verify per-turn token counts appear in output
        assert "1,500 in" in markdown, "Input tokens should appear in transcript"
        assert "250 out" in markdown, "Output tokens should appear in transcript"
        assert "tokens" in markdown, "Token label should appear"

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
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

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
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

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
                    "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "result"}]
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
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Tokens should be aggregated: 500+700=1200 in, 100+150=250 out
        assert "1,200 in" in markdown, "Aggregated input tokens should appear"
        assert "250 out" in markdown, "Aggregated output tokens should appear"
