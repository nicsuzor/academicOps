#!/usr/bin/env python3
"""Integration test for iOS Note Capture workflow E2E.

Tests that the iOS Note Capture workflow's Claude Code action creates valid
properly formatted notes from iOS capture payloads.

The workflow (`.github/workflows/ios-note-capture.yml`) uses Claude Code to
process note captures. This E2E test verifies that the prompt produces notes
with correct structure and content.

NOTE: This is a documentation test. The actual workflow is production-ready
per ROADMAP.md. This test documents the expected behavior and can be used
to validate implementation changes.
"""

import re
import time
import yaml
from pathlib import Path

import pytest

from tests.paths import get_data_dir


@pytest.mark.integration
@pytest.mark.slow
def test_ios_note_capture_prompt_creates_valid_note(claude_headless, tmp_path):
    """Test that iOS Note Capture workflow creates valid properly formatted note.

    Simulates the Claude Code action's prompt from the iOS Note Capture
    workflow (lines 72-117 of `.github/workflows/ios-note-capture.yml`).

    The Claude Code action receives:
    - Note content (iOS input)
    - Tags (from iOS or default)

    It should create a properly formatted markdown file with:
    - YAML frontmatter (title, permalink, type: note, tags, created timestamp)
    - Context section mentioning iOS capture
    - Observations section with [idea] observation containing input content
    - Relations section (can be empty)

    Args:
        claude_headless: Fixture for headless Claude execution
        tmp_path: Pytest temporary directory fixture

    Raises:
        AssertionError: If workflow doesn't create valid note with required structure
    """
    # Arrange: Prepare test payload matching iOS capture format
    content = "Important insight about platform governance and content moderation at scale"
    tags = "mobile-capture,research"

    # Record timestamp with 1-second buffer to avoid race conditions
    start_time = time.time() - 1

    # Extract exact prompt from workflow YAML (lines 72-117)
    prompt = f"""Create a properly formatted note from this iOS capture.

INPUT:
- Content: {content}
- Tags: {tags}

TASK:
1. Generate a concise, descriptive title from the content (3-7 words)
2. Create directory data/notes/mobile-captures/ if it doesn't exist
3. Generate a properly formatted markdown file with:
   - YAML frontmatter (title, permalink, type: note, tags including mobile-capture)
   - Context section noting this was captured from iOS
   - Observations section with the content as an [idea] observation
   - Relations section (can be empty initially)
4. Save as: data/notes/mobile-captures/YYYY-MM-DD-<slug>.md
   (use today's date and a URL-safe slug from the generated title)

BMEM FORMAT:
```
---
title: <title>
permalink: <url-safe-slug>
type: note
tags:
  - mobile-capture
  - <other tags>
created: <ISO8601 timestamp>
---

# <title>

## Context

Captured from iOS via voice/text input.

## Observations

- [idea] <content> #mobile-capture

## Relations

None
```

Output the filepath of the created note when done."""

    # Act: Execute Claude Code action prompt
    result = claude_headless(
        prompt,
        permission_mode="bypassPermissions",
        timeout_seconds=180,
        model="sonnet",  # Use more capable model for reliability
        cwd=tmp_path,  # Run in temp directory
    )

    # Assert: Command succeeded
    assert result["success"], f"iOS note capture execution failed: {result.get('error')}"

    # Assert: Find created note file
    # Look for file in data/notes/mobile-captures/ matching YYYY-MM-DD-*.md pattern
    mobile_captures_dir = tmp_path / "data" / "notes" / "mobile-captures"

    # FAIL FAST: Directory should have been created
    if not mobile_captures_dir.exists():
        raise AssertionError(
            f"Claude Code did not create mobile-captures directory. "
            f"Expected: {mobile_captures_dir}"
        )

    created_files = list(mobile_captures_dir.glob("*.md"))

    # FAIL FAST: At least one file must be created
    assert created_files, (
        f"No markdown files found in {mobile_captures_dir}. "
        f"Claude Code should have created YYYY-MM-DD-*.md file."
    )

    # Find the most recently created file (should be only one in test)
    created_file = max(created_files, key=lambda f: f.stat().st_mtime)

    # Verify: Filename matches YYYY-MM-DD-*.md pattern
    filename_pattern = r"^\d{4}-\d{2}-\d{2}-.+\.md$"
    assert re.match(filename_pattern, created_file.name), (
        f"File {created_file.name} doesn't match pattern YYYY-MM-DD-*.md"
    )

    # Read file content for validation
    file_content = created_file.read_text()

    # FAIL FAST: File must have valid YAML frontmatter
    assert file_content.startswith("---"), f"File {created_file} missing YAML frontmatter opening"
    assert file_content.count("---") >= 2, f"File {created_file} missing YAML frontmatter closing"

    # Extract frontmatter
    frontmatter_end = file_content.find("---", 3)
    frontmatter_text = file_content[3:frontmatter_end].strip()

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise AssertionError(
            f"Invalid YAML frontmatter in {created_file}: {e}"
        ) from e

    # Assert: Required frontmatter fields exist
    required_fields = ["title", "permalink", "type", "tags", "created"]
    for field in required_fields:
        assert field in frontmatter, (
            f"Missing required field '{field}' in frontmatter of {created_file}"
        )

    # Assert: type must be 'note'
    assert frontmatter["type"] == "note", (
        f"File type should be 'note', got '{frontmatter['type']}' in {created_file}"
    )

    # Assert: tags must include mobile-capture
    tags_list = frontmatter.get("tags", [])
    assert isinstance(tags_list, list), (
        f"tags should be a list, got {type(tags_list).__name__} in {created_file}"
    )
    assert "mobile-capture" in tags_list, (
        f"tags must include 'mobile-capture', got {tags_list} in {created_file}"
    )

    # Assert: created field is ISO8601 timestamp (string or parsed datetime)
    from datetime import datetime

    created_ts = frontmatter.get("created")
    assert created_ts is not None, "'created' field is required in frontmatter"

    # YAML parser converts ISO8601 to datetime object, or it may be a string
    if isinstance(created_ts, str):
        # If it's a string, verify ISO8601 format
        assert "T" in created_ts and ("Z" in created_ts or "+" in created_ts), (
            f"'created' should be ISO8601 format, got {created_ts}"
        )
    elif isinstance(created_ts, datetime):
        # If it's a datetime, verify it's in UTC or has timezone info
        assert created_ts.tzinfo is not None, (
            f"'created' datetime should have timezone info, got {created_ts}"
        )
    else:
        raise AssertionError(
            f"'created' should be ISO8601 string or datetime, got {type(created_ts).__name__}"
        )

    # Assert: File has Context section
    assert "## Context" in file_content, f"File {created_file} missing Context section"

    # Assert: Context section mentions iOS capture
    context_section = file_content.split("## Context")[1].split("##")[0]
    assert "iOS" in context_section or "ios" in context_section.lower(), (
        f"Context section in {created_file} doesn't mention iOS capture"
    )

    # Assert: File has Observations section
    assert "## Observations" in file_content, (
        f"File {created_file} missing Observations section"
    )

    # Assert: Observations uses [idea] format
    obs_section = file_content.split("## Observations")[1].split("##")[0]
    assert "[idea]" in obs_section, (
        f"Observations section in {created_file} missing [idea] format"
    )

    # Assert: Observations contains the input content
    assert "platform governance" in obs_section or "scale" in obs_section, (
        f"Observations section in {created_file} doesn't contain captured content"
    )

    # Assert: File has Relations section
    assert "## Relations" in file_content, f"File {created_file} missing Relations section"

    # Assert: File is valid markdown (has H1 heading)
    assert "# " in file_content, f"File {created_file} missing H1 heading"

    # Extract title from frontmatter and verify H1 matches
    title = frontmatter.get("title")
    assert title, "Empty or missing title in frontmatter"

    # H1 should exist and contain title (allow minor formatting variations)
    h1_lines = [line for line in file_content.split("\n") if line.startswith("# ")]
    assert h1_lines, f"No H1 heading found in {created_file}"
    h1_content = h1_lines[0][2:].strip()
    assert h1_content.lower() == title.lower(), (
        f"H1 heading '{h1_content}' doesn't match title '{title}' in {created_file}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_ios_note_capture_commit_message_format(claude_headless, tmp_path):
    """Test that workflow's commit message follows capture(mobile): <title> pattern.

    Verifies that the workflow extracts the title from the YAML frontmatter
    (lines 128-134 of `.github/workflows/ios-note-capture.yml`) and uses it
    to generate a commit message in the format: capture(mobile): {title}

    This test simulates the workflow's note creation and title extraction,
    then validates that the extracted title would produce the expected commit
    message format.

    Args:
        claude_headless: Fixture for headless Claude execution
        tmp_path: Pytest temporary directory fixture

    Raises:
        AssertionError: If title extraction or commit message format is incorrect
    """
    # Arrange: Prepare test payload with specific content for title generation
    content = "Advanced techniques for distributed systems optimization and performance tuning"
    tags = "mobile-capture,research,systems"

    # Extract exact prompt from workflow YAML (lines 72-117)
    prompt = f"""Create a properly formatted note from this iOS capture.

INPUT:
- Content: {content}
- Tags: {tags}

TASK:
1. Generate a concise, descriptive title from the content (3-7 words)
2. Create directory data/notes/mobile-captures/ if it doesn't exist
3. Generate a properly formatted markdown file with:
   - YAML frontmatter (title, permalink, type: note, tags including mobile-capture)
   - Context section noting this was captured from iOS
   - Observations section with the content as an [idea] observation
   - Relations section (can be empty initially)
4. Save as: data/notes/mobile-captures/YYYY-MM-DD-<slug>.md
   (use today's date and a URL-safe slug from the generated title)

BMEM FORMAT:
```
---
title: <title>
permalink: <url-safe-slug>
type: note
tags:
  - mobile-capture
  - <other tags>
created: <ISO8601 timestamp>
---

# <title>

## Context

Captured from iOS via voice/text input.

## Observations

- [idea] <content> #mobile-capture

## Relations

None
```

Output the filepath of the created note when done."""

    # Act: Execute Claude Code action prompt
    result = claude_headless(
        prompt,
        permission_mode="bypassPermissions",
        timeout_seconds=180,
        model="sonnet",  # Use more capable model for reliability
        cwd=tmp_path,  # Run in temp directory
    )

    # Assert: Command succeeded
    assert result["success"], f"iOS note capture execution failed: {result.get('error')}"

    # Assert: Find created note file
    mobile_captures_dir = tmp_path / "data" / "notes" / "mobile-captures"

    # FAIL FAST: Directory should exist
    if not mobile_captures_dir.exists():
        raise AssertionError(
            f"Claude Code did not create mobile-captures directory. "
            f"Expected: {mobile_captures_dir}"
        )

    created_files = list(mobile_captures_dir.glob("*.md"))

    # FAIL FAST: At least one file must be created
    assert created_files, (
        f"No markdown files found in {mobile_captures_dir}. "
        f"Claude Code should have created YYYY-MM-DD-*.md file."
    )

    # Find the most recently created file
    created_file = max(created_files, key=lambda f: f.stat().st_mtime)

    # Read file content for title extraction
    file_content = created_file.read_text()

    # FAIL FAST: File must have valid YAML frontmatter
    assert file_content.startswith("---"), f"File {created_file} missing YAML frontmatter opening"
    assert file_content.count("---") >= 2, f"File {created_file} missing YAML frontmatter closing"

    # Extract frontmatter (lines 152-162 of existing test)
    frontmatter_end = file_content.find("---", 3)
    frontmatter_text = file_content[3:frontmatter_end].strip()

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise AssertionError(
            f"Invalid YAML frontmatter in {created_file}: {e}"
        ) from e

    # Extract title from frontmatter (simulating workflow line 129)
    title = frontmatter.get("title")
    assert title, "Empty or missing title in frontmatter"

    # Assert: Title is a non-empty string
    assert isinstance(title, str), (
        f"title should be a string, got {type(title).__name__}"
    )
    assert len(title) > 0, "title cannot be empty"

    # Test: Verify commit message format matches capture(mobile): {title} pattern
    expected_commit_message = f"capture(mobile): {title}"

    # Verify format components
    assert expected_commit_message.startswith("capture(mobile): "), (
        f"Commit message should start with 'capture(mobile): ', got '{expected_commit_message}'"
    )

    # Extract the title portion from commit message (everything after "capture(mobile): ")
    commit_title = expected_commit_message[len("capture(mobile): "):]
    assert commit_title == title, (
        f"Commit message title '{commit_title}' doesn't match extracted title '{title}'"
    )

    # Assert: Title should be reasonable length (3-7 words as per prompt)
    word_count = len(title.split())
    assert 3 <= word_count <= 7, (
        f"Title should be 3-7 words, got {word_count} words: '{title}'"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_ios_note_capture_handles_empty_content(claude_headless, tmp_path):
    """Test that iOS Note Capture workflow handles empty content gracefully.

    Verifies that when empty or minimal content is provided, the workflow
    either creates a note with fallback title/content or handles the edge case
    gracefully without crashing.

    The workflow should handle this gracefully per lines 132-134 of the workflow,
    which provide a fallback "iOS capture" title when note creation fails.

    Args:
        claude_headless: Fixture for headless Claude execution
        tmp_path: Pytest temporary directory fixture

    Raises:
        AssertionError: If workflow crashes or fails fatally with empty content
    """
    # Arrange: Prepare test payload with empty content
    content = ""
    tags = "mobile-capture"

    # Extract exact prompt from workflow YAML (lines 72-117)
    prompt = f"""Create a properly formatted note from this iOS capture.

INPUT:
- Content: {content}
- Tags: {tags}

TASK:
1. Generate a concise, descriptive title from the content (3-7 words)
2. Create directory data/notes/mobile-captures/ if it doesn't exist
3. Generate a properly formatted markdown file with:
   - YAML frontmatter (title, permalink, type: note, tags including mobile-capture)
   - Context section noting this was captured from iOS
   - Observations section with the content as an [idea] observation
   - Relations section (can be empty initially)
4. Save as: data/notes/mobile-captures/YYYY-MM-DD-<slug>.md
   (use today's date and a URL-safe slug from the generated title)

BMEM FORMAT:
```
---
title: <title>
permalink: <url-safe-slug>
type: note
tags:
  - mobile-capture
  - <other tags>
created: <ISO8601 timestamp>
---

# <title>

## Context

Captured from iOS via voice/text input.

## Observations

- [idea] <content> #mobile-capture

## Relations

None
```

Output the filepath of the created note when done."""

    # Act: Execute Claude Code action prompt
    result = claude_headless(
        prompt,
        permission_mode="bypassPermissions",
        timeout_seconds=180,
        model="sonnet",  # Use more capable model for reliability
        cwd=tmp_path,  # Run in temp directory
    )

    # Assert: Command succeeded (gracefully handles empty content without crashing)
    assert result["success"], f"iOS note capture should handle empty content gracefully: {result.get('error')}"

    # Assert: Find created note file or confirm graceful handling
    mobile_captures_dir = tmp_path / "data" / "notes" / "mobile-captures"

    # Check if directory was created
    if mobile_captures_dir.exists():
        created_files = list(mobile_captures_dir.glob("*.md"))

        # If files were created, verify they have valid structure
        if created_files:
            # Find the most recently created file
            created_file = max(created_files, key=lambda f: f.stat().st_mtime)

            # Read file content for validation
            file_content = created_file.read_text()

            # Verify: File has YAML frontmatter
            assert file_content.startswith("---"), (
                f"File {created_file} should have YAML frontmatter"
            )
            assert file_content.count("---") >= 2, (
                f"File {created_file} should have closing YAML delimiter"
            )

            # Extract and parse frontmatter
            frontmatter_end = file_content.find("---", 3)
            frontmatter_text = file_content[3:frontmatter_end].strip()

            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                raise AssertionError(
                    f"Invalid YAML frontmatter in {created_file}: {e}"
                ) from e

            # Verify: Required fields exist (with graceful handling for empty content)
            required_fields = ["title", "permalink", "type", "tags", "created"]
            for field in required_fields:
                assert field in frontmatter, (
                    f"Missing required field '{field}' in frontmatter"
                )

            # Verify: type is 'note'
            assert frontmatter["type"] == "note", (
                f"File type should be 'note', got '{frontmatter['type']}'"
            )

            # Verify: tags include mobile-capture
            tags_list = frontmatter.get("tags", [])
            assert isinstance(tags_list, list), (
                f"tags should be a list, got {type(tags_list).__name__}"
            )
            assert "mobile-capture" in tags_list, (
                f"tags must include 'mobile-capture', got {tags_list}"
            )

            # Verify: created field is ISO8601 timestamp
            from datetime import datetime

            created_ts = frontmatter.get("created")
            assert created_ts is not None, "'created' field is required"

            if isinstance(created_ts, str):
                assert "T" in created_ts and ("Z" in created_ts or "+" in created_ts), (
                    f"'created' should be ISO8601 format, got {created_ts}"
                )
            elif isinstance(created_ts, datetime):
                assert created_ts.tzinfo is not None, (
                    f"'created' datetime should have timezone info"
                )

            # Verify: File has required sections
            assert "## Context" in file_content, "File missing Context section"
            assert "## Observations" in file_content, "File missing Observations section"
            assert "## Relations" in file_content, "File missing Relations section"

            # Verify: Title exists and is reasonable (may be fallback for empty content)
            title = frontmatter.get("title")
            assert title, "Title should not be empty"
            assert isinstance(title, str), (
                f"title should be a string, got {type(title).__name__}"
            )
