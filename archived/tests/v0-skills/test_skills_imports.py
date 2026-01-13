"""Test that skills package structure supports proper imports.

This test verifies that the skills package can be imported and that
skill modules (like task_ops) are accessible via proper import paths.
"""


def test_skills_package_import():
    """Test that skills package can be imported."""
    import skills

    assert skills is not None


def test_task_ops_import():
    """Test that task_ops module can be imported from skills.tasks."""
    from skills.tasks import task_ops

    assert task_ops is not None
    # Verify key functions exist
    assert hasattr(task_ops, "list_tasks")
    assert hasattr(task_ops, "archive_task")
