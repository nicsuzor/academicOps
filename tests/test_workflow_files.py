"""Tests for workflow definition files."""

import sys
from pathlib import Path

import pytest

# Add aops-core to path
AOPS_CORE = Path(__file__).parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.paths import get_workflows_dir


class TestWorkflowFiles:
    """Validate workflow markdown files."""

    def test_workflows_dir_exists(self) -> None:
        """Verify workflow directory exists."""
        workflows_dir = get_workflows_dir()
        assert workflows_dir.exists(), f"Workflows directory missing: {workflows_dir}"

    def test_workflow_files_have_frontmatter(self) -> None:
        """Verify all .md files in workflows/ have YAML frontmatter."""
        import yaml

        workflows_dir = get_workflows_dir()
        for workflow_file in workflows_dir.glob("*.md"):
            # Skip base files or non-workflow docs if needed
            if workflow_file.name.startswith("base-"):
                continue

            content = workflow_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                pytest.fail(f"Workflow {workflow_file.name} missing frontmatter marker (---)")

            try:
                # Extract frontmatter
                _, fm_text, _ = content.split("---", 2)
                fm = yaml.safe_load(fm_text)
                assert isinstance(fm, dict), "Frontmatter must be a dictionary"
                assert "id" in fm, f"Workflow {workflow_file.name} missing 'id' in frontmatter"
                assert "category" in fm, (
                    f"Workflow {workflow_file.name} missing 'category' in frontmatter"
                )
            except ValueError:
                pytest.fail(f"Workflow {workflow_file.name} has invalid frontmatter structure")
            except yaml.YAMLError as e:
                pytest.fail(f"Workflow {workflow_file.name} has invalid YAML: {e}")

    def test_specific_workflows_exist(self) -> None:
        """Verify expected workflow files exist."""
        workflows_dir = get_workflows_dir()
        expected_workflows = [
            "feature-dev.md",
            "simple-question.md",
        ]

        for workflow_name in expected_workflows:
            workflow_path = workflows_dir / workflow_name
            assert workflow_path.exists(), f"Expected workflow file {workflow_name} does not exist"
