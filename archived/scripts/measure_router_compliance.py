#!/usr/bin/env python3
"""
Measure prompt router compliance rate.

Analyzes session transcripts to determine how often agents comply with
skill invocation suggestions from the prompt router hook.

Usage:
    uv run python scripts/measure_router_compliance.py [--date DATE] [--verbose]

Output:
    - Total router suggestions
    - Compliance rate (agent invoked Skill tool first)
    - Accuracy rate (agent invoked SUGGESTED skill)
    - Per-session breakdown
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def find_hook_logs(date_str: str | None = None) -> list[Path]:
    """Find hook log files, optionally filtered by date."""
    hook_dir = Path.home() / ".cache" / "aops" / "sessions"
    if not hook_dir.exists():
        return []

    pattern = f"{date_str}-*-hooks.jsonl" if date_str else "*-hooks.jsonl"
    return sorted(hook_dir.glob(pattern))


def find_transcript(hook_log: Path) -> Path | None:
    """Find the transcript file corresponding to a hook log."""
    # Hook log format: DATE-SESSIONID-hooks.jsonl
    # We need to find the transcript_path from inside the hook log
    try:
        with hook_log.open() as f:
            for line in f:
                entry = json.loads(line)
                if "transcript_path" in entry:
                    transcript = Path(entry["transcript_path"])
                    if transcript.exists():
                        return transcript
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def extract_router_events(hook_log: Path) -> list[dict]:
    """Extract PromptRouter events from hook log."""
    events = []
    try:
        with hook_log.open() as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("hook_event") == "PromptRouter":
                    hook_output = entry.get("hookSpecificOutput", {})
                    skills = hook_output.get("skillsMatched", [])
                    if skills:  # Only count if skills were suggested
                        events.append(
                            {
                                "timestamp": entry.get("logged_at"),
                                "prompt": entry.get("prompt", "")[:100],
                                "skills_suggested": skills,
                            }
                        )
    except (json.JSONDecodeError, KeyError):
        pass
    return events


def extract_first_tool_after_prompt(
    transcript: Path, prompt_snippet: str
) -> dict | None:
    """Find the first tool_use after a user prompt in transcript."""
    try:
        with transcript.open() as f:
            found_prompt = False
            for line in f:
                entry = json.loads(line)

                # Look for user message containing our prompt
                if entry.get("type") == "user" and not found_prompt:
                    message = entry.get("message", {})
                    content = message.get("content", "")
                    if isinstance(content, str) and prompt_snippet[:50] in content:
                        found_prompt = True
                        continue

                # After finding prompt, look for first assistant tool_use
                if found_prompt and entry.get("type") == "assistant":
                    message = entry.get("message", {})
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if (
                                isinstance(block, dict)
                                and block.get("type") == "tool_use"
                            ):
                                return {
                                    "tool_name": block.get("name"),
                                    "tool_input": block.get("input", {}),
                                }
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def analyze_compliance(router_events: list[dict], transcript: Path | None) -> dict:
    """Analyze compliance for router events against transcript."""
    results = {
        "total_suggestions": len(router_events),
        "skill_invoked_first": 0,
        "correct_skill_invoked": 0,
        "other_tool_first": 0,
        "no_tool_found": 0,
        "details": [],
    }

    if not transcript:
        results["no_tool_found"] = len(router_events)
        return results

    for event in router_events:
        prompt = event["prompt"]
        skills_suggested = event["skills_suggested"]

        first_tool = extract_first_tool_after_prompt(transcript, prompt)

        detail = {
            "prompt": prompt,
            "skills_suggested": skills_suggested,
            "first_tool": first_tool.get("tool_name") if first_tool else None,
            "compliant": False,
            "correct_skill": False,
        }

        if not first_tool:
            results["no_tool_found"] += 1
        elif first_tool["tool_name"] == "Skill":
            results["skill_invoked_first"] += 1
            detail["compliant"] = True

            # Check if the invoked skill matches suggestion
            skill_input = first_tool.get("tool_input", {})
            invoked_skill = skill_input.get("skill", "")
            if invoked_skill in skills_suggested:
                results["correct_skill_invoked"] += 1
                detail["correct_skill"] = True
            detail["invoked_skill"] = invoked_skill
        else:
            results["other_tool_first"] += 1
            detail["first_tool"] = first_tool["tool_name"]

        results["details"].append(detail)

    return results


def main():
    parser = argparse.ArgumentParser(description="Measure prompt router compliance")
    parser.add_argument("--date", help="Date to analyze (YYYY-MM-DD), default: today")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show per-event details"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Analyze all available dates"
    )
    args = parser.parse_args()

    if args.all:
        date_str = None
    else:
        date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    hook_logs = find_hook_logs(date_str)

    if not hook_logs:
        print(f"No hook logs found for {'all dates' if args.all else date_str}")
        return

    print(f"Analyzing {len(hook_logs)} hook log(s)...")
    print("=" * 60)

    totals = defaultdict(int)
    all_details = []

    for hook_log in hook_logs:
        router_events = extract_router_events(hook_log)
        if not router_events:
            continue

        transcript = find_transcript(hook_log)
        results = analyze_compliance(router_events, transcript)

        # Accumulate totals
        totals["total_suggestions"] += results["total_suggestions"]
        totals["skill_invoked_first"] += results["skill_invoked_first"]
        totals["correct_skill_invoked"] += results["correct_skill_invoked"]
        totals["other_tool_first"] += results["other_tool_first"]
        totals["no_tool_found"] += results["no_tool_found"]
        all_details.extend(results["details"])

        if args.verbose:
            print(f"\n{hook_log.name}:")
            print(f"  Suggestions: {results['total_suggestions']}")
            print(f"  Skill first: {results['skill_invoked_first']}")
            print(f"  Other first: {results['other_tool_first']}")

    # Print summary
    print("\n" + "=" * 60)
    print("COMPLIANCE SUMMARY")
    print("=" * 60)

    total = totals["total_suggestions"]
    if total == 0:
        print("No router suggestions found.")
        return

    compliance_rate = (totals["skill_invoked_first"] / total) * 100
    accuracy_rate = (
        (totals["correct_skill_invoked"] / totals["skill_invoked_first"] * 100)
        if totals["skill_invoked_first"] > 0
        else 0
    )

    print(f"Total router suggestions:     {total}")
    print(
        f"Agent invoked Skill first:    {totals['skill_invoked_first']} ({compliance_rate:.1f}%)"
    )
    print(
        f"  - Correct skill invoked:    {totals['correct_skill_invoked']} ({accuracy_rate:.1f}% of compliant)"
    )
    print(
        f"Agent used other tool first:  {totals['other_tool_first']} ({totals['other_tool_first']/total*100:.1f}%)"
    )
    print(f"No tool found after prompt:   {totals['no_tool_found']}")

    print("\n" + "-" * 60)
    print("BASELINE METRICS")
    print("-" * 60)
    print(f"Compliance Rate: {compliance_rate:.1f}%")
    print(f"Accuracy Rate:   {accuracy_rate:.1f}% (when compliant)")

    if args.verbose and all_details:
        print("\n" + "-" * 60)
        print("DETAILED BREAKDOWN")
        print("-" * 60)
        for i, detail in enumerate(all_details, 1):
            status = "✓" if detail["compliant"] else "✗"
            correct = " (correct)" if detail.get("correct_skill") else ""
            print(f"{i}. {status} Suggested: {detail['skills_suggested']}")
            print(f"      First tool: {detail['first_tool']}{correct}")
            print(f"      Prompt: {detail['prompt'][:60]}...")


if __name__ == "__main__":
    main()
