"""Marketplace-key selection in build_utils.check_installed_plugin_version.

Source installs (`make dev`) land under the LOCAL `aops` marketplace, so the
version-mismatch check must look up `aops-core@aops` FIRST, and only fall back to
the released `aops-core@academicOps` key when no `@aops` install is present. These
tests pin both branches (the primary `@aops` branch was previously uncovered — the
only fixtures exercised the `@academicOps` fallback).
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_UTILS = REPO_ROOT / "scripts" / "lib" / "build_utils.py"


def _load():
    spec = importlib.util.spec_from_file_location("aops_build_utils_under_test", BUILD_UTILS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_installed(tmp_path: Path, plugins: dict) -> Path:
    path = tmp_path / "installed_plugins.json"
    path.write_text(json.dumps({"plugins": plugins}))
    return path


def test_matches_when_aops_key_commit_matches(tmp_path):
    """The `@aops` (local-dev) install is the PRIMARY key and is compared."""
    bu = _load()
    installed = _write_installed(
        tmp_path, {"aops-core@aops": [{"gitCommitSha": "abcdef1234567890"}]}
    )
    matches, commit = bu.check_installed_plugin_version("aops-core", "abcdef1234567890", installed)
    assert matches is True
    assert commit == "abcdef1234567890"


def test_mismatch_reported_from_aops_key(tmp_path):
    """A stale `@aops` install is reported as a mismatch (primary branch, not fallback)."""
    bu = _load()
    installed = _write_installed(
        tmp_path, {"aops-core@aops": [{"gitCommitSha": "0000000000000000"}]}
    )
    matches, commit = bu.check_installed_plugin_version("aops-core", "ffffffffffffffff", installed)
    assert matches is False
    assert commit == "0000000000000000"


def test_falls_back_to_academicops_key(tmp_path):
    """With no `@aops` install, the released `@academicOps` key is used."""
    bu = _load()
    installed = _write_installed(
        tmp_path, {"aops-core@academicOps": [{"gitCommitSha": "1111111111111111"}]}
    )
    matches, commit = bu.check_installed_plugin_version("aops-core", "2222222222222222", installed)
    assert matches is False
    assert commit == "1111111111111111"


def test_aops_key_preferred_over_academicops(tmp_path):
    """When BOTH keys exist, `@aops` wins — the dev install is what `make dev` just laid down."""
    bu = _load()
    installed = _write_installed(
        tmp_path,
        {
            "aops-core@aops": [{"gitCommitSha": "aaaaaaaaaaaaaaaa"}],
            "aops-core@academicOps": [{"gitCommitSha": "bbbbbbbbbbbbbbbb"}],
        },
    )
    # source_commit matches the @aops install → match; if the fallback were chosen
    # instead, this would report a mismatch against bbbb...
    matches, commit = bu.check_installed_plugin_version("aops-core", "aaaaaaaaaaaaaaaa", installed)
    assert matches is True
    assert commit == "aaaaaaaaaaaaaaaa"


def test_no_install_is_not_a_mismatch(tmp_path):
    """Neither key present → (True, None): nothing installed, nothing to warn about."""
    bu = _load()
    installed = _write_installed(tmp_path, {"some-other-plugin@foo": [{"gitCommitSha": "x"}]})
    matches, commit = bu.check_installed_plugin_version("aops-core", "deadbeef", installed)
    assert matches is True
    assert commit is None
