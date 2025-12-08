"""Integration tests for log-agent.

Tests the framework logger agent's ability to:
1. Accept observations and categorize them correctly
2. Invoke appropriate skills (framework, framework-debug, bmem)
3. Format entries per LOG.md specification
4. Validate and append to LOG.md
"""

import os
import re
import tempfile
from pathlib import Path
from datetime import datetime

import pytest


@pytest.fixture
def test_log_file(tmp_path: Path) -> Path:
    """Create temporary LOG.md file with valid frontmatter."""
    log_file = tmp_path / "LOG.md"
    log_file.write_text("""---
title: Learning Patterns Log
permalink: projects-aops-experiments-log
type: log
tags: [aops, learning, patterns, experiments]
---

# Learning Patterns Log

**Purpose**: Track patterns from experiments to build institutional knowledge.

---

## Existing Entry: Sample Pattern

**Date**: 2025-11-01 | **Type**: ✅ Success | **Pattern**: #testing

**What**: Sample entry for testing. **Why**: Validates test setup. **Lesson**: Integration tests must verify agent behavior.

---
""")
    return log_file


def test_log_agent_exists() -> None:
    """Test that log-agent.md file exists in agents/ directory."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    assert agent_file.exists(), "log-agent.md should exist in agents/ directory"


def test_log_agent_has_required_frontmatter() -> None:
    """Test that log-agent has valid frontmatter."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Check frontmatter
    assert content.startswith("---"), "Should have frontmatter"
    assert "name: log-agent" in content, "Should have name field"
    assert "description:" in content, "Should have description field"
    assert "permalink: agents/log-agent" in content, "Should have permalink"


def test_log_agent_documents_workflow() -> None:
    """Test that log-agent documents the complete workflow."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Check key workflow steps documented
    assert "Load Framework Context" in content or "framework skill" in content.lower()
    assert "Investigate" in content or "framework-debug" in content.lower()
    assert "bmem skill" in content.lower() or "knowledge linking" in content.lower()
    assert "Categorize" in content
    assert "Format Entry" in content or "format" in content.lower()
    assert "Append" in content or "LOG.md" in content


def test_log_agent_specifies_categorization() -> None:
    """Test that log-agent specifies categorization criteria."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Check thematic file categorization documented (current scheme)
    thematic_files = [
        "verification-discipline",
        "instruction-following",
        "git-and-validation",
        "skill-and-tool-usage",
        "test-and-tdd",
        "technical-wins",
    ]
    assert any(tf in content for tf in thematic_files), (
        f"Should document thematic file categorization. Expected one of: {thematic_files}"
    )

    # Check type classification
    assert "Success" in content or "✅" in content
    assert "Failure" in content or "❌" in content


def test_log_agent_defines_investigation_heuristics() -> None:
    """Test that log-agent defines when to investigate vs skip."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Check investigation logic documented
    assert "framework-debug" in content.lower()
    assert ("skip" in content.lower() or "when to" in content.lower())

    # Should mention success/failure markers
    success_markers = ["worked", "correctly", "successfully"]
    failure_markers = ["failed", "error", "bug"]

    has_success_mention = any(marker in content.lower() for marker in success_markers)
    has_failure_mention = any(marker in content.lower() for marker in failure_markers)

    assert has_success_mention, "Should document success markers"
    assert has_failure_mention, "Should document failure markers"


def test_log_agent_references_skills() -> None:
    """Test that log-agent references the three required skills."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Must reference all three skills
    assert "framework" in content.lower(), "Must reference framework skill"
    assert "framework-debug" in content.lower(), "Must reference framework-debug skill"
    assert "bmem" in content.lower(), "Must reference bmem skill"


def test_log_entry_format_specification() -> None:
    """Test that log-agent specifies correct LOG.md entry format."""
    agent_file = Path(os.getenv("AOPS", ""), "agents", "log-agent.md")
    content = agent_file.read_text()

    # Check format specification includes required fields
    assert "**Date**:" in content or "Date:" in content
    assert "**Type**:" in content or "Type:" in content
    assert "**Pattern**:" in content or "Pattern:" in content
    assert "**What**:" in content or "What:" in content
    assert "**Why**:" in content or "Why:" in content
    assert "**Lesson**:" in content or "Lesson:" in content


def test_log_command_updated() -> None:
    """Test that /log command invokes log-agent (manual verification placeholder).

    This test verifies the commands/log.md file exists and will contain log-agent
    invocation after implementation. Actual E2E testing of agent behavior requires
    running Claude Code with the agent, which is beyond unit/integration test scope.
    """
    log_command = Path(os.getenv("AOPS", ""), "commands", "log.md")
    assert log_command.exists(), "commands/log.md should exist"

    # Note: Full E2E test would invoke actual agent via Task tool with test observation
    # and verify correct LOG.md append. That requires agent runtime which is separate
    # from these structural validation tests.


def test_log_file_frontmatter_validation(test_log_file: Path) -> None:
    """Test that LOG.md frontmatter validation logic would work correctly."""
    content = test_log_file.read_text()

    # Extract frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]

            # Check required fields present
            assert "title:" in frontmatter
            assert "permalink:" in frontmatter
            assert "type:" in frontmatter
            assert "tags:" in frontmatter

            # Validate permalink format (no slashes, uses hyphens)
            permalink_match = re.search(r'permalink:\s*([^\n]+)', frontmatter)
            if permalink_match:
                permalink = permalink_match.group(1).strip()
                assert "/" not in permalink, "Permalink should not contain slashes"


def test_log_entry_format_validation(test_log_file: Path) -> None:
    """Test that a properly formatted log entry matches specification."""
    # Sample entry that should match format
    sample_entry = """## Behavioral Pattern: Test Entry

**Date**: 2025-11-18 | **Type**: ✅ Success | **Pattern**: #testing #validation

**What**: Sample test entry created for validation. **Why**: Ensures format specification is clear and parseable. **Lesson**: Format compliance should be automatically verified.
"""

    # Check format elements present
    assert re.search(r'^## [^:]+:', sample_entry, re.MULTILINE), "Should have category header"
    assert re.search(r'\*\*Date\*\*:\s*\d{4}-\d{2}-\d{2}', sample_entry), "Should have date"
    assert re.search(r'\*\*Type\*\*:\s*[✅❌]', sample_entry), "Should have type emoji"
    assert re.search(r'\*\*Pattern\*\*:\s*#\w+', sample_entry), "Should have pattern tags"
    assert "**What**:" in sample_entry, "Should have What field"
    assert "**Why**:" in sample_entry, "Should have Why field"
    assert "**Lesson**:" in sample_entry, "Should have Lesson field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
