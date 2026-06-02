#!/usr/bin/env python3
"""Tests for project alias / repo-name resolution in PolecatManager.

Covers the schema extension that lets ``-p <value>`` accept:
    1. canonical project slug (``aops``)
    2. shorthand aliases via ``project_aliases`` (top-level)
    3. per-project ``aliases:`` list
    4. the project's ``repo:`` field
    5. unknown values still raise with a helpful error listing aliases.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import (  # noqa: E402
    PolecatManager,
    load_project_aliases,
    load_projects,
)

# ---------------------------------------------------------------------------
# load_projects / load_project_aliases — pure-function tests
# ---------------------------------------------------------------------------


def _write_registry(tmp_path: Path, registry: dict) -> Path:
    import yaml

    sessions = tmp_path / "sessions"
    sessions.mkdir(exist_ok=True)
    cfg = sessions / "polecat.yaml"
    # polecat_home is a required key; inject it when the caller's minimal
    # fixture omits it so resolve_polecat_home() (called transitively via
    # load_local_overlay) doesn't fail on a stub yaml.
    if "polecat_home" not in registry:
        registry = {**registry, "polecat_home": str(tmp_path / "polecat_home")}
    cfg.write_text(yaml.dump(registry))
    return cfg


def test_load_projects_captures_aliases_list(tmp_path):
    cfg = _write_registry(
        tmp_path,
        {
            "projects": {
                "aops": {
                    "repo": "academicOps",
                    "aliases": ["acaops", "aca"],
                    "default_branch": "main",
                },
                "brain": {"repo": "brain"},
            }
        },
    )
    projects = load_projects(cfg)
    assert projects["aops"]["aliases"] == ["acaops", "aca"]
    assert projects["aops"]["repo"] == "academicOps"
    assert projects["brain"]["aliases"] == []


def test_load_project_aliases_merges_all_sources(tmp_path):
    cfg = _write_registry(
        tmp_path,
        {
            "projects": {
                "aops": {
                    "repo": "academicOps",
                    "aliases": ["acaops"],
                },
                "buttermilk": {"repo": "buttermilk"},
            },
            "project_aliases": {"bm": "buttermilk"},
        },
    )
    aliases = load_project_aliases(cfg)
    # Top-level alias preserved
    assert aliases["bm"] == "buttermilk"
    # Per-project alias merged
    assert aliases["acaops"] == "aops"
    # Repo name resolves to slug
    assert aliases["academicOps"] == "aops"
    # Canonical slug self-references
    assert aliases["aops"] == "aops"
    assert aliases["buttermilk"] == "buttermilk"


# ---------------------------------------------------------------------------
# PolecatManager.resolve_project_alias — integration with the registry
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path, projects: dict, aliases: dict) -> PolecatManager:
    """Build a PolecatManager without touching disk-resident config."""
    with (
        patch("manager.load_config", return_value={}),
        patch("manager.load_projects", return_value=projects),
        patch("manager.load_project_aliases", return_value=aliases),
        patch("manager.load_crew_names", return_value=["weasel"]),
    ):
        return PolecatManager(home_dir=tmp_path)


@pytest.fixture
def manager(tmp_path):
    projects = {
        "aops": {
            "path": tmp_path / "aops",
            "default_branch": "main",
            "repo": "academicOps",
            "aliases": ["acaops"],
        },
        "buttermilk": {
            "path": tmp_path / "buttermilk",
            "default_branch": "main",
            "repo": "buttermilk",
            "aliases": [],
        },
    }
    aliases = {
        "aops": "aops",
        "buttermilk": "buttermilk",
        "academicOps": "aops",
        "acaops": "aops",
        "bm": "buttermilk",
    }
    return _make_manager(tmp_path, projects, aliases)


class TestResolveProjectAlias:
    def test_canonical_slug_resolves_to_itself(self, manager):
        assert manager.resolve_project_alias("aops") == "aops"

    def test_per_project_alias_resolves(self, manager):
        assert manager.resolve_project_alias("acaops") == "aops"

    def test_top_level_alias_resolves(self, manager):
        assert manager.resolve_project_alias("bm") == "buttermilk"

    def test_repo_name_resolves(self, manager):
        # 'academicOps' is the repo: field for aops
        assert manager.resolve_project_alias("academicOps") == "aops"

    def test_unknown_raises_with_aliases_in_message(self, manager):
        with pytest.raises(ValueError) as ei:
            manager.resolve_project_alias("not-a-project")
        msg = str(ei.value)
        assert "not-a-project" in msg
        # Error must list canonical names AND surface aliases
        assert "aops" in msg
        assert "buttermilk" in msg
        assert "academicOps" in msg or "acaops" in msg

    def test_repo_name_resolves_via_field_fallback(self, tmp_path):
        # If alias map is missing the repo entry (hand-built manager), the
        # field-scan fallback in resolve_project_alias should still find it.
        projects = {
            "aops": {
                "path": tmp_path / "aops",
                "default_branch": "main",
                "repo": "academicOps",
                "aliases": [],
            },
        }
        # Deliberately omit 'academicOps' from the alias map.
        aliases = {"aops": "aops"}
        m = _make_manager(tmp_path, projects, aliases)
        assert m.resolve_project_alias("academicOps") == "aops"


# ---------------------------------------------------------------------------
# get_repo_path canonicalises task.project via aliases / repo names
# ---------------------------------------------------------------------------


class _Task:
    def __init__(self, task_id: str, project: str):
        self.id = task_id
        self.project = project


class TestGetRepoPathAcceptsAliases:
    def test_repo_name_resolves_to_project_path(self, manager, tmp_path):
        # Pre-create the repo path so get_repo_path returns it (no mirror present).
        (tmp_path / "aops").mkdir()
        task = _Task("task-x", "academicOps")
        path = manager.get_repo_path(task)
        assert path == tmp_path / "aops"
        # task.project should have been canonicalised
        assert task.project == "aops"

    def test_alias_resolves_to_project_path(self, manager, tmp_path):
        (tmp_path / "aops").mkdir()
        task = _Task("task-y", "acaops")
        path = manager.get_repo_path(task)
        assert path == tmp_path / "aops"
        assert task.project == "aops"

    def test_unknown_project_error_includes_aliases(self, manager):
        task = _Task("task-z", "not-real")
        with pytest.raises(ValueError) as ei:
            manager.get_repo_path(task)
        msg = str(ei.value)
        assert "not-real" in msg
        assert "academicOps" in msg or "acaops" in msg
