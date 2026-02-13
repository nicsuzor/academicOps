#!/usr/bin/env python3
"""Tests for task_sync module."""

import tempfile
from pathlib import Path

import pytest
from lib.task_model import TaskType
from lib.task_storage import TaskStorage
from lib.task_sync import SyncResult, TaskSyncService, sync_task_from_session


class TestTaskSyncService:
    """Tests for TaskSyncService."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_data_dir):
        """Create a TaskStorage with temp directory."""
        return TaskStorage(data_root=temp_data_dir)

    @pytest.fixture
    def service(self, storage):
        """Create a TaskSyncService with storage."""
        return TaskSyncService(storage=storage)

    @pytest.fixture
    def sample_task(self, storage):
        """Create a sample task with checklist items."""
        task = storage.create_task(
            title="Implement feature X",
            project="test",
            type=TaskType.TASK,
        )
        task.body = """# Implement feature X

## Acceptance Criteria

- [ ] Write unit tests
- [ ] Implement core logic
- [ ] Add documentation
- [ ] Update README

## Notes

Some notes about the feature.
"""
        storage.save_task(task)
        return task

    def test_extract_task_id_from_wikilink(self, service):
        """Test extracting task_id from wikilink."""
        accomplishment = "Completed [[test-a1b2c3d4]] implementation"
        task_id = service._extract_task_id(accomplishment)
        assert task_id == "test-a1b2c3d4"

    def test_extract_task_id_from_dict(self, service):
        """Test extracting task_id from dict."""
        accomplishment = {"task_id": "test-12345678", "text": "Did something"}
        task_id = service._extract_task_id(accomplishment)
        assert task_id == "test-12345678"

    def test_extract_task_id_from_pattern(self, service):
        """Test extracting task_id from pattern in text."""
        accomplishment = "Fixed bug in aops-abcdef12 module"
        task_id = service._extract_task_id(accomplishment)
        assert task_id == "aops-abcdef12"

    def test_extract_task_id_none_when_missing(self, service):
        """Test returns None when no task_id found."""
        accomplishment = "Did something unrelated"
        task_id = service._extract_task_id(accomplishment)
        assert task_id is None

    def test_mark_checklist_items(self, service, sample_task):
        """Test marking checklist items as complete."""
        marked = service._mark_checklist_items(sample_task, "Wrote unit tests for feature X")
        assert len(marked) >= 1
        assert "Write unit tests" in marked
        assert "[x] Write unit tests" in sample_task.body
        # Other items should remain unchecked
        assert "- [ ] Implement core logic" in sample_task.body

    def test_mark_checklist_items_no_match(self, service, sample_task):
        """Test no items marked when no match."""
        marked = service._mark_checklist_items(sample_task, "Something completely unrelated")
        assert len(marked) == 0
        # Body should be unchanged (all items still unchecked)
        assert "- [ ] Write unit tests" in sample_task.body

    def test_add_progress_entry_new_section(self, service, sample_task):
        """Test adding progress entry creates new section."""
        added = service._add_progress_entry(
            sample_task,
            "Completed unit tests",
            "abc12345",
            "2026-01-24",
        )
        assert added is True
        assert "## Progress" in sample_task.body
        assert "2026-01-24: Completed unit tests (session: abc12345)" in sample_task.body

    def test_add_progress_entry_existing_section(self, service, sample_task):
        """Test adding progress entry to existing section."""
        # First entry
        service._add_progress_entry(sample_task, "First entry", "sess1234", "2026-01-23")
        # Second entry
        added = service._add_progress_entry(sample_task, "Second entry", "sess5678", "2026-01-24")
        assert added is True
        assert "First entry" in sample_task.body
        assert "Second entry" in sample_task.body

    def test_sync_accomplishments_with_task_id(self, service, storage, sample_task):
        """Test full sync with explicit task_id."""
        insights = {
            "session_id": "test1234",
            "date": "2026-01-24",
            "accomplishments": [
                {"task_id": sample_task.id, "text": "Wrote unit tests for the feature"}
            ],
        }

        report = service.sync_accomplishments_to_tasks(insights)

        assert report.session_id == "test1234"
        assert report.tasks_updated == 1
        assert report.tasks_failed == 0
        assert len(report.results) == 1

        result = report.results[0]
        assert result.success is True
        assert result.task_id == sample_task.id
        assert result.progress_entry_added is True

    def test_sync_accomplishments_task_not_found(self, service):
        """Test sync when task doesn't exist."""
        insights = {
            "session_id": "test1234",
            "date": "2026-01-24",
            "accomplishments": [{"task_id": "nonexistent-12345678", "text": "Something"}],
        }

        report = service.sync_accomplishments_to_tasks(insights)

        assert report.tasks_failed == 1
        assert report.results[0].success is False
        assert "not found" in report.results[0].error

    def test_sync_accomplishments_no_task_id(self, service):
        """Test sync skips accomplishments without task_id."""
        insights = {
            "session_id": "test1234",
            "date": "2026-01-24",
            "accomplishments": ["Did something without a task reference"],
        }

        report = service.sync_accomplishments_to_tasks(insights)

        assert report.tasks_updated == 0
        assert report.tasks_failed == 0
        assert len(report.results) == 0

    def test_normalize_for_matching(self, service):
        """Test text normalization for matching."""
        text = "Implemented [[task-id]] feature: 100% complete!"
        normalized = service._normalize_for_matching(text)
        assert normalized == "implemented task id feature 100 complete"

    def test_items_match_high_overlap(self, service):
        """Test items match with high word overlap."""
        item_text = "Write unit tests"
        accomplishment = "Wrote unit tests for the module"
        words = set(service._normalize_for_matching(accomplishment).split())

        assert service._items_match(item_text, accomplishment, words) is True

    def test_items_match_low_overlap(self, service):
        """Test items don't match with low overlap."""
        item_text = "Write unit tests"
        accomplishment = "Fixed the documentation typo"
        words = set(service._normalize_for_matching(accomplishment).split())

        assert service._items_match(item_text, accomplishment, words) is False


class TestSyncTaskFromSession:
    """Tests for sync_task_from_session convenience function."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_sync_task_returns_result(self, temp_data_dir, monkeypatch):
        """Test convenience function returns SyncResult."""
        # This test would need proper setup - simplified for now
        result = sync_task_from_session(
            task_id="nonexistent-12345678",
            accomplishment="Did something",
            session_id="test1234",
        )

        assert isinstance(result, SyncResult)
        assert result.success is False  # Task doesn't exist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
