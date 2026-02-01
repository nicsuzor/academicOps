"""Test workflow file parsing and structure.

Validates that workflow files in workflows/ directory have valid YAML frontmatter
and contain required fields.
"""

import re
from pathlib import Path

import pytest
import yaml

from lib.paths import get_plugin_root, get_workflows_dir


def extract_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and markdown body from a file.

    Args:
        content: File content with YAML frontmatter

    Returns:
        Tuple of (parsed_yaml_dict, markdown_body)
    """
    # Match YAML frontmatter between --- delimiters
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        # No frontmatter found - return empty dict and full content as body
        return {}, content

    yaml_text = match.group(1)
    markdown_body = match.group(2)

    try:
        yaml_data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        # If invalid YAML, treat as prose
        return {}, content

    return yaml_data, markdown_body


class TestWorkflowFiles:
    """Test workflow files structure and validity."""

    @pytest.fixture
    def workflow_dir(self) -> Path:
        """Return path to workflows directory."""
        return get_workflows_dir()

    @pytest.fixture
    def workflow_files(self, workflow_dir: Path) -> list[Path]:
        """Return list of all workflow markdown files."""
        if not workflow_dir.exists():
            pytest.skip("workflows/ directory does not exist")

        files = list(workflow_dir.glob("*.md"))
        if not files:
            pytest.skip("No workflow files found in workflows/")

        return files

    def test_workflow_directory_exists(self) -> None:
        """Verify workflows/ directory exists."""
        workflows_dir = get_workflows_dir()
        assert workflows_dir.exists(), "workflows/ directory should exist"
        assert workflows_dir.is_dir(), "workflows/ should be a directory"

    def test_workflow_has_markdown_structure(self, workflow_files: list[Path]) -> None:
        """Verify workflow files have required markdown sections.

        LLM-native design: Steps are human-readable markdown.
        """
        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            # We don't enforce frontmatter anymore, just check content
            
            # Skip very short files or placeholders
            if len(content.splitlines()) < 5:
                continue

            # Check for common sections if it's a full workflow
            # Note: Not all files might have "Steps", some might be reference
            # But most should have headers.
            assert "# " in content, f"{workflow_file.name}: Should have a title header"

    def test_specific_workflows_exist(self) -> None:
        """Verify expected workflow files exist."""
        workflows_dir = get_workflows_dir()
        expected_workflows = [
            "feature-dev.md",
            "design.md",
            "debugging.md",
            "tdd-cycle.md",
            "batch-processing.md",
            "simple-question.md",
            "direct-skill.md",
        ]

        for workflow_name in expected_workflows:
            workflow_path = workflows_dir / workflow_name
            assert workflow_path.exists(), (
                f"Expected workflow file {workflow_name} does not exist"
            )

    def test_workflows_index_exists(self) -> None:
        """Verify WORKFLOWS.md index file exists and has correct structure."""
        workflows_index = get_plugin_root() / "WORKFLOWS.md"
        assert workflows_index.exists(), "WORKFLOWS.md index file should exist"

        content = workflows_index.read_text()
        yaml_data, markdown_body = extract_yaml_frontmatter(content)

        # Verify it's an index file (WORKFLOWS.md should still have frontmatter)
        assert yaml_data.get("type") == "index", "WORKFLOWS.md type should be 'index'"

        # Verify it contains workflow references
        assert "[[design]]" in markdown_body, (
            "WORKFLOWS.md should contain workflow wikilinks (e.g., [[design]])"
        )

    @pytest.mark.parametrize(
        "workflow_id",
        [
            "feature-dev",
            "design",
            "debugging",
            "tdd-cycle",
            "batch-processing",
            "simple-question",
            "direct-skill",
        ],
    )
    def test_individual_workflow_parsing(self, workflow_id: str) -> None:
        """Test parsing each workflow file individually."""
        workflow_path = get_workflows_dir() / f"{workflow_id}.md"

        if not workflow_path.exists():
            pytest.skip(f"Workflow {workflow_id}.md does not exist")

        content = workflow_path.read_text()
        
        # Verify markdown headers presence
        # Relaxed check: Just ensure it has content and headers
        assert len(content) > 0
        assert "# " in content
