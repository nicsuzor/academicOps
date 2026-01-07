#!/usr/bin/env python3
"""
Tests for namespace collision detection.

Per H8: Framework objects (skills, commands, hooks, agents) must have unique
names across all namespaces. Claude Code treats same-named commands as
model-only, causing "can only be invoked by Claude" errors.
"""

from pathlib import Path


class TestNamespaceCollisionDetection:
    """Tests for check_namespace_collisions() function."""

    def test_detects_command_skill_collision(self, tmp_path: Path) -> None:
        """Test detection of command/skill name collision."""
        # Arrange - Create collision: commands/foo.md and skills/foo/
        commands_dir = tmp_path / "commands"
        skills_dir = tmp_path / "skills"
        commands_dir.mkdir()
        skills_dir.mkdir()

        (commands_dir / "foo.md").touch()
        (skills_dir / "foo").mkdir()
        (skills_dir / "foo" / "SKILL.md").touch()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert
        assert len(collisions) == 1
        name, ns1, ns2 = collisions[0]
        assert name == "foo"
        assert {ns1, ns2} == {"commands", "skills"}

    def test_detects_multiple_collisions(self, tmp_path: Path) -> None:
        """Test detection of multiple collisions across namespaces."""
        # Arrange - Create multiple collisions
        commands_dir = tmp_path / "commands"
        skills_dir = tmp_path / "skills"
        agents_dir = tmp_path / "agents"
        hooks_dir = tmp_path / "hooks"

        for d in [commands_dir, skills_dir, agents_dir, hooks_dir]:
            d.mkdir()

        # Collision 1: audit in commands and skills
        (commands_dir / "audit.md").touch()
        (skills_dir / "audit").mkdir()

        # Collision 2: next in commands and skills
        (commands_dir / "next.md").touch()
        (skills_dir / "next").mkdir()

        # Collision 3: convert-to-md in commands and skills
        (commands_dir / "convert-to-md.md").touch()
        (skills_dir / "convert-to-md").mkdir()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert
        assert len(collisions) == 3
        collision_names = {c[0] for c in collisions}
        assert collision_names == {"audit", "next", "convert-to-md"}

    def test_detects_hook_agent_collision(self, tmp_path: Path) -> None:
        """Test detection of hook/agent name collision."""
        # Arrange
        agents_dir = tmp_path / "agents"
        hooks_dir = tmp_path / "hooks"
        agents_dir.mkdir()
        hooks_dir.mkdir()

        (agents_dir / "example.md").touch()
        (hooks_dir / "example.py").touch()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert
        assert len(collisions) == 1
        name, ns1, ns2 = collisions[0]
        assert name == "example"
        assert {ns1, ns2} == {"agents", "hooks"}

    def test_no_collision_returns_empty(self, tmp_path: Path) -> None:
        """Test no collisions returns empty list."""
        # Arrange - Create non-colliding names
        commands_dir = tmp_path / "commands"
        skills_dir = tmp_path / "skills"
        commands_dir.mkdir()
        skills_dir.mkdir()

        (commands_dir / "do.md").touch()
        (commands_dir / "learn.md").touch()
        (skills_dir / "framework").mkdir()
        (skills_dir / "remember").mkdir()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert
        assert collisions == []

    def test_handles_missing_directories(self, tmp_path: Path) -> None:
        """Test graceful handling when directories don't exist."""
        # Arrange - Only create commands, not skills/agents/hooks
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "foo.md").touch()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert - Should not crash, return empty
        assert collisions == []

    def test_ignores_non_md_command_files(self, tmp_path: Path) -> None:
        """Test that non-.md files in commands are ignored."""
        # Arrange
        commands_dir = tmp_path / "commands"
        skills_dir = tmp_path / "skills"
        commands_dir.mkdir()
        skills_dir.mkdir()

        # Create .py file in commands (should be ignored)
        (commands_dir / "foo.py").touch()
        (skills_dir / "foo").mkdir()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert - No collision because foo.py is ignored
        assert collisions == []

    def test_ignores_files_in_skills_dir(self, tmp_path: Path) -> None:
        """Test that files (not directories) in skills/ are ignored."""
        # Arrange
        commands_dir = tmp_path / "commands"
        skills_dir = tmp_path / "skills"
        commands_dir.mkdir()
        skills_dir.mkdir()

        (commands_dir / "readme.md").touch()
        # Create file instead of directory in skills - should be ignored
        (skills_dir / "readme").touch()

        # Act
        from scripts.audit_framework_health import check_namespace_collisions

        collisions = check_namespace_collisions(tmp_path)

        # Assert - No collision because skills/readme is a file, not directory
        assert collisions == []
