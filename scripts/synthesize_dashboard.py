#!/usr/bin/env python3
"""Aggregate per-session insights into synthesis.json for the dashboard.

Reads today's session summary files from $AOPS_SESSIONS/summaries/
and produces $ACA_DATA/dashboard/synthesis.json — a pure aggregation
with no LLM calls.

Token metrics are NOT included here; the dashboard aggregates those
directly from per-session files at render time.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib.paths import get_data_root, get_summaries_dir  # noqa: E402


def load_today_sessions(summaries_dir: Path, date_prefix: str) -> list[dict]:
    """Load all session summary JSONs matching today's date prefix."""
    sessions = []
    for f in sorted(summaries_dir.glob(f"{date_prefix}*.json")):
        try:
            with open(f) as fh:
                sessions.append(json.load(fh))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skipping malformed file {f.name}: {e}", file=sys.stderr)
    return sessions


def _is_placeholder(text: str) -> bool:
    """Return True if text is a template placeholder with no real content."""
    if not text:
        return True
    t = text.strip().lower()
    # Literal bracket placeholders from Framework Reflection templates
    if "[summary]" in t or "[link]" in t or "[description]" in t:
        return True
    # Generic "Successfully completed:" with nothing meaningful after
    if t.startswith("successfully completed:") and len(t) < 60:
        return True
    return False


def synthesize(sessions: list[dict], today: str) -> dict:
    """Build synthesis.json from a list of per-session dicts."""
    now = datetime.now(UTC)

    # --- sessions summary ---
    project_counts: Counter[str] = Counter()
    for s in sessions:
        proj = s.get("project") or "unknown"
        project_counts[proj] += 1

    recent = [
        {
            "session_id": s.get("session_id", ""),
            "project": s.get("project", "unknown"),
            "summary": s.get("summary"),
        }
        for s in sessions[-5:]
    ]

    # --- narrative ---
    narrative = []
    for s in sessions:
        summary = s.get("summary")
        if summary and not _is_placeholder(summary):
            proj = s.get("project") or "unknown"
            narrative.append(f"[{proj}] {summary}")
    narrative = narrative[:10]

    # --- accomplishments ---
    all_accomplishments: list[dict] = []
    unique_items: list[str] = []
    for s in sessions:
        proj = s.get("project") or "unknown"
        for item in s.get("accomplishments") or []:
            if _is_placeholder(item):
                continue
            all_accomplishments.append({"text": item, "project": proj})
            if item not in unique_items:
                unique_items.append(item)

    acc_summary = "; ".join(unique_items[:3]) if unique_items else ""

    # --- alignment ---
    outcomes = [s.get("outcome") for s in sessions if s.get("outcome") is not None]
    if not outcomes:
        alignment_status = "blocked"
        alignment_note = "No session outcomes recorded"
    else:
        success_count = sum(1 for o in outcomes if o == "success")
        total = len(outcomes)
        if success_count == total:
            alignment_status = "on_track"
        else:
            alignment_status = "drifted"
        alignment_note = f"{success_count}/{total} sessions successful"

    # --- context ---
    unique_projects = list(dict.fromkeys(s.get("project") or "unknown" for s in sessions))

    # --- waiting_on (from friction_points) ---
    waiting_on: list[dict] = []
    for s in sessions:
        for fp in s.get("friction_points") or []:
            if fp and len(waiting_on) < 5:
                waiting_on.append({"task": fp})

    # --- skill_insights ---
    followed_count = 0
    total_reflections = 0
    for s in sessions:
        for ref in s.get("framework_reflections") or []:
            val = ref.get("followed")
            if val is not None:
                total_reflections += 1
                if val:
                    followed_count += 1

    compliance_rate = (followed_count / total_reflections) if total_reflections > 0 else None

    unique_friction: list[str] = []
    for s in sessions:
        for fp in s.get("friction_points") or []:
            if fp and fp not in unique_friction:
                unique_friction.append(fp)
    top_context_gaps = unique_friction[:5]

    # --- suggestion ---
    friction_by_project: Counter[str] = Counter()
    for s in sessions:
        proj = s.get("project") or "unknown"
        friction_by_project[proj] += len(s.get("friction_points") or [])
    most_friction = friction_by_project.most_common(1)
    if most_friction and most_friction[0][1] > 0:
        proj, count = most_friction[0]
        suggestion = f"Focus on {proj} — {count} friction point{'s' if count != 1 else ''}"
    else:
        suggestion = None

    return {
        "generated": now.isoformat(),
        "date": today,
        "sessions": {
            "total": len(sessions),
            "by_project": dict(project_counts),
            "recent": recent,
        },
        "narrative": narrative,
        "accomplishments": {
            "count": len(all_accomplishments),
            "summary": acc_summary,
            "items": all_accomplishments,
        },
        "alignment": {
            "status": alignment_status,
            "note": alignment_note,
        },
        "context": {
            "recent_threads": unique_projects,
        },
        "waiting_on": waiting_on,
        "skill_insights": {
            "compliance_rate": compliance_rate,
            "top_context_gaps": top_context_gaps,
        },
        "suggestion": suggestion,
    }


def main() -> None:
    today = datetime.now().strftime("%Y%m%d")

    summaries_dir = get_summaries_dir()
    sessions = load_today_sessions(summaries_dir, today)
    print(f"Found {len(sessions)} session file(s) for {today}", file=sys.stderr)

    synthesis = synthesize(sessions, today)

    # Write atomically
    out_dir = get_data_root() / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "synthesis.json"

    fd, tmp_path = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(synthesis, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, out_path)
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
