#!/usr/bin/env python3
"""Diagnostic test to determine where bmem writes files when invoked from /tmp.

This test verifies that bmem writes files to $ACA_DATA (writing repository)
regardless of the current working directory (CWD). Test runs Claude from /tmp
and then searches both /tmp and $ACA_DATA for created files.

Expected behavior: Files should be found in $ACA_DATA, not in /tmp.
"""

import os
import time
from pathlib import Path

import pytest

from tests.paths import get_data_dir


@pytest.mark.integration
@pytest.mark.slow
def test_bmem_writes_to_aca_data_not_tmp(claude_headless):
    """Test that bmem writes to $ACA_DATA even when invoked from /tmp CWD.

    This diagnostic test:
    1. Runs Claude from /tmp (automatic with claude_headless fixture)
    2. Creates a unique note via bmem with identifiable content
    3. Searches BOTH locations:
       - /tmp/claude-test-* (where test runs)
       - $ACA_DATA (where bmem should write)
    4. Reports exactly where files were found
    5. Verifies files are in $ACA_DATA, not /tmp
    """
    # Arrange
    start_time = time.time() - 1
    unique_marker = f"diagnostic_test_{int(start_time)}"
    prompt = f"""
    Using the bmem MCP tool, create a diagnostic note to verify file location.

    Create a note with:
    - Title: "Diagnostic Test Note {unique_marker}"
    - Content: Include marker "{unique_marker}" so we can identify it
    - Store it in the knowledge base

    After creating the note, report its file location.
    """

    # Act: Execute Claude from /tmp
    result = claude_headless(
        prompt,
        permission_mode="bypassPermissions",
        timeout_seconds=180,
        model="haiku",
    )

    # Assert: Command succeeded
    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Assert: File was created in $ACA_DATA, not /tmp
    aca_data = get_data_dir()
    assert aca_data.exists(), f"ACA_DATA not found: {aca_data}"

    # Search for created file in $ACA_DATA
    aca_data_files = list(aca_data.rglob("*.md"))

    # Find the newly created file (modified after test start, contains marker)
    created_file_in_aca_data = None
    for file in aca_data_files:
        # Only check files modified after test started (with 1s buffer)
        if file.stat().st_mtime < start_time:
            continue
        content = file.read_text()
        if unique_marker in content:
            created_file_in_aca_data = file
            break

    # Assert: File exists in $ACA_DATA
    assert (
        created_file_in_aca_data is not None
    ), f"bmem did not create file in $ACA_DATA\nSearched {len(aca_data_files)} files in {aca_data}"

    # Assert: File does NOT exist in /tmp
    tmp_test_dirs = list(Path("/tmp").glob("claude-test-*"))
    for tmp_dir in tmp_test_dirs:
        tmp_files = list(tmp_dir.rglob("*.md"))
        for file in tmp_files:
            content = file.read_text()
            if unique_marker in content:
                pytest.fail(
                    f"Found file in /tmp (incorrect location): {file}\n"
                    f"File should be in $ACA_DATA: {created_file_in_aca_data}"
                )

    # Diagnostic output
    relative_path = created_file_in_aca_data.relative_to(aca_data)
    print(f"\nDiagnostic Results:")
    print(f"  Marker: {unique_marker}")
    print(f"  Found in $ACA_DATA: Yes")
    print(f"  ACA_DATA: {aca_data}")
    print(f"  Relative path: {relative_path}")
    print(f"  Absolute path: {created_file_in_aca_data}")
    print(f"  Found in /tmp: No (correct)")

    # Assert: File has valid structure
    content = created_file_in_aca_data.read_text()
    assert content.startswith("---"), "File missing YAML frontmatter"
    assert "title:" in content, "File missing title field"
    assert unique_marker in content, "File missing diagnostic marker"
