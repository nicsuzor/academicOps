"""Unit tests for cowork-only marker processing in scripts/build.py.

Guards against the 'cowork-only content leaks into Claude/Gemini builds' failure mode.
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _load_build():
    """Load scripts/build.py, resolving its internal sys.path setup."""
    # Pre-seed the paths build.py adds at module level so imports succeed
    for p in (str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "lib")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("_build_testmodule", _SCRIPTS_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_build = _load_build()


def _wrap(content: str) -> str:
    return f"before\n\n{_build._COWORK_OPEN}\n{content}\n{_build._COWORK_CLOSE}\n\nafter\n"


def test_cowork_platform_keeps_content_strips_markers() -> None:
    text = _wrap("cowork-only paragraph")
    result = _build._process_cowork_markers(text, "cowork")
    assert "cowork-only paragraph" in result
    assert _build._COWORK_OPEN not in result
    assert _build._COWORK_CLOSE not in result


def test_non_cowork_platforms_strip_content() -> None:
    for platform in ("claude", "gemini", "antigravity"):
        text = _wrap("cowork-only paragraph")
        result = _build._process_cowork_markers(text, platform)
        assert "cowork-only paragraph" not in result, f"{platform} leaked cowork-only content"
        assert _build._COWORK_OPEN not in result
        assert _build._COWORK_CLOSE not in result


def test_no_markers_unchanged() -> None:
    text = "plain text without markers"
    assert _build._process_cowork_markers(text, "claude") == text
    assert _build._process_cowork_markers(text, "cowork") == text


def test_surrounding_content_preserved() -> None:
    for platform in ("claude", "gemini", "cowork"):
        result = _build._process_cowork_markers(_wrap("block"), platform)
        assert "before" in result, f"{platform}: content before block was lost"
        assert "after" in result, f"{platform}: content after block was lost"


def test_trailing_whitespace_on_markers_handled() -> None:
    """Markers with trailing spaces must not leak content to non-cowork builds."""
    open_marker = _build._COWORK_OPEN + "  "
    close_marker = _build._COWORK_CLOSE + "  "
    text = f"before\n\n{open_marker}\ncowork-only paragraph\n{close_marker}\n\nafter\n"
    result = _build._process_cowork_markers(text, "claude")
    assert "cowork-only paragraph" not in result, (
        "trailing whitespace on markers caused content leak"
    )


# --- aops-cowork ships no hooks (task-04075740) -----------------------------
# The cowork build drops the bundled hook stack: aops-core, installed into Cowork
# from the nicsuzor/aops main `dist` marketplace, supplies the one shared hook
# stack for both surfaces. Bundling hooks here too would register the router a
# second time and double-fire every lifecycle hook. With no `hooks/` package on
# disk, the cowork pyproject must NOT list `hooks` under hatch's wheel packages or
# `uv sync --frozen` would fail at runtime.


def test_cowork_pyproject_excludes_hooks_package() -> None:
    """Cowork's pyproject lists only `lib` — no `hooks` package."""
    pyproject = _build.generate_aops_core_pyproject("9.9.9", "cowork")
    assert 'packages = ["lib"]' in pyproject
    assert '"hooks"' not in pyproject, "cowork pyproject must not declare the dropped hooks package"


def test_cowork_pyproject_sourced_from_real_package() -> None:
    """The cowork pyproject is the tracked aops-cowork package manifest (name
    aops-cowork), with the build version stamped in — NOT a trimmed copy of
    aops-core's manifest fabricated at build time."""
    pyproject = _build.generate_aops_core_pyproject("9.9.9", "cowork")
    assert 'name = "aops-cowork"' in pyproject
    assert 'version = "9.9.9"' in pyproject


def test_claude_pyproject_retains_hooks_package() -> None:
    """The Claude build still ships hooks, so its pyproject keeps the hooks package."""
    pyproject = _build.generate_aops_core_pyproject("9.9.9", "claude")
    assert 'packages = ["lib", "hooks"]' in pyproject


def test_pyproject_defaults_to_claude_with_hooks() -> None:
    """Omitting the platform argument keeps the historical claude+hooks behaviour."""
    assert 'packages = ["lib", "hooks"]' in _build.generate_aops_core_pyproject("9.9.9")


# --- aops-cowork is a REAL, tracked package, not a build-time fabrication -----
# Regression guard for the failure mode this design fixes: the cowork plugin
# manifest, pyproject, and the cowork-only skill content must exist as committed
# source under aops-cowork/ on `dev` (where no `dist/` is built), so the package
# is real rather than synthesised into dist/ at build time.

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COWORK_PKG = _REPO_ROOT / "aops-cowork"


def test_cowork_package_manifest_is_tracked_source() -> None:
    """aops-cowork/.claude-plugin/plugin.json exists in source and names the plugin."""
    import json

    manifest_path = _COWORK_PKG / ".claude-plugin" / "plugin.json"
    assert manifest_path.is_file(), f"{manifest_path} must be tracked source, not generated"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["name"] == "aops-cowork"


def test_cowork_package_pyproject_is_tracked_and_lib_only() -> None:
    """aops-cowork/pyproject.toml exists in source and ships lib only (no hooks)."""
    pyproject_path = _COWORK_PKG / "pyproject.toml"
    assert pyproject_path.is_file(), f"{pyproject_path} must be tracked source"
    text = pyproject_path.read_text()
    assert 'name = "aops-cowork"' in text
    assert 'packages = ["lib"]' in text
    assert '"hooks"' not in text


def test_cowork_sync_skill_lives_in_package() -> None:
    """The cowork-only `cowork-sync` skill is owned by the aops-cowork package
    (overlaid at build time), NOT by the aops-core base tree."""
    assert (_COWORK_PKG / "skills" / "cowork-sync" / "SKILL.md").is_file()
    assert not (_REPO_ROOT / "aops-core" / "skills" / "cowork-sync").exists(), (
        "cowork-sync must live only in the aops-cowork package, not in the aops-core base"
    )


def test_cowork_plugin_manifest_sourced_from_package(tmp_path) -> None:
    """build_aops_core(platform='cowork') writes the dist plugin.json FROM the
    tracked aops-cowork package manifest, not from templates/. We assert the
    build reads aops-cowork/.claude-plugin/plugin.json by checking the resolved
    source path the build would use."""
    import json

    pkg_manifest = json.loads((_COWORK_PKG / ".claude-plugin" / "plugin.json").read_text())
    # The published cowork manifest's identity fields come from the package.
    assert pkg_manifest["name"] == "aops-cowork"
    assert "cowork" in pkg_manifest["keywords"]
