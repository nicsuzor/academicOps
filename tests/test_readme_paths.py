#!/usr/bin/env python3
"""
Tests that README.md files contain correct authoritative paths.

These tests ensure the AUTHORITATIVE path documentation in README files
stays synchronized with actual environment variables and filesystem layout.

Critical: README files are the SINGLE SOURCE OF TRUTH for directory structure.
If these tests fail, the README documentation is WRONG and must be fixed.
"""

import os
import re
from pathlib import Path

import pytest


def test_aops_readme_aca_data_path_is_correct():
    """Test that $AOPS/README.md shows correct $ACA_DATA example path.

    The README contains an example showing where $ACA_DATA typically lives.
    This must match the actual $ACA_DATA environment variable structure.

    Raises:
        AssertionError: If README shows wrong path for $ACA_DATA
    """
    # Arrange
    aops_readme = Path(os.environ["AOPS"]) / "README.md"
    actual_aca_data = Path(os.environ["ACA_DATA"])

    assert aops_readme.exists(), f"$AOPS/README.md not found at {aops_readme}"

    # Act - Find the line showing $ACA_DATA example path
    readme_content = aops_readme.read_text()

    # Look for line like: $ACA_DATA/  (e.g., ~/writing/data/)
    pattern = r'\$ACA_DATA/\s+\(e\.g\.,\s+([^\)]+)\)'
    match = re.search(pattern, readme_content)

    # Assert
    assert match, (
        "$AOPS/README.md missing $ACA_DATA example path.\n"
        "Expected line like: $ACA_DATA/  (e.g., ~/writing/data/)"
    )

    readme_path = match.group(1).strip()

    # Expand ~ to actual home directory for comparison
    readme_expanded = Path(readme_path.replace("~", str(Path.home())))

    assert readme_expanded == actual_aca_data, (
        f"$AOPS/README.md shows wrong $ACA_DATA path.\n"
        f"  README shows: {readme_path}\n"
        f"  Expands to:   {readme_expanded}\n"
        f"  Actual env:   {actual_aca_data}\n"
        f"\n"
        f"Fix by editing $AOPS/README.md to match actual $ACA_DATA location."
    )


def test_writing_readme_path_matches_actual_location():
    """Test that ~/writing/README.md shows correct repository path.

    The writing repository README has an AUTHORITATIVE directory tree
    that must show the actual repository location.

    Raises:
        AssertionError: If README shows wrong repository path
    """
    # Arrange - Get writing repo location from $ACA_DATA (which is inside it)
    aca_data = Path(os.environ["ACA_DATA"])
    writing_repo = aca_data.parent  # $ACA_DATA is ~/writing/data, so parent is ~/writing
    writing_readme = writing_repo / "README.md"

    assert writing_readme.exists(), (
        f"Writing README not found at {writing_readme}"
    )

    # Act - Find the authoritative directory tree header
    readme_content = writing_readme.read_text()

    # Look for the path in the directory tree (first line after opening ```)
    # Pattern: finds the path after "```" in the Directory Structure section
    pattern = r'## 📁 Directory Structure.*?```\s*\n(/[^\n]+)'
    match = re.search(pattern, readme_content, re.DOTALL)

    # Assert
    assert match, (
        "Writing README missing directory structure path.\n"
        "Expected section:\n"
        "## 📁 Directory Structure\n"
        "...\n"
        "```\n"
        "/home/nic/writing/\n"
    )

    readme_path = Path(match.group(1).strip())

    # Remove trailing slash if present for comparison
    readme_path_str = str(readme_path).rstrip('/')
    writing_repo_str = str(writing_repo).rstrip('/')

    assert readme_path_str == writing_repo_str, (
        f"Writing README shows wrong repository path.\n"
        f"  README shows: {readme_path}\n"
        f"  Actual location: {writing_repo}\n"
        f"  (derived from $ACA_DATA={aca_data})\n"
        f"\n"
        f"Fix by editing {writing_readme} to show correct path.\n"
        f"This is the AUTHORITATIVE path documentation."
    )


def test_writing_repo_not_in_src_directory():
    """Test that writing repository is NOT in ~/src/ directory.

    Common confusion: Framework is in ~/src/aOps/, but writing repo
    is in ~/writing/ (not ~/src/writing/).

    This test prevents regression to the old incorrect documentation.

    Raises:
        AssertionError: If writing repo is incorrectly placed in src/
    """
    # Arrange
    aca_data = Path(os.environ["ACA_DATA"])
    writing_repo = aca_data.parent

    # Assert - Writing repo should NOT be in a "src" directory
    assert "src" not in writing_repo.parts, (
        f"Writing repository incorrectly located in src/ directory.\n"
        f"  Current location: {writing_repo}\n"
        f"  Expected pattern: ~/writing/ (not ~/src/writing/)\n"
        f"\n"
        f"Architecture:\n"
        f"  Framework: ~/src/aOps/  ($AOPS)\n"
        f"  Writing:   ~/writing/   (contains $ACA_DATA)\n"
    )


def test_readme_paths_environment_consistency():
    """Test that README paths match environment variable structure.

    Comprehensive check that all path documentation is consistent:
    - $AOPS points to framework repository
    - $ACA_DATA points to data directory inside writing repository
    - README files document these correctly

    Raises:
        AssertionError: If any path inconsistency detected
    """
    # Arrange - Get all relevant paths
    aops = Path(os.environ["AOPS"])
    aca_data = Path(os.environ["ACA_DATA"])
    writing_repo = aca_data.parent

    # Assert - Verify expected structure
    assert aops.name in ["aOps", "academicOps"], (
        f"$AOPS has unexpected name: {aops.name}"
    )

    assert aops.parent.name == "src", (
        f"Framework should be in src/ directory.\n"
        f"  Expected: ~/src/aOps/\n"
        f"  Actual:   {aops}"
    )

    assert aca_data.name == "data", (
        f"$ACA_DATA should be 'data' directory.\n"
        f"  Expected: .../writing/data/\n"
        f"  Actual:   {aca_data}"
    )

    assert writing_repo.name == "writing", (
        f"Writing repo should be named 'writing'.\n"
        f"  Expected: ~/writing/\n"
        f"  Actual:   {writing_repo}"
    )

    assert aca_data == writing_repo / "data", (
        f"$ACA_DATA should be data/ subdirectory of writing repo.\n"
        f"  Writing repo: {writing_repo}\n"
        f"  ACA_DATA:     {aca_data}\n"
        f"  Expected:     {writing_repo / 'data'}"
    )
