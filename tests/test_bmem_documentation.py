"""Test that bmem SKILL.md documents default_project_mode configuration.

This test verifies that the bmem SKILL.md file explicitly documents:
1. That default_project_mode is configurable
2. That the project parameter is optional (not required)
3. Configuration location (~/.basic-memory/config.json)
"""

from pathlib import Path


def test_bmem_skill_documents_default_project_mode(bots_dir: Path) -> None:
    """Test that bmem SKILL.md documents default_project_mode configuration.

    Verifies the SKILL.md file contains documentation explaining that:
    - default_project_mode can be configured
    - project parameter is optional when default is set
    - Configuration location is ~/.basic-memory/config.json

    Args:
        bots_dir: Framework root directory fixture

    Raises:
        AssertionError: If required documentation is missing
    """
    skill_path = bots_dir / "skills" / "bmem" / "SKILL.md"
    assert skill_path.exists(), f"bmem SKILL.md not found at {skill_path}"

    content = skill_path.read_text(encoding="utf-8")

    # Check for documentation about default_project_mode configuration
    assert "default_project_mode" in content, (
        "SKILL.md must document 'default_project_mode' configuration"
    )

    # Check that project parameter is documented as optional
    assert "project parameter is optional" in content or (
        "project" in content and "optional" in content
    ), (
        "SKILL.md must state that project parameter is optional"
    )

    # Check for configuration location documentation
    assert "~/.basic-memory/config.json" in content or (
        "config.json" in content and "basic-memory" in content
    ), (
        "SKILL.md must document configuration location "
        "(~/.basic-memory/config.json)"
    )
