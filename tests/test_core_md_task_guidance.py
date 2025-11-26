"""Test that CORE.md guides agents to check skills for task operations.

Integration test validating that agent instructions include proper guidance
for task-related operations to use the task skill.
"""

from pathlib import Path

from lib.paths import get_data_root


def test_core_md_references_task_skill():
    """Verify CORE.md guides agents to check skills/README.md for task operations.

    This test validates that agents receive explicit guidance to:
    1. Check skills/README.md when handling task operations
    2. Use the task skill for task management
    3. Not write task files directly

    The test will fail if CORE.md lacks this critical guidance.
    """
    # Arrange: Locate CORE.md in data repository (user-specific, not framework)
    core_md_path = get_data_root() / "CORE.md"
    assert core_md_path.exists(), f"CORE.md not found at {core_md_path}"

    # Act: Read CORE.md content
    core_content = core_md_path.read_text()

    # Assert: Verify task-related guidance exists
    # Look for a section about tasks/task operations
    assert (
        "## Task" in core_content or "task" in core_content.lower()
    ), "CORE.md should mention tasks to guide agents on task operations"

    # Verify it references the skills system for task operations
    assert "skills/README.md" in core_content or "task skill" in core_content.lower(), (
        "CORE.md should reference skills/README.md or task skill for task operations. "
        "Agents need explicit guidance to check skills documentation when handling "
        "task-related requests (viewing tasks, archiving, creating). "
        "Expected: A section that tells agents to check skills/README.md or use the task skill."
    )

    # Verify it mentions NOT writing task files directly
    assert "script" in core_content.lower() or "skill" in core_content.lower(), (
        "CORE.md should guide agents to use scripts/skills for task operations, "
        "not write task files directly"
    )
