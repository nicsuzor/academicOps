"""Tests for batch-processing workflow patterns.

Regression tests ensuring workflow documentation contains required patterns.
"""

import re
from pathlib import Path

import pytest

WORKFLOW_PATH = Path(__file__).parent.parent.parent / "workflows" / "batch-processing.md"


@pytest.fixture
def workflow_content() -> str:
    """Load batch-processing workflow content."""
    return WORKFLOW_PATH.read_text()


def test_lazy_batching_pattern_exists(workflow_content: str) -> None:
    """Regression: Lazy batching pattern must be documented.

    Added after ns-nvam session revealed friction from exhaustive upfront enumeration.
    Lazy batching = supervisor defines boundaries, agents pull items within.
    """
    assert "### Lazy Batching" in workflow_content, (
        "Lazy batching pattern missing from batch-processing workflow"
    )


def test_lazy_batching_has_supervisor_agent_split(workflow_content: str) -> None:
    """Lazy batching must clarify supervisor vs agent responsibilities."""
    assert "**Supervisor role:**" in workflow_content
    assert "**Agent role" in workflow_content


def test_lazy_batching_shows_parallel_vs_sequential(workflow_content: str) -> None:
    """Lazy batching must document both parallel and sequential execution options."""
    # Check for execution model choice
    assert re.search(r"parallel.*sequential|sequential.*parallel", workflow_content, re.IGNORECASE), (
        "Lazy batching should document both parallel and sequential execution options"
    )


def test_lazy_batching_has_subtask_example(workflow_content: str) -> None:
    """Lazy batching must show bd subtask creation pattern."""
    assert "bd create" in workflow_content
    assert "--parent=" in workflow_content, (
        "Lazy batching example should show subtask creation with --parent flag"
    )


def test_smart_subagent_dumb_supervisor_principle(workflow_content: str) -> None:
    """Core principle: supervisor writes ONE prompt, subagent discovers."""
    assert "Smart Subagent, Dumb Supervisor" in workflow_content
    assert "supervisor doesn't know what it will find" in workflow_content.lower() or \
           "supervisor doesn't know item count" in workflow_content.lower(), (
        "Workflow should explain why lazy discovery beats upfront enumeration"
    )
