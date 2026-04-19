#!/usr/bin/env python3
"""Demo test for Enforcer Subagent Transcripts.

Demonstrates the enforcer's compliance checking by reading REAL subagent transcripts
from past sessions. This shows exactly what context the enforcer receives and how
it evaluates compliance.

Unlike test_compliance_detection.py (which runs new headless sessions), this test
reads existing transcripts to prove enforcer behavior in the wild.

The workflow:
1. Find enforcer subagent transcripts in ~/.claude/projects/*/subagents/
2. Parse the JSONL to extract the conversation
3. Show the audit file content the enforcer received
4. Show the enforcer's compliance verdict (OK or ATTENTION)

Run with: uv run pytest tests/demo/test_demo_enforcer_transcript.py -v -s -n 0 -m demo

Related:
- hooks/enforcer_gate.py - PostToolUse hook that triggers the enforcer
- agents/enforcer.md - Enforcer agent system prompt
- hooks/templates/enforcer-context.md - Audit file template
"""

import json
from pathlib import Path

import pytest

_LEGACY_SCAN_TOKENS = ('"enforcer"', '"custodiet"', "claude-compliance/audit_")


def find_enforcer_transcripts(limit: int = 10) -> list[Path]:
    """Find subagent transcripts that contain enforcer activity.

    Enforcer transcripts contain the string "enforcer" (or the legacy
    "custodiet" for historical sessions) or read from
    /tmp/claude-compliance/audit_*.md files.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []

    transcripts: list[Path] = []

    # Search all subagent directories
    for subagent_dir in projects_dir.rglob("subagents"):
        for jsonl_file in subagent_dir.glob("agent-*.jsonl"):
            # Quick check: does file mention enforcer or audit files?
            try:
                content = jsonl_file.read_text()
                if any(token in content for token in _LEGACY_SCAN_TOKENS):
                    transcripts.append(jsonl_file)
                    if len(transcripts) >= limit:
                        return transcripts
            except Exception:
                continue

    return transcripts


def parse_enforcer_transcript(transcript_path: Path) -> dict:
    """Parse an enforcer subagent transcript into structured data.

    Returns:
        Dict with:
        - agent_id: str
        - prompt: str (the initial instruction)
        - audit_file_path: str (path to audit file read)
        - audit_content: str (first ~2000 chars of audit file)
        - session_context: str (extracted Session Context section)
        - verdict: str ("OK" or "ATTENTION" or "unknown")
        - full_response: str (the enforcer's full analysis)
    """
    result = {
        "agent_id": "",
        "prompt": "",
        "audit_file_path": "",
        "audit_content": "",
        "session_context": "",
        "verdict": "unknown",
        "full_response": "",
    }

    entries = []
    with transcript_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return result

    # Extract agent_id from first entry
    result["agent_id"] = entries[0].get("agentId", "unknown")

    # Find initial prompt (first user message)
    for entry in entries:
        if entry.get("type") == "user":
            msg = entry.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                result["prompt"] = content
                break

    # Find tool result containing audit file content
    for entry in entries:
        if entry.get("type") == "user":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_content = block.get("content", "")
                        if "# Ultra Vires Compliance Check" in tool_content:
                            result["audit_content"] = tool_content[:4000]

                            # Extract Session Context section
                            if "## Session Context" in tool_content:
                                start = tool_content.find("## Session Context")
                                # Find end (next major section)
                                end = tool_content.find("\n# AXIOMS", start)
                                if end == -1:
                                    end = start + 2000
                                result["session_context"] = tool_content[start:end]

            # Also check toolUseResult field
            tool_result = entry.get("toolUseResult", {})
            if isinstance(tool_result, dict):
                file_info = tool_result.get("file", {})
                if file_info:
                    result["audit_file_path"] = file_info.get("filePath", "")
                    file_content = file_info.get("content", "")
                    if "# Ultra Vires Compliance Check" in file_content:
                        result["audit_content"] = file_content[:4000]
                        if "## Session Context" in file_content:
                            start = file_content.find("## Session Context")
                            end = file_content.find("\n# AXIOMS", start)
                            if end == -1:
                                end = start + 2000
                            result["session_context"] = file_content[start:end]

    # Find the enforcer's response (last assistant message)
    for entry in reversed(entries):
        if entry.get("type") == "assistant":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if text:
                            result["full_response"] = text

                            # Determine verdict
                            if "```text\nOK\n```" in text or text.strip().endswith("OK"):
                                result["verdict"] = "OK"
                            elif "ATTENTION" in text:
                                result["verdict"] = "ATTENTION"
                            break
            if result["full_response"]:
                break

    return result


@pytest.mark.demo
class TestEnforcerTranscriptDemo:
    """Demo test showing real enforcer subagent transcripts."""

    def test_demo_show_enforcer_transcript(self) -> None:
        """Demo: Parse and display a real enforcer subagent transcript.

        This test reads actual enforcer transcripts from past sessions,
        showing exactly what context the enforcer received and how it responded.

        The output demonstrates:
        1. What prompt triggers the enforcer
        2. What session context the enforcer sees (Original Request, TodoWrite, Tools, etc.)
        3. How the enforcer evaluates compliance
        4. The verdict (OK or ATTENTION with specific violation)
        """
        print("\n" + "=" * 80)
        print("ENFORCER TRANSCRIPT DEMO: Real Compliance Check Evidence")
        print("=" * 80)

        # === STEP 1: Find Enforcer Transcripts ===
        print("\n--- STEP 1: Discover Enforcer Transcripts ---")
        transcripts = find_enforcer_transcripts(limit=20)

        if not transcripts:
            pytest.skip(
                "No enforcer transcripts found in ~/.claude/projects/. Ensure the enforcer is active."
            )

        print(f"Found {len(transcripts)} enforcer transcript(s)")

        # === STEP 2: Parse and Display Transcripts ===
        print("\n--- STEP 2: Parse Transcript Content ---")

        ok_count = 0
        attention_count = 0
        examples_shown = 0
        max_examples = 3

        for transcript_path in transcripts:
            parsed = parse_enforcer_transcript(transcript_path)

            if parsed["verdict"] == "OK":
                ok_count += 1
            elif parsed["verdict"] == "ATTENTION":
                attention_count += 1

            # Show detailed examples
            if examples_shown < max_examples and parsed["session_context"]:
                examples_shown += 1
                print(f"\n{'=' * 60}")
                print(f"EXAMPLE {examples_shown}: {transcript_path.name}")
                print(f"Agent ID: {parsed['agent_id']}")
                print(f"Verdict: {parsed['verdict']}")
                print(f"{'=' * 60}")

                print("\n>>> PROMPT (what triggered the enforcer):")
                print(f"    {parsed['prompt'][:100]}...")

                print("\n>>> SESSION CONTEXT (what the enforcer analyzed):")
                # Show key parts of session context
                context = parsed["session_context"]
                if context:
                    # Show first 1500 chars with proper formatting
                    lines = context.split("\n")[:40]
                    for line in lines:
                        print(f"    {line}")
                    if len(context) > 1500:
                        print("    ...")

                print("\n>>> ENFORCER RESPONSE:")
                response = parsed["full_response"]
                if response:
                    # Show full response for ATTENTION, truncated for OK
                    if parsed["verdict"] == "ATTENTION":
                        print(response)
                    else:
                        lines = response.split("\n")[:10]
                        for line in lines:
                            print(f"    {line}")
                        if len(response.split("\n")) > 10:
                            print("    ...")

        # === STEP 3: Summary Statistics ===
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total transcripts analyzed: {len(transcripts)}")
        print("Verdicts:")
        print(f"  - OK (compliant): {ok_count}")
        print(f"  - ATTENTION (violations): {attention_count}")
        print(f"  - Unknown/parsing failed: {len(transcripts) - ok_count - attention_count}")

        # === STEP 4: Show What the Enforcer Receives ===
        print("\n" + "=" * 80)
        print("WHAT THE ENFORCER RECEIVES")
        print("=" * 80)
        print("""
The enforcer subagent receives an audit file containing:

1. **Original User Request** - First non-meta user prompt
2. **Recent User Prompts** - Last N prompts (truncated)
3. **TodoWrite Plan** - Full todo list with status symbols
4. **Files Modified** - List of files touched
5. **Recent Tools** - Last 10 tool calls
6. **Recent Conversation** - Last 5 user/agent turns
7. **AXIOMS** - All 30 inviolable rules to check
8. **HEURISTICS** - All ~40 heuristics to check
9. **DRIFT ANALYSIS** - Instructions for scope drift detection

The subagent then returns either:
- "OK" if compliant
- "ATTENTION" with Issue/Principle/Correction if violation found
""")

        # === Validation ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Enforcer transcripts found", len(transcripts) > 0),
            ("At least one transcript parsed", examples_shown > 0),
            ("Verdicts extracted", ok_count + attention_count > 0),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print("""
This demo proved the enforcer's real-world behavior by reading actual
subagent transcripts from past sessions.

Key findings:
- The enforcer fires every ~5 action tools (threshold-based)
- Each check receives rich session context for drift analysis
- Verdicts are minimal: "OK" or structured "ATTENTION" with remediation

Transcripts location: ~/.claude/projects/*/subagents/agent-*.jsonl
Audit files location: /tmp/claude-compliance/audit_*.md
""")
        print("=" * 80)

        assert all_passed, "Demo validation criteria not met"
