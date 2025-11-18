"""Test that CLAUDE.md includes required files in session start sequence.

This test verifies that the session start configuration in CLAUDE.md properly
references all critical documentation files using @-references.
"""

from pathlib import Path
from lib.paths import get_aops_root


def test_claude_md_includes_skills_readme():
    """Verify CLAUDE.md includes @skills/README.md in session start sequence.

    Behavior to test: CLAUDE.md should reference @skills/README.md so that
    agents understand available skills at session start.

    This is an integration test validating session start configuration integrity.
    """
    # Arrange: Find and read CLAUDE.md in $AOPS
    aops_root = get_aops_root()
    claude_md_path = aops_root / "CLAUDE.md"

    assert claude_md_path.exists(), f"CLAUDE.md not found at {claude_md_path}"

    claude_content = claude_md_path.read_text()

    # Act: Parse @-references from CLAUDE.md
    # @-references are markdown-style references to other files that Claude Code
    # automatically loads at session start
    at_references = []
    for line in claude_content.split("\n"):
        # Look for lines containing @filename patterns
        if "@" in line and not line.strip().startswith("#"):
            # Extract all @-references from the line
            words = line.split()
            for word in words:
                if word.startswith("@") and not word.startswith("@@"):
                    # Clean up the reference (remove trailing punctuation)
                    ref = word.lstrip("@").rstrip(".,;:")
                    at_references.append(ref)

    # Assert: Verify @skills/README.md is included
    expected_ref = "skills/README.md"

    assert expected_ref in at_references, (
        f"CLAUDE.md must include @{expected_ref} in session start sequence.\n"
        f"Found @-references: {at_references}\n"
        f"Missing: @{expected_ref}\n\n"
        f"Why this matters: The skills README documents all available skills and\n"
        f"should be loaded at session start so agents know what capabilities exist."
    )
