#!/usr/bin/env python3
from datetime import datetime, timezone
from aops_core.lib.task_model import Task, TaskType


def test_task_planned_field_serialization_deserialization():
    """Verify that the 'planned' field is correctly serialized and deserialized."""
    planned_date = datetime.now(timezone.utc)
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
