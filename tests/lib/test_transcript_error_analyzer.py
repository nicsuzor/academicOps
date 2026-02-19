"""Tests for lib/transcript_error_analyzer.py - Transcript error extraction and hydration gap analysis.

TDD: Tests written first, then implementation.

Extracts errors from session transcripts and classifies them to identify
where hydration failed to provide sufficient context to the agent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# --- Test helpers (reused patterns from test_session_reader.py) ---


def _make_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO timestamp with optional offset from base time."""
    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    ts = base + timedelta(seconds=offset_seconds)
    return ts.isoformat().replace("+00:00", "Z")


def _create_user_entry(prompt: str, offset: int = 0) -> dict:
    """Create a user message entry."""
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {"content": [{"type": "text", "text": prompt}]},
    }


def _create_assistant_entry(text: str = "I'll help with that.", offset: int = 0) -> dict:
    """Create an assistant response entry."""
    return {
        "type": "assistant",
        "uuid": f"assistant-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _create_tool_use_entry(
    tool_name: str, tool_input: dict, offset: int = 0, tool_id: str | None = None
) -> dict:
    """Create an assistant entry with a tool invocation."""
    tid = tool_id or f"tool-{offset}"
    return {
        "type": "assistant",
        "uuid": f"tool-{tool_name}-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tid,
                    "name": tool_name,
                    "input": tool_input,
                }
            ]
        },
    }


def _create_tool_result_entry(
    tool_id: str, result: str, is_error: bool = False, offset: int = 0
) -> dict:
    """Create a user entry with tool result."""
    return {
        "type": "user",
        "uuid": f"result-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                    "is_error": is_error,
                }
            ]
        },
    }


def _create_skill_entry(skill_name: str, offset: int = 0) -> dict:
    """Create an assistant entry invoking a Skill."""
    return _create_tool_use_entry("Skill", {"skill": skill_name}, offset, f"skill-{offset}")


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Write entries to JSONL file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# --- Tests: Error Extraction ---


