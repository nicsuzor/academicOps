"""
Unit tests for skills/next/scripts/select_task.py

Tests data preparation for LLM-driven task selection.
Verifies H12a compliance (no algorithmic scoring).
"""

import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add skills path to import
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "next" / "scripts"))

from select_task import (  # noqa: E402
    calculate_priority_distribution,
    detect_stale_tasks,
    enrich_task,
    get_active_tasks,
    get_todays_work,
    load_json,
    parse_due_date,
)


class TestLoadJson:
    """Tests for load_json - Axiom #7 fail-fast compliance."""

    def test_raises_on_missing_file(self, tmp_path):
        """Fail fast when required file is missing."""
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError, match="Required file not found"):
            load_json(missing)

    def test_loads_valid_json(self, tmp_path):
        """Successfully loads valid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        result = load_json(json_file)
        assert result == {"key": "value"}


class TestParseDueDate:
    """Tests for date parsing flexibility."""

    def test_parses_iso_format(self):
        result = parse_due_date("2025-12-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 15

    def test_parses_iso_with_time(self):
        result = parse_due_date("2025-12-15T14:30:00")
        assert result is not None
        assert result.year == 2025

    def test_parses_iso_with_timezone(self):
        result = parse_due_date("2025-12-15T14:30:00Z")
        assert result is not None
        assert result.year == 2025

    def test_returns_none_for_empty(self):
        assert parse_due_date(None) is None
        assert parse_due_date("") is None

    def test_returns_none_for_invalid(self):
        assert parse_due_date("not a date") is None
        assert parse_due_date("tomorrow") is None


class TestGetActiveTasks:
    """Tests for task filtering logic."""

    def test_excludes_archived_status(self):
        index = {
            "tasks": [
                {"slug": "active", "status": "inbox"},
                {"slug": "archived", "status": "archived"},
            ]
        }
        result = get_active_tasks(index)
        assert len(result) == 1
        assert result[0]["slug"] == "active"

    def test_excludes_done_status(self):
        index = {
            "tasks": [
                {"slug": "active", "status": "inbox"},
                {"slug": "done", "status": "done"},
            ]
        }
        result = get_active_tasks(index)
        assert len(result) == 1
        assert result[0]["slug"] == "active"

    def test_excludes_archived_path(self):
        index = {
            "tasks": [
                {"slug": "active", "file": "tasks/inbox/task.md"},
                {"slug": "archived", "file": "tasks/archived/old.md"},
            ]
        }
        result = get_active_tasks(index)
        assert len(result) == 1
        assert result[0]["slug"] == "active"

    def test_handles_empty_tasks(self):
        assert get_active_tasks({}) == []
        assert get_active_tasks({"tasks": []}) == []


class TestGetTodaysWork:
    """Tests for accomplishment counting."""

    def test_counts_by_project(self):
        synthesis = {
            "accomplishments": {
                "items": [
                    {"project": "aops"},
                    {"project": "aops"},
                    {"project": "research"},
                ]
            }
        }
        result = get_todays_work(synthesis)
        assert result["aops"] == 2
        assert result["research"] == 1

    def test_handles_missing_project(self):
        synthesis = {"accomplishments": {"items": [{"no_project": True}]}}
        result = get_todays_work(synthesis)
        assert result["unknown"] == 1

    def test_handles_empty_synthesis(self):
        assert get_todays_work({}) == Counter()
        assert get_todays_work({"accomplishments": {}}) == Counter()


class TestDetectStaleTasks:
    """Tests for stale task detection rules."""

    def test_events_stale_after_7_days(self):
        """Events more than 7 days past should be flagged."""
        now = datetime(2025, 1, 15)
        tasks = [
            {
                "slug": "old-event",
                "title": "Past Meeting",
                "classification": "event",
                "due": "2025-01-05",  # 10 days ago
                "file": "tasks/inbox/old.md",
                "tags": [],
            }
        ]
        result = detect_stale_tasks(tasks, now)
        assert len(result) == 1
        assert "10 days ago" in result[0]["reason"]

    def test_events_fresh_within_7_days(self):
        """Events within 7 days should not be flagged."""
        now = datetime(2025, 1, 15)
        tasks = [
            {
                "slug": "recent-event",
                "title": "Recent Meeting",
                "classification": "event",
                "due": "2025-01-10",  # 5 days ago
                "file": "tasks/inbox/recent.md",
                "tags": [],
            }
        ]
        result = detect_stale_tasks(tasks, now)
        assert len(result) == 0

    def test_non_events_stale_after_60_days(self):
        """Non-events overdue 60+ days should be flagged."""
        now = datetime(2025, 3, 15)
        tasks = [
            {
                "slug": "old-task",
                "title": "Old Task",
                "classification": "task",
                "due": "2025-01-01",  # 73 days overdue
                "file": "tasks/inbox/old.md",
                "tags": [],
            }
        ]
        result = detect_stale_tasks(tasks, now)
        assert len(result) == 1
        assert "73 days" in result[0]["reason"]

    def test_non_events_fresh_under_60_days(self):
        """Non-events under 60 days overdue should not be flagged."""
        now = datetime(2025, 2, 15)
        tasks = [
            {
                "slug": "overdue-task",
                "title": "Overdue Task",
                "classification": "task",
                "due": "2025-01-01",  # 45 days overdue
                "file": "tasks/inbox/task.md",
                "tags": [],
            }
        ]
        result = detect_stale_tasks(tasks, now)
        assert len(result) == 0

    def test_limits_to_5_candidates(self):
        """Should return at most 5 stale candidates."""
        now = datetime(2025, 6, 1)
        tasks = [
            {
                "slug": f"old-{i}",
                "title": f"Task {i}",
                "classification": "task",
                "due": "2025-01-01",  # Very overdue
                "file": f"tasks/inbox/{i}.md",
                "tags": [],
            }
            for i in range(10)
        ]
        result = detect_stale_tasks(tasks, now)
        assert len(result) == 5


class TestCalculatePriorityDistribution:
    """Tests for priority counting."""

    def test_counts_all_priorities(self):
        tasks = [
            {"priority": 0},
            {"priority": 1},
            {"priority": 1},
            {"priority": 2},
            {"priority": 3},
            {"priority": 3},
            {"priority": 3},
        ]
        result = calculate_priority_distribution(tasks)
        assert result == {"P0": 1, "P1": 2, "P2": 1, "P3": 3}

    def test_defaults_missing_priority_to_p3(self):
        tasks = [{"no_priority": True}, {"priority": 1}]
        result = calculate_priority_distribution(tasks)
        assert result["P3"] == 1
        assert result["P1"] == 1

    def test_handles_empty_list(self):
        result = calculate_priority_distribution([])
        assert result == {"P0": 0, "P1": 0, "P2": 0, "P3": 0}


class TestEnrichTask:
    """Tests for task enrichment with computed fields."""

    def test_adds_due_parsed_field(self):
        task = {"due": "2025-12-15", "file": "tasks/inbox/test.md"}
        result = enrich_task(task)
        assert result["due_parsed"] == "2025-12-15"

    def test_adds_days_until_due(self):
        # Use a fixed date for testing
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        task = {"due": future_date, "file": "tasks/inbox/test.md"}
        result = enrich_task(task)
        assert result["days_until_due"] == 5

    def test_handles_no_due_date(self):
        task = {"file": "tasks/inbox/test.md"}
        result = enrich_task(task)
        assert result["due_parsed"] is None
        assert result["days_until_due"] is None

    def test_preserves_original_fields(self):
        task = {"slug": "test", "title": "Test Task", "file": "tasks/inbox/test.md"}
        result = enrich_task(task)
        assert result["slug"] == "test"
        assert result["title"] == "Test Task"

    def test_adds_next_subtasks_field(self):
        task = {"file": "tasks/inbox/test.md"}
        result = enrich_task(task)
        assert "next_subtasks" in result
        assert isinstance(result["next_subtasks"], list)


class TestNoAlgorithmicScoring:
    """
    Meta-tests verifying H12a compliance.

    These tests verify the script does NOT contain scoring logic.
    """

    def test_no_score_field_in_output(self):
        """Output should not contain score/ranking fields."""
        task = {"slug": "test", "priority": 1, "file": "tasks/inbox/test.md"}
        result = enrich_task(task)

        forbidden_keys = ["score", "rank", "weight", "recommendation", "selected"]
        for key in forbidden_keys:
            assert key not in result, f"Found forbidden scoring key: {key}"

    def test_priority_distribution_is_counts_not_scores(self):
        """Priority distribution should be simple counts, not weighted scores."""
        tasks = [{"priority": 0}, {"priority": 1}]
        result = calculate_priority_distribution(tasks)

        # Values should be simple integers (counts), not floats (scores)
        for key, value in result.items():
            assert isinstance(
                value, int
            ), f"{key} should be int count, not {type(value)}"
