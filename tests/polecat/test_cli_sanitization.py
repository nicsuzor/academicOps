"""Unit tests for input sanitization of project and session_name in lib/polecat/cli.py."""

import pytest

from lib.polecat.cli import _sanitize_path_component


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("my-project", "my-project"),
        ("session-123_abc", "session-123_abc"),
        ("../../etc/passwd", "etc_passwd"),
        ("../..", None),
        (".", None),
        ("..", None),
        ("   ", None),
        (None, None),
        ("foo/bar/baz", "foo_bar_baz"),
        ("foo\\bar\\baz", "foo_bar_baz"),
        ("  session 1 !@# ", "session_1"),
        ("--option-name--", "option-name"),
        ("...malicious...", "malicious"),
        ("___project___", "project"),
    ],
)
def test_sanitize_path_component(input_val: str | None, expected: str | None) -> None:
    """_sanitize_path_component cleans path traversal, bad chars, and leading/trailing separators."""
    assert _sanitize_path_component(input_val) == expected


def test_sanitize_path_component_custom_default() -> None:
    """_sanitize_path_component uses custom default when input is empty or invalid."""
    assert _sanitize_path_component("..", default="fallback") == "fallback"
    assert _sanitize_path_component(None, default="workspace") == "workspace"
