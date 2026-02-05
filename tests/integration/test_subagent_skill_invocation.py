#!/usr/bin/env python3
"""Integration test for subagent skill invocation.

Tests that when a subagent is instructed to use a skill, it invokes the Skill tool
to load the skill BEFORE calling MCP tools directly.

Background:
- Observed failure: Subagent told "use your remember skill" but called mcp__memory__store_memory
  directly without invoking Skill("remember") first
- This bypassed skill formatting guidance and led to YAML errors
- Detection is INDIRECT since headless output doesn't show tool traces

Detection approach:
Since we can't directly observe Skill tool invocation in headless mode, we verify
INDIRECTLY by checking output format quality:
- Notes following memory format = skill was likely loaded
- Notes lacking structure = skill was likely bypassed
"""

import time

import pytest

from tests.paths import get_data_dir

# Disable parallel execution for these tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("skill_invocation_sequential"),
    pytest.mark.xfail(
        reason="LLM behavior is non-deterministic - observational test", strict=False
    ),
]


def retry_flaky_e2e(test_func, max_attempts: int = 3):
    """Retry E2E test up to max_attempts times.

    E2E tests with LLMs are non-deterministic. This wrapper allows tests to
    retry, passing if ANY attempt succeeds. This tests capability (can it work?)
    rather than consistency (does it always work?).

    Args:
        test_func: Test function to execute
        max_attempts: Maximum number of attempts (default: 3)

    Returns:
        Result of first successful attempt

    Raises:
        AssertionError: If all attempts fail, raises last attempt's error
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return test_func()
        except AssertionError as e:
            last_error = e
            if attempt < max_attempts:
                # Brief pause between retries
                time.sleep(1)
                continue
            else:
                # All attempts failed
                raise AssertionError(
                    f"Test failed after {max_attempts} attempts. Last error: {e}"
                ) from last_error
    # This should never be reached, but satisfies type checker
    raise AssertionError("Retry logic error")


@pytest.mark.integration
@pytest.mark.slow
def test_skill_invocation_produces_formatted_output(claude_headless) -> None:
    """Test that invoking remember skill produces properly formatted notes.

    INDIRECT verification: If skill was loaded, notes follow memory format.
    If skill was bypassed, notes lack structure.

    Format markers checked:
    - Proper frontmatter (title, permalink, type, tags)
    - Content with [[wikilinks]] for related concepts
    """

    def _test_attempt():
        start_time = time.time() - 1

        prompt = """
        IMPORTANT: First invoke the remember skill using Skill("remember"), then create a note.

        Steps:
        1. Call Skill("remember") to load the remember skill FIRST
        2. After skill loads, use mcp__memory__store_memory to create a note about "Test Automation Patterns"
        3. The note MUST follow memory format with all required sections

        This is testing that skill invocation provides formatting guidance.
        """

        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        # Find created file
        data_dir = get_data_dir()
        data_files = list(data_dir.rglob("*.md"))

        created_file = None
        for file in data_files:
            # Only check files modified after test started
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            if (
                "test automation" in content.lower()
                or "automation patterns" in content.lower()
            ):
                created_file = file
                break

        assert created_file is not None, (
            f"No file matching 'test automation patterns' was created. "
            f"Checked {len([f for f in data_files if f.stat().st_mtime >= start_time])} "
            f"files modified since {start_time}"
        )
        return created_file

    created_file = retry_flaky_e2e(_test_attempt)
    content = created_file.read_text()

    # Verify memory format compliance (indicates skill was loaded)
    format_markers = {
        "frontmatter": content.startswith("---"),
        "title_field": "title:" in content,
        "permalink_field": "permalink:" in content,
        "type_field": "type:" in content,
        "has_wikilinks": "[[" in content and "]]" in content,
    }

    # At least 4 of 5 markers should be present if skill was properly loaded
    markers_present = sum(format_markers.values())

    assert markers_present >= 4, (
        f"Note lacks memory format (skill may not have been invoked). "
        f"Only {markers_present}/5 format markers found: {format_markers}"
    )
