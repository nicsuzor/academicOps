"""Tests for email metadata storage in tasks.

Verifies that source email metadata (entry_id, subject, from, date) is stored
in task frontmatter and used for duplicate detection.

QA Finding 2026-01-08: Email IDs were being stored in body text using inconsistent
formats, breaking duplicate detection. This test ensures proper frontmatter storage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from skills.tasks import task_ops


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "tasks/inbox").mkdir(parents=True)
    (data_dir / "tasks/archived").mkdir(parents=True)
    return data_dir


class TestSourceEmailMetadata:
    """Tests for source email metadata storage in task frontmatter."""

    def test_create_task_with_source_email_id_stores_in_frontmatter(
        self, test_data_dir: Path
    ):
        """Task created with source_email_id should store it in frontmatter, not body.

        This is the key requirement: the email ID must be in frontmatter YAML
        so duplicate detection can reliably find it.
        """
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700ABC123"

        result = task_ops.create_task(
            title="Test email task",
            data_dir=test_data_dir,
            priority=1,
            source_email_id=email_id,
        )

        assert result["success"], f"Task creation failed: {result.get('message')}"

        # Read the created file and parse frontmatter
        task_path = test_data_dir / "tasks/inbox" / result["filename"]
        content = task_path.read_text(encoding="utf-8")

        # Parse frontmatter
        assert content.startswith("---"), "File should start with frontmatter"
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Key assertion: source_email_id MUST be in frontmatter
        assert "source_email_id" in frontmatter, (
            f"source_email_id not found in frontmatter. "
            f"Frontmatter keys: {list(frontmatter.keys())}"
        )
        assert frontmatter["source_email_id"] == email_id

        # Verify it's NOT in the body (old broken behavior)
        body = parts[2]
        assert (
            f"source_email_id: {email_id}" not in body
        ), "source_email_id should be in frontmatter, not body text"

    def test_create_task_with_full_email_metadata(self, test_data_dir: Path):
        """Task can store full email context: id, subject, from, date."""
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700ABC456"
        subject = "[ACTION REQUIRED] OSB Cycle 38 Vote"
        from_email = "OSB Secretariat <secretariat@oversightboard.com>"
        received_date = "2025-11-10T09:23:00Z"

        result = task_ops.create_task(
            title="OSB Vote task",
            data_dir=test_data_dir,
            priority=0,
            source_email_id=email_id,
            source_subject=subject,
            source_from=from_email,
            source_date=received_date,
        )

        assert result["success"], f"Task creation failed: {result.get('message')}"

        # Parse frontmatter
        task_path = test_data_dir / "tasks/inbox" / result["filename"]
        content = task_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # All email metadata should be in frontmatter
        assert frontmatter.get("source_email_id") == email_id
        assert frontmatter.get("source_subject") == subject
        assert frontmatter.get("source_from") == from_email
        assert frontmatter.get("source_date") == received_date

    def test_load_task_preserves_email_metadata_in_file(self, test_data_dir: Path):
        """Email metadata should persist in the file and be readable."""
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700ABC789"

        # Create task with email metadata
        result = task_ops.create_task(
            title="Task with email",
            data_dir=test_data_dir,
            source_email_id=email_id,
        )
        assert result["success"]

        # Verify the file still has the email metadata after creation
        task_path = test_data_dir / "tasks/inbox" / result["filename"]
        content = task_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Email metadata should be in frontmatter
        assert (
            frontmatter.get("source_email_id") == email_id
        ), "Email metadata should persist in file frontmatter"


class TestDuplicateDetection:
    """Tests for email-based duplicate detection."""

    def test_find_task_by_email_id_in_inbox(self, test_data_dir: Path):
        """Should find existing task by source_email_id in inbox."""
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700DEF111"

        # Create a task with this email ID
        result = task_ops.create_task(
            title="Original task",
            data_dir=test_data_dir,
            source_email_id=email_id,
        )
        assert result["success"]

        # Should be able to find this task by email ID
        found = task_ops.find_task_by_email_id(email_id, test_data_dir)
        assert found is not None, "Should find task by email ID"
        assert found.name == result["filename"]

    def test_find_task_by_email_id_in_archived(self, test_data_dir: Path):
        """Should find existing task by source_email_id in archived folder too."""
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700DEF222"

        # Create and archive a task
        result = task_ops.create_task(
            title="Archived task",
            data_dir=test_data_dir,
            source_email_id=email_id,
        )
        assert result["success"]

        archive_result = task_ops.archive_task(result["filename"], test_data_dir)
        assert archive_result["success"]

        # Should still find this task by email ID
        found = task_ops.find_task_by_email_id(email_id, test_data_dir)
        assert found is not None, "Should find archived task by email ID"

    def test_find_task_by_email_id_returns_none_when_not_found(
        self, test_data_dir: Path
    ):
        """Should return None when no task has the given email ID."""
        found = task_ops.find_task_by_email_id(
            "nonexistent_email_id_12345", test_data_dir
        )
        assert found is None

    def test_duplicate_detection_prevents_duplicate_tasks(self, test_data_dir: Path):
        """Creating task with same email ID should be blocked."""
        email_id = "000000007B6215BCACD3504A9611009CCE8879880700DEF333"

        # Create first task
        result1 = task_ops.create_task(
            title="First task",
            data_dir=test_data_dir,
            source_email_id=email_id,
        )
        assert result1["success"]

        # Attempt to create second task with same email ID should fail
        result2 = task_ops.create_task(
            title="Duplicate task",
            data_dir=test_data_dir,
            source_email_id=email_id,
        )
        assert not result2["success"], "Should reject duplicate email ID"
        assert (
            "duplicate" in result2["message"].lower()
            or "already" in result2["message"].lower()
        )
