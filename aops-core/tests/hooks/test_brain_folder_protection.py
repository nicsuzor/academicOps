"""Tests for brain folder creation protection.

This gate blocks new folder creation in ~/brain to prevent folder proliferation.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import HookContext
from lib.gate_types import GateState, GateStatus
from lib.gates.custom_conditions import check_custom_condition
from lib.session_state import SessionState


@pytest.fixture
def mock_session_state():
    """Create a minimal session state for testing."""
    return SessionState.create("test-session")


@pytest.fixture
def gate_state():
    """Create a gate state for testing."""
    return GateState(status=GateStatus.OPEN)


def make_context(tool_name: str, tool_input: dict) -> HookContext:
    """Create a HookContext for testing."""
    return HookContext(
        session_id="test-session",
        trace_id="test-trace",
        hook_event="PreToolUse",
        tool_name=tool_name,
        tool_input=tool_input,
    )


class TestBrainFolderWriteProtection:
    """Test Write tool protection for brain folders."""

    def test_blocks_write_to_new_subfolder(self, mock_session_state, gate_state, tmp_path):
        """Write to a new subfolder in brain should be blocked."""
        # Create a fake brain root that exists
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Write",
                {"file_path": f"{fake_brain}/new-category/note.md", "content": "test"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is True
            assert "new-category" in gate_state.metrics.get("blocked_path", "")

    def test_allows_write_to_existing_folder(self, mock_session_state, gate_state, tmp_path):
        """Write to an existing folder in brain should be allowed."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()
        existing_folder = fake_brain / "existing-category"
        existing_folder.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Write",
                {
                    "file_path": f"{existing_folder}/note.md",
                    "content": "test",
                },
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is False

    def test_allows_write_to_brain_root(self, mock_session_state, gate_state, tmp_path):
        """Write directly to brain root should be allowed."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Write",
                {"file_path": f"{fake_brain}/note.md", "content": "test"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is False

    def test_allows_write_outside_brain(self, mock_session_state, gate_state, tmp_path):
        """Write outside brain directory should be allowed."""
        ctx = make_context(
            "Write",
            {"file_path": f"{tmp_path}/other/new-folder/file.txt", "content": "test"},
        )
        result = check_custom_condition("creates_brain_folder", ctx, gate_state, mock_session_state)
        assert result is False


class TestBrainFolderBashProtection:
    """Test Bash command protection for brain folders."""

    def test_blocks_mkdir_new_folder(self, mock_session_state, gate_state, tmp_path):
        """mkdir for new brain folder should be blocked."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Bash",
                {"command": f"mkdir {fake_brain}/new-project"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is True

    def test_blocks_mkdir_p_new_folder(self, mock_session_state, gate_state, tmp_path):
        """mkdir -p for new brain folder should be blocked."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Bash",
                {"command": f"mkdir -p {fake_brain}/deeply/nested/new"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is True

    def test_allows_mkdir_existing_folder(self, mock_session_state, gate_state, tmp_path):
        """mkdir for existing brain folder should be allowed (mkdir will fail gracefully)."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()
        existing = fake_brain / "existing"
        existing.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Bash",
                {"command": f"mkdir {existing}"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is False

    def test_allows_mkdir_outside_brain(self, mock_session_state, gate_state, tmp_path):
        """mkdir outside brain should be allowed."""
        ctx = make_context(
            "Bash",
            {"command": f"mkdir {tmp_path}/other-project"},
        )
        result = check_custom_condition("creates_brain_folder", ctx, gate_state, mock_session_state)
        assert result is False

    def test_handles_tilde_expansion(self, mock_session_state, gate_state, tmp_path):
        """mkdir with ~/brain path should be detected."""
        fake_brain = tmp_path / "brain"
        fake_brain.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            ctx = make_context(
                "Bash",
                {"command": "mkdir ~/brain/new-folder"},
            )
            result = check_custom_condition(
                "creates_brain_folder", ctx, gate_state, mock_session_state
            )
            assert result is True


class TestOtherTools:
    """Test that other tools are not affected."""

    def test_read_tool_not_affected(self, mock_session_state, gate_state):
        """Read tool should not trigger the condition."""
        ctx = make_context(
            "Read",
            {"file_path": "/home/nic/brain/new-folder/file.md"},
        )
        result = check_custom_condition("creates_brain_folder", ctx, gate_state, mock_session_state)
        assert result is False

    def test_glob_tool_not_affected(self, mock_session_state, gate_state):
        """Glob tool should not trigger the condition."""
        ctx = make_context(
            "Glob",
            {"pattern": "/home/nic/brain/**/*.md"},
        )
        result = check_custom_condition("creates_brain_folder", ctx, gate_state, mock_session_state)
        assert result is False
