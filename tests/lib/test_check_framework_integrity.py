"""Tests for scripts/check_framework_integrity.py.

Covers both directions of the skills index check:
1. SKILLS.md -> disk: dangling references caught
2. disk -> SKILLS.md: missing entries caught (the bug from 2026-03-05 audit)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_framework_integrity import (
    check_index_skills,
    check_index_wikilinks,
    check_workflow_length,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def plugin_root(tmp_path: Path) -> Path:
    """Minimal plugin root with skills/ and commands/ directories."""
    (tmp_path / "skills").mkdir()
    (tmp_path / "commands").mkdir()
    return tmp_path


def make_skill(root: Path, name: str) -> None:
    """Create a skills/<name>/SKILL.md file."""
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n# {name}\n")


def make_command(root: Path, name: str) -> None:
    """Create a commands/<name>.md file."""
    (root / "commands" / f"{name}.md").write_text(f"---\nname: {name}\n---\n# {name}\n")


def make_skills_index(root: Path, entries: list[str]) -> None:
    """Create SKILLS.md with the given skill/command names in the table."""
    rows = "\n".join(f"| `/{name}` | trigger | Description for {name} |" for name in entries)
    content = (
        "---\nname: skills\n---\n\n"
        "# Skills Index\n\n"
        "| Skill | Triggers | Description |\n"
        "| ----- | -------- | ----------- |\n"
        f"{rows}\n"
    )
    (root / "SKILLS.md").write_text(content)


# ---------------------------------------------------------------------------
# check_index_skills: Check 1 — SKILLS.md -> disk (dangling refs)
# ---------------------------------------------------------------------------


def test_skills_index_dangling_ref_caught(plugin_root: Path) -> None:
    """SKILLS.md entry with no corresponding SKILL.md or command file is an error."""
    make_skills_index(plugin_root, ["ghost-skill"])
    # No skill directory created on disk

    errors = check_index_skills(plugin_root)

    assert len(errors) == 1
    assert "ghost-skill" in errors[0]
    assert "missing from SKILLS.md" not in errors[0]  # This is the other direction


def test_skills_index_valid_entry_passes(plugin_root: Path) -> None:
    """SKILLS.md entry with matching SKILL.md passes."""
    make_skill(plugin_root, "analyst")
    make_skills_index(plugin_root, ["analyst"])

    errors = check_index_skills(plugin_root)

    assert errors == []


def test_command_valid_entry_passes(plugin_root: Path) -> None:
    """SKILLS.md entry with matching commands/<name>.md passes."""
    make_command(plugin_root, "dump")
    make_skills_index(plugin_root, ["dump"])

    errors = check_index_skills(plugin_root)

    assert errors == []


# ---------------------------------------------------------------------------
# check_index_skills: Check 2 — disk -> SKILLS.md (missing entries)
# This is the bug discovered in the 2026-03-05 audit: 5 skills had SKILL.md
# files on disk but were absent from SKILLS.md, causing silent routing gaps.
# ---------------------------------------------------------------------------


def test_unindexed_skill_caught(plugin_root: Path) -> None:
    """SKILL.md on disk but absent from SKILLS.md is an error."""
    make_skill(plugin_root, "hdr")
    make_skills_index(plugin_root, [])  # Empty index — hdr not listed

    errors = check_index_skills(plugin_root)

    assert len(errors) == 1
    assert "hdr" in errors[0]
    assert "missing from SKILLS.md" in errors[0]


def test_unindexed_command_caught(plugin_root: Path) -> None:
    """commands/<name>.md on disk but absent from SKILLS.md is an error."""
    make_command(plugin_root, "bump")
    make_skills_index(plugin_root, [])  # Empty index — bump not listed

    errors = check_index_skills(plugin_root)

    assert len(errors) == 1
    assert "bump" in errors[0]
    assert "missing from SKILLS.md" in errors[0]


def test_multiple_unindexed_skills_all_caught(plugin_root: Path) -> None:
    """Regression: 2026-03-05 audit found 5 skills + 2 commands missing.

    All should be reported, not just the first.
    """
    missing = ["annotations", "email-triage", "extract", "hdr", "qa"]
    for name in missing:
        make_skill(plugin_root, name)
    # Only index one of them
    make_skill(plugin_root, "analyst")
    make_skills_index(plugin_root, ["analyst"])

    errors = check_index_skills(plugin_root)

    assert len(errors) == len(missing)
    reported_names = " ".join(errors)
    for name in missing:
        assert name in reported_names, f"Expected {name} to appear in errors: {errors}"


def test_fully_synced_index_passes(plugin_root: Path) -> None:
    """All skills on disk are indexed and all index entries have files — no errors."""
    skills = ["analyst", "audit", "daily"]
    commands = ["dump", "pull"]

    for name in skills:
        make_skill(plugin_root, name)
    for name in commands:
        make_command(plugin_root, name)

    make_skills_index(plugin_root, skills + commands)

    errors = check_index_skills(plugin_root)

    assert errors == []


def test_bidirectional_errors_both_reported(plugin_root: Path) -> None:
    """Both dangling refs (index->disk) and missing entries (disk->index) reported together."""
    make_skill(plugin_root, "real-skill")
    make_skills_index(plugin_root, ["real-skill", "ghost-skill"])
    # real-skill: on disk + indexed = OK
    # ghost-skill: indexed but NOT on disk = dangling ref error
    # unindexed-skill: not created, so nothing to miss

    # Add an unindexed skill to trigger the reverse error too
    make_skill(plugin_root, "unindexed-skill")

    errors = check_index_skills(plugin_root)

    assert len(errors) == 2
    error_text = " | ".join(errors)
    assert "ghost-skill" in error_text
    assert "unindexed-skill" in error_text


# ---------------------------------------------------------------------------
# check_index_skills: edge cases
# ---------------------------------------------------------------------------


def test_no_skills_index_returns_no_errors(plugin_root: Path) -> None:
    """Missing SKILLS.md skips check gracefully (returns empty list)."""
    make_skill(plugin_root, "analyst")
    # No SKILLS.md created

    errors = check_index_skills(plugin_root)

    assert errors == []


def test_skill_dir_without_skill_md_ignored(plugin_root: Path) -> None:
    """Directory under skills/ without SKILL.md is not treated as a skill."""
    (plugin_root / "skills" / "not-a-skill").mkdir()
    # No SKILL.md inside — should NOT appear as a missing-from-index error
    make_skills_index(plugin_root, [])

    errors = check_index_skills(plugin_root)

    assert errors == []


# ---------------------------------------------------------------------------
# check_index_wikilinks: smoke tests
# ---------------------------------------------------------------------------


def test_wikilinks_missing_workflow_caught(plugin_root: Path) -> None:
    """WORKFLOWS.md wikilink to nonexistent workflow file is an error."""
    (plugin_root / "WORKFLOWS.md").write_text("# Workflows\n\n[[ghost-workflow]]\n")
    (plugin_root / "workflows").mkdir()

    errors = check_index_wikilinks(plugin_root)

    assert any("ghost-workflow" in e for e in errors)


def test_wikilinks_existing_workflow_passes(plugin_root: Path) -> None:
    """WORKFLOWS.md wikilink to existing workflow file passes."""
    wf_dir = plugin_root / "workflows"
    wf_dir.mkdir()
    (wf_dir / "feature-dev.md").write_text("# feature-dev\n")
    (plugin_root / "WORKFLOWS.md").write_text("# Workflows\n\n[[feature-dev]]\n")

    errors = check_index_wikilinks(plugin_root)

    assert errors == []


# ---------------------------------------------------------------------------
# check_workflow_length: smoke tests
# ---------------------------------------------------------------------------


def test_workflow_too_long_caught(plugin_root: Path) -> None:
    """Workflow file exceeding 100 lines is an error."""
    wf_dir = plugin_root / "workflows"
    wf_dir.mkdir()
    long_content = "\n".join(f"line {i}" for i in range(101))
    (wf_dir / "too-long.md").write_text(long_content)

    errors = check_workflow_length(plugin_root)

    assert any("too-long.md" in e for e in errors)


def test_workflow_within_limit_passes(plugin_root: Path) -> None:
    """Workflow file at exactly 100 lines passes."""
    wf_dir = plugin_root / "workflows"
    wf_dir.mkdir()
    content = "\n".join(f"line {i}" for i in range(100))
    (wf_dir / "short.md").write_text(content)

    errors = check_workflow_length(plugin_root)

    assert errors == []
