"""Test workflow file parsing and structure.

Validates that workflow files in workflows/ directory have valid YAML frontmatter
and contain required fields.
"""

import re
from pathlib import Path

import pytest
import yaml

from lib.paths import get_aops_root


def extract_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and markdown body from a file.

    Args:
        content: File content with YAML frontmatter

    Returns:
        Tuple of (parsed_yaml_dict, markdown_body)

    Raises:
        ValueError: If no valid frontmatter found
    """
    # Match YAML frontmatter between --- delimiters
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        raise ValueError("No YAML frontmatter found")

    yaml_text = match.group(1)
    markdown_body = match.group(2)

    try:
        yaml_data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}")

    return yaml_data, markdown_body


class TestWorkflowFiles:
    """Test workflow files structure and validity."""

    @pytest.fixture
    def workflow_dir(self) -> Path:
        """Return path to workflows directory."""
        return get_aops_root() / "workflows"

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
        workflows_dir = get_aops_root() / "workflows"
        assert workflows_dir.exists(), "workflows/ directory should exist"
        assert workflows_dir.is_dir(), "workflows/ should be a directory"

    def test_workflow_files_have_valid_yaml_frontmatter(
        self, workflow_files: list[Path]
    ) -> None:
        """Verify all workflow files have valid YAML frontmatter."""
        for workflow_file in workflow_files:
            content = workflow_file.read_text()

            # Should not raise ValueError
            yaml_data, markdown_body = extract_yaml_frontmatter(content)

            assert yaml_data is not None, (
                f"{workflow_file.name}: Empty YAML frontmatter"
            )
            assert len(markdown_body) > 0, f"{workflow_file.name}: Empty markdown body"

    def test_workflow_files_have_required_fields(
        self, workflow_files: list[Path]
    ) -> None:
        """Verify workflow files contain required YAML fields.

        LLM-native design: Only minimal frontmatter for tooling (id, category).
        All workflow content is in human-readable markdown prose.
        """
        required_fields = ["id", "category"]

        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            yaml_data, _ = extract_yaml_frontmatter(content)

            for field in required_fields:
                assert field in yaml_data, (
                    f"{workflow_file.name}: Missing required field '{field}'"
                )

            # Verify category is valid
            valid_categories = [
                "development",
                "planning",
                "quality-assurance",
                "operations",
                "information",
                "routing",
            ]
            assert yaml_data["category"] in valid_categories, (
                f"{workflow_file.name}: Invalid category '{yaml_data['category']}'. "
                f"Must be one of {valid_categories}"
            )

            # Verify no mechanistic fields remain (title, type, steps should not be in frontmatter)
            mechanistic_fields = ["title", "type", "steps", "dependencies"]
            for field in mechanistic_fields:
                assert field not in yaml_data, (
                    f"{workflow_file.name}: Should not have '{field}' in frontmatter. "
                    "Workflow content should be in markdown prose, not YAML structure."
                )

    def test_workflow_has_markdown_steps_section(self, workflow_files: list[Path]) -> None:
        """Verify workflow files have steps in markdown prose (not YAML).

        LLM-native design: Steps are human-readable markdown, not structured YAML.
        The hydrator (LLM) reads and understands the prose directly.
        """
        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            yaml_data, markdown_body = extract_yaml_frontmatter(content)

            # Verify steps section exists in markdown
            assert "## Steps" in markdown_body, (
                f"{workflow_file.name}: Should have '## Steps' section in markdown body"
            )

            # Verify no steps in YAML frontmatter (LLM-native design)
            assert "steps" not in yaml_data, (
                f"{workflow_file.name}: Steps should be in markdown prose, not YAML frontmatter"
            )

    def test_workflow_id_matches_filename(self, workflow_files: list[Path]) -> None:
        """Verify workflow ID matches filename (without .md extension)."""
        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            yaml_data, _ = extract_yaml_frontmatter(content)

            filename_id = workflow_file.stem  # Remove .md extension
            yaml_id = yaml_data.get("id")

            assert yaml_id == filename_id, (
                f"{workflow_file.name}: ID '{yaml_id}' should match "
                f"filename '{filename_id}'"
            )

    def test_specific_workflows_exist(self) -> None:
        """Verify expected workflow files exist."""
        workflows_dir = get_aops_root() / "workflows"
        expected_workflows = [
            "feature-dev.md",
            "minor-edit.md",
            "debugging.md",
            "tdd-cycle.md",
            "spec-review.md",
            "qa-demo.md",
            "batch-processing.md",
            "simple-question.md",
            "direct-skill.md",
            "bd-workflow.md",
        ]

        for workflow_name in expected_workflows:
            workflow_path = workflows_dir / workflow_name
            assert workflow_path.exists(), (
                f"Expected workflow file {workflow_name} does not exist"
            )

    def test_workflows_index_exists(self) -> None:
        """Verify WORKFLOWS.md index file exists and has correct structure."""
        workflows_index = get_aops_root() / "WORKFLOWS.md"
        assert workflows_index.exists(), "WORKFLOWS.md index file should exist"

        content = workflows_index.read_text()
        yaml_data, markdown_body = extract_yaml_frontmatter(content)

        # Verify it's an index file
        assert yaml_data.get("type") == "index", "WORKFLOWS.md type should be 'index'"

        # Verify it contains workflow references
        assert "[[workflows/" in markdown_body, (
            "WORKFLOWS.md should contain workflow wikilinks"
        )

    @pytest.mark.parametrize(
        "workflow_id",
        [
            "feature-dev",
            "minor-edit",
            "debugging",
            "tdd-cycle",
            "spec-review",
            "qa-demo",
            "batch-processing",
            "simple-question",
            "direct-skill",
            "bd-workflow",
        ],
    )
    def test_individual_workflow_parsing(self, workflow_id: str) -> None:
        """Test parsing each workflow file individually.

        LLM-native design: Minimal frontmatter (id, category), all content in markdown.
        """
        workflow_path = get_aops_root() / "workflows" / f"{workflow_id}.md"

        if not workflow_path.exists():
            pytest.skip(f"Workflow {workflow_id}.md does not exist")

        content = workflow_path.read_text()
        yaml_data, markdown_body = extract_yaml_frontmatter(content)

        # Basic structure checks - minimal frontmatter only
        assert yaml_data["id"] == workflow_id
        assert "category" in yaml_data

        # Verify no mechanistic fields in frontmatter
        assert "type" not in yaml_data, "type should not be in frontmatter"
        assert "title" not in yaml_data, "title should not be in frontmatter"
        assert "steps" not in yaml_data, "steps should be in markdown prose, not YAML"

        # Markdown body should have overview and steps sections
        assert "## Overview" in markdown_body
        assert "## When to Use" in markdown_body
        assert "## Steps" in markdown_body
