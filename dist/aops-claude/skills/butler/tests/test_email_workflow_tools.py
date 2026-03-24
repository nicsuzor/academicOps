"""Test email-capture workflow documentation completeness.

Validates that email-capture.md exists and references the details document
for step-by-step implementation guidance.
"""

import os
from pathlib import Path

AOPS = os.environ.get("AOPS") or str(Path(__file__).resolve().parents[4])


def test_email_workflow_has_explicit_tool_examples() -> None:
    """Email-capture.md must provide actionable workflow structure.

    The workflow was refactored to delegate detailed tool examples to
    email-capture-details. This test validates:
    - The workflow file exists at the expected path
    - It contains the summary checklist of steps
    - It references the details document for implementation specifics
    - It includes critical guardrails
    """
    workflow_file = Path(AOPS) / "aops-core/skills/hydrator/workflows/email-capture.md"
    assert workflow_file.exists(), f"Workflow file not found: {workflow_file}"

    content = workflow_file.read_text()

    # Must reference the details document for step-by-step implementation
    assert "email-capture-details" in content, (
        "email-capture.md must reference email-capture-details for "
        "detailed tool examples and implementation guidance"
    )

    # Must contain the summary checklist
    assert "Summary Checklist" in content or "## Summary" in content, (
        "email-capture.md must contain a summary checklist of workflow steps"
    )

    # Must include critical guardrails
    assert "Guardrails" in content or "guardrail" in content.lower(), (
        "email-capture.md must include critical guardrails section"
    )

    # Must mention task creation (Step 6)
    assert "task" in content.lower(), (
        "email-capture.md must reference task creation as part of the workflow"
    )

    # Must mention duplicate prevention
    assert "duplicate" in content.lower() or "task_add.py" in content, (
        "email-capture.md must address duplicate prevention"
    )
