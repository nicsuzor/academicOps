"""Tests for R1: Email Triage Workflow Component (wf-email-triage.md).

Verifies file location, frontmatter schema, INDEX.md routing, and inclusion
in dist/ build artifacts.
"""

from pathlib import Path

import yaml

from build.build import build_all

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_MARKETPLACE = PROJECT_ROOT / "build" / "marketplace.toml"
WORKFLOW_SOURCE = PROJECT_ROOT / "plugins" / "pkb" / "workflows" / "wf-email-triage.md"
INDEX_SOURCE = PROJECT_ROOT / "plugins" / "pkb" / "workflows" / "INDEX.md"


def _parse_frontmatter(file_path: Path) -> dict:
    content = file_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return yaml.safe_load(parts[1])
    raise ValueError(f"No YAML frontmatter found in {file_path}")


def test_wf_email_triage_file_exists():
    """Verify wf-email-triage.md exists at expected location in plugins/pkb/workflows/."""
    assert WORKFLOW_SOURCE.is_file(), f"Expected workflow component file at {WORKFLOW_SOURCE}"


def test_wf_email_triage_frontmatter_schema():
    """Verify frontmatter schema: id, kind, permalink, and requires."""
    fm = _parse_frontmatter(WORKFLOW_SOURCE)

    assert fm.get("id") == "wf-email-triage", f"Expected id='wf-email-triage', got {fm.get('id')}"
    assert fm.get("kind") == "obligation", f"Expected kind='obligation', got {fm.get('kind')}"
    assert fm.get("permalink") == "wf-email-triage", (
        f"Expected permalink='wf-email-triage', got {fm.get('permalink')}"
    )

    requires = fm.get("requires")
    assert isinstance(requires, list), f"Expected requires to be a list, got {type(requires)}"
    assert "task-tracking" in requires, f"Expected 'task-tracking' in requires, got {requires}"


def test_wf_email_triage_indexed():
    """Verify plugins/pkb/workflows/INDEX.md routes and lists [[wf-email-triage]]."""
    assert INDEX_SOURCE.is_file(), f"Expected INDEX.md at {INDEX_SOURCE}"
    content = INDEX_SOURCE.read_text(encoding="utf-8")
    assert "[[wf-email-triage]]" in content, "Expected [[wf-email-triage]] to be listed in INDEX.md"


def test_wf_email_triage_dist_artifact_inclusion(tmp_path):
    """Verify wf-email-triage.md is included in dist artifacts for all client targets after build."""
    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["pkb"],
        version="0.0.0-test",
    )

    for client in ("claude", "agy"):
        built_file = dist_root / f"pkb-{client}" / "workflows" / "wf-email-triage.md"
        assert built_file.is_file(), f"Built artifact missing at {built_file}"

        fm = _parse_frontmatter(built_file)
        assert fm.get("id") == "wf-email-triage"
        assert fm.get("kind") == "obligation"
        assert fm.get("permalink") == "wf-email-triage"
        assert "task-tracking" in fm.get("requires", [])
