#!/usr/bin/env python3
"""Assemble a threaded user-prompt timeline across sessions.

Used as a "catch-up" route: reconstruct what Nic was juggling over a period.
The timeline separates Nic's genuine interactive instructions from
automated/worker sessions (polecat/crew/gemini workers, subagents,
stop-hook-feedback runs): interactive prompts are threaded in full in the main
body, while automated sessions are collapsed to a one-line abstract each in an
appendix. Prompt-level noise (stop-hook boilerplate, system-injected reminders,
bare slash commands, single-word acks) is dropped even inside interactive
sessions. See aops-62abcf9d.
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add aops-core to path
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_naming import (
    generate_base_name,
    infer_provider_from_path,
    is_automated_session,
)
from lib.session_reader import find_sessions
from lib.transcript_parser import (
    SessionProcessor,
    extract_timeline_events,
    resolve_task_title,
)

# Short acknowledgements that are not substantive instructions.
_ACK_WORDS = frozenset(
    {
        "y",
        "n",
        "yes",
        "no",
        "ok",
        "okay",
        "k",
        "kk",
        "go",
        "yep",
        "yeah",
        "yup",
        "sure",
        "continue",
        "cont",
        "ty",
        "thanks",
        "thx",
        "thank you",
        "proceed",
        "done",
        "next",
        "stop",
        "good",
        "great",
        "nice",
        "perfect",
    }
)

# Substrings that mark a "user" turn as system-injected, not Nic typing.
_SYSTEM_MARKERS = (
    "<system-reminder",
    "[Request interrupted",
    "This session is being continued",
    "Compliance report ready",
    "Compliance check required",
    "Your task has already been claimed",
    "Caveat: The messages below",
    "<command-name>",
    "Base directory for this skill",
)


def is_noise_prompt(text: str | None) -> bool:
    """True if a "user" turn is system-injected noise, not Nic typing.

    Dropped: empty/whitespace, system-injected reminders, bare slash-commands
    (no substantive args), and single-word acknowledgements. A slash-command
    *with* a real instruction (e.g. ``/q fix the parser``) is kept — that is
    Nic typing. (The stop-hook honesty/handover reminder is no longer filtered
    by a substring match here — spec mem-438429c5 §5.6; the structural fix is
    deferred to aops-884e4214.)
    """
    if not text:
        return True
    s = text.strip()
    if not s:
        return True
    low = s.lower()

    # NOTE: the brittle `"before you stop" && "be honest"` substring filter
    # that used to live here was removed (spec mem-438429c5 §5.6 — a
    # deterministic rig doing a semantic job; it broke the instant the honesty
    # reminder was reworded). No replacement sentinel is added (rejected scope);
    # the proper structural transcript-rendering fix is deferred (follow-up
    # aops-884e4214). Stop-hook honesty/handover reminders that reach this path
    # are no longer specially dropped here.

    # System-injected context (reminders, interrupts, continuation banners).
    for marker in _SYSTEM_MARKERS:
        if marker.lower() in low[: len(marker) + 80]:
            return True

    # Bare slash-command with no substantive argument (e.g. "/daily", "/pull").
    if s.startswith("/") and "\n" not in s:
        if re.fullmatch(r"/[\w:.-]+\s*", s):
            return True

    # Single-word / single-char acknowledgements.
    if len(s) <= 2:
        return True
    if low in _ACK_WORDS:
        return True

    return False


def parse_period(period_str: str) -> datetime:
    period_str = period_str.strip().lower()
    now = datetime.now().astimezone()

    if period_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_str == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check for Xd, Xh
    if period_str.endswith("d") and period_str[:-1].isdigit():
        return now - timedelta(days=int(period_str[:-1]))
    if period_str.endswith("h") and period_str[:-1].isdigit():
        return now - timedelta(hours=int(period_str[:-1]))

    # Check for YYYY-MM-DD
    try:
        dt = datetime.strptime(period_str, "%Y-%m-%d")
        return dt.astimezone()
    except ValueError:
        pass

    print(f"Warning: Unknown period format '{period_str}'. Defaulting to today.", file=sys.stderr)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _task_id_from_path(session_path) -> str | None:
    """Extract the task_id from a ``.../polecats/<task_id>/...`` worker path.

    Polecat worker sessions are stored under ``polecats/<task_id>/`` but the raw
    session's ParsedSession often carries no ``task_id`` (it isn't in the
    transcript body). The path segment is the reliable source for the collapsed
    abstract's id column.
    """
    parts = Path(session_path).parts
    if "polecats" in parts:
        idx = parts.index("polecats")
        if len(parts) > idx + 1:
            return parts[idx + 1]
    return None


def _pr_short(pr_url: str | None) -> str | None:
    """Render a PR url as a compact ``owner/repo#NN`` (or the raw url)."""
    if not pr_url:
        return None
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if m:
        return f"{m.group(1)}/{m.group(2)}#{m.group(3)}"
    return pr_url


