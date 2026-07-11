"""Tests for scripts/gen_dev_polecat_config.py's version-sanitized mount paths.

Claude Code's plugin installer writes cache/installPath dirs with `+`
replaced by `-` (SemVer build metadata like `0.3.78+ga7f022b7` installs to
`.../0.3.78-ga7f022b7/`). The dev-loop live-edit mount target must encode
the version the same way or the bind-mount silently lands on a directory
Claude Code never reads (task aops_1e9793a8, surfaced via task_499355a9's
PR #2216 review — a false FAIL where a corrected fix wasn't actually
visible to the container despite the mount succeeding).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "gen_dev_polecat_config.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_dev_polecat_config_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sanitize_cache_version_replaces_plus_with_hyphen():
    m = _load()
    assert m.sanitize_cache_version("0.3.78+ga7f022b7") == "0.3.78-ga7f022b7"


def test_sanitize_cache_version_is_noop_without_plus():
    m = _load()
    assert m.sanitize_cache_version("0.3.78") == "0.3.78"


def test_build_config_mount_path_matches_installer_encoding(tmp_path: Path):
    """The generated Claude mount container path must use the same `-`
    encoding as the real installed_plugins.json installPath, not the raw
    `+`-carrying marketplace.json version."""
    m = _load()

    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "marketplace.json").write_text(
        json.dumps(
            {
                "plugins": [
                    {"name": "aops-core", "version": "0.3.78+ga7f022b7"},
                ]
            }
        )
    )
    dist_dir = tmp_path / "dist" / "aops-claude" / "hooks"
    dist_dir.mkdir(parents=True)
    (dist_dir / "dummy.sh").write_text("")

    config = m.build_config(tmp_path, "~/.polecat-dev")
    mounts = config["projects"]["aops-dev"]["mounts"]

    assert mounts, "expected at least one mount for aops-core"
    for mount in mounts:
        assert "+" not in mount["container"], mount["container"]
        assert "0.3.78-ga7f022b7" in mount["container"]
