"""Behaviour tests for the isolated cowork marketplace.

The cowork build is a DISTINCT plugin from aops-core. A local Cowork install
must live in its OWN marketplace + plugin namespace (`academicOps-cowork`) so it
never clobbers the genuine `academicOps` marketplace or the aops-core/aops-tools
plugins. These tests run the REAL build generators against the REAL templates
and assert on the generated manifests — behaviour, not raw file-text mirrors.

See task aops-407f4af0 and scripts/build.py:generate_cowork_marketplace.
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"


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
    # generate_cowork_marketplace requires the built plugin dir to exist first.
    cowork_plugin = dist_root / "aops-cowork" / ".claude-plugin"
    cowork_plugin.mkdir(parents=True)
    (cowork_plugin / "plugin.json").write_text(json.dumps({"name": "aops-cowork"}))
    return aops_root, dist_root


def _generate(tmp_path: Path, version: str = "9.9.9-test"):
    build = _load_build_module()
    aops_root, dist_root = _stage(tmp_path)
    build.generate_marketplace(aops_root, dist_root, version)
    build.generate_cowork_marketplace(aops_root, dist_root, version)
    proper = json.loads((aops_root / ".claude-plugin" / "marketplace.json").read_text())
    cowork = json.loads(
        (dist_root / "aops-cowork" / ".claude-plugin" / "marketplace.json").read_text()
    )
    return proper, cowork, version


def test_cowork_marketplace_is_isolated(tmp_path):
    """The cowork marketplace is named academicOps-cowork (NOT academicOps)."""
    _proper, cowork, _ = _generate(tmp_path)
    assert cowork["name"] == "academicOps-cowork"
    assert cowork["name"] != "academicOps"


def test_cowork_marketplace_lists_only_aops_cowork(tmp_path):
    """The isolated marketplace lists exactly the aops-cowork plugin — nothing else."""
    _proper, cowork, _ = _generate(tmp_path)
    names = [p["name"] for p in cowork["plugins"]]
    assert names == ["aops-cowork"], names
    # It must NOT pull in the genuine core/tools plugin namespaces.
    assert "aops-core" not in names
    assert "aops-tools" not in names


def test_cowork_marketplace_source_resolves_to_plugin(tmp_path):
    """The single plugin's source resolves to the co-located .claude-plugin/plugin.json."""
    _proper, cowork, _ = _generate(tmp_path)
    src = cowork["plugins"][0]["source"]
    # Self-referential "./" so `claude plugin marketplace add dist/aops-cowork`
    # finds dist/aops-cowork/.claude-plugin/plugin.json as the plugin.
    assert src in ("./", "."), src


def test_proper_manifest_retains_aops_cowork(tmp_path):
    """The genuine academicOps manifest is unchanged in intent: still lists aops-cowork."""
    proper, _cowork, _ = _generate(tmp_path)
    assert proper["name"] == "academicOps"
    names = [p["name"] for p in proper["plugins"]]
    assert "aops-cowork" in names, names
    # Sanity: the proper manifest still carries the core plugins too.
    assert "aops-core" in names
    assert "aops-tools" in names


def test_version_injected_into_both_manifests(tmp_path):
    """Version lockstep: __VERSION__ placeholder is replaced in every plugin entry."""
    proper, cowork, version = _generate(tmp_path)
    for manifest in (proper, cowork):
        for plugin in manifest["plugins"]:
            assert plugin["version"] == version
            assert "__VERSION__" not in plugin["version"]
