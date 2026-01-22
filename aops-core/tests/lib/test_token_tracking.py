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
