#!/usr/bin/env python3
"""
Unit tests for framework installation validation.

These tests verify that setup.sh has been run correctly by checking that all
required symlinks exist in ~/.claude/ and point to the correct targets.
"""

from pathlib import Path

import pytest

from lib.paths import get_aops_root


def test_claude_directory_exists() -> None:
    """Test that ~/.claude/ directory exists.

    Raises:
        AssertionError: If ~/.claude/ directory doesn't exist
    """
    claude_dir = Path.home() / ".claude"
    assert claude_dir.exists(), f"~/.claude/ directory doesn't exist: {claude_dir}"
    assert claude_dir.is_dir(), f"~/.claude/ exists but is not a directory: {claude_dir}"


def test_settings_json_symlink_exists() -> None:
    """Test that ~/.claude/settings.json is a symlink.

    Raises:
        AssertionError: If settings.json doesn't exist or is not a symlink
    """
    settings_link = Path.home() / ".claude" / "settings.json"
    assert settings_link.exists(), f"settings.json doesn't exist: {settings_link}"
    assert settings_link.is_symlink(), f"settings.json exists but is not a symlink: {settings_link}"


def test_settings_json_points_to_correct_target() -> None:
    """Test that ~/.claude/settings.json points to $AOPS/config/claude/settings.json.

    Raises:
        AssertionError: If settings.json doesn't point to the correct target
    """
    aops_root = get_aops_root()
    settings_link = Path.home() / ".claude" / "settings.json"
    expected_target = aops_root / "config" / "claude" / "settings.json"

    actual_target = settings_link.resolve()
    assert actual_target == expected_target, (
        f"settings.json symlink points to wrong target.\n"
        f"  Expected: {expected_target}\n"
        f"  Actual:   {actual_target}"
    )


def test_skills_symlink_exists_and_points_to_aops() -> None:
    """Test that ~/.claude/skills symlink exists and points to $AOPS/skills.

    Raises:
        AssertionError: If skills symlink doesn't exist or points to wrong target
    """
    aops_root = get_aops_root()
    skills_link = Path.home() / ".claude" / "skills"
    expected_target = aops_root / "skills"

    assert skills_link.exists(), f"skills symlink doesn't exist: {skills_link}"
    assert skills_link.is_symlink(), f"skills exists but is not a symlink: {skills_link}"

    actual_target = skills_link.resolve()
    assert actual_target == expected_target, (
        f"skills symlink points to wrong target.\n"
        f"  Expected: {expected_target}\n"
        f"  Actual:   {actual_target}"
    )


def test_commands_symlink_exists_and_points_to_aops() -> None:
    """Test that ~/.claude/commands symlink exists and points to $AOPS/commands.

    Raises:
        AssertionError: If commands symlink doesn't exist or points to wrong target
    """
    aops_root = get_aops_root()
    commands_link = Path.home() / ".claude" / "commands"
    expected_target = aops_root / "commands"

    assert commands_link.exists(), f"commands symlink doesn't exist: {commands_link}"
    assert commands_link.is_symlink(), f"commands exists but is not a symlink: {commands_link}"

    actual_target = commands_link.resolve()
    assert actual_target == expected_target, (
        f"commands symlink points to wrong target.\n"
        f"  Expected: {expected_target}\n"
        f"  Actual:   {actual_target}"
    )


def test_agents_symlink_exists_and_points_to_aops() -> None:
    """Test that ~/.claude/agents symlink exists and points to $AOPS/agents.

    Raises:
        AssertionError: If agents symlink doesn't exist or points to wrong target
    """
    aops_root = get_aops_root()
    agents_link = Path.home() / ".claude" / "agents"
    expected_target = aops_root / "agents"

    assert agents_link.exists(), f"agents symlink doesn't exist: {agents_link}"
    assert agents_link.is_symlink(), f"agents exists but is not a symlink: {agents_link}"

    actual_target = agents_link.resolve()
    assert actual_target == expected_target, (
        f"agents symlink points to wrong target.\n"
        f"  Expected: {expected_target}\n"
        f"  Actual:   {actual_target}"
    )


def test_mcp_json_symlink_exists_and_points_to_aops() -> None:
    """Test that ~/.mcp.json symlink exists and points to $AOPS/config/claude/mcp.json.

    Raises:
        AssertionError: If .mcp.json symlink doesn't exist or points to wrong target
    """
    aops_root = get_aops_root()
    mcp_link = Path.home() / ".mcp.json"
    expected_target = aops_root / "config" / "claude" / "mcp.json"

    assert mcp_link.exists(), f".mcp.json symlink doesn't exist: {mcp_link}"
    assert mcp_link.is_symlink(), f".mcp.json exists but is not a symlink: {mcp_link}"

    actual_target = mcp_link.resolve()
    assert actual_target == expected_target, (
        f".mcp.json symlink points to wrong target.\n"
        f"  Expected: {expected_target}\n"
        f"  Actual:   {actual_target}"
    )


def test_claude_json_has_no_mcp_servers() -> None:
    """Test that ~/.claude.json doesn't contain mcpServers keys.

    MCP configs should live in .mcp.json files, not ~/.claude.json.
    setup.sh removes these to prevent config drift.

    Raises:
        AssertionError: If mcpServers found in ~/.claude.json
    """
    import json

    claude_json = Path.home() / ".claude.json"
    if not claude_json.exists():
        pytest.skip("~/.claude.json doesn't exist")

    data = json.loads(claude_json.read_text())

    # Check root-level mcpServers
    assert "mcpServers" not in data, (
        "~/.claude.json contains root-level mcpServers. "
        "Run setup.sh to clean up (MCP configs should be in .mcp.json)"
    )

    # Check project-level mcpServers
    projects_with_mcp = []
    for project_path, project_data in data.get("projects", {}).items():
        if isinstance(project_data, dict) and project_data.get("mcpServers"):
            projects_with_mcp.append(project_path)

    assert not projects_with_mcp, (
        f"~/.claude.json contains mcpServers in projects: {projects_with_mcp}. "
        "Run setup.sh to clean up (MCP configs should be in .mcp.json)"
    )
