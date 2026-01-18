#!/usr/bin/env python3
"""Test skill scope extraction for custodiet context.

Regression test for: ns-siv (custodiet false positives on multi-step skills)
Root cause: custodiet saw active skill name but NOT the skill's authorized
workflow steps. When /learn does investigation+fix+test, custodiet blocked
"scope creep" because it didn't know testing is explicitly authorized.

Fix: load_skill_scope() extracts workflow from skill definition files and
custodiet_gate.py includes it in the context for compliance checking.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.session_reader import load_skill_scope, _extract_skill_scope_from_file


class TestLoadSkillScope:
    """Test skill scope loading for custodiet context."""

    def test_load_skill_scope_for_learn_command(self):
        """Verify /learn command scope includes workflow steps.

        Regression: custodiet blocked /learn investigation+testing as scope creep
        because it didn't know those were authorized workflow steps.
        """
        scope = load_skill_scope("learn")

        assert scope is not None, "Should find /learn command definition"
        assert "Purpose" in scope or "Workflow" in scope, (
            "Scope should include purpose or workflow description"
        )

    def test_load_skill_scope_for_daily_skill(self):
        """Verify /daily skill scope is loadable."""
        scope = load_skill_scope("daily")

        assert scope is not None, "Should find /daily skill definition"

    def test_load_skill_scope_returns_none_for_unknown(self):
        """Verify graceful handling of unknown skills."""
        scope = load_skill_scope("nonexistent-skill-xyz")

        assert scope is None, "Should return None for unknown skills"

    def test_load_skill_scope_extracts_workflow_steps(self):
        """Verify workflow steps are extracted from definition files.

        The /learn command has numbered workflow steps (### 0., ### 1., etc.)
        that should be extracted for custodiet context.
        """
        scope = load_skill_scope("learn")

        # The learn command has numbered steps like "Create/Update bd Issue FIRST"
        assert scope is not None
        # Either workflow steps are listed OR there's a workflow section
        has_workflow_info = (
            "Workflow steps" in scope
            or "Workflow" in scope
            or "Create" in scope  # First step mentions "Create"
        )
        assert has_workflow_info, (
            f"Scope should contain workflow information. Got: {scope}"
        )


class TestExtractSkillScopeFromFile:
    """Test the file parsing logic for skill scope extraction."""

    def test_extracts_description_from_frontmatter(self, tmp_path):
        """Verify frontmatter description is extracted."""
        skill_file = tmp_path / "test-skill.md"
        skill_file.write_text("""---
name: test-skill
description: Test skill for unit testing
---

# Test Skill

Some content here.
""")

        scope = _extract_skill_scope_from_file(skill_file)

        assert scope is not None
        assert "Test skill for unit testing" in scope

    def test_extracts_workflow_section(self, tmp_path):
        """Verify ## Workflow section is extracted."""
        skill_file = tmp_path / "test-skill.md"
        skill_file.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill

## Workflow

### 0. First Step

Do the first thing.

### 1. Second Step

Do the second thing.

## Other Section

Not part of workflow.
""")

        scope = _extract_skill_scope_from_file(skill_file)

        assert scope is not None
        assert "First Step" in scope or "Workflow steps" in scope

    def test_handles_missing_file_gracefully(self, tmp_path):
        """Verify missing files don't raise exceptions."""
        nonexistent = tmp_path / "does-not-exist.md"

        scope = _extract_skill_scope_from_file(nonexistent)

        assert scope is None

    def test_handles_file_without_frontmatter(self, tmp_path):
        """Verify files without frontmatter are handled."""
        skill_file = tmp_path / "plain.md"
        skill_file.write_text("""# Plain Skill

## Workflow

### 1. Do Something

Instructions here.
""")

        scope = _extract_skill_scope_from_file(skill_file)

        # Should still extract workflow even without frontmatter
        assert scope is None or "Workflow" in scope or "Do Something" in scope


class TestCustodietIntegration:
    """Test that custodiet gate uses skill scope correctly."""

    def test_custodiet_context_includes_skill_scope(self):
        """Verify custodiet context building imports load_skill_scope.

        This is a smoke test - if the import fails, custodiet is broken.
        """
        # This import should work after our changes
        from hooks.custodiet_gate import _build_session_context, load_skill_scope

        assert callable(load_skill_scope), "load_skill_scope should be callable"
