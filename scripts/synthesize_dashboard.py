#!/usr/bin/env python3
"""Synthesize dashboard data from session insights.

Reads pre-mined insights from session-insights skill (via Gemini)
and aggregates into dashboard format. NO API calls.

Usage:
    uv run python scripts/synthesize_dashboard.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx


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
        lines = primary_section.split("\n")
        if lines:
            result["primary_focus"] = lines[0].strip().lstrip("#").strip()

    # Extract accomplishments (checked items)
    accomplishments = re.findall(r"- \[x\] (.+)", content, re.IGNORECASE)
    result["accomplishments"] = accomplishments[:10]

    # Extract blockers
    blocker_match = re.search(r"## BLOCKERS?\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if blocker_match:
        blockers = re.findall(r"- (.+)", blocker_match.group(1))
        result["blockers"] = blockers[:5]

    return result, content


def extract_narrative_signals(daily_content: str) -> dict:
    """Extract Session Context and Abandoned Todos from daily note."""
    result = {
        "session_context": [],
        "abandoned_todos": [],
    }

    if not daily_content:
        return result

    context_match = re.search(
        r"## Session Context\s*\n(.*?)(?=\n##|\Z)",
        daily_content,
        re.DOTALL,
    )
    if context_match:
        for line in context_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                result["session_context"].append(line[2:])

    abandoned_match = re.search(
        r"## Abandoned Todos\s*\n(.*?)(?=\n##|\Z)",
        daily_content,
        re.DOTALL,
    )
    if abandoned_match:
        for line in abandoned_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("- [ ]"):
                result["abandoned_todos"].append(line[6:].strip())

    return result


def load_session_summaries(daily_content: str) -> dict:
    """Parse Session Log table from daily.md content."""
    result: dict = {
        "total": 0,
        "by_project": {},
        "summaries": [],
    }

    if not daily_content:
        return result

    session_log_match = re.search(
        r"## Session Log\s*\n\s*\|.*?\|\s*\n\s*\|[-|\s]+\|\s*\n(.*?)(?=\n##|\Z)",
        daily_content,
        re.DOTALL,
    )

    if not session_log_match:
        return result

    table_body = session_log_match.group(1)
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

    result["p0_tasks"] = result["p0_tasks"][:6]
    result["p1_tasks"] = result["p1_tasks"][:4]
    result["waiting_tasks"] = result["waiting_tasks"][:4]

    return result


def load_insights(data_dir: Path) -> dict | None:
    """Load session insights from insights.json (created by session-insights skill)."""
    insights_path = data_dir / "dashboard" / "insights.json"

    if not insights_path.exists():
        return None

    try:
        with open(insights_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: Could not load insights.json: {e}", file=sys.stderr)
        return None


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
        prompts = response.json()

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


def build_synthesis(
    daily_log: dict,
    task_index: dict,
    session_summaries: dict,
    narrative_signals: dict,
    insights: dict | None,
    cloudflare_prompts: list[dict],
) -> dict:
    """Build synthesis from pre-mined data. No LLM call.

    Uses insights from Gemini mining (via session-insights skill)
    plus task/session data to create dashboard summary.
    """
    # Build narrative from session context
    narrative = []
    if narrative_signals["session_context"]:
        narrative.append(f"Started: {narrative_signals['session_context'][0][:60]}")
    if len(narrative_signals["session_context"]) > 1:
        narrative.append(f"Also worked on: {narrative_signals['session_context'][1][:50]}")
    if narrative_signals["abandoned_todos"]:
        narrative.append(f"Left unfinished: {narrative_signals['abandoned_todos'][0][:50]}")

    # Accomplishments summary
    acc_count = len(daily_log["accomplishments"])
    acc_summary = ""
    if acc_count > 0:
        acc_summary = "; ".join(daily_log["accomplishments"][:3])
        if len(acc_summary) > 80:
            acc_summary = acc_summary[:77] + "..."

    # Pick next action from P0 tasks
    next_action = {}
    if task_index["p0_tasks"]:
        top_task = task_index["p0_tasks"][0]
        next_action = {
            "task": top_task["title"],
            "reason": "Highest priority task",
            "project": top_task["project"],
        }
    elif task_index["p1_tasks"]:
        top_task = task_index["p1_tasks"][0]
        next_action = {
            "task": top_task["title"],
            "reason": "Next priority task",
            "project": top_task["project"],
        }

    # Alignment status
    alignment = {"status": "on_track", "note": ""}
    if daily_log["blockers"]:
        alignment = {"status": "blocked", "note": daily_log["blockers"][0][:60]}
    elif not daily_log["accomplishments"] and session_summaries["total"] > 3:
        alignment = {"status": "drifted", "note": "Many sessions but no recorded accomplishments"}

    # Context from recent activity
    context = {
        "last_machine": get_hostname(),
        "last_project": "",
        "recent_threads": [],
    }
    if cloudflare_prompts:
        context["last_project"] = cloudflare_prompts[0].get("project", "")
        context["recent_threads"] = [p["prompt"][:30] for p in cloudflare_prompts[:2]]

    # Waiting tasks
    waiting_on = []
    for task in task_index["waiting_tasks"][:3]:
        waiting_on.append({"task": task["title"], "blocker": "waiting on external"})

    # Include insights from Gemini mining if available
    skill_insights = {}
    if insights:
        summary = insights.get("summary", {})
        skill_insights = {
            "compliance_rate": summary.get("compliance_rate"),
            "skills_suggested": summary.get("skills_suggested", []),
            "skills_invoked": summary.get("skills_invoked", []),
            "top_context_gaps": summary.get("top_context_gaps", []),
            "corrections_count": len(insights.get("corrections", [])),
            "failures_count": len(insights.get("failures", [])),
            "successes_count": len(insights.get("successes", [])),
        }

    return {
        "narrative": narrative if narrative else ["No session context recorded"],
        "accomplishments": {
            "count": acc_count,
            "summary": acc_summary or "None recorded",
            "highlight": daily_log["accomplishments"][0] if daily_log["accomplishments"] else None,
        },
        "alignment": alignment,
        "next_action": next_action,
        "context": context,
        "waiting_on": waiting_on,
        "suggestion": None,
        "skill_insights": skill_insights,
    }


def write_synthesis_to_daily(synthesis: dict, daily_path: Path) -> bool:
    """Write Focus section to daily.md for lo-fi dashboard viewing."""
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

        # Build Focus section
        acc = synthesis.get("accomplishments", {})
        align = synthesis.get("alignment", {})
        next_act = synthesis.get("next_action", {})
        skill_ins = synthesis.get("skill_insights", {})

        focus_md = f"""## Focus (Synthesized)

