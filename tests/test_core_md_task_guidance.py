"""Test that CORE.md guides agents to check skills for task operations.

Integration test validating that agent instructions include proper guidance
for task-related operations to use the task skill.
"""

from pathlib import Path


def test_core_md_references_task_skill():
    """Verify CORE.md guides agents to check skills/README.md for task operations.

    This test validates that agents receive explicit guidance to:
    1. Check bots/skills/README.md when handling task operations
    2. Use the task skill for task management
    3. Not write task files directly

    The test will fail if CORE.md lacks this critical guidance.
    """
    # Arrange: Locate CORE.md
    # Path: tests/ -> bots/ -> CORE.md
    repo_root = Path(__file__).parent.parent.parent
    core_md_path = repo_root / "bots" / "CORE.md"
    assert core_md_path.exists(), f"CORE.md not found at {core_md_path}"

    # Act: Read CORE.md content
    core_content = core_md_path.read_text()

    # Assert: Verify the exact task guidance text exists
    # This prevents false positives from loose substring matching
    expected_guidance = (
        "**Task operations**: For task management (viewing, archiving, creating), "
        "check [[skills/README.md]] for the task skill. Tasks are stored in `data/tasks/`. "
        "Use task scripts, never write task files directly."
    )

    assert expected_guidance in core_content, (
        f"CORE.md is missing the specific task operations guidance.\n"
        f"Expected text:\n{expected_guidance}\n\n"
        f"This is critical for preventing agents from working around documented skills "
        f"and directly manipulating task files."
    )
