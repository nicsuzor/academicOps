"""Tests for P#26 file read tracking in session_state.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


class TestFileReadTracking:
    """Tests for P#26 file read tracking API."""

    def test_record_file_read_creates_entry(self, tmp_path: Path) -> None:
        """record_file_read adds file to files_read list."""
        from lib import session_state

        # Set up isolated session state directory
        state_dir = tmp_path / "sessions" / "status"
        state_dir.mkdir(parents=True)

        with patch("lib.session_paths.get_session_status_dir", return_value=state_dir):
            session_id = "test-file-read-session"
            test_file = "/home/user/project/file.py"

            # Record a file read
            session_state.record_file_read(session_id, test_file)

            # Verify the file is tracked
            assert session_state.has_file_been_read(session_id, test_file)

    def test_has_file_been_read_returns_false_for_unread(self, tmp_path: Path) -> None:
        """has_file_been_read returns False for files not read."""
        from lib import session_state

        state_dir = tmp_path / "sessions" / "status"
        state_dir.mkdir(parents=True)

        with patch("lib.session_paths.get_session_status_dir", return_value=state_dir):
            session_id = "test-unread-session"
            test_file = "/home/user/project/unread.py"

            # File not read yet
            assert not session_state.has_file_been_read(session_id, test_file)

    def test_record_file_read_normalizes_path(self, tmp_path: Path) -> None:
        """record_file_read normalizes paths for consistent tracking."""
        from lib import session_state

        state_dir = tmp_path / "sessions" / "status"
        state_dir.mkdir(parents=True)

        # Create a real file for path resolution
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        with patch("lib.session_paths.get_session_status_dir", return_value=state_dir):
            session_id = "test-normalize-session"

            # Record with one path format
            session_state.record_file_read(session_id, str(test_file))

            # Check with resolved path
            resolved = str(test_file.resolve())
            assert session_state.has_file_been_read(session_id, resolved)

    def test_record_file_read_avoids_duplicates(self, tmp_path: Path) -> None:
        """record_file_read doesn't add duplicate entries."""
        from lib import session_state

        state_dir = tmp_path / "sessions" / "status"
        state_dir.mkdir(parents=True)

        with patch("lib.session_paths.get_session_status_dir", return_value=state_dir):
            session_id = "test-duplicate-session"
            test_file = "/home/user/project/file.py"

            # Record same file multiple times
            session_state.record_file_read(session_id, test_file)
            session_state.record_file_read(session_id, test_file)
            session_state.record_file_read(session_id, test_file)

            # Verify only one entry
            files = session_state.get_files_read(session_id)
            # Count occurrences of the normalized path
            from pathlib import Path as P

            try:
                normalized = str(P(test_file).resolve())
            except (OSError, ValueError):
                normalized = test_file
            count = sum(1 for f in files if f == normalized)
            assert count == 1

    def test_get_files_read_returns_all_files(self, tmp_path: Path) -> None:
        """get_files_read returns list of all tracked files."""
        from lib import session_state

        state_dir = tmp_path / "sessions" / "status"
        state_dir.mkdir(parents=True)

        with patch("lib.session_paths.get_session_status_dir", return_value=state_dir):
            session_id = "test-all-files-session"

            # Record multiple files
            files_to_read = [
                "/home/user/project/a.py",
                "/home/user/project/b.py",
                "/home/user/project/c.py",
            ]
            for f in files_to_read:
                session_state.record_file_read(session_id, f)

            # Verify all are returned
            tracked_files = session_state.get_files_read(session_id)
            assert len(tracked_files) == 3

    def test_has_file_been_read_returns_false_for_no_state(self) -> None:
        """has_file_been_read returns False when no session state exists."""
        from lib import session_state

        # Use a session that doesn't exist
        with patch.object(session_state, "load_session_state", return_value=None):
            assert not session_state.has_file_been_read("nonexistent", "/some/file.py")

    def test_get_files_read_returns_empty_for_no_state(self) -> None:
        """get_files_read returns empty list when no session state exists."""
        from lib import session_state

        with patch.object(session_state, "load_session_state", return_value=None):
            assert session_state.get_files_read("nonexistent") == []
