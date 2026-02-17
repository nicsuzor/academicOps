"""Tests for extract_recent_context in insights_generator."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from lib.insights_generator import extract_recent_context
from lib.transcript_parser import SessionInfo

_DUMMY_DT = datetime(2025, 1, 1, tzinfo=UTC)


class TestExtractRecentContext:
    """Test actual transcript extraction logic."""

    @patch("lib.insights_generator.find_sessions")
    @patch("lib.insights_generator.extract_gate_context")
    def test_extract_by_session_id(self, mock_extract, mock_find):
        """Test extracting context using a session ID."""
        session_id = "test-session-123"
        mock_path = Path("/tmp/test-session-123.jsonl")
        mock_session = SessionInfo(
            path=mock_path,
            project="test-project",
            session_id=session_id,
            last_modified=_DUMMY_DT,
        )
        mock_find.return_value = [mock_session]
        mock_extract.return_value = {"conversation": ["[User]: Hello", "[Agent]: Hi there"]}

        result = extract_recent_context(session_id)

        assert result == "[User]: Hello\n\n[Agent]: Hi there"
        mock_find.assert_called_once()
        mock_extract.assert_called_once_with(mock_path, include={"conversation"}, max_turns=20)

    @patch("lib.insights_generator.find_sessions")
    @patch("lib.insights_generator.extract_gate_context")
    def test_extract_by_short_hash(self, mock_extract, mock_find):
        """Test extracting context where input is full ID but on-disk is short hash."""
        session_id = "a1b2c3d4e5f6g7h8"
        short_hash = "a1b2c3d4"
        mock_path = Path("/tmp/a1b2c3d4.jsonl")
        mock_session = SessionInfo(
            path=mock_path,
            project="test-project",
            session_id=short_hash,
            last_modified=_DUMMY_DT,
        )
        mock_find.return_value = [mock_session]
        mock_extract.return_value = {"conversation": ["[User]: Request"]}

        result = extract_recent_context(session_id)

        assert result == "[User]: Request"
        mock_find.assert_called_once()
        mock_extract.assert_called_once_with(mock_path, include={"conversation"}, max_turns=20)

    @patch("lib.insights_generator.find_sessions")
    @patch("lib.insights_generator.extract_gate_context")
    def test_extract_by_prefix(self, mock_extract, mock_find):
        """Test extracting context where input is short hash but on-disk is full ID."""
        session_id = "a1b2c3d4"
        full_id = "a1b2c3d4e5f6g7h8"
        mock_path = Path("/tmp/full.jsonl")
        mock_session = SessionInfo(
            path=mock_path,
            project="test-project",
            session_id=full_id,
            last_modified=_DUMMY_DT,
        )
        mock_find.return_value = [mock_session]
        mock_extract.return_value = {"conversation": ["[User]: Prefix match"]}

        result = extract_recent_context(session_id)

        assert result == "[User]: Prefix match"
        mock_find.assert_called_once()
        mock_extract.assert_called_once_with(mock_path, include={"conversation"}, max_turns=20)

    @patch("lib.insights_generator.extract_gate_context")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_extract_by_direct_path(self, mock_is_file, mock_exists, mock_extract):
        """Test extracting context using a direct file path."""
        file_path = "/tmp/direct.jsonl"
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_extract.return_value = {"conversation": ["[User]: Direct path"]}

        result = extract_recent_context(file_path)

        assert result == "[User]: Direct path"
        mock_extract.assert_called_once_with(Path(file_path), include={"conversation"}, max_turns=20)

    @patch("lib.insights_generator.find_sessions")
    def test_session_not_found(self, mock_find):
        """Test behavior when session is not found."""
        mock_find.return_value = []

        result = extract_recent_context("non-existent")

        assert result == ""

    @patch("lib.insights_generator.find_sessions")
    @patch("lib.insights_generator.extract_gate_context")
    def test_empty_conversation(self, mock_extract, mock_find):
        """Test behavior when conversation is empty."""
        session_id = "empty-session"
        mock_session = SessionInfo(
            path=Path("/tmp/empty.jsonl"),
            project="test",
            session_id=session_id,
            last_modified=_DUMMY_DT,
        )
        mock_find.return_value = [mock_session]
        mock_extract.return_value = {"conversation": []}

        result = extract_recent_context(session_id)

        assert result == ""

    @patch("lib.insights_generator.find_sessions")
    def test_empty_session_id_returns_empty(self, mock_find):
        """Test that empty or whitespace-only session IDs return empty string."""
        assert extract_recent_context("") == ""
        assert extract_recent_context("   ") == ""
        mock_find.assert_not_called()
