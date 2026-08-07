"""Skill status classification and diagnosis domain module.

Provides status classification and diagnostic reporting for skills in the
academicOps framework, correctly distinguishing deliberately removed/retired
skills (such as `/daily`) from installation failures or missing skills.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any


def _find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "plugins").exists() and (parent / "pyproject.toml").exists():
            return parent
    return Path(__file__).resolve().parents[4]


PROJECT_ROOT = _find_project_root()
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Known retired or intentionally removed skills across the framework
DELIBERATELY_REMOVED_SKILLS: set[str] = {
    "daily",
    "/daily",
    "daily-note-template",
    "/daily-note-template",
    "aops-core:daily",
}


class SkillStatus(StrEnum):
    INSTALLED = "installed"
    DELIBERATELY_REMOVED = "deliberately_removed"
    INSTALL_FAILURE = "install_failure"
    MISSING = "missing"


def normalize_skill_name(name: str) -> str:
    """Normalize skill name by removing leading slash and whitespace."""
    return name.strip().lstrip("/")


def is_deliberately_removed(skill_name: str, retired_set: set[str] | None = None) -> bool:
    """Check if a skill was deliberately removed/retired."""
    retired = retired_set if retired_set is not None else DELIBERATELY_REMOVED_SKILLS
    normalized = normalize_skill_name(skill_name)
    raw = skill_name.strip()
    return raw in retired or normalized in retired or f"/{normalized}" in retired


def diagnose_skill_status(
    skill_name: str,
    plugins_dir: Path | None = None,
    retired_skills: set[str] | None = None,
) -> SkillStatus:
    """Diagnose the status of a skill.

    Accurately distinguishes deliberately removed skills (such as `/daily`)
    from skills missing due to install failures or absent skills.
    """
    if is_deliberately_removed(skill_name, retired_skills):
        return SkillStatus.DELIBERATELY_REMOVED

    p_dir = plugins_dir or PLUGINS_DIR
    normalized = normalize_skill_name(skill_name)

    if p_dir.exists():
        matching_dirs = [p for p in p_dir.rglob(normalized) if p.is_dir()]
        if matching_dirs:
            for d in matching_dirs:
                if (d / "SKILL.md").is_file():
                    return SkillStatus.INSTALLED
            return SkillStatus.INSTALL_FAILURE

        # Search for SKILL.md parent folder matching normalized
        for skill_md in p_dir.rglob("SKILL.md"):
            if skill_md.parent.name == normalized:
                return SkillStatus.INSTALLED

    return SkillStatus.MISSING


def diagnose_skill(
    skill_name: str,
    plugins_dir: Path | None = None,
    retired_skills: set[str] | None = None,
) -> dict[str, Any]:
    """Return a detailed diagnostic report for a given skill."""
    status = diagnose_skill_status(skill_name, plugins_dir, retired_skills)
    normalized = normalize_skill_name(skill_name)

    if status == SkillStatus.DELIBERATELY_REMOVED:
        details = f"Skill '{skill_name}' was deliberately removed and retired from the framework."
    elif status == SkillStatus.INSTALLED:
        details = f"Skill '{skill_name}' is installed and active."
    elif status == SkillStatus.INSTALL_FAILURE:
        details = f"Skill '{skill_name}' installation failed."
    else:
        details = f"Skill '{skill_name}' is missing."

    return {
        "skill": skill_name,
        "normalized_name": normalized,
        "status": status.value,
        "is_deliberately_removed": status == SkillStatus.DELIBERATELY_REMOVED,
        "is_install_failure": status == SkillStatus.INSTALL_FAILURE,
        "details": details,
    }


def get_all_skills_diagnostics(
    requested_skills: list[str] | None = None,
    plugins_dir: Path | None = None,
    retired_skills: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a list of skills or all known skills."""
    skills_to_check = requested_skills or ["/daily", "daily"]
    return {
        s: diagnose_skill(s, plugins_dir=plugins_dir, retired_skills=retired_skills)
        for s in skills_to_check
    }
