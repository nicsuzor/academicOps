#!/usr/bin/env python3
"""Integration test for bmem YAML escaping.

Tests that bmem correctly handles content with special YAML characters
(specifically colons) in titles without generating parse errors.

Root cause test for: 'Invalid YAML in frontmatter: mapping values are not allowed here'
This error occurs when titles contain colons that aren't properly quoted in YAML.
"""

import time

import pytest
import yaml

from tests.paths import get_data_dir

# Disable parallel execution - these tests modify shared state
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.xdist_group("bmem_yaml_sequential")]


def retry_flaky_e2e(test_func, max_attempts=3):
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
                    f"Test failed after {max_attempts} attempts. "
                    f"Last error: {e}"
                ) from last_error


@pytest.mark.integration
@pytest.mark.slow
def test_bmem_handles_colons_in_title(claude_headless) -> None:
    """Test that bmem correctly escapes colons in note titles.

    Root cause test for: 'Invalid YAML in frontmatter: mapping values are not allowed here'

    This error occurs when YAML frontmatter contains unquoted values with colons:
        title: Meeting: Strategy Discussion  # INVALID - colon interpreted as mapping
        title: "Meeting: Strategy Discussion"  # VALID - quoted string

    The test verifies bmem properly quotes or escapes titles containing colons.
    """

    def _test_attempt():
        # Arrange: Record timestamp with 1-second buffer
        start_time = time.time() - 1

        prompt = '''
        Using mcp__bmem__write_note, create a note with this EXACT title:
        "Meeting: Strategy Discussion"

        The title MUST contain the colon character. Store in notes folder.
        Content can be brief - just a test note about strategy meetings.
        '''

        # Act: Execute Claude with bmem tool
        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",
        )

        # Assert: Command succeeded
        assert result["success"], f"bmem skill execution failed: {result.get('error')}"

        # Find created file (modified after test start, contains meeting/strategy)
        data_dir = get_data_dir()
        data_files = list(data_dir.rglob("*.md"))

        created_file = None
        for file in data_files:
            # Only check files modified after test started
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            # Look for files containing meeting or strategy (case-insensitive)
            if "meeting" in content.lower() or "strategy" in content.lower():
                created_file = file
                break

        assert created_file is not None, (
            f"bmem did not create a file matching criteria\n"
            f"Checked {len([f for f in data_files if f.stat().st_mtime >= start_time])} "
            f"files modified since {start_time}"
        )
        return created_file

    # Run with retry logic for E2E reliability
    created_file = retry_flaky_e2e(_test_attempt)

    # Assert: File has valid YAML frontmatter
    content = created_file.read_text()
    assert content.startswith("---"), f"File missing YAML frontmatter: {created_file}"

    # Parse frontmatter - this is the key assertion
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"Malformed frontmatter in {created_file}"

    try:
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter is not None, "Frontmatter parsed to None"
        assert "title" in frontmatter, f"Title field missing from frontmatter: {frontmatter}"
    except yaml.YAMLError as e:
        pytest.fail(
            f"Generated file has invalid YAML frontmatter: {e}\n"
            f"File: {created_file}\n"
            f"Frontmatter content:\n{parts[1]}"
        )

    # Additional validation: title should contain colon (verifying test setup)
    title = frontmatter.get("title", "")
    assert ":" in title, (
        f"Title does not contain colon - test may not be exercising the right path\n"
        f"Expected title with colon, got: {title}"
    )