class TestExtractTranscriptErrors:
    """Test basic error extraction from session entries."""

    def test_extracts_file_not_found_error(self, tmp_path: Path) -> None:
        """Extract a Read tool 'file does not exist' error."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Help me fix the auth module", 0),
            _create_tool_use_entry(
                "Read",
                {"file_path": "/home/user/src/project/auth.py"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors) == 1
        assert errors[0].tool_name == "Read"
        assert "auth.py" in errors[0].tool_input_summary
        assert "does not exist" in errors[0].error_content

    def test_extracts_multiple_errors(self, tmp_path: Path) -> None:
        """Extract multiple errors from a session."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Set up the project", 0),
            _create_tool_use_entry("Read", {"file_path": "/src/config.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
            _create_tool_use_entry("Bash", {"command": "npm install"}, 20, "tool-20"),
            _create_tool_result_entry(
                "tool-20",
                "Exit code 1\nnpm ERR! missing script: install",
                is_error=True,
                offset=21,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors) == 2
        assert errors[0].tool_name == "Read"
        assert errors[1].tool_name == "Bash"

    def test_ignores_successful_results(self, tmp_path: Path) -> None:
        """Successful tool results are not extracted as errors."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Read the config", 0),
            _create_tool_use_entry("Read", {"file_path": "/src/config.py"}, 10, "tool-10"),
            _create_tool_result_entry("tool-10", "x = 1\ny = 2", is_error=False, offset=11),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors) == 0

    def test_handles_hook_denial_errors(self, tmp_path: Path) -> None:
        """Hook denial errors are extracted."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Run the build", 0),
            _create_tool_use_entry("Bash", {"command": "make build"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "Hook PreToolUse:Bash denied this tool",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors) == 1
        assert "denied" in errors[0].error_content

    def test_handles_user_rejection_errors(self, tmp_path: Path) -> None:
        """User rejection errors are extracted."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Edit the file", 0),
            _create_tool_use_entry(
                "Edit",
                {"file_path": "/src/main.py", "old_string": "x", "new_string": "y"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "The user doesn't want to proceed with this tool use.",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors) == 1

    def test_extracts_error_with_timestamp(self, tmp_path: Path) -> None:
        """Each error includes the timestamp of when it occurred."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Do something", 0),
            _create_tool_use_entry("Read", {"file_path": "/missing.py"}, 100, "tool-100"),
            _create_tool_result_entry(
                "tool-100",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=101,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert errors[0].timestamp is not None

    def test_empty_session_returns_empty(self, tmp_path: Path) -> None:
        """Empty session file returns no errors."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        _write_jsonl(tmp_path / "session.jsonl", [])

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert errors == []


# --- Tests: Error Classification ---


class TestClassifyErrors:
    """Test error classification into diagnostic categories."""

    def test_file_not_found_classified_as_hydration_gap(self, tmp_path: Path) -> None:
        """Read 'file does not exist' after user mentions file is a hydration_gap."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        entries = [
            _create_user_entry("Fix the bug in auth.py", 0),
            _create_assistant_entry("Let me read auth.py", 5),
            _create_tool_use_entry(
                "Read",
                {"file_path": "/home/user/src/project/auth.py"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        assert classified[0].category == "hydration_gap"

    def test_exploration_read_classified_as_exploration_miss(self, tmp_path: Path) -> None:
        """Read of a common convention path (README, setup.py) is exploration_miss."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        entries = [
            _create_user_entry("What does this project do?", 0),
            _create_assistant_entry("Let me check the project structure", 5),
            _create_tool_use_entry(
                "Read",
                {"file_path": "/home/user/src/project/README.md"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        assert classified[0].category == "exploration_miss"

    def test_bash_exit_code_classified_as_tool_failure(self, tmp_path: Path) -> None:
        """Bash command with non-zero exit code is a tool_failure."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        entries = [
            _create_user_entry("Run the tests", 0),
            _create_tool_use_entry("Bash", {"command": "pytest tests/"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "Exit code 1\nERROR: not found",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        assert classified[0].category == "tool_failure"

    def test_hook_denial_classified_as_hook_denial(self, tmp_path: Path) -> None:
        """Hook denial errors get their own category."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        entries = [
            _create_user_entry("Run a command", 0),
            _create_tool_use_entry("Bash", {"command": "rm -rf /"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "Hook PreToolUse:Bash denied this tool",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        assert classified[0].category == "hook_denial"

    def test_repeated_same_path_classified_as_stuck_pattern(self, tmp_path: Path) -> None:
        """Repeated attempts to read the same file is a stuck_pattern."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        path = "/home/user/src/project/missing.py"
        entries = [
            _create_user_entry("Find the module", 0),
            # First attempt
            _create_tool_use_entry("Read", {"file_path": path}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
            # Second attempt - same path
            _create_tool_use_entry("Read", {"file_path": path}, 20, "tool-20"),
            _create_tool_result_entry(
                "tool-20",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=21,
            ),
            # Third attempt - same path
            _create_tool_use_entry("Read", {"file_path": path}, 30, "tool-30"),
            _create_tool_result_entry(
                "tool-30",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=31,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        # At least the later attempts should be stuck_pattern
        stuck = [e for e in classified if e.category == "stuck_pattern"]
        assert len(stuck) >= 2

    def test_user_rejection_classified_as_user_rejection(self, tmp_path: Path) -> None:
        """User rejecting a tool use gets its own category."""
        from lib.transcript_error_analyzer import classify_errors, extract_transcript_errors

        entries = [
            _create_user_entry("Edit the file", 0),
            _create_tool_use_entry(
                "Edit",
                {"file_path": "/src/main.py", "old_string": "x", "new_string": "y"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "The user doesn't want to proceed with this tool use.",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")
        classified = classify_errors(errors, entries)

        assert classified[0].category == "user_rejection"


# --- Tests: Hydration State Correlation ---


class TestHydrationStateCorrelation:
    """Test that errors are correlated with the hydration state at time of error."""

    def test_captures_active_skill(self, tmp_path: Path) -> None:
        """Error records which skill was active when it occurred."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Work on the feature", 0),
            _create_skill_entry("python-dev", 5),
            _create_tool_result_entry("skill-5", "Skill loaded", offset=6),
            _create_tool_use_entry("Read", {"file_path": "/missing.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert errors[0].hydration_state.active_skill == "python-dev"

    def test_captures_recent_prompts(self, tmp_path: Path) -> None:
        """Error records recent user prompts for context."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("First, set up the project", 0),
            _create_assistant_entry("Sure", 1),
            _create_user_entry("Now fix the auth module in auth.py", 10),
            _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 20, "tool-20"),
            _create_tool_result_entry(
                "tool-20",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=21,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors[0].hydration_state.recent_prompts) >= 1
        assert "auth" in errors[0].hydration_state.recent_prompts[-1].lower()

    def test_captures_recent_tool_calls(self, tmp_path: Path) -> None:
        """Error records recent tool calls before the error."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Explore the codebase", 0),
            _create_tool_use_entry("Glob", {"pattern": "**/*.py"}, 5, "tool-5"),
            _create_tool_result_entry("tool-5", "src/main.py\nsrc/utils.py", offset=6),
            _create_tool_use_entry("Read", {"file_path": "/src/missing.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert len(errors[0].hydration_state.recent_tool_calls) >= 1
        assert errors[0].hydration_state.recent_tool_calls[0]["tool_name"] == "Glob"

    def test_no_skill_yields_none(self, tmp_path: Path) -> None:
        """If no skill was invoked, active_skill is None."""
        from lib.transcript_error_analyzer import extract_transcript_errors

        entries = [
            _create_user_entry("Read a file", 0),
            _create_tool_use_entry("Read", {"file_path": "/missing.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        errors = extract_transcript_errors(tmp_path / "session.jsonl")

        assert errors[0].hydration_state.active_skill is None


# --- Tests: Analysis Report ---


class TestErrorAnalysisReport:
    """Test the summary report generation."""

    def test_report_includes_counts_by_category(self, tmp_path: Path) -> None:
        """Report includes error counts grouped by category."""
        from lib.transcript_error_analyzer import analyze_transcript

        entries = [
            _create_user_entry("Fix auth.py", 0),
            # hydration_gap (user mentioned auth.py)
            _create_tool_use_entry(
                "Read",
                {"file_path": "/src/auth.py"},
                10,
                "tool-10",
            ),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
            # tool_failure
            _create_tool_use_entry("Bash", {"command": "pytest"}, 20, "tool-20"),
            _create_tool_result_entry(
                "tool-20",
                "Exit code 1\nfailed",
                is_error=True,
                offset=21,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        report = analyze_transcript(tmp_path / "session.jsonl")

        assert report.total_errors == 2
        assert "hydration_gap" in report.errors_by_category
        assert "tool_failure" in report.errors_by_category

    def test_report_hydration_gap_score(self, tmp_path: Path) -> None:
        """Report calculates hydration gap score (fraction of hydration-related errors)."""
        from lib.transcript_error_analyzer import analyze_transcript

        entries = [
            _create_user_entry("Fix auth.py", 0),
            # hydration_gap
            _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
            # tool_failure
            _create_tool_use_entry("Bash", {"command": "pytest"}, 20, "tool-20"),
            _create_tool_result_entry("tool-20", "Exit code 1\nfailed", is_error=True, offset=21),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        report = analyze_transcript(tmp_path / "session.jsonl")

        # 1 hydration gap out of 2 errors = 0.5
        assert report.hydration_gap_score == pytest.approx(0.5)

    def test_report_zero_errors(self, tmp_path: Path) -> None:
        """Report handles sessions with no errors gracefully."""
        from lib.transcript_error_analyzer import analyze_transcript

        entries = [
            _create_user_entry("Hello", 0),
            _create_assistant_entry("Hi there!", 1),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        report = analyze_transcript(tmp_path / "session.jsonl")

        assert report.total_errors == 0
        assert report.hydration_gap_score == 0.0
        assert report.errors == []

    def test_report_as_dict(self, tmp_path: Path) -> None:
        """Report can be serialized to dict for JSON output."""
        from lib.transcript_error_analyzer import analyze_transcript

        entries = [
            _create_user_entry("Read something", 0),
            _create_tool_use_entry("Read", {"file_path": "/missing.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        report = analyze_transcript(tmp_path / "session.jsonl")
        d = report.to_dict()

        assert isinstance(d, dict)
        assert "total_errors" in d
        assert "errors_by_category" in d
        assert "hydration_gap_score" in d
        assert "severity_score" in d
        assert "session_path" in d
        assert "errors" in d
        assert isinstance(d["errors"], list)

    def test_report_severity_score(self, tmp_path: Path) -> None:
        """Report includes a severity score based on weighted categories."""
        from lib.transcript_error_analyzer import analyze_transcript

        entries = [
            _create_user_entry("Fix auth.py", 0),
            # hydration_gap (weight 3)
            _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
            _create_tool_result_entry(
                "tool-10",
                "<tool_use_error>File does not exist.</tool_use_error>",
                is_error=True,
                offset=11,
            ),
            # hook_denial (weight 1)
            _create_tool_use_entry("Bash", {"command": "rm -rf /"}, 20, "tool-20"),
            _create_tool_result_entry(
                "tool-20",
                "Hook PreToolUse:Bash denied this tool",
                is_error=True,
                offset=21,
            ),
        ]
        _write_jsonl(tmp_path / "session.jsonl", entries)

        report = analyze_transcript(tmp_path / "session.jsonl")

        # hydration_gap(3) + hook_denial(1) = 4
        assert report.severity_score == pytest.approx(4.0)


# --- Tests: Severity Scoring ---


class TestSeverityWeighting:
    """Test severity weight assignments."""

    def test_hydration_gap_is_high(self) -> None:
        """hydration_gap is high severity (weight 3)."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("hydration_gap")
        assert label == "high"
        assert weight == 3

    def test_stuck_pattern_is_high(self) -> None:
        """stuck_pattern with 2 repeats is high (weight 3)."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("stuck_pattern", repeat_count=2)
        assert label == "high"
        assert weight == 3

    def test_stuck_pattern_escalates_to_critical(self) -> None:
        """stuck_pattern with 3+ repeats escalates to critical (weight 4)."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("stuck_pattern", repeat_count=3)
        assert label == "critical"
        assert weight == 4

    def test_hook_denial_is_low(self) -> None:
        """hook_denial is low severity (weight 1)."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("hook_denial")
        assert label == "low"
        assert weight == 1

    def test_tool_failure_is_medium(self) -> None:
        """tool_failure is medium severity (weight 2)."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("tool_failure")
        assert label == "medium"
        assert weight == 2

    def test_unknown_category_defaults_medium(self) -> None:
        """Unknown category defaults to medium."""
        from lib.transcript_error_analyzer import severity_for

        label, weight = severity_for("never_heard_of_this")
        assert label == "medium"
        assert weight == 2


# --- Tests: Multi-Session Scanning ---


class TestScanRecentSessions:
    """Test multi-session scanning and aggregation."""

    def _create_session(self, tmp_path: Path, name: str, entries: list[dict]) -> Path:
        """Helper to create a session JSONL file."""
        path = tmp_path / f"{name}.jsonl"
        _write_jsonl(path, entries)
        return path

    def test_scans_directory_for_sessions(self, tmp_path: Path) -> None:
        """scan_recent_sessions finds and processes JSONL files."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        # Create two sessions with errors
        self._create_session(
            tmp_path,
            "session-a",
            [
                _create_user_entry("Fix auth.py", 0),
                _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
                _create_tool_result_entry(
                    "tool-10",
                    "<tool_use_error>File does not exist.</tool_use_error>",
                    is_error=True,
                    offset=11,
                ),
            ],
        )
        # Clean session
        self._create_session(
            tmp_path,
            "session-b",
            [
                _create_user_entry("Hello", 0),
                _create_assistant_entry("Hi!", 1),
            ],
        )

        report = scan_recent_sessions(tmp_path, hours=24)

        assert report.sessions_scanned == 2
        assert report.sessions_with_errors == 1
        assert report.total_errors == 1

    def test_excludes_hooks_and_agent_files(self, tmp_path: Path) -> None:
        """Hook and agent JSONL files are excluded from scanning."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        # Normal session
        self._create_session(
            tmp_path,
            "session-a",
            [_create_user_entry("Hello", 0), _create_assistant_entry("Hi!", 1)],
        )
        # Hook file (should be excluded)
        self._create_session(
            tmp_path,
            "session-a-hooks",
            [_create_user_entry("hook data", 0)],
        )
        # Agent file (should be excluded)
        self._create_session(
            tmp_path,
            "agent-explore",
            [_create_user_entry("agent data", 0)],
        )

        report = scan_recent_sessions(tmp_path, hours=24)

        assert report.sessions_scanned == 1

    def test_investigation_queue_sorted_by_weighted_score(self, tmp_path: Path) -> None:
        """Investigation queue is sorted by severity * frequency descending."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        # Session with hydration_gap (high, weight 3) and tool_failure (medium, weight 2)
        self._create_session(
            tmp_path,
            "session-a",
            [
                _create_user_entry("Fix auth.py", 0),
                _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
                _create_tool_result_entry(
                    "tool-10",
                    "<tool_use_error>File does not exist.</tool_use_error>",
                    is_error=True,
                    offset=11,
                ),
                _create_tool_use_entry("Bash", {"command": "pytest"}, 20, "tool-20"),
                _create_tool_result_entry(
                    "tool-20",
                    "Exit code 1\nfailed",
                    is_error=True,
                    offset=21,
                ),
            ],
        )

        report = scan_recent_sessions(tmp_path, hours=24)

        assert len(report.investigation_queue) == 2
        # hydration_gap (3) should be first, tool_failure (2) second
        assert report.investigation_queue[0].category == "hydration_gap"
        assert report.investigation_queue[1].category == "tool_failure"

    def test_aggregates_same_pattern_across_sessions(self, tmp_path: Path) -> None:
        """Same error pattern across sessions is aggregated."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        for name in ("session-a", "session-b"):
            self._create_session(
                tmp_path,
                name,
                [
                    _create_user_entry("Fix auth.py", 0),
                    _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
                    _create_tool_result_entry(
                        "tool-10",
                        "<tool_use_error>File does not exist.</tool_use_error>",
                        is_error=True,
                        offset=11,
                    ),
                ],
            )

        report = scan_recent_sessions(tmp_path, hours=24)

        # Same pattern in both sessions should be aggregated
        assert len(report.investigation_queue) == 1
        assert report.investigation_queue[0].count == 2
        assert len(report.investigation_queue[0].session_ids) == 2

    def test_format_markdown_produces_output(self, tmp_path: Path) -> None:
        """Markdown formatting produces human-readable report."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        self._create_session(
            tmp_path,
            "session-a",
            [
                _create_user_entry("Fix auth.py", 0),
                _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
                _create_tool_result_entry(
                    "tool-10",
                    "<tool_use_error>File does not exist.</tool_use_error>",
                    is_error=True,
                    offset=11,
                ),
            ],
        )

        report = scan_recent_sessions(tmp_path, hours=24)
        md = report.format_markdown()

        assert "Investigation Queue" in md
        assert "hydration_gap" in md
        assert "auth.py" in md

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory produces empty report."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        report = scan_recent_sessions(tmp_path, hours=24)

        assert report.sessions_scanned == 0
        assert report.total_errors == 0
        assert report.investigation_queue == []

    def test_to_dict_serialization(self, tmp_path: Path) -> None:
        """Multi-session report can be serialized to dict."""
        from lib.transcript_error_analyzer import scan_recent_sessions

        self._create_session(
            tmp_path,
            "session-a",
            [
                _create_user_entry("Fix auth.py", 0),
                _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 10, "tool-10"),
                _create_tool_result_entry(
                    "tool-10",
                    "<tool_use_error>File does not exist.</tool_use_error>",
                    is_error=True,
                    offset=11,
                ),
            ],
        )

        report = scan_recent_sessions(tmp_path, hours=24)
        d = report.to_dict()

        assert "sessions_scanned" in d
        assert "investigation_queue" in d
        assert "session_summaries" in d
        assert isinstance(d["investigation_queue"], list)
        assert d["investigation_queue"][0]["weighted_score"] > 0
