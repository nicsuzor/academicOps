"""Test that CORE.md contains explicit email workflow trigger phrases.

Integration test validating that CORE.md provides agents with specific
trigger phrases for the email-task-capture workflow, not vague "or similar".
"""

from pathlib import Path


def test_core_md_has_explicit_email_workflow_triggers():
    """Verify CORE.md contains explicit trigger phrases for email workflow.

    This test validates that CORE.md includes the documented trigger phrases
    from email-capture.md (lines 402-408) so agents know exactly when to
    invoke the email-task-capture workflow.

    The test will fail if:
    - CORE.md uses vague language like "or similar"
    - Required trigger phrases are missing
    - Email workflow guidance is incomplete

    Required trigger phrases from email-capture.md specification:
    - "check my email for tasks"
    - "process emails"
    - "any new tasks from email"
    - "what's in my inbox that needs action"
    - "email triage"
    - "review emails for action items"
    """
    # Arrange: Locate CORE.md
    core_md_path = Path("/home/nic/src/academicOps/CORE.md")
    assert core_md_path.exists(), f"CORE.md not found at {core_md_path}"

    # Act: Read CORE.md content
    core_content = core_md_path.read_text()

    # Assert: Verify email workflow section exists
    assert (
        "Email → Task workflow" in core_content or "email-task-capture" in core_content
    ), (
        "CORE.md should have an Email → Task workflow section referencing "
        "email-task-capture workflow"
    )

    # Define required trigger phrases from email-capture.md spec (lines 402-408)
    required_triggers = [
        "check my email for tasks",
        "process emails",
        "any new tasks from email",
        "what's in my inbox that needs action",
        "email triage",
        "review emails for action items",
    ]

    # Assert: Each trigger phrase must be present in CORE.md
    missing_triggers = []
    for trigger in required_triggers:
        # Check for exact phrase match (case-insensitive)
        if trigger.lower() not in core_content.lower():
            missing_triggers.append(trigger)

    assert not missing_triggers, (
        f"CORE.md is missing {len(missing_triggers)} explicit email workflow trigger phrases:\n"
        + "\n".join(f"  - '{trigger}'" for trigger in missing_triggers)
        + "\n\nThese trigger phrases must be explicitly listed in CORE.md (not just 'or similar')."
        + "\nExpected: A section that lists all trigger phrases from email-capture.md specification."
        + "\n\nSee: bots/skills/tasks/workflows/email-capture.md lines 402-408"
    )

    # Assert: Should NOT use vague "or similar" language
    # Check the email workflow section specifically
    email_section_start = core_content.find("Email → Task workflow")
    if email_section_start == -1:
        email_section_start = core_content.find("email-task-capture")

    if email_section_start != -1:
        # Get next 500 characters after the section marker
        email_section = core_content[email_section_start : email_section_start + 500]

        assert "or similar" not in email_section.lower(), (
            "CORE.md email workflow section should NOT use vague 'or similar' language. "
            "Agents need explicit trigger phrases to reliably invoke the workflow."
        )


def test_email_workflow_guidance_is_complete():
    """Verify email workflow guidance is complete and actionable.

    This test validates that CORE.md provides:
    1. Clear trigger phrases (not vague references)
    2. Reference to the workflow documentation
    3. Description of what the workflow does
    """
    # Arrange: Locate CORE.md
    core_md_path = Path("/home/nic/src/academicOps/CORE.md")
    core_content = core_md_path.read_text()

    # Assert: Should reference the workflow documentation
    assert (
        "email-capture.md" in core_content or "workflows/email-capture" in core_content
    ), (
        "CORE.md should reference the email-capture.md workflow documentation "
        "so agents can find detailed implementation guidance"
    )

    # Assert: Should describe what the workflow does
    workflow_keywords = ["extract", "action items", "categorize", "task"]
    found_keywords = [
        kw for kw in workflow_keywords if kw.lower() in core_content.lower()
    ]

    assert len(found_keywords) >= 3, (
        f"CORE.md email workflow description should include key concepts. "
        f"Found only {len(found_keywords)}/4 keywords: {found_keywords}. "
        f"Expected keywords: {workflow_keywords}"
    )
