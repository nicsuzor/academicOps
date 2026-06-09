"""Behaviour tests for the isolated local-dev cowork marketplace.

The cowork build ships as TWO artifacts that differ only in name (see
scripts/build.py:build_coworklocal_plugin):

  • dist/aops-cowork      — the PUBLISHED plugin (name `aops-cowork`), resolved
    by the github `dist` marketplaces via `./dist/aops-cowork`. A plain published
    plugin: it carries NO marketplace.json of its own.
  • dist/aops-coworklocal — a rename-only COPY (name `aops-coworklocal`) for local
    Cowork installs, WITH a co-located, isolated `academicOps-cowork`
    marketplace.json. A local Cowork install must live in its OWN marketplace +
    plugin namespace so it never clobbers the genuine `academicOps` marketplace
    or the aops-core/aops-tools plugins.

These tests run the REAL build generators against the REAL templates and assert
on the generated manifests — behaviour, not raw file-text mirrors.

See task aops-407f4af0 and scripts/build.py:build_coworklocal_plugin.
"""

import importlib.util
import json
from collections import namedtuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

# proper  = the genuine root academicOps marketplace
# cowork  = the isolated academicOps-cowork marketplace (inside aops-coworklocal)
# coworklocal_plugin = the renamed local-dev plugin manifest
Generated = namedtuple("Generated", "proper cowork coworklocal_plugin version")


def _load_build_module():
    """Import scripts/build.py as a module without running main()."""
    build_path = REPO_ROOT / "scripts" / "build.py"
    spec = importlib.util.spec_from_file_location("aops_build_under_test", build_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stage(tmp_path: Path) -> tuple[Path, Path]:
    """Stage a minimal aops_root (real templates) + dist tree, return both roots."""
    aops_root = tmp_path / "repo"
    dist_root = aops_root / "dist"
    (aops_root / "templates").mkdir(parents=True)
    for name in ("marketplace.json", "marketplace-cowork.json"):
        (aops_root / "templates" / name).write_text((TEMPLATES_DIR / name).read_text())
    # build_coworklocal_plugin copies the already-built published plugin dir, so
    # dist/aops-cowork/.claude-plugin/plugin.json must exist first.
    cowork_plugin = dist_root / "aops-cowork" / ".claude-plugin"
    cowork_plugin.mkdir(parents=True)
    (cowork_plugin / "plugin.json").write_text(json.dumps({"name": "aops-cowork"}))
    return aops_root, dist_root


def _generate(tmp_path: Path, version: str = "9.9.9-test") -> Generated:
    build = _load_build_module()
    aops_root, dist_root = _stage(tmp_path)
    build.generate_marketplace(aops_root, dist_root, version)
    build.build_coworklocal_plugin(aops_root, dist_root, version)
    proper = json.loads((aops_root / ".claude-plugin" / "marketplace.json").read_text())
    # The isolated marketplace + the renamed manifest live inside the LOCAL-dev
    # plugin dir (aops-coworklocal), NOT the published aops-cowork dir.
    local_plugin_dir = dist_root / "aops-coworklocal" / ".claude-plugin"
    cowork = json.loads((local_plugin_dir / "marketplace.json").read_text())
    coworklocal_plugin = json.loads((local_plugin_dir / "plugin.json").read_text())
    return Generated(proper, cowork, coworklocal_plugin, version)


def test_cowork_marketplace_is_isolated(tmp_path):
    """The cowork marketplace is named academicOps-cowork (NOT academicOps)."""
    g = _generate(tmp_path)
    assert g.cowork["name"] == "academicOps-cowork"
    assert g.cowork["name"] != "academicOps"


def test_cowork_marketplace_lists_only_aops_coworklocal(tmp_path):
    """The isolated marketplace lists exactly the aops-coworklocal plugin — nothing else."""
    g = _generate(tmp_path)
    names = [p["name"] for p in g.cowork["plugins"]]
    assert names == ["aops-coworklocal"], names
    # It must NOT pull in the published aops-cowork plugin namespace, nor the
    # genuine core/tools plugin namespaces.
    assert "aops-cowork" not in names
    assert "aops-core" not in names
    assert "aops-tools" not in names


def test_cowork_marketplace_source_resolves_to_plugin(tmp_path):
    """The single plugin's source resolves to the co-located .claude-plugin/plugin.json."""
    g = _generate(tmp_path)
    src = g.cowork["plugins"][0]["source"]
    # Self-referential "./" so `claude plugin marketplace add dist/aops-coworklocal`
    # finds dist/aops-coworklocal/.claude-plugin/plugin.json as the plugin.
    assert src in ("./", "."), src


def test_coworklocal_plugin_is_renamed(tmp_path):
    """The local-dev copy is renamed `aops-coworklocal` so it lives in its own
    plugin/skill namespace and never clobbers a published `aops-cowork` install."""
    g = _generate(tmp_path)
    assert g.coworklocal_plugin["name"] == "aops-coworklocal"


def test_proper_manifest_retains_aops_cowork(tmp_path):
    """The genuine academicOps manifest is unchanged in intent: still lists aops-cowork."""
    g = _generate(tmp_path)
    assert g.proper["name"] == "academicOps"
    names = [p["name"] for p in g.proper["plugins"]]
    assert "aops-cowork" in names, names
    # Sanity: the proper manifest still carries the core plugins too.
    assert "aops-core" in names
    assert "aops-tools" in names


def test_version_injected_into_both_manifests(tmp_path):
    """Version lockstep: __VERSION__ placeholder is replaced in every plugin entry."""
    g = _generate(tmp_path)
    for manifest in (g.proper, g.cowork):
        for plugin in manifest["plugins"]:
            assert plugin["version"] == g.version
            assert "__VERSION__" not in plugin["version"]
