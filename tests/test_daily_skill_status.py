"""Tests for skill status classification and diagnosis, specifically verifying that
the retired `/daily` skill is correctly diagnosed as `deliberately_removed`.
"""

from __future__ import annotations

from pathlib import Path

from transcripts.domain.skills import (
    SkillStatus,
    diagnose_skill,
    diagnose_skill_status,
    get_all_skills_diagnostics,
    is_deliberately_removed,
)

PLUGINS_ROOT = Path(__file__).resolve().parent.parent / "plugins"


def test_daily_skill_status_diagnosed_as_deliberately_removed() -> None:
    """Verify that `/daily` skill is diagnosed as `deliberately_removed`."""
    status_slash = diagnose_skill_status("/daily", plugins_dir=PLUGINS_ROOT)
    status_plain = diagnose_skill_status("daily", plugins_dir=PLUGINS_ROOT)

    assert status_slash == SkillStatus.DELIBERATELY_REMOVED
    assert status_slash == "deliberately_removed"
    assert status_plain == SkillStatus.DELIBERATELY_REMOVED

    # Ensure it is NOT misdiagnosed as install failure or missing
    assert status_slash != SkillStatus.INSTALL_FAILURE
    assert status_slash != "install_failure"
    assert status_slash != SkillStatus.MISSING


def test_daily_skill_detailed_diagnostics() -> None:
    """Verify detailed diagnostic reporting dictionary for `/daily`."""
    diag = diagnose_skill("/daily", plugins_dir=PLUGINS_ROOT)

    assert diag["skill"] == "/daily"
    assert diag["status"] == "deliberately_removed"
    assert diag["is_deliberately_removed"] is True
    assert diag["is_install_failure"] is False
    assert "deliberately removed" in diag["details"].lower()


def test_is_deliberately_removed_helper() -> None:
    """Verify `is_deliberately_removed` correctly identifies retired skill variants."""
    assert is_deliberately_removed("/daily") is True
    assert is_deliberately_removed("daily") is True
    assert is_deliberately_removed("/daily-note-template") is True
    assert is_deliberately_removed("aops-core:daily") is True
    assert is_deliberately_removed("analyst") is False
    assert is_deliberately_removed("non_existent_skill") is False


def test_active_skill_status_diagnosed_as_installed() -> None:
    """Verify that active skills (e.g. analyst, brief) are diagnosed as installed."""
    assert diagnose_skill_status("analyst", plugins_dir=PLUGINS_ROOT) == SkillStatus.INSTALLED
    assert diagnose_skill_status("brief", plugins_dir=PLUGINS_ROOT) == SkillStatus.INSTALLED


def test_unknown_skill_diagnosed_as_missing() -> None:
    """Verify that an unknown non-existent skill is diagnosed as missing."""
    status = diagnose_skill_status("nonexistent_random_skill_9999", plugins_dir=PLUGINS_ROOT)
    assert status == SkillStatus.MISSING
    assert status != SkillStatus.DELIBERATELY_REMOVED
    assert status != SkillStatus.INSTALLED


def test_corrupted_skill_diagnosed_as_install_failure(tmp_path: Path) -> None:
    """Verify that a skill directory present without SKILL.md returns INSTALL_FAILURE."""
    plugins_dir = tmp_path / "plugins"
    skill_dir = plugins_dir / "tools" / "skills" / "broken_skill"
    skill_dir.mkdir(parents=True)

    status = diagnose_skill_status("broken_skill", plugins_dir=plugins_dir)
    assert status == SkillStatus.INSTALL_FAILURE
    assert status == "install_failure"

    diag = diagnose_skill("broken_skill", plugins_dir=plugins_dir)
    assert diag["status"] == "install_failure"
    assert diag["is_install_failure"] is True
    assert "installation failed" in diag["details"].lower()


def test_all_skills_diagnostics_report() -> None:
    """Verify diagnostic batch summary for multiple skills."""
    skills_to_test = ["/daily", "analyst", "nonexistent_skill_xyz"]
    report = get_all_skills_diagnostics(skills_to_test, plugins_dir=PLUGINS_ROOT)

    assert report["/daily"]["status"] == "deliberately_removed"
    assert report["/daily"]["is_deliberately_removed"] is True

    assert report["analyst"]["status"] == "installed"
    assert report["analyst"]["is_deliberately_removed"] is False

    assert report["nonexistent_skill_xyz"]["status"] == "missing"
    assert report["nonexistent_skill_xyz"]["is_deliberately_removed"] is False
