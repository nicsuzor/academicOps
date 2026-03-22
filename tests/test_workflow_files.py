"""Tests for workflow definition files."""

import sys
from pathlib import Path

from lib.paths import get_workflows_dir

# Add aops-core to path
AOPS_CORE = Path(__file__).parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))


class TestWorkflowFiles:
    """Validate workflow markdown files."""

    def test_workflows_dir_exists(self) -> None:
        """Verify workflow directory exists."""
        workflows_dir = get_workflows_dir()
        assert workflows_dir.exists(), f"Workflows directory missing: {workflows_dir}"

    def test_workflow_files_are_non_empty(self) -> None:
        """Verify all .md files in workflows/ are non-empty markdown."""
        workflows_dir = get_workflows_dir()
        for workflow_file in workflows_dir.glob("*.md"):
            content = workflow_file.read_text(encoding="utf-8").strip()
            assert len(content) > 0, f"Workflow {workflow_file.name} is empty"
            assert "# " in content, (
                f"Workflow {workflow_file.name} must contain at least one markdown heading"
            )

    def test_specific_workflows_exist(self) -> None:
        """Verify expected workflow files exist."""
        workflows_dir = get_workflows_dir()
        expected_workflows = [
            "05-feature-development.md",
        ]

        for workflow_name in expected_workflows:
            workflow_path = workflows_dir / workflow_name
            assert workflow_path.exists(), f"Expected workflow file {workflow_name} does not exist"
