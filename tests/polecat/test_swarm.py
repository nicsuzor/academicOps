"""Tests for polecat swarm functionality, including gemini_stagger feature."""

import multiprocessing
import sys
import time
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from swarm import DEFAULT_GEMINI_STAGGER_S, STOP_EVENT, run_swarm


@pytest.fixture(autouse=True)
def reset_stop_event():
    """Reset STOP_EVENT before each test."""
    STOP_EVENT.clear()
    yield
    STOP_EVENT.clear()


class TestGeminiStagger:
    """Tests for Gemini worker spawn stagger functionality."""

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_gemini_stagger_default_delay(self, mock_sleep, mock_process):
        """Test that Gemini workers spawn with default 15s stagger delay."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=0,
            gemini_count=3,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=None,  # Use default
        )

        # Assert: First worker spawns immediately, subsequent workers have stagger
        # Expected sleep calls: 2 (for workers 1 and 2, not worker 0)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([
            call(DEFAULT_GEMINI_STAGGER_S),
            call(DEFAULT_GEMINI_STAGGER_S),
        ])

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_gemini_stagger_custom_delay(self, mock_sleep, mock_process):
        """Test that custom gemini_stagger value is respected."""
        # Arrange
        custom_stagger = 5.0
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=0,
            gemini_count=2,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=custom_stagger,
        )

        # Assert: Only 1 sleep call for second worker
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_once_with(custom_stagger)

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_gemini_stagger_zero_disables_delay(self, mock_sleep, mock_process):
        """Test that gemini_stagger=0 disables stagger delay."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=0,
            gemini_count=3,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=0.0,
        )

        # Assert: No sleep calls should occur
        assert mock_sleep.call_count == 0

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_gemini_stagger_bypassed_in_dry_run(self, mock_sleep, mock_process):
        """Test that stagger delay is NOT applied in dry_run mode (bypassed)."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act: dry_run=True should bypass sleep even with non-zero stagger
        run_swarm(
            claude_count=0,
            gemini_count=3,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=15.0,
        )

        # Assert: No sleep should happen in dry_run mode
        # Note: The code checks `if i > 0 and stagger > 0 and not dry_run`
        # so dry_run bypasses the stagger
        assert mock_sleep.call_count == 0

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_single_gemini_worker_no_stagger(self, mock_sleep, mock_process):
        """Test that a single Gemini worker spawns without any delay."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=0,
            gemini_count=1,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=15.0,
        )

        # Assert: No stagger needed for single worker
        assert mock_sleep.call_count == 0

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_claude_workers_unaffected_by_gemini_stagger(self, mock_sleep, mock_process):
        """Test that Claude workers spawn without stagger delay."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=3,
            gemini_count=0,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=15.0,
        )

        # Assert: Claude workers should spawn without any stagger
        assert mock_sleep.call_count == 0

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    def test_mixed_workers_only_gemini_staggers(self, mock_sleep, mock_process):
        """Test that only Gemini workers get stagger delay in mixed swarm."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=2,
            gemini_count=2,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
            gemini_stagger=10.0,
        )

        # Assert: Only 1 sleep call for second Gemini worker
        # (first Gemini worker doesn't sleep, only i > 0)
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_once_with(10.0)

    @patch("swarm.multiprocessing.Process")
    @patch("swarm.time.sleep")
    @patch("swarm.STOP_EVENT")
    def test_stop_event_during_stagger_prevents_spawn(self, mock_stop_event, mock_sleep, mock_process):
        """Test that STOP_EVENT during stagger prevents further Gemini worker spawns."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Simulate STOP_EVENT being set after first sleep
        mock_stop_event.is_set.side_effect = [False, False, True]  # Set after first stagger

        # Act
        run_swarm(
            claude_count=0,
            gemini_count=3,
            project=None,
            caller="test",
            dry_run=False,  # Must be False for stagger to apply
            home_dir=None,
            gemini_stagger=5.0,
        )

        # Assert: Should spawn first worker, sleep once, check STOP_EVENT, and stop
        # First worker (i=0): spawns without sleep
        # Second worker (i=1): sleeps, then checks STOP_EVENT (is_set=True), breaks
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_once_with(5.0)

        # Only 1 Gemini worker process should be created (before STOP_EVENT)
        # Actually, the code spawns worker 0, then sleeps before worker 1,
        # then checks STOP_EVENT and breaks, so 1 worker spawned
        assert mock_process.call_count == 1


class TestSwarmCLI:
    """Tests for CLI argument parsing and parameter passing."""

    @patch("swarm.run_swarm")
    @patch("sys.argv", ["swarm.py", "--claude=1", "--gemini=2", "--gemini-stagger=20"])
    def test_cli_gemini_stagger_flag(self, mock_run_swarm):
        """Test that --gemini-stagger CLI flag is parsed and passed correctly."""
        from swarm import main

        # Act
        main()

        # Assert
        mock_run_swarm.assert_called_once_with(
            1,  # claude
            2,  # gemini
            None,  # project
            "polecat",  # caller
            False,  # dry_run
            None,  # home
            20.0,  # gemini_stagger
        )

    @patch("swarm.run_swarm")
    @patch("sys.argv", ["swarm.py", "--claude=1", "--gemini=2"])
    def test_cli_gemini_stagger_default(self, mock_run_swarm):
        """Test that CLI defaults gemini_stagger to None when not specified."""
        from swarm import main

        # Act
        main()

        # Assert
        mock_run_swarm.assert_called_once_with(
            1,  # claude
            2,  # gemini
            None,  # project
            "polecat",  # caller
            False,  # dry_run
            None,  # home
            None,  # gemini_stagger (uses DEFAULT_GEMINI_STAGGER_S in run_swarm)
        )


class TestSwarmBasicFunctionality:
    """Tests for basic swarm functionality."""

    @patch("swarm.multiprocessing.Process")
    def test_no_workers_exits_immediately(self, mock_process):
        """Test that run_swarm exits immediately if no workers specified."""
        # Act
        run_swarm(
            claude_count=0,
            gemini_count=0,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
        )

        # Assert: No processes should be created
        assert mock_process.call_count == 0

    @patch("swarm.multiprocessing.Process")
    def test_correct_worker_count(self, mock_process):
        """Test that correct number of worker processes are spawned."""
        # Arrange
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Act
        run_swarm(
            claude_count=2,
            gemini_count=3,
            project=None,
            caller="test",
            dry_run=True,
            home_dir=None,
        )

        # Assert: 5 total workers (2 claude + 3 gemini)
        assert mock_process.call_count == 5
