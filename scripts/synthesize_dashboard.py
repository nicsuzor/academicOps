#!/usr/bin/env python3
"""Synthesize dashboard data using LLM.

Reads multiple data sources and uses Claude to generate a synthesis
that helps the user understand what to focus on next.

Usage:
    uv run python scripts/synthesize_dashboard.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import subprocess


def get_data_dir() -> Path:
    """Get data directory from ACA_DATA env var."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("ERROR: ACA_DATA environment variable not set", file=sys.stderr)
        sys.exit(1)
    return Path(aca_data)


def load_daily_log(data_dir: Path) -> tuple[dict, str]:
    """Load today's daily log and extract key info.

    Returns:
        Tuple of (result dict, raw content string for reuse)
    """
    today = datetime.now().strftime("%Y%m%d")
    daily_path = data_dir / "sessions" / f"{today}-daily.md"

    result = {
        "primary_focus": None,
        "accomplishments": [],
        "blockers": [],
    }

    if not daily_path.exists():
        return result, ""

    content = daily_path.read_text(encoding="utf-8")

    # Extract PRIMARY section
    primary_match = re.search(r"## PRIMARY[:\s]+(.+?)(?=\n##|\Z)", content, re.DOTALL)
    if primary_match:
        primary_section = primary_match.group(1).strip()
        # Get first line as title
        lines = primary_section.split("\n")
        if lines:
            result["primary_focus"] = lines[0].strip().lstrip("#").strip()

    # Extract accomplishments (checked items)
    accomplishments = re.findall(r"- \[x\] (.+)", content, re.IGNORECASE)
    result["accomplishments"] = accomplishments[:10]  # Limit to 10

    # Extract blockers
    blocker_match = re.search(r"## BLOCKERS?\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if blocker_match:
        blockers = re.findall(r"- (.+)", blocker_match.group(1))
        result["blockers"] = blockers[:5]

    return result, content


def load_session_summaries(daily_content: str) -> dict:
    """Parse Session Log table from daily.md content.

    Args:
        daily_content: Raw content of the daily.md file

    Returns:
        Dict with:
            - total: count of sessions
            - by_project: dict of project -> count
            - summaries: list of {session_id, project, summary}
    """
    result: dict = {
        "total": 0,
        "by_project": {},
        "summaries": [],
    }

    if not daily_content:
        return result

    # Find the Session Log section and its table
    session_log_match = re.search(
        r"## Session Log\s*\n\s*\|.*?\|\s*\n\s*\|[-|\s]+\|\s*\n(.*?)(?=\n##|\Z)",
        daily_content,
        re.DOTALL,
    )

    if not session_log_match:
        return result

    table_body = session_log_match.group(1)

    # Parse each row: | session_id | project | summary |
    row_pattern = re.compile(r"\|\s*([a-f0-9]+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|")

    for match in row_pattern.finditer(table_body):
        session_id = match.group(1)
        project = match.group(2)
        summary = match.group(3).strip()

        result["summaries"].append({
            "session_id": session_id,
            "project": project,
            "summary": summary,
        })

        # Count by project
        result["by_project"][project] = result["by_project"].get(project, 0) + 1

    result["total"] = len(result["summaries"])

    return result


def load_task_index(data_dir: Path) -> dict:
    """Load task index and extract priority tasks."""
    index_path = data_dir / "tasks" / "index.json"

    result = {
        "p0_tasks": [],
        "p1_tasks": [],
        "waiting_tasks": [],
        "total_tasks": 0,
    }

    if not index_path.exists():
        return result

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    result["total_tasks"] = index.get("total_tasks", 0)

    for task in index.get("tasks", []):
        # Skip archived tasks
        if task.get("status") == "archived":
            continue

        priority = task.get("priority")
        status = task.get("status")

        task_summary = {
            "title": task.get("title", "")[:60],
            "project": task.get("project", "uncategorized"),
            "subtasks_done": task.get("subtasks_done", 0),
            "subtasks_total": task.get("subtasks_total", 0),
        }

        if status == "waiting":
            result["waiting_tasks"].append(task_summary)
        elif priority == 0:
            result["p0_tasks"].append(task_summary)
        elif priority == 1:
            result["p1_tasks"].append(task_summary)

    # Limit results
    result["p0_tasks"] = result["p0_tasks"][:6]
    result["p1_tasks"] = result["p1_tasks"][:4]
    result["waiting_tasks"] = result["waiting_tasks"][:4]

    return result


def fetch_cloudflare_prompts() -> list[dict]:
    """Fetch recent prompts from Cloudflare R2."""
    api_key = os.environ.get("PROMPT_LOG_API_KEY")
    if not api_key:
        return []

    try:
        response = httpx.get(
            "https://prompt-logs.nicsuzor.workers.dev/read",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        prompts = response.json()  # Returns list directly

        # Parse JSON content from each prompt (same as dashboard)
        result = []
        for p in prompts[:10]:
            try:
                content = p.get("content", "")
                if content.startswith("{"):
                    data = json.loads(content)
                    result.append({
                        "prompt": data.get("prompt", "")[:100],
                        "project": data.get("project", ""),
                        "hostname": data.get("hostname", ""),
                        "timestamp": p.get("timestamp", ""),
                    })
                else:
                    # Plain text prompt (legacy)
                    result.append({
                        "prompt": content[:100],
                        "project": "",
                        "hostname": "unknown",
                        "timestamp": p.get("timestamp", ""),
                    })
            except (json.JSONDecodeError, AttributeError):
                continue
        return result
    except Exception as e:
        print(f"WARNING: Could not fetch Cloudflare prompts: {e}", file=sys.stderr)
        return []


def get_hostname() -> str:
    """Get current machine hostname."""
    import socket
    return socket.gethostname()


SYNTHESIS_PROMPT = """You are a focus coach helping someone with ADHD regain context after a break.

INPUT DATA:
- STATED FOCUS: {primary_focus}
- ACCOMPLISHMENTS TODAY ({accomplishment_count}): {accomplishments}
- P0 TASKS (urgent): {p0_tasks}
- P1 TASKS (high priority): {p1_tasks}
- WAITING ON: {waiting_tasks}
- RECENT ACTIVITY (last prompts): {recent_prompts}
- CURRENT MACHINE: {hostname}
- SESSION ACTIVITY: {session_count} sessions today across projects: {session_projects}
- RECENT SESSIONS: {recent_sessions}

Analyze this data and output a JSON object with these fields:

{{
  "accomplishments": {{
    "count": <number of items done>,
    "summary": "<1-sentence summary of what was accomplished>",
    "highlight": "<the most significant accomplishment>"
  }},
  "alignment": {{
    "status": "<one of: on_track, drifted, blocked>",
    "note": "<1-sentence explaining alignment between activity and priorities>"
  }},
  "next_action": {{
    "task": "<specific task title to do next>",
    "reason": "<why this task - consider cognitive load, momentum, urgency>",
    "project": "<project slug>"
  }},
  "context": {{
    "last_machine": "<machine name from recent activity>",
    "last_project": "<project from recent activity>",
    "recent_threads": ["<topic 1>", "<topic 2>"]
  }},
  "waiting_on": [
    {{"task": "<task title>", "blocker": "<what's blocking it>"}}
  ],
  "suggestion": "<optional tactical suggestion, e.g. 'batch related tasks'>"
}}

RULES:
- Pick ONE next_action from P0 tasks if any exist, otherwise P1
- If multiple P0 tasks relate to same project, suggest batching in suggestion field
- alignment.status: "on_track" if recent activity matches priorities, "drifted" if working on non-priority items, "blocked" if waiting tasks are blocking progress
- Keep all text fields concise (under 80 chars each)
- reason should consider: cognitive load (review vs create), momentum (continue vs switch), dependencies
- Output ONLY valid JSON, no other text"""


def call_claude_headless(prompt: str) -> dict | None:
    """Call Claude via headless mode (claude -p)."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"ERROR: Claude headless failed: {result.stderr}", file=sys.stderr)
            return None

        content = result.stdout.strip()

        # Try to parse JSON directly
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            print(f"WARNING: Could not parse JSON from response: {content[:200]}", file=sys.stderr)
            return None

    except subprocess.TimeoutExpired:
        print("ERROR: Claude headless timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("ERROR: 'claude' command not found - is Claude Code installed?", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Claude headless call failed: {e}", file=sys.stderr)
        return None


def write_synthesis_to_daily(synthesis: dict, daily_path: Path) -> bool:
    """Write Focus section to daily.md for lo-fi dashboard viewing.

    Inserts Focus section immediately after YAML frontmatter for visibility.

    Args:
        synthesis: Dict with keys: accomplishments, alignment, next_action, suggestion, generated
        daily_path: Path to daily.md file

    Returns:
        True if written successfully, False if daily.md doesn't exist or write failed
    """
    if not daily_path.exists():
        return False

    try:
        content = daily_path.read_text(encoding="utf-8")

        # Remove existing ## Focus (Synthesized) section
        content = re.sub(
            r"\n*##\s*Focus\s*\(Synthesized\)\s*\n.*?(?=\n##\s|\Z)",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove legacy ## Synthesis section (backward compat)
        content = re.sub(
            r"\n*##\s*Synthesis\s*\n.*?(?=\n##\s|\Z)",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove standalone ## Accomplishments section (now summarized in Focus)
        content = re.sub(
            r"\n*##\s*Accomplishments\s*\n.*?(?=\n##\s|\Z)",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Build Focus section
        acc = synthesis.get("accomplishments", {})
        align = synthesis.get("alignment", {})
        next_act = synthesis.get("next_action", {})
        suggestion = synthesis.get("suggestion", "")

        focus_md = f"""## Focus (Synthesized)

**Next Action**: {next_act.get('task', 'Not set')} [{next_act.get('project', 'unknown')}]
**Why**: {next_act.get('reason', 'N/A')}
**Alignment**: {align.get('status', 'unknown')} - {align.get('note', 'N/A')}
**Today** ({acc.get('count', 0)}): {acc.get('summary', 'None recorded')}
"""
        if suggestion:
            focus_md += f"""
> {suggestion}
"""

        focus_md += """
---
"""

        # Find end of YAML frontmatter and insert Focus section after it
        # YAML frontmatter starts and ends with ---
        frontmatter_match = re.match(r"^---\n.*?\n---\n?", content, re.DOTALL)
        if frontmatter_match:
            frontmatter_end = frontmatter_match.end()
            # Insert Focus section after frontmatter
            content = (
                content[:frontmatter_end].rstrip()
                + "\n\n"
                + focus_md
                + content[frontmatter_end:].lstrip()
            )
        else:
            # No frontmatter - insert at beginning
            content = focus_md + "\n" + content.lstrip()

        daily_path.write_text(content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"WARNING: Could not write synthesis to daily.md: {e}", file=sys.stderr)
        return False


def main() -> None:
    """Main entry point."""
    data_dir = get_data_dir()

    # Load all data sources
    print("Loading daily log...")
    daily_log, daily_content = load_daily_log(data_dir)

    print("Loading session summaries...")
    session_summaries = load_session_summaries(daily_content)

    print("Loading task index...")
    task_index = load_task_index(data_dir)

    print("Fetching Cloudflare prompts...")
    cloudflare_prompts = fetch_cloudflare_prompts()

    hostname = get_hostname()

    # Format data for prompt
    accomplishments_str = "; ".join(daily_log["accomplishments"][:5]) if daily_log["accomplishments"] else "None recorded"
    p0_str = "; ".join([f"{t['title']} (#{t['project']})" for t in task_index["p0_tasks"]]) if task_index["p0_tasks"] else "None"
    p1_str = "; ".join([f"{t['title']} (#{t['project']})" for t in task_index["p1_tasks"]]) if task_index["p1_tasks"] else "None"
    waiting_str = "; ".join([f"{t['title']} (#{t['project']})" for t in task_index["waiting_tasks"]]) if task_index["waiting_tasks"] else "None"

    prompts_str = "; ".join([f"[{p['project']}@{p['hostname']}] {p['prompt']}" for p in cloudflare_prompts[:5]]) if cloudflare_prompts else "No recent activity"

    # Format session data for prompt
    session_projects_str = ", ".join([f"{proj}: {count}" for proj, count in session_summaries["by_project"].items()]) if session_summaries["by_project"] else "None"
    recent_sessions_str = "; ".join([f"[{s['project']}] {s['summary'][:80]}" for s in session_summaries["summaries"][:5]]) if session_summaries["summaries"] else "No sessions"

    # Build prompt
    prompt = SYNTHESIS_PROMPT.format(
        primary_focus=daily_log["primary_focus"] or "Not set",
        accomplishment_count=len(daily_log["accomplishments"]),
        accomplishments=accomplishments_str,
        p0_tasks=p0_str,
        p1_tasks=p1_str,
        waiting_tasks=waiting_str,
        recent_prompts=prompts_str,
        hostname=hostname,
        session_count=session_summaries["total"],
        session_projects=session_projects_str,
        recent_sessions=recent_sessions_str,
    )

    print("Calling Claude API for synthesis...")
    synthesis = call_claude_headless(prompt)

    if not synthesis:
        print("ERROR: Failed to generate synthesis", file=sys.stderr)
        sys.exit(1)

    # Add metadata
    synthesis["generated"] = datetime.now(UTC).isoformat()
    synthesis["data_sources"] = {
        "daily_log": bool(daily_log["accomplishments"]) or bool(daily_log["primary_focus"]),
        "task_index": task_index["total_tasks"] > 0,
        "cloudflare": len(cloudflare_prompts) > 0,
        "session_log": session_summaries["total"] > 0,
    }

    # Add session data to output
    synthesis["sessions"] = {
        "total": session_summaries["total"],
        "by_project": session_summaries["by_project"],
        "recent": [
            {"project": s["project"], "summary": s["summary"]}
            for s in session_summaries["summaries"][:5]
        ],
    }

    # Write output
    output_dir = data_dir / "dashboard"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "synthesis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(synthesis, f, indent=2, ensure_ascii=False)

    print(f"Wrote synthesis to {output_path}")

    # Also write to daily.md for lo-fi viewing
    today = datetime.now().strftime("%Y%m%d")
    daily_path = data_dir / "sessions" / f"{today}-daily.md"
    if write_synthesis_to_daily(synthesis, daily_path):
        print(f"Wrote synthesis to {daily_path}")

    # Print summary
    print("\n=== SYNTHESIS ===")
    print(f"Accomplishments: {synthesis.get('accomplishments', {}).get('summary', 'N/A')}")
    print(f"Alignment: {synthesis.get('alignment', {}).get('status', 'N/A')} - {synthesis.get('alignment', {}).get('note', '')}")
    print(f"Next action: {synthesis.get('next_action', {}).get('task', 'N/A')}")
    print(f"Reason: {synthesis.get('next_action', {}).get('reason', 'N/A')}")


if __name__ == "__main__":
    main()
