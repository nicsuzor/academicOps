#!/usr/bin/env python3
"""Polecat post-mortem diagnostics — structured exit metadata.

Eliminates the ~15-tool-call manual forensics path documented in GitHub #487
(read polecat output → check worktree → parse JSONL → hunt transcript →
correlate session IDs → count compliance markers).

The flow is:

1. On exit, ``polecat run`` calls :func:`build_exit_metadata` to derive a
   structured summary of *why* the run ended, then :func:`write_exit_metadata`
   appends it as a ``{"type": "exit_metadata", ...}`` line to the same
   per-task JSONL that ``save_worker_transcript`` writes
   (``$POLECAT_HOME/polecats/<task-id>.jsonl``).
2. ``polecat analyze <task-id>`` reads it back via :func:`read_exit_metadata`
   and renders the human summary with :func:`format_exit_summary`.
3. ``polecat list`` renders a one-line exit reason with
   :func:`format_exit_oneline`.

Every function here is best-effort: observability must never crash a run, so
the writer swallows errors and the readers degrade to ``None``.
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Exit reasons, in priority order. compliance_blocked wins over max_turns
# because a compliance block can also exhaust the turn budget, and the block
# is the more actionable root cause for a supervisor.
EXIT_REASONS = ("compliance_blocked", "max_turns", "error", "success")

# Fallback used only when the enforcer templates are unavailable (e.g. running
# outside the repo). Real values are loaded from the templates below so that
# detection stays in sync when template wording changes (A5: one source).
_COMPLIANCE_BLOCK_MARKERS_FALLBACK = (
    "✕ Compliance check required",
    "Compliance check OVERDUE",
)


def _load_compliance_block_markers() -> tuple[str, ...]:
    """Derive compliance-block detection substrings from enforcer template files.

    Reads the same templates the enforcer hook renders from so that detection
    automatically stays in sync when template wording changes (A5: one source).
    Falls back to _COMPLIANCE_BLOCK_MARKERS_FALLBACK when templates are missing.
    """
    try:
        repo_root = Path(__file__).parent.parent
        templates_dir = repo_root / "aops-core" / "hooks" / "templates"
        markers: list[str] = []

        # enforcer-policy-message.md: "✕ Compliance check required ({ops}...)"
        msg_path = templates_dir / "enforcer-policy-message.md"
        if msg_path.is_file():
            for line in msg_path.read_text().splitlines():
                if line.startswith("✕") and "Compliance check required" in line:
                    # Strip template variable "{...}" and any trailing "(" or space
                    stable = re.sub(r"\s*\{[^}]*\}.*", "", line).rstrip(" (")
                    if stable:
                        markers.append(stable)
                    break

        # enforcer-policy-context.md: "**ERROR:** Compliance check OVERDUE. ..."
        ctx_path = templates_dir / "enforcer-policy-context.md"
        if ctx_path.is_file():
            for line in ctx_path.read_text().splitlines():
                if "Compliance check OVERDUE" in line:
                    # Strip markdown bold, take phrase up to first ".", find OVERDUE substring
                    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
                    phrase = plain.split(".")[0].strip()
                    idx = phrase.find("Compliance check OVERDUE")
                    if idx >= 0:
                        markers.append(phrase[idx:])
                    break

        return tuple(markers) if len(markers) == 2 else _COMPLIANCE_BLOCK_MARKERS_FALLBACK
    except Exception:
        return _COMPLIANCE_BLOCK_MARKERS_FALLBACK


# Substrings the enforcer gate emits when it BLOCKS a tool call (overdue past
# the compliance threshold). Distinct from the non-blocking countdown warning
# ("◇ N turns until compliance check") which must NOT be treated as a block.
# Derived from aops-core/hooks/templates/ at import time (A5: one source).
_COMPLIANCE_BLOCK_MARKERS = _load_compliance_block_markers()

# Non-blocking countdown warning: "◇ {remaining} turns until compliance check."
_COUNTDOWN_RE = re.compile(r"◇\s*(\d+)\s*turns until compliance check")


def _git_remote_url(worktree_path: Path | None) -> str | None:
    """Return the ``origin`` remote URL of the worktree, or None."""
    if not worktree_path or not Path(worktree_path).exists():
        return None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _count_commits_ahead(worktree_path: Path | None) -> int | None:
    """Return the number of commits in the worktree ahead of origin/main.

    Returns None when the worktree is gone or git cannot answer (e.g. no
    origin/main ref). Best-effort — used only for the post-mortem summary.
    """
    if not worktree_path or not Path(worktree_path).exists():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def detect_compliance_block(stdout: str | None, stderr: str | None) -> tuple[bool, int]:
    """Detect whether the enforcer compliance gate blocked the run.

    Returns ``(compliance_blocked, countdown_at_exit)``:
    - ``compliance_blocked`` is True when the enforcer's OVERDUE deny message
      appears in the combined output (the agent was prevented from using tools
      until it ran a compliance check).
    - ``countdown_at_exit`` is the last observed "turns until compliance check"
      value. It is forced to 0 when blocked (overdue == 0 remaining).
    """
    combined = (stdout or "") + (stderr or "")
    blocked = any(marker in combined for marker in _COMPLIANCE_BLOCK_MARKERS)

    countdown = 0
    for match in _COUNTDOWN_RE.finditer(combined):
        countdown = int(match.group(1))
    if blocked:
        countdown = 0
    return blocked, countdown


def count_turns_used(
    real_transcript: Path | None,
    stdout: str | None,
    stderr: str | None,
    turns_max: int | str | None,
) -> int | None:
    """Estimate how many turns the agent used before exiting.

    Preference order:
    1. Count ``type == "assistant"`` entries in the real Claude session
       transcript (each assistant response is ~one turn).
    2. If the agent hit the budget ("Reached max turns"), report ``turns_max``.
    3. Otherwise None — the headless ``claude -p`` text output does not carry a
       reliable turn count.
    """
    if real_transcript and Path(real_transcript).exists():
        try:
            count = 0
            for line in Path(real_transcript).read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and entry.get("type") == "assistant":
                    count += 1
            if count:
                return count
        except OSError:
            pass

    combined = (stdout or "") + (stderr or "")
    if "Reached max turns" in combined:
        if turns_max is None:
            return None
        try:
            return int(turns_max)
        except ValueError:
            return None
    return None


def build_exit_metadata(
    *,
    task,
    exit_code: int,
    stdout: str | None,
    stderr: str | None,
    worktree_path: Path | None,
    real_transcript: Path | None,
    turns_max: int | str | None,
    budget_exhausted: bool,
) -> dict:
    """Derive the structured exit-metadata block for a finished polecat run.

    Pure (apart from read-only git queries against the worktree) so it can be
    unit-tested without dispatching a container. See module docstring and #487
    for the field catalogue.
    """
    compliance_blocked, countdown = detect_compliance_block(stdout, stderr)
    turns_used = count_turns_used(real_transcript, stdout, stderr, turns_max)

    if compliance_blocked:
        exit_reason = "compliance_blocked"
    elif budget_exhausted:
        exit_reason = "max_turns"
    elif exit_code == 0:
        exit_reason = "success"
    else:
        exit_reason = "error"

    pr_url = getattr(task, "pr_url", None)
    if not pr_url:
        pr_number = getattr(task, "pr", None)
        pr_url = f"#{pr_number}" if pr_number else None

    if turns_max is None:
        turns_max_val: int | str | None = None
    else:
        try:
            turns_max_val = int(turns_max)
        except ValueError:
            turns_max_val = turns_max

    return {
        "type": "exit_metadata",
        "exit_reason": exit_reason,
        "repo_cloned": getattr(task, "project", None),
        "repo_url": _git_remote_url(worktree_path),
        "commits_count": _count_commits_ahead(worktree_path),
        "pr_url": pr_url,
        "turns_used": turns_used,
        "turns_max": turns_max_val,
        "compliance_blocked": compliance_blocked,
        "compliance_countdown_at_exit": countdown,
        "transcript_path": str(real_transcript) if real_transcript else None,
    }


def _transcripts_dir(home_dir: Path | None) -> Path:
    """Resolve the directory holding per-task polecat JSONL files."""
    try:
        from lib.paths import get_polecat_transcripts_dir

        return get_polecat_transcripts_dir()
    except ImportError:
        base = home_dir or Path.home() / ".polecat"
        return Path(base) / "transcripts"


def write_exit_metadata(task_id: str, metadata: dict, home_dir: Path | None) -> Path | None:
    """Append an exit-metadata line to ``<task-id>.jsonl``. Never raises.

    Returns the path written, or None on failure (observability must never
    crash the run).
    """
    try:
        transcript_dir = _transcripts_dir(home_dir)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "task_id": task_id,
            "session_type": "polecat",
            **metadata,
        }
        transcript_file = transcript_dir / f"{task_id}.jsonl"
        with open(transcript_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return transcript_file
    except Exception:
        return None


def read_exit_metadata(task_id: str, home_dir: Path | None = None) -> dict | None:
    """Return the most recent exit-metadata block for ``task_id``, or None.

    Reads the per-task JSONL (checking legacy locations via
    ``lib.paths.find_polecat_transcript`` when available) and returns the last
    line whose ``type`` is ``exit_metadata``.
    """
    try:
        from lib.paths import find_polecat_transcript

        jsonl_path = find_polecat_transcript(task_id)
    except ImportError:
        jsonl_path = _transcripts_dir(home_dir) / f"{task_id}.jsonl"

    if not jsonl_path or not Path(jsonl_path).is_file():
        return None

    try:
        content = Path(jsonl_path).read_text()
    except OSError:
        return None

    for line in reversed(content.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("type") == "exit_metadata":
            return entry
    return None


_REASON_BLURB = {
    "compliance_blocked": "compliance_blocked",
    "max_turns": "max turns reached",
    "error": "error",
    "success": "success",
}


def format_exit_oneline(metadata: dict | None) -> str:
    """One-line exit reason for ``polecat list``.

    Example: ``exited: compliance_blocked (11/30 turns, 0 commits)``.
    Returns an empty string when no exit metadata is available.
    """
    if not metadata:
        return ""
    reason = metadata.get("exit_reason", "?")
    blurb = _REASON_BLURB.get(reason, reason)
    bits = [blurb]
    turns_used = metadata.get("turns_used")
    turns_max = metadata.get("turns_max")
    if turns_used is not None and turns_max is not None:
        bits.append(f"{turns_used}/{turns_max} turns")
    commits = metadata.get("commits_count")
    if commits is not None:
        bits.append(f"{commits} commit{'s' if commits != 1 else ''}")
    pr_url = metadata.get("pr_url")
    if pr_url:
        bits.append(f"PR {pr_url}")
    return (
        f"exited: {bits[0]} (" + ", ".join(bits[1:]) + ")"
        if len(bits) > 1
        else f"exited: {bits[0]}"
    )


def format_exit_summary(task, metadata: dict) -> str:
    """Render the structured post-mortem summary (the #487 format).

    ``task`` may be None (worktree/task already cleaned up) — the title line
    degrades gracefully.
    """
    reason = metadata.get("exit_reason", "?")
    turns_used = metadata.get("turns_used")
    turns_max = metadata.get("turns_max")
    countdown = metadata.get("compliance_countdown_at_exit")
    commits = metadata.get("commits_count")
    pr_url = metadata.get("pr_url")
    repo = metadata.get("repo_cloned")
    repo_url = metadata.get("repo_url")
    transcript = metadata.get("transcript_path")

    title = getattr(task, "title", None) if task is not None else None
    task_id = getattr(task, "id", None) if task is not None else None
    status = "FAILED" if reason in ("compliance_blocked", "max_turns", "error") else "SUCCESS"

    # Exit-reason line, with the block-specific countdown qualifier.
    reason_line = reason
    if reason == "compliance_blocked":
        rem = countdown if countdown is not None else 0
        reason_line = f"compliance_blocked ({rem} turns remaining)"
    elif reason == "max_turns":
        reason_line = "max_turns (turn budget exhausted)"

    if turns_used is not None and turns_max is not None:
        qualifier = " before block" if reason == "compliance_blocked" else " used"
        turns_line = f"{turns_used}/{turns_max}{qualifier}"
    elif turns_max is not None:
        turns_line = f"?/{turns_max} (turns_used unknown — see transcript)"
    else:
        turns_line = "unknown"

    repo_line = repo or "(unknown)"
    if repo_url:
        repo_line = f"{repo_line} ({repo_url})" if repo else repo_url

    lines = [
        "📮 POST-MORTEM",
        f"   Task:        {task_id or metadata.get('task_id', '(unknown)')}"
        + (f" ({title})" if title else ""),
        f"   Status:      {status}",
        f"   Exit reason: {reason_line}",
        f"   Repo:        {repo_line}",
        f"   Turns:       {turns_line}",
        f"   Commits:     {commits if commits is not None else 'unknown'}",
        f"   PR:          {pr_url or 'none'}",
        f"   Transcript:  {transcript or '(not captured)'}",
    ]
    return "\n".join(lines)
