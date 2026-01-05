"""Test session start hooks and mechanisms.

CLAUDE.md structure varies by project, so we test that session start WORKS
(information loads properly) rather than testing specific CLAUDE.md content.

TODO: Add unit tests for session start hooks after removing CLAUDE.md-specific tests.
"""


# Removed test_claude_md_includes_skills_readme - CLAUDE.md structure is project-specific
# Instead, test that session start hooks properly load information (not CLAUDE.md content)

# TODO: Add unit tests for session start hook functionality:
# - Test that hooks/session-start.sh exists and is executable
# - Test that hook properly processes @ references
# - Test that hook loads referenced files correctly