**Next Action**: {next_act.get('task', 'Not set')} [{next_act.get('project', 'unknown')}]
**Why**: {next_act.get('reason', 'N/A')}
**Alignment**: {align.get('status', 'unknown')} - {align.get('note', 'N/A')}
**Today** ({acc.get('count', 0)}): {acc.get('summary', 'None recorded')}
"""
        # Add skill insights if available
        if skill_ins and skill_ins.get("compliance_rate"):
            rate = skill_ins["compliance_rate"]
            focus_md += f"**Skill Compliance**: {rate:.0%}\n"
            if skill_ins.get("top_context_gaps"):
                focus_md += f"**Context Gaps**: {', '.join(skill_ins['top_context_gaps'][:2])}\n"

        focus_md += "\n---\n"

        # Insert after YAML frontmatter
        frontmatter_match = re.match(r"^---\n.*?\n---\n?", content, re.DOTALL)
        if frontmatter_match:
            frontmatter_end = frontmatter_match.end()
            content = (
                content[:frontmatter_end].rstrip()
                + "\n\n"
                + focus_md
                + content[frontmatter_end:].lstrip()
            )
        else:
            content = focus_md + "\n" + content.lstrip()

        daily_path.write_text(content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"WARNING: Could not write synthesis to daily.md: {e}", file=sys.stderr)
        return False


def main() -> None:
    """Main entry point."""
    data_dir = get_data_dir()

    print("Loading daily log...")
    daily_log, daily_content = load_daily_log(data_dir)

    print("Extracting narrative signals...")
    narrative_signals = extract_narrative_signals(daily_content)

    print("Loading session summaries...")
    session_summaries = load_session_summaries(daily_content)

    print("Loading task index...")
    task_index = load_task_index(data_dir)

    print("Loading session insights (from Gemini mining)...")
    insights = load_insights(data_dir)
    if insights:
        print(f"  Found insights from {insights.get('date', 'unknown date')}")
    else:
        print("  No insights.json found - run session-insights skill first")

    print("Fetching Cloudflare prompts...")
    cloudflare_prompts = fetch_cloudflare_prompts()

    # Build synthesis from pre-mined data (NO API CALL)
    print("Building synthesis from pre-mined data...")
    synthesis = build_synthesis(
        daily_log=daily_log,
        task_index=task_index,
        session_summaries=session_summaries,
        narrative_signals=narrative_signals,
        insights=insights,
        cloudflare_prompts=cloudflare_prompts,
    )

    # Add metadata
    synthesis["generated"] = datetime.now(UTC).isoformat()
    synthesis["data_sources"] = {
        "daily_log": bool(daily_log["accomplishments"]) or bool(daily_log["primary_focus"]),
        "task_index": task_index["total_tasks"] > 0,
        "cloudflare": len(cloudflare_prompts) > 0,
        "session_log": session_summaries["total"] > 0,
        "insights": insights is not None,
    }

    # Add session data
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

    # Write to daily.md
    today = datetime.now().strftime("%Y%m%d")
    daily_path = data_dir / "sessions" / f"{today}-daily.md"
    if write_synthesis_to_daily(synthesis, daily_path):
        print(f"Wrote synthesis to {daily_path}")

    # Print summary
    print("\n=== SYNTHESIS ===")

    narrative = synthesis.get("narrative", [])
    if narrative:
        print("\n📖 NARRATIVE:")
        for bullet in narrative:
            print(f"  • {bullet}")

    print(f"\nAccomplishments: {synthesis.get('accomplishments', {}).get('summary', 'N/A')}")
    print(f"Alignment: {synthesis.get('alignment', {}).get('status', 'N/A')} - {synthesis.get('alignment', {}).get('note', '')}")
    print(f"Next action: {synthesis.get('next_action', {}).get('task', 'N/A')}")

    # Print skill insights if available
    skill_ins = synthesis.get("skill_insights", {})
    if skill_ins and skill_ins.get("compliance_rate"):
        print(f"\n📊 SKILL INSIGHTS:")
        print(f"  Compliance: {skill_ins['compliance_rate']:.0%}")
        if skill_ins.get("corrections_count"):
            print(f"  Corrections: {skill_ins['corrections_count']}")
        if skill_ins.get("top_context_gaps"):
            print(f"  Context gaps: {', '.join(skill_ins['top_context_gaps'][:2])}")


if __name__ == "__main__":
    main()
