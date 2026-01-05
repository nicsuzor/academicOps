#!/usr/bin/env python3
"""Tests for CORE.md existence and validity.

CORE.md is required for SessionStart hooks to load user context.
"""


from lib.paths import get_data_root


def test_core_md_exists() -> None:
    """Test that CORE.md exists at $ACA_DATA/CORE.md.

    CORE.md is required by SessionStart hooks to inject user context.
    Without it, hooks will fail-fast and sessions cannot start.

    Raises:
        AssertionError: If CORE.md doesn't exist or is not readable
    """
    data_root = get_data_root()
    core_path = data_root / "CORE.md"

    assert core_path.exists(), (
        f"CORE.md missing at {core_path}. "
        f"SessionStart hooks require this file. "
        f"Create it at $ACA_DATA/CORE.md with user context."
    )

    assert core_path.is_file(), f"CORE.md exists but is not a file: {core_path}"

    # Verify file is readable
    try:
        content = core_path.read_text(encoding="utf-8")
        assert len(content) > 0, f"CORE.md at {core_path} is empty"
    except Exception as e:
        msg = f"CORE.md is not readable at {core_path}: {e}"
        raise AssertionError(msg) from e


def test_core_md_contains_user_info() -> None:
    """Test that CORE.md contains user context sections.

    CORE.md should contain user information that agents need to know.

    Raises:
        AssertionError: If CORE.md doesn't contain expected sections
    """
    data_root = get_data_root()
    core_path = data_root / "CORE.md"

    content = core_path.read_text(encoding="utf-8")

    # Check for key sections (flexible - just verify SOME user context exists)
    has_content = (
        "##" in content  # Has markdown sections
        and len(content) > 100  # Not trivially small
    )

    assert has_content, (
        f"CORE.md at {core_path} appears empty or incomplete. "
        f"It should contain user context sections."
    )
