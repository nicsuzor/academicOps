"""Tests for task assignment routing logic in batch_worker.

Tests the determine_assignee() and process_task() functions which route tasks
to the appropriate assignee based on content analysis:
- Mechanical work → polecat (swarm-claimable)
- Judgment-call tasks → None (unassigned backlog)
- Explicit assignee → preserved as-is

See P#102 (Judgment Tasks Default Unassigned) in HEURISTICS.md.
"""

import sys
from pathlib import Path

# Add hypervisor scripts to path for import
sys.path.insert(
    0,
    str(Path(__file__).parent.parent / "aops-core" / "skills" / "hypervisor" / "scripts"),
)

from batch_worker import determine_assignee, process_task


class TestDetermineAssigneeJudgmentTasks:
    """Judgment-call tasks should default to None (unassigned backlog)."""

    def test_review_task_unassigned(self):
        """Tasks with 'review' in title should be unassigned (not auto-assigned to nic)."""
        result = determine_assignee(
            body="Review the current metrics approach",
            fm={},
            title="Review design decisions",
        )
        assert result is None

    def test_evaluate_task_unassigned(self):
        """Tasks about evaluation should be unassigned."""
        result = determine_assignee(
            body="Re-evaluate the metrics we use for assessment",
            fm={},
            title="Re-evaluate X metrics",
        )
        assert result is None

    def test_decision_task_unassigned(self):
        """Tasks requiring decisions should be unassigned."""
        result = determine_assignee(
            body="Make a decision about the architecture approach",
            fm={},
            title="Decide on database strategy",
        )
        assert result is None

    def test_meeting_task_unassigned(self):
        """Meeting tasks should be unassigned."""
        result = determine_assignee(
            body="Schedule and prepare for stakeholder meeting",
            fm={},
            title="Prepare for team meeting",
        )
        assert result is None

    def test_vague_task_unassigned(self):
        """Vague tasks without clear mechanical patterns should be unassigned."""
        result = determine_assignee(
            body="Think about how to improve the onboarding process",
            fm={},
            title="Improve onboarding",
        )
        assert result is None

    def test_needs_clarification_unassigned(self):
        """Tasks marked as needing clarification should be unassigned."""
        result = determine_assignee(
            body="This needs clarification from the team",
            fm={},
            title="Underspecified requirement",
        )
        assert result is None


class TestDetermineAssigneeMechanicalTasks:
    """Mechanical work should default to polecat (swarm-claimable)."""

    def test_implement_function_polecat(self):
        """Implement function tasks should go to polecat."""
        result = determine_assignee(
            body="Implement a new function for data processing",
            fm={},
            title="Implement validation function",
        )
        assert result == "polecat"

    def test_fix_bug_polecat(self):
        """Bug fix tasks should go to polecat."""
        result = determine_assignee(
            body="Fix the bug in the parser module",
            fm={},
            title="Fix parsing error",
        )
        assert result == "polecat"

    def test_refactor_polecat(self):
        """Refactoring tasks should go to polecat."""
        result = determine_assignee(
            body="Refactor the routing module for clarity",
            fm={},
            title="Refactor task router",
        )
        assert result == "polecat"

    def test_update_config_polecat(self):
        """Config update tasks should go to polecat."""
        result = determine_assignee(
            body="Update the config to support new options",
            fm={},
            title="Update configuration schema",
        )
        assert result == "polecat"

    def test_create_skill_polecat(self):
        """Create skill tasks should go to polecat."""
        result = determine_assignee(
            body="Create a new skill for automated reporting",
            fm={},
            title="Create reporting skill",
        )
        assert result == "polecat"

    def test_bot_assigned_tag_polecat(self):
        """Tasks with bot-assigned tag should go to polecat."""
        result = determine_assignee(
            body="Some vague task",
            fm={"tags": ["bot-assigned"]},
            title="Some task",
        )
        assert result == "polecat"

    def test_task_with_acceptance_criteria_polecat(self):
        """Tasks with acceptance criteria should go to polecat."""
        result = determine_assignee(
            body="## Acceptance Criteria\n- [ ] Tests pass\n- [ ] Docs updated",
            fm={},
            title="Some structured task",
        )
        assert result == "polecat"

    def test_task_with_checkboxes_polecat(self):
        """Tasks with checkboxes should go to polecat."""
        result = determine_assignee(
            body="Do the thing:\n- [ ] Step 1\n- [ ] Step 2",
            fm={},
            title="Structured work",
        )
        assert result == "polecat"


class TestDetermineAssigneeExplicitOverride:
    """Explicit assignee in frontmatter should be preserved."""

    def test_explicit_nic_preserved(self):
        """Explicit nic assignment should be preserved."""
        result = determine_assignee(
            body="Some task",
            fm={"assignee": "nic"},
            title="Some task",
        )
        assert result == "nic"

    def test_explicit_polecat_preserved(self):
        """Explicit polecat assignment should be preserved."""
        result = determine_assignee(
            body="Review the design",
            fm={"assignee": "polecat"},
            title="Review design",
        )
        assert result == "polecat"

    def test_explicit_custom_assignee_preserved(self):
        """Custom explicit assignee should be preserved."""
        result = determine_assignee(
            body="Deploy to production",
            fm={"assignee": "ops-team"},
            title="Production deployment",
        )
        assert result == "ops-team"


class TestProcessTaskAssignment:
    """Integration tests for process_task assignment routing."""

    def test_mechanical_complexity_assigns_polecat(self, tmp_path):
        """Tasks with mechanical complexity should be assigned to polecat."""
        task_file = tmp_path / "task-mechanical.md"
        task_file.write_text(
            "---\ntitle: Fix parser bug\ntype: task\nstatus: active\n---\n"
            "Fix the bug in `parser.py`:\n- [ ] Fix regex\n- [ ] Add test\n"
        )
        result = process_task(str(task_file))
        assert "polecat" in result["action"]

    def test_judgment_task_unassigned(self, tmp_path):
        """Judgment-call tasks should be unassigned (None)."""
        task_file = tmp_path / "task-judgment.md"
        task_file.write_text(
            "---\ntitle: Think about strategy\ntype: task\nstatus: active\n---\n"
            "Consider the best approach for the project.\n"
        )
        result = process_task(str(task_file))
        assert result["action"] == "assign:None"

    def test_blocked_human_unassigned(self, tmp_path):
        """Tasks with blocked-human complexity should be unassigned."""
        task_file = tmp_path / "task-blocked.md"
        task_file.write_text(
            "---\ntitle: Wait for client response\ntype: task\nstatus: active\n"
            "complexity: blocked-human\n---\n"
            "Waiting for external input.\n"
        )
        result = process_task(str(task_file))
        assert result["action"] == "assign:None"

    def test_explicit_nic_assignment_preserved(self, tmp_path):
        """Explicit nic assignment should be preserved in process_task."""
        task_file = tmp_path / "task-nic.md"
        task_file.write_text(
            "---\ntitle: Respond to email\ntype: task\nstatus: active\n"
            "assignee: nic\n---\n"
            "Respond to the client email.\n"
        )
        result = process_task(str(task_file))
        assert "nic" in result["action"]
