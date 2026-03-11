"""Tests for hydration context loaders.

Validates that context loaders return meaningful content when framework
files exist, and that missing framework files raise FileNotFoundError
immediately (fail fast — no silent degraded behavior).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure aops-core is importable
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from lib.hydration.context_loaders import (
    get_plugin_root,
    load_glossary,
    load_scripts_index,
    load_skills_index,
    load_workflows_index,
)


class TestContextLoadersWithRealFiles:
    """Test that context loaders return content when framework files exist.

    These tests run against the real aops-core directory to verify that
    the loader functions find and read the actual framework files.
    """

    def setup_method(self) -> None:
        """Clear lru_cache on get_plugin_root between tests."""
        get_plugin_root.cache_clear()

    def test_load_glossary_returns_content(self) -> None:
        """GLOSSARY.md exists in aops-core and loader returns non-empty content."""
        glossary_path = AOPS_CORE_DIR / "GLOSSARY.md"
        assert glossary_path.exists(), f"GLOSSARY.md missing from {AOPS_CORE_DIR}"
        content = load_glossary()
        assert content, "load_glossary() returned empty string despite GLOSSARY.md existing"
        assert len(content) > 50, "Glossary content suspiciously short"

    def test_load_skills_index_returns_content(self) -> None:
        """SKILLS.md exists in aops-core and loader returns non-empty content."""
        skills_path = AOPS_CORE_DIR / "SKILLS.md"
        assert skills_path.exists(), f"SKILLS.md missing from {AOPS_CORE_DIR}"
        content = load_skills_index()
        assert content, "load_skills_index() returned empty string despite SKILLS.md existing"
        assert len(content) > 50, "Skills index content suspiciously short"

    def test_load_scripts_index_returns_content(self) -> None:
        """SCRIPTS.md exists in aops-core and loader returns non-empty content."""
        scripts_path = AOPS_CORE_DIR / "SCRIPTS.md"
        assert scripts_path.exists(), f"SCRIPTS.md missing from {AOPS_CORE_DIR}"
        content = load_scripts_index()
        assert content, "load_scripts_index() returned empty string despite SCRIPTS.md existing"
        assert len(content) > 50, "Scripts index content suspiciously short"

    def test_load_workflows_index_returns_content(self) -> None:
        """WORKFLOWS.md exists in aops-core and loader returns non-empty content."""
        workflows_path = AOPS_CORE_DIR / "WORKFLOWS.md"
        assert workflows_path.exists(), f"WORKFLOWS.md missing from {AOPS_CORE_DIR}"
        content = load_workflows_index()
        assert content, "load_workflows_index() returned empty despite WORKFLOWS.md existing"


class TestContextLoadersMissingFiles:
    """Test that context loaders raise FileNotFoundError for missing files.

    Fail fast: missing framework files are a deployment error, not a recoverable
    condition. The framework should crash out immediately rather than degrade silently.
    """

    def setup_method(self) -> None:
        get_plugin_root.cache_clear()

    def test_load_glossary_raises_when_missing(self, tmp_path: Path) -> None:
        """When GLOSSARY.md is missing, loader must raise FileNotFoundError."""
        with patch(
            "lib.hydration.context_loaders.get_plugin_root",
            return_value=tmp_path,
        ):
            get_plugin_root.cache_clear()
            with pytest.raises(FileNotFoundError, match="GLOSSARY.md"):
                load_glossary()

    def test_load_skills_index_raises_when_missing(self, tmp_path: Path) -> None:
        """When SKILLS.md is missing, loader must raise FileNotFoundError."""
        with patch(
            "lib.hydration.context_loaders.get_plugin_root",
            return_value=tmp_path,
        ):
            get_plugin_root.cache_clear()
            with pytest.raises(FileNotFoundError, match="SKILLS.md"):
                load_skills_index()

    def test_load_scripts_index_raises_when_missing(self, tmp_path: Path) -> None:
        """When SCRIPTS.md is missing, loader must raise FileNotFoundError."""
        with patch(
            "lib.hydration.context_loaders.get_plugin_root",
            return_value=tmp_path,
        ):
            get_plugin_root.cache_clear()
            with pytest.raises(FileNotFoundError, match="SCRIPTS.md"):
                load_scripts_index()


class TestHydrationContextCompleteness:
    """Test that the assembled hydration context file has critical sections populated.

    This is the integration-level test that catches the exact failure mode observed:
    the Gemini hydrator received a context file where glossary, skills index, and
    scripts index were all empty, causing it to spin without producing output.
    """

    def setup_method(self) -> None:
        get_plugin_root.cache_clear()

    def test_hydration_context_has_glossary_section(self) -> None:
        """The glossary section in hydration output must not be empty."""
        from lib.hydration.context_loaders import load_glossary

        content = load_glossary()
        # Glossary must have at least some definitions
        assert content, "Glossary section is empty — hydrator will lack terminology context"

    def test_hydration_context_has_workflows_section(self) -> None:
        """The workflows section must return non-empty content."""
        content = load_workflows_index()
        assert content, "Workflows index is empty — hydrator cannot route to workflows"

    def test_hydration_context_has_skills_section(self) -> None:
        """The skills section must not be empty."""
        content = load_skills_index()
        assert content, "Skills index is empty — hydrator cannot route to skills"

    def test_critical_framework_files_exist(self) -> None:
        """All framework files referenced by context loaders must exist."""
        critical_files = ["GLOSSARY.md", "SKILLS.md", "SCRIPTS.md", "WORKFLOWS.md"]
        missing = []
        for filename in critical_files:
            path = AOPS_CORE_DIR / filename
            if not path.exists():
                missing.append(filename)

        assert not missing, (
            f"Critical framework files missing from {AOPS_CORE_DIR}: {missing}. "
            "These are required for the hydrator to produce useful context. "
            "If deploying to Gemini extensions, ensure these are included."
        )
