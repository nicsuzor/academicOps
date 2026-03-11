#!/usr/bin/env python3
"""Test custodiet context includes implicit authority guidance for skills.

Regression test for: ns-zer9 (custodiet blocks /pull task claiming)
Root cause: custodiet context template lacked guidance that /pull grants
implicit authority to claim tasks.

This is a FAST unit test (no Claude session) that verifies the template
contains the necessary guidance to prevent false positives.
"""

from pathlib import Path

# Template location
CUSTODIET_CONTEXT_TEMPLATE = (
    Path(__file__).parent.parent.parent
    / "aops-core"
    / "hooks"
    / "templates"
    / "custodiet-context.md"
)


def test_custodiet_template_exists() -> None:
    """Verify custodiet context template exists."""
    assert CUSTODIET_CONTEXT_TEMPLATE.exists(), (
        f"Custodiet context template not found at {CUSTODIET_CONTEXT_TEMPLATE}"
    )


def test_custodiet_template_has_implicit_authority_section() -> None:
    """Verify template documents skills with implicit authority grants.

    Regression: ns-zer9 - custodiet blocked /pull task claiming because
    it didn't know /pull grants implicit authority to claim tasks.
    """
    content = CUSTODIET_CONTEXT_TEMPLATE.read_text()

    assert "Skills with implicit authority grants" in content, (
        "Custodiet template should document skills with implicit authority grants"
    )


def test_custodiet_template_documents_pull_authority() -> None:
    """Verify /pull is documented as granting task-claiming authority.

    Regression: ns-zer9 - custodiet blocked /pull task claiming.
    The template must explicitly state that /pull grants authority to
    claim AND execute tasks.
    """
    content = CUSTODIET_CONTEXT_TEMPLATE.read_text()

    # Check /pull is listed
    assert "`/pull`" in content or "/pull" in content, (
        "Custodiet template should list /pull as a skill with implicit authority"
    )

    # Check the authority description includes task claiming
    assert "claim" in content.lower(), (
        "Custodiet template should mention /pull grants authority to CLAIM tasks"
    )


def test_custodiet_template_documents_other_authority_skills() -> None:
    """Verify other skills with implicit authority are documented.

    This prevents future false positives for other common skills.
    """
    content = CUSTODIET_CONTEXT_TEMPLATE.read_text()

    # /q creates issues
    assert "/q" in content, (
        "Custodiet template should document /q implicit authority (create issues)"
    )

    # /dump has broad authority
    assert "/dump" in content, "Custodiet template should document /dump implicit authority"


def test_custodiet_template_links_bd_update_to_pull() -> None:
    """Verify bd update --status=in_progress is linked to /pull workflow.

    Regression: ns-zer9 - custodiet saw bd update as unauthorized action.
    The template should explicitly connect this to /pull's workflow.
    """
    content = CUSTODIET_CONTEXT_TEMPLATE.read_text()

    # Should mention that bd update is part of /pull workflow
    assert "in_progress" in content or "in-progress" in content, (
        "Custodiet template should mention status changes as part of /pull workflow"
    )