def build_threads(sessions) -> list[dict]:
    """Parse sessions into thread dicts, classifying each interactive/automated."""
    processor = SessionProcessor()
    threads: list[dict] = []

    for session in sessions:
        try:
            summary, entries, agent_entries = processor.parse_session_file(session.path)
            if not entries:
                continue

            turns = processor.group_entries_into_turns(entries, agent_entries)
            timeline_events = extract_timeline_events(turns, session.session_id)

            prompts = [e for e in timeline_events if e.get("type") == "user_prompt"]
            if not prompts:
                continue

            # True start time from the first timestamped entry.
            session_start = session.last_modified
            for entry in entries:
                if entry.timestamp:
                    session_start = entry.timestamp
                    break

            provider = summary.provider or infer_provider_from_path(session.path)
            repo = summary.repo or session.project
            sid = session.session_id
            slug = summary.slug or processor.generate_session_slug(entries)

            # PR url, if the session opened one.
            pr_url = None
            for ev in timeline_events:
                if ev.get("type") == "pr_create" and ev.get("pr_url"):
                    pr_url = ev["pr_url"]
                    break

            # Polecat worker sessions carry their task_id in the path, not always
            # on the summary — recover it so the collapsed abstract is useful.
            task_id = summary.task_id or _task_id_from_path(session.path)

            is_auto, reason = is_automated_session(
                session_path=session.path,
                task_id=summary.task_id,
                slug=slug,
                provider=provider,
                client=getattr(summary, "client", None),
                surface=getattr(summary, "surface", None),
                crew=summary.crew,
                subagent_type=getattr(summary, "subagent_type", None),
                parent_session=getattr(summary, "parent_session", None),
                hostname=getattr(summary, "hostname", None),
            )

            filename_base = generate_base_name(
                session_id=sid,
                timestamp=session_start,
                slug=slug,
                repo=repo,
                provider=provider,
                task_id=summary.task_id,
            )
            rotation_dir = session_start.astimezone().strftime("%Y-%m")
            transcript_url = f"$AOPS_SESSIONS/transcripts/{rotation_dir}/{filename_base}-full.md"

            threads.append(
                {
                    "start_time": session_start,
                    "session_id": sid,
                    "repo": repo,
                    "model": provider or "unknown",
                    "slug": slug,
                    "url": transcript_url,
                    "prompts": prompts,
                    "task_id": task_id,
                    "task_title": getattr(summary, "task_title", None),
                    "pr_url": pr_url,
                    "is_automated": is_auto,
                    "reason": reason,
                }
            )
        except Exception as e:
            print(f"Error processing {session.path}: {e}", file=sys.stderr)

    threads.sort(key=lambda x: x["start_time"])
    return threads


def abstract_title(thread: dict) -> str:
    """Resolve a human title for a collapsed automated session.

    task_title (from frontmatter) > PKB lookup by task_id > task_id literal >
    PR short ref > slug.
    """
    if thread.get("task_title"):
        return thread["task_title"]
    task_id = thread.get("task_id")
    if task_id:
        return resolve_task_title(task_id) or task_id
    pr = _pr_short(thread.get("pr_url"))
    if pr:
        return pr
    return thread.get("slug") or "(no title)"


def abstract_id(thread: dict) -> str:
    """The ``<task_id or pr>`` column for the collapsed one-liner."""
    return thread.get("task_id") or _pr_short(thread.get("pr_url")) or "-"


def render(threads: list[dict], period: str) -> list[str]:
    """Render the markdown timeline: interactive body + collapsed appendix."""
    interactive = [t for t in threads if not t["is_automated"]]
    automated = [t for t in threads if t["is_automated"]]

    # Filter prompt-level noise inside interactive sessions; drop sessions that
    # end up with nothing Nic actually typed.
    kept_interactive: list[dict] = []
    interactive_prompt_count = 0
    for t in interactive:
        clean = [p for p in t["prompts"] if not is_noise_prompt(p.get("description"))]
        if not clean:
            continue
        t = {**t, "prompts": clean}
        interactive_prompt_count += len(clean)
        kept_interactive.append(t)

    out: list[str] = []
    out.append(f"# User Prompt Timeline: Since {period}\n")
    out.append(
        f"> {len(kept_interactive)} interactive sessions "
        f"({interactive_prompt_count} prompts) in the main body; "
        f"{len(automated)} automated/worker sessions collapsed below.\n"
    )

    for thread in kept_interactive:
        ts_str = thread["start_time"].strftime("%Y-%m-%d %H:%M:%S")
        out.append(
            f"## {ts_str} | {thread['repo']} | {thread['model']} | "
            f"[{thread['session_id']}]({thread['url']})"
        )
        out.append(f"**Context**: {thread['slug']}")
        out.append("")
        for i, p in enumerate(thread["prompts"], 1):
            p_ts = ""
            if p.get("timestamp"):
                dt = datetime.fromisoformat(p["timestamp"]).astimezone()
                p_ts = dt.strftime("%H:%M:%S")
            out.append(f"### Prompt {i} ({p_ts})")
            for line in p["description"].strip().splitlines():
                out.append(f"> {line}")
            out.append("")
        out.append("---\n")

    # Collapsed appendix — one line per automated session.
    if automated:
        out.append("## Automated / worker sessions (collapsed)\n")
        out.append("_One line per automated/worker session — visible but not dumped in full._\n")
        for thread in automated:
            hhmm = thread["start_time"].strftime("%H:%M")
            out.append(
                f"- `{hhmm}` | {thread['repo']} | {abstract_id(thread)} | {abstract_title(thread)}"
            )
        out.append("")

    return out


def main():
    parser = argparse.ArgumentParser(description="Assemble threaded user-prompt timeline")
    parser.add_argument(
        "--period", "-p", default="today", help="Period (e.g. today, 1d, 7d, 2026-05-29)"
    )
    args = parser.parse_args()

    cutoff = parse_period(args.period)
    sessions = find_sessions(since=cutoff)

    if not sessions:
        print(f"No sessions found since {cutoff.isoformat()}")
        return

    threads = build_threads(sessions)
    for line in render(threads, args.period):
        print(line)


if __name__ == "__main__":
    main()
