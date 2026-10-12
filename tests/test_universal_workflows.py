"""Tests for universal workflow template resolution and contract compliance.

Verifies that universal workflow templates configured in tests/policy.toml
resolve in the ida plugin's universal workflow-library tier and meet structural
schema requirements (frontmatter type, title, description, and line limit < 100).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from build.build import build_all

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POLICY_FILE = _REPO_ROOT / "tests" / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}
_REQUIRED_WORKFLOWS = (
    _policy.get("plugins", {}).get("workflows", {}).get("required_universal_workflows", [])
)
_WORKFLOWS_DIR = _REPO_ROOT / "plugins" / "ida" / "skills" / "workflow-library" / "workflows"
_MARKETPLACE_PATH = _REPO_ROOT / "build" / "marketplace.toml"


def _parse_frontmatter(path: Path) -> tuple[dict, str, int]:
    """Parse YAML frontmatter and body from a markdown template file.

    Returns (frontmatter_dict, body_text, total_line_count).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_count = len(lines)

    if not text.startswith("---"):
        return {}, text, line_count

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text, line_count

    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return frontmatter, body, line_count


@pytest.mark.parametrize("slug", _REQUIRED_WORKFLOWS)
def test_universal_workflow_resolves_in_source(slug: str) -> None:
    """Verify that required universal workflow templates exist and satisfy schema in source."""
    template_path = _WORKFLOWS_DIR / f"{slug}.md"
    assert template_path.is_file(), (
        f"Universal workflow template {slug} not found at {template_path}"
    )

    frontmatter, _body, line_count = _parse_frontmatter(template_path)
    assert frontmatter.get("type") == "template", f"{slug} must have frontmatter 'type: template'"
    assert frontmatter.get("title"), f"{slug} must have frontmatter 'title'"
    assert frontmatter.get("description"), f"{slug} must have frontmatter 'description'"
    assert line_count < 100, f"{slug} line count must be under 100 lines (got {line_count})"


def test_universal_workflows_resolve_in_built_plugins(tmp_path: Path) -> None:
    """Verify that building the ida plugin distributes required universal workflows."""
    assert _MARKETPLACE_PATH.is_file(), f"Missing {_MARKETPLACE_PATH}"

    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_MARKETPLACE_PATH,
        plugins=["ida"],
        clients=["claude", "agy"],
        version="0.10.10-test",
    )

    for client in ("claude", "agy"):
        plugin_workflows_dir = (
            dist_root / f"ida-{client}" / "skills" / "workflow-library" / "workflows"
        )
        assert plugin_workflows_dir.is_dir(), f"Expected workflows dir at {plugin_workflows_dir}"

        for slug in _REQUIRED_WORKFLOWS:
            template_path = plugin_workflows_dir / f"{slug}.md"
            assert template_path.is_file(), (
                f"Universal workflow template {slug} not found in built ida-{client} distribution"
            )
