"""Tests for unified session summary architecture.

TDD tests for lib/session_summary.py - write tests first, then implementation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


class TestSessionSummaryPaths:
    """Test path resolution functions."""

    def test_get_session_summary_dir_uses_aca_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Session summary dir should be under $ACA_DATA/dashboard/sessions/."""
        monkeypatch.setenv("ACA_DATA", "/home/test/data")

        from lib.session_summary import get_session_summary_dir

        result = get_session_summary_dir()
        assert result == Path("/home/test/data/dashboard/sessions")

    def test_get_session_summary_dir_fails_without_aca_data(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should fail fast if ACA_DATA not set."""
        monkeypatch.delenv("ACA_DATA", raising=False)

        from lib.session_summary import get_session_summary_dir

        with pytest.raises(ValueError, match="ACA_DATA"):
            get_session_summary_dir()

    def test_get_task_contributions_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Task contributions file uses session_id as key."""
        monkeypatch.setenv("ACA_DATA", "/home/test/data")

        from lib.session_summary import get_task_contributions_path

        sid = "abc12345-uuid-here"
        h = hashlib.sha256(sid.encode()).hexdigest()[:8]
        result = get_task_contributions_path(sid)
        assert result == Path(f"/home/test/data/dashboard/sessions/{h}.tasks.json")

    def test_get_session_summary_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Session summary file uses session_id as key."""
        monkeypatch.setenv("ACA_DATA", "/home/test/data")

        from lib.session_summary import get_session_summary_path

        sid = "abc12345-uuid-here"
        h = hashlib.sha256(sid.encode()).hexdigest()[:8]
        result = get_session_summary_path(sid)
        assert result == Path(f"/home/test/data/dashboard/sessions/{h}.summary.json")


class TestTaskContributions:
    """Test task contribution capture."""

    @pytest.fixture
    def temp_aca_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Set up temporary ACA_DATA directory."""
        aca_data = tmp_path / "data"
        aca_data.mkdir()
        monkeypatch.setenv("ACA_DATA", str(aca_data))
        return aca_data

    def test_append_task_contribution_creates_file(self, temp_aca_data: Path) -> None:
        """First contribution creates the file."""
        from lib.session_summary import append_task_contribution

        task_data = {
            "request": "Create stub spec",
            "guidance": "N/A",
            "followed": "yes",
            "outcome": "success",
            "accomplishment": "Created spec",
            "project": "aops",
        }

        sid = "test-session-123"
        h = hashlib.sha256(sid.encode()).hexdigest()[:8]
        append_task_contribution(sid, task_data)

        # Verify file was created
        tasks_file = temp_aca_data / "dashboard" / "sessions" / f"{h}.tasks.json"
        assert tasks_file.exists()

        # Verify content
        data = json.loads(tasks_file.read_text())
        assert data["session_id"] == sid
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["request"] == "Create stub spec"

    def test_append_task_contribution_appends_to_existing(self, temp_aca_data: Path) -> None:
        """Subsequent contributions append to existing file."""
        from lib.session_summary import append_task_contribution

        sid = "test-session-123"
        h = hashlib.sha256(sid.encode()).hexdigest()[:8]

        # First task
        append_task_contribution(
            sid,
            {
                "request": "Task 1",
                "outcome": "success",
            },
        )

        # Second task
        append_task_contribution(
            sid,
            {
                "request": "Task 2",
                "outcome": "success",
            },
        )

        # Verify both tasks present
        tasks_file = temp_aca_data / "dashboard" / "sessions" / f"{h}.tasks.json"
        data = json.loads(tasks_file.read_text())
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["request"] == "Task 1"
        assert data["tasks"][1]["request"] == "Task 2"

    def test_append_task_contribution_includes_timestamp(self, temp_aca_data: Path) -> None:
        """Each contribution gets a timestamp."""
        from lib.session_summary import append_task_contribution

        sid = "test-session-123"
        h = hashlib.sha256(sid.encode()).hexdigest()[:8]
        append_task_contribution(sid, {"request": "Test"})

        tasks_file = temp_aca_data / "dashboard" / "sessions" / f"{h}.tasks.json"
        data = json.loads(tasks_file.read_text())

        assert "updated_at" in data
        assert "timestamp" in data["tasks"][0]

    def test_load_task_contributions_returns_list(self, temp_aca_data: Path) -> None:
        """Loading task contributions returns list of tasks."""
        from lib.session_summary import (
            append_task_contribution,
            load_task_contributions,
        )

        append_task_contribution("test-session-123", {"request": "Task 1"})
        append_task_contribution("test-session-123", {"request": "Task 2"})

        tasks = load_task_contributions("test-session-123")
        assert len(tasks) == 2

    def test_load_task_contributions_returns_empty_for_missing(self, temp_aca_data: Path) -> None:
        """Returns empty list if no contributions file exists."""
        from lib.session_summary import load_task_contributions

        tasks = load_task_contributions("nonexistent-session")
        assert tasks == []


class TestSessionSynthesis:
    """Test session summary synthesis."""

    @pytest.fixture
    def temp_aca_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Set up temporary ACA_DATA directory."""
        aca_data = tmp_path / "data"
        aca_data.mkdir()
        monkeypatch.setenv("ACA_DATA", str(aca_data))
        return aca_data

    def test_synthesize_session_creates_summary(self, temp_aca_data: Path) -> None:
        """Synthesis creates session summary JSON."""
        from lib.session_summary import append_task_contribution, synthesize_session

        # Add task contributions
        append_task_contribution(
            "test-session-123",
            {
                "request": "Create spec",
                "outcome": "success",
                "accomplishment": "Created unified session summary spec",
                "project": "aops",
            },
        )

        # Synthesize
        summary = synthesize_session("test-session-123", project="writing", date="2026-01-08")

        assert summary["session_id"] == "test-session-123"
        assert summary["project"] == "writing"
        assert summary["date"] == "2026-01-08"
        assert len(summary["tasks"]) == 1
        assert "Created unified session summary spec" in summary["accomplishments"]

    def test_synthesize_session_extracts_accomplishments(self, temp_aca_data: Path) -> None:
        """Accomplishments extracted from successful tasks."""
        from lib.session_summary import append_task_contribution, synthesize_session

        append_task_contribution(
            "test-session-123",
            {
                "request": "Task 1",
                "outcome": "success",
                "accomplishment": "Accomplishment A",
            },
        )
        append_task_contribution(
            "test-session-123",
            {
                "request": "Task 2",
                "outcome": "partial",
                "accomplishment": "Accomplishment B",
            },
        )
        append_task_contribution(
            "test-session-123",
            {
                "request": "Task 3",
                "outcome": "failure",
                # No accomplishment for failures
            },
        )

        summary = synthesize_session("test-session-123")

        # Only success/partial get accomplishments
        assert "Accomplishment A" in summary["accomplishments"]
        assert "Accomplishment B" in summary["accomplishments"]
        assert len(summary["accomplishments"]) == 2

    def test_synthesize_session_without_contributions(self, temp_aca_data: Path) -> None:
        """Synthesis works even without task contributions (for fallback)."""
        from lib.session_summary import synthesize_session

        summary = synthesize_session(
            "test-session-123",
            project="writing",
            date="2026-01-08",
            summary="Mined from transcript",
            accomplishments=["Mining-derived accomplishment"],
        )

        assert summary["session_id"] == "test-session-123"
        assert summary["summary"] == "Mined from transcript"
        assert summary["accomplishments"] == ["Mining-derived accomplishment"]
        assert summary["tasks"] == []  # No task contributions

    def test_synthesize_session_merges_additional_data(self, temp_aca_data: Path) -> None:
        """Additional data from Gemini mining merges with task contributions."""
        from lib.session_summary import append_task_contribution, synthesize_session

        append_task_contribution(
            "test-session-123",
            {
                "request": "Task 1",
                "outcome": "success",
                "accomplishment": "Task-derived accomplishment",
            },
        )

        summary = synthesize_session(
            "test-session-123",
            project="writing",
            learning_observations=[{"category": "user_correction", "evidence": "quote"}],
            skill_compliance={
                "suggested": ["framework"],
                "invoked": [],
                "compliance_rate": 0.0,
            },
        )

        # Task contributions present
        assert len(summary["tasks"]) == 1
        # Additional data merged
        assert len(summary["learning_observations"]) == 1
        assert summary["skill_compliance"]["compliance_rate"] == 0.0

    def test_save_session_summary_persists(self, temp_aca_data: Path) -> None:
        """Saving session summary writes to disk."""
        from lib.session_summary import get_session_summary_path, save_session_summary

        summary = {
            "session_id": "test-session-123",
            "date": "2026-01-08",
            "project": "writing",
            "accomplishments": ["Test"],
        }

        save_session_summary("test-session-123", summary)

        summary_file = get_session_summary_path("test-session-123")
        assert summary_file.exists()

        loaded = json.loads(summary_file.read_text())
        assert loaded["session_id"] == "test-session-123"

    def test_synthesize_is_idempotent(self, temp_aca_data: Path) -> None:
        """Running synthesis multiple times produces same result."""
        from lib.session_summary import append_task_contribution, synthesize_session

        append_task_contribution(
            "test-session-123",
            {
                "request": "Task 1",
                "outcome": "success",
                "accomplishment": "Done",
            },
        )

        summary1 = synthesize_session("test-session-123", project="aops")
        summary2 = synthesize_session("test-session-123", project="aops")

        # Same accomplishments (not duplicated)
        assert summary1["accomplishments"] == summary2["accomplishments"]


class TestSchemaValidation:
    """Test schema validation for task contributions and summaries."""

    @pytest.fixture
    def temp_aca_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Set up temporary ACA_DATA directory."""
        aca_data = tmp_path / "data"
        aca_data.mkdir()
        monkeypatch.setenv("ACA_DATA", str(aca_data))
        return aca_data

    def test_task_contribution_requires_request(self, temp_aca_data: Path) -> None:
        """Task contribution must have 'request' field."""
        from lib.session_summary import append_task_contribution

        with pytest.raises(ValueError, match="request"):
            append_task_contribution("test-session", {})

    def test_task_contribution_validates_outcome(self, temp_aca_data: Path) -> None:
        """Outcome must be valid enum value."""
        from lib.session_summary import append_task_contribution

        with pytest.raises(ValueError, match="outcome"):
            append_task_contribution(
                "test-session",
                {
                    "request": "Test",
                    "outcome": "invalid_value",
                },
            )

    def test_valid_outcomes(self, temp_aca_data: Path) -> None:
        """Valid outcome values are accepted."""
        from lib.session_summary import append_task_contribution

        for outcome in ["success", "partial", "failure"]:
            append_task_contribution(
                f"test-{outcome}",
                {
                    "request": "Test",
                    "outcome": outcome,
                },
            )
            # Should not raise


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.fixture
    def temp_aca_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Set up temporary ACA_DATA directory."""
        aca_data = tmp_path / "data"
        aca_data.mkdir()
        monkeypatch.setenv("ACA_DATA", str(aca_data))
        return aca_data

    def test_full_workflow_task_to_summary(self, temp_aca_data: Path) -> None:
        """Full workflow: task contributions → synthesis → saved summary."""
        from lib.session_summary import (
            append_task_contribution,
            get_session_summary_path,
            save_session_summary,
            synthesize_session,
        )

        session_id = "integration-test-session"

        # Step 1: Agent completes tasks and records contributions
        append_task_contribution(
            session_id,
            {
                "request": "Create debug-headless skill stub",
                "guidance": "Hydrator suggested /framework",
                "followed": "no",
                "outcome": "success",
                "accomplishment": "Created debug-headless skill stub spec",
                "project": "academicOps",
            },
        )

        append_task_contribution(
            session_id,
            {
                "request": "Update AGENTS.md with structured reflection",
                "guidance": "N/A",
                "followed": "yes",
                "outcome": "success",
                "accomplishment": "Enhanced framework reflection format",
                "project": "academicOps",
            },
        )

        # Step 2: Stop hook synthesizes session
        summary = synthesize_session(
            session_id,
            project="writing",
            date="2026-01-08",
            summary="Framework improvements: debug skill stub and reflection format",
        )

        # Step 3: Save summary
        save_session_summary(session_id, summary)

        # Verify result
        summary_path = get_session_summary_path(session_id)
        assert summary_path.exists()

        loaded = json.loads(summary_path.read_text())
        assert loaded["session_id"] == session_id
        assert len(loaded["tasks"]) == 2
        assert len(loaded["accomplishments"]) == 2
        assert "debug-headless" in loaded["accomplishments"][0].lower()

    def test_concurrent_sessions_isolated(self, temp_aca_data: Path) -> None:
        """Multiple sessions in same directory don't collide (different session IDs)."""
        from lib.session_summary import (
            append_task_contribution,
            load_task_contributions,
        )

        # Two sessions running in parallel (different terminals, same cwd)
        session_a = "terminal-1-session-aaa"
        session_b = "terminal-2-session-bbb"

        append_task_contribution(session_a, {"request": "Task from terminal 1"})
        append_task_contribution(session_b, {"request": "Task from terminal 2"})
        append_task_contribution(session_a, {"request": "Another from terminal 1"})

        # Each session has its own tasks
        tasks_a = load_task_contributions(session_a)
        tasks_b = load_task_contributions(session_b)

        assert len(tasks_a) == 2
        assert len(tasks_b) == 1
        assert tasks_a[0]["request"] == "Task from terminal 1"
        assert tasks_b[0]["request"] == "Task from terminal 2"
