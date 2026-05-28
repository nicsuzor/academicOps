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
    assert "cowork-only paragraph" not in result, "trailing whitespace on markers caused content leak"
