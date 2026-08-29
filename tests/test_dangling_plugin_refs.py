"""Tests for R2: Fix Dangling Plugin References.

Verifies that zero dangling `/email` slash command references exist in source
(`plugins/`) and build artifacts (`dist/`).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_ROOT = PROJECT_ROOT / "plugins"
DIST_ROOT = PROJECT_ROOT / "dist"

# Pattern matching dangling `/email` slash command references as standalone command calls.
# Ignores:
# - URL paths like `https://example.com/email`
# - File paths like `plugins/aops-core/workflows/process/email-triage.md`
# - Workflow IDs or permalinks like `wf-email-triage` or `email-triage`
# - Package names like `email_validator` or python imports `from email import ...`
SLASH_EMAIL_REGEX = re.compile(r"(?<![A-Za-z0-9_/-])/(?:email)(?![A-Za-z0-9_/-]|\.[a-zA-Z0-9])")


def _scan_directory_for_dangling_slash_email(directory: Path) -> list[tuple[str, int, str]]:
    """Scan all text/markdown/json files under directory for dangling `/email` slash command references.

    Returns list of tuples: (relative_file_path, line_number, line_content).
    """
    matches = []
    text_extensions = {".md", ".json", ".toml", ".txt", ".yaml", ".yml", ".py", ".sh"}

    for root, _dirs, files in os.walk(directory):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in text_extensions:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for idx, line in enumerate(content.splitlines(), start=1):
                # Skip comments or URL references if needed, but SLASH_EMAIL_REGEX handles slash command shape
                if SLASH_EMAIL_REGEX.search(line):
                    # Filter out valid URLs or python module imports if any false positive
                    if "http://" in line or "https://" in line:
                        # Check if match is part of URL
                        if re.search(r"https?://[^\s]+/email", line):
                            continue
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    matches.append((rel_path, idx, line.strip()))

    return matches


def test_dangling_email_slash_command_regex_unit():
    """Unit test for SLASH_EMAIL_REGEX matching accuracy."""
    # Positive matches (dangling slash command calls)
    assert SLASH_EMAIL_REGEX.search("Use /email to triage your inbox") is not None
    assert SLASH_EMAIL_REGEX.search("Run /email") is not None
    assert SLASH_EMAIL_REGEX.search("Available commands: /email, /daily") is not None
    assert SLASH_EMAIL_REGEX.search("Execute `/email` now") is not None
    assert SLASH_EMAIL_REGEX.search("Use /email.") is not None

    # Negative matches (valid references, workflow names, packages)
    assert SLASH_EMAIL_REGEX.search("See [[wf-email-triage]] for workflow") is None
    assert SLASH_EMAIL_REGEX.search("Process file email-triage.md") is None
    assert SLASH_EMAIL_REGEX.search("import email_validator") is None
    assert SLASH_EMAIL_REGEX.search("https://api.example.com/email/send") is None
    assert (
        SLASH_EMAIL_REGEX.search("https://files.pythonhosted.org/.../email_validator-2.3.0.tar.gz")
        is None
    )
    assert SLASH_EMAIL_REGEX.search("plugins/aops-core/workflows/process/email-triage.md") is None
    assert SLASH_EMAIL_REGEX.search("See /email.md for docs") is None


def test_no_dangling_email_references_in_plugins_source():
    """Verify zero dangling `/email` slash command references exist in plugins/ source directory."""
    assert PLUGINS_ROOT.is_dir(), f"Expected plugins directory at {PLUGINS_ROOT}"

    matches = _scan_directory_for_dangling_slash_email(PLUGINS_ROOT)
    failure_msg = "\n".join(f"  {path}:{line} -> {text}" for path, line, text in matches)
    assert not matches, (
        f"Found dangling `/email` slash command reference(s) in source plugins:\n{failure_msg}"
    )


def test_no_dangling_email_references_in_dist_artifacts():
    """Verify zero dangling `/email` slash command references exist in dist/ build directory if present."""
    if not DIST_ROOT.exists():
        if os.environ.get("CI"):
            raise RuntimeError(
                f"{DIST_ROOT} does not exist under CI — build step must run before pytest"
            )
        pytest.skip(f"{DIST_ROOT} does not exist — run build step to test dist artifacts")

    matches = _scan_directory_for_dangling_slash_email(DIST_ROOT)
    failure_msg = "\n".join(f"  {path}:{line} -> {text}" for path, line, text in matches)
    assert not matches, (
        f"Found dangling `/email` slash command reference(s) in dist/ build artifacts:\n{failure_msg}"
    )
