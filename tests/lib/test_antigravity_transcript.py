"""Test antigravity transcript parsing with PLANNER_RESPONSE thinking + tool_calls.

Task aops-9d9b23d2: Fix parser to read thinking and tool_calls fields instead of
dropping PLANNER_RESPONSE steps with empty content.
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.transcript_parser import SessionProcessor


def test_antigravity_planner_response_with_thinking_and_tool_calls(tmp_path: Path) -> None:
    """Parse fixture with PLANNER_RESPONSE thinking + tool_calls fields.

    Verifies:
    - Parsed entries contain the command 'gh pr view 1604 --comments'
    - Parsed entries contain the intent summary 'View PR 1604'
    - Parsed entries contain model reasoning from 'thinking'
    - Tool use blocks have descriptions from toolSummary, NOT from result text
    - Multi-call planner step yields three distinct tool calls
    - No spinner glyphs survive in tool_result content
    """
    # Copy fixture to antigravity brain directory structure
    brain_dir = tmp_path / "76d2a81d"
    logs_dir = brain_dir / ".system_generated" / "logs"
    logs_dir.mkdir(parents=True)
    fixture_src = Path(__file__).parent / "fixtures" / "antigravity_brain_sample.jsonl"
    transcript_path = logs_dir / "transcript.jsonl"
    transcript_path.write_text(fixture_src.read_text(), encoding="utf-8")

    # Parse through antigravity path
    processor = SessionProcessor()
    summary, entries, _ = processor.parse_session_file(brain_dir)

    # Extract all text content from entries for checking
    all_content = []
    tool_use_blocks = []
    tool_result_blocks = []
    thinking_blocks = []

    for entry in entries:
        content_list = entry.message.get("content", [])
        if isinstance(content_list, list):
            for block in content_list:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        all_content.append(block.get("text", ""))
                    elif block_type == "thinking":
                        thinking_blocks.append(block.get("thinking", ""))
                        all_content.append(block.get("thinking", ""))
                    elif block_type == "tool_use":
                        tool_use_blocks.append(block)
                        tool_input = block.get("input", {})
                        all_content.append(json.dumps(tool_input))
                    elif block_type == "tool_result":
                        tool_result_blocks.append(block)
                        result_content = block.get("content", "")
                        all_content.append(result_content)

    all_text = "\n".join(all_content)

    # AC 1: Command appears in parsed entries
    assert "gh pr view 1604 --comments" in all_text, (
        "Parsed entries must contain the command from tool_calls"
    )

    # AC 2: Intent summary appears in parsed entries
    assert "View PR 1604" in all_text, "Parsed entries must contain the toolSummary from tool_calls"

    # AC 3: Model reasoning from thinking appears
    assert "Prioritizing Tool Usage" in all_text, (
        "Parsed entries must contain model reasoning from thinking field"
    )
    assert len(thinking_blocks) > 0, "Must have at least one thinking block"
    assert any("Prioritizing Tool Usage" in t for t in thinking_blocks), (
        "Thinking blocks must contain reasoning text"
    )

    # AC 4: Tool use blocks have descriptions from toolSummary, NOT "The command completed successfully"
    found_good_description = False
    for block in tool_use_blocks:
        tool_input = block.get("input", {})
        desc = tool_input.get("description", "")
        # Verify we're using the intent summary, not the result message
        assert "The command completed successfully" not in desc, (
            f"Tool use description must come from toolSummary, not result. Got: {desc}"
        )
        if "View PR 1604" in desc or "Checkout PR branch" in desc:
            found_good_description = True
    assert found_good_description, "Must find at least one tool use with intent summary"

    # AC 5: Multi-call planner step (step 10) yields three distinct tool calls
    # Step 10 has: grep_search, view_file, view_file - should produce 3 tool_use blocks
    # Total: steps 3 (1) + 7 (1) + 10 (3) = 5 tool uses
    assert len(tool_use_blocks) >= 5, (
        f"Expected >=5 tool_use blocks (3+1+1), got {len(tool_use_blocks)}"
    )

    multi_call_summaries = [
        "Find context-map references",
        "View pre-commit config",
        "View framework integrity script",
    ]
    for summary_text in multi_call_summaries:
        found = any(summary_text in json.dumps(b.get("input", {})) for b in tool_use_blocks)
        assert found, f"Multi-call planner must emit tool call with summary: {summary_text}"

    # AC 6: No spinner glyphs survive in tool results
    spinner_glyphs = "⣾⣽⣻⢿⡿⣟⣯⣷"
    for result_block in tool_result_blocks:
        content = result_block.get("content", "")
        for glyph in spinner_glyphs:
            assert glyph not in content, (
                f"Spinner glyph {glyph!r} must not survive in tool_result content"
            )


def test_antigravity_entries_count(tmp_path: Path) -> None:
    """Verify parser creates proper entry structure."""
    brain_dir = tmp_path / "76d2a81d"
    logs_dir = brain_dir / ".system_generated" / "logs"
    logs_dir.mkdir(parents=True)
    fixture_src = Path(__file__).parent / "fixtures" / "antigravity_brain_sample.jsonl"
    transcript_path = logs_dir / "transcript.jsonl"
    transcript_path.write_text(fixture_src.read_text(), encoding="utf-8")

    processor = SessionProcessor()
    summary, entries, _ = processor.parse_session_file(brain_dir)

    # Should have entries for:
    # - 1 USER_INPUT (step 0)
    # - 3 PLANNER_RESPONSE (steps 3, 7, 10) -> 3 assistant entries with thinking/tool_use
    # - Multiple tool results (steps 4, 8, 11, 12, 13, 16, 17) -> user entries with tool_result
    # Total should be > 10 entries
    assert len(entries) > 10, f"Expected >10 entries, got {len(entries)}"

    # Check we have thinking blocks
    thinking_count = sum(
        1
        for e in entries
        for block in e.message.get("content", [])
        if isinstance(block, dict) and block.get("type") == "thinking"
    )
    assert thinking_count >= 3, f"Expected >=3 thinking blocks, got {thinking_count}"

    # Check we have tool_use blocks
    tool_use_count = sum(
        1
        for e in entries
        for block in e.message.get("content", [])
        if isinstance(block, dict) and block.get("type") == "tool_use"
    )
    # 2 single-call planners + 1 three-call planner = 5 tool uses
    assert tool_use_count >= 5, f"Expected >=5 tool_use blocks, got {tool_use_count}"


def test_antigravity_spinner_scrubbing() -> None:
    """Verify _scrub_binary removes spinner glyphs."""
    from lib.transcript_parser import SessionProcessor

    # Content with spinner glyphs
    content_with_spinners = "Output:\n⣾\n⣽\n⣻\n⢿\nActual output here"
    scrubbed = SessionProcessor._scrub_binary(content_with_spinners)

    # Spinner lines should be collapsed
    assert "⣾" not in scrubbed
    assert "⣽" not in scrubbed
    assert "⣻" not in scrubbed
    assert "⢿" not in scrubbed
    assert "Actual output here" in scrubbed
    assert "[binary data omitted:" in scrubbed or "Output:" in scrubbed
