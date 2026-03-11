#!/usr/bin/env python3
from datetime import UTC, datetime

from task_model import Task, TaskStatus, TaskType


def test_task_planned_field_serialization_deserialization():
    """Verify that the 'planned' field is correctly serialized and deserialized."""
    planned_date = datetime.now(UTC)
    task = Task(
        id="test-123",
        title="Test Task with Planned Date",
        type=TaskType.TASK,
        planned=planned_date,
    )

    # Serialize to markdown
    markdown_content = task.to_markdown()

    # Deserialize back to a Task object
    rehydrated_task = Task.from_markdown(markdown_content)

    # Assert that the 'planned' field is correctly restored
    assert rehydrated_task.planned is not None
    assert rehydrated_task.planned.year == planned_date.year
    assert rehydrated_task.planned.month == planned_date.month
    assert rehydrated_task.planned.day == planned_date.day
    assert rehydrated_task.planned.hour == planned_date.hour
    assert rehydrated_task.planned.minute == planned_date.minute
    # Comparing seconds can be flaky, so we check the other components

    # Check that it's in the frontmatter
    assert "planned:" in markdown_content


def test_task_planned_field_is_optional():
    """Verify that a task can be created without a 'planned' date."""
    task = Task(
        id="test-456",
        title="Test Task without Planned Date",
        type=TaskType.TASK,
    )
    assert task.planned is None

    # Serialize and deserialize
    markdown_content = task.to_markdown()
    rehydrated_task = Task.from_markdown(markdown_content)

    assert rehydrated_task.planned is None
    assert "planned:" not in markdown_content


def test_pr_and_issue_fields_serialization():
    """Verify that pr and issue fields are correctly serialized and deserialized."""
    task = Task(
        id="test-pr-issue",
        title="Task with PR and Issue",
        type=TaskType.TASK,
        pr=42,
        issue=7,
    )

    markdown_content = task.to_markdown()
    rehydrated = Task.from_markdown(markdown_content)

    assert rehydrated.pr == 42
    assert rehydrated.issue == 7
    assert "pr: 42" in markdown_content
    assert "issue: 7" in markdown_content


def test_pr_and_issue_fields_are_optional():
    """Verify that pr and issue fields are omitted when not set."""
    task = Task(id="test-no-pr", title="Task without PR or Issue", type=TaskType.TASK)

    markdown_content = task.to_markdown()
    rehydrated = Task.from_markdown(markdown_content)

    assert rehydrated.pr is None
    assert rehydrated.issue is None
    assert "pr:" not in markdown_content
    assert "issue:" not in markdown_content


def test_review_transition_requires_pr_or_pr_url():
    """Verify that transitioning to REVIEW without pr or pr_url is rejected."""
    task = Task(
        id="test-review-guard",
        title="Task to test review guard",
        type=TaskType.TASK,
        status=TaskStatus.IN_PROGRESS,
        worker_id="polecat-1",
    )

    result = task.transition_to(TaskStatus.REVIEW)
    assert not result.success
    assert "pr_url or pr" in (result.error or "")


def test_review_transition_succeeds_with_pr_number():
    """Verify that transitioning to REVIEW succeeds when pr (number) is provided."""
    task = Task(
        id="test-review-pr",
        title="Task to test review with pr number",
        type=TaskType.TASK,
        status=TaskStatus.IN_PROGRESS,
        worker_id="polecat-1",
    )

    task.transition_to(TaskStatus.REVIEW, pr=99)

    assert task.status == TaskStatus.REVIEW
    assert task.pr == 99


def test_issue_field_preserved_across_transitions():
    """Verify that the issue field persists when a task moves back from REVIEW to IN_PROGRESS."""
    task = Task(
        id="test-issue-persist",
        title="Task to verify issue persistence",
        type=TaskType.TASK,
        status=TaskStatus.IN_PROGRESS,
        worker_id="polecat-1",
        issue=101,
    )

    task.transition_to(TaskStatus.REVIEW, pr=55)
    assert task.issue == 101

    # Transition back (changes requested) — pr is cleared, but issue must persist
    task.transition_to(TaskStatus.IN_PROGRESS, worker_id="polecat-1")
    assert task.issue == 101
    assert task.pr is None
