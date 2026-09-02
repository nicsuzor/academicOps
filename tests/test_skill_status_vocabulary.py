"""Tests asserting that skill files only mandate canonical task statuses.

The single source of truth for task statuses is mem's VALID_STATUSES
(references/TAXONOMY.md), mirrored in tests/policy.toml under [pkb.taxonomy].

Skill files must never mandate or template non-canonical status values
(such as 'failed', 'completed', or 'in-progress').
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"

_policy = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
VALID_STATUSES = set(
    _policy.get("aops", _policy.get("pkb", {})).get("taxonomy", {}).get("valid_statuses", [])
)


def skill_files() -> list[Path]:
    return sorted(PLUGINS_DIR.rglob("SKILL.md"))


def test_valid_statuses_policy_loaded():
    assert VALID_STATUSES, "tests/policy.toml [aops.taxonomy].valid_statuses must not be empty"
    assert "done" in VALID_STATUSES
    assert "in_progress" in VALID_STATUSES
    assert "failed" not in VALID_STATUSES


def test_dump_skill_status_template_uses_canonical_statuses():
    dump_skill = PLUGINS_DIR / "aops" / "skills" / "dump" / "SKILL.md"
    assert dump_skill.exists(), f"Missing {dump_skill}"

    text = dump_skill.read_text(encoding="utf-8")
    status_template_re = re.compile(r"<status:\s*([^>]+)>", re.IGNORECASE)

    matches = list(status_template_re.finditer(text))
    assert matches, f"No <status: ...> template found in {dump_skill}"

    for match in matches:
        raw_statuses = [s.strip() for s in match.group(1).split("|")]
        invalid = [s for s in raw_statuses if s not in VALID_STATUSES]
        assert not invalid, (
            f"{dump_skill.relative_to(REPO_ROOT)} mandates non-canonical statuses "
            f"in template: {invalid}. Valid statuses are: {sorted(VALID_STATUSES)}"
        )


@pytest.mark.parametrize("skill_path", skill_files(), ids=lambda p: str(p.relative_to(PLUGINS_DIR)))
def test_all_skills_mandated_statuses_are_canonical(skill_path: Path):
    text = skill_path.read_text(encoding="utf-8")
    status_template_re = re.compile(r"<status:\s*([^>]+)>", re.IGNORECASE)

    for match in status_template_re.finditer(text):
        raw_statuses = [s.strip() for s in match.group(1).split("|")]
        invalid = [s for s in raw_statuses if s not in VALID_STATUSES]
        assert not invalid, (
            f"{skill_path.relative_to(REPO_ROOT)} templates non-canonical statuses: "
            f"{invalid}. Valid statuses: {sorted(VALID_STATUSES)}"
        )


def test_no_skill_mandates_literal_blocked_status_write():
    """Assert no skill file instructs writing or releasing literal 'status: blocked' directly.

    'blocked' is a derived field computed from directed 'blocks' edges, never a value
    stored in frontmatter directly.
    """
    for skill_path in skill_files():
        text = skill_path.read_text(encoding="utf-8")
        assert not re.search(r"release the task as\s+['\"]blocked['\"]", text, re.IGNORECASE), (
            f"{skill_path.relative_to(REPO_ROOT)} instructs releasing task as 'blocked'. "
            "Blocked status must be derived from directed 'blocks' edges."
        )
        assert not re.search(r"released as\s+['\"]blocked['\"]", text, re.IGNORECASE), (
            f"{skill_path.relative_to(REPO_ROOT)} instructs releasing task as 'blocked'. "
            "Blocked status must be derived from directed 'blocks' edges."
        )
        assert not re.search(r"(?m)^\s*status:\s*\"?blocked\"?", text), (
            f"{skill_path.relative_to(REPO_ROOT)} contains literal 'status: blocked' frontmatter write."
        )


def test_dump_skill_does_not_template_literal_blocked():
    """Assert dump skill template does not offer 'blocked' as a writable release status."""
    dump_skill = PLUGINS_DIR / "aops" / "skills" / "dump" / "SKILL.md"
    text = dump_skill.read_text(encoding="utf-8")
    status_template_re = re.compile(r"<status:\s*([^>]+)>", re.IGNORECASE)
    for match in status_template_re.finditer(text):
        raw_statuses = [s.strip() for s in match.group(1).split("|")]
        assert "blocked" not in raw_statuses, (
            f"{dump_skill.relative_to(REPO_ROOT)} includes 'blocked' in <status: ...> template. "
            "'blocked' is derived and should not be offered as a writable status."
        )
