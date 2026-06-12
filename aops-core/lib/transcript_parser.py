"""
Transcript Parser - Core logic for parsing session files.

This module provides the core data structures and processing logic for
parsing Claude Code and Gemini session files into structured objects.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any

import lib.session_naming as session_naming
from lib.secret_redaction import redact_secrets

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Worktree basename patterns:
#   - pure hex run of 6+ chars (e.g. "79257c", "008c345f")
#   - <one or more lowercase-word segments>-<6+ hex> (e.g.
#     "gallant-albattani-79257c", "modest-jemison-1202c6", "aops-008c345f")
#   - <label>_<20+ base62 chars>: CC/polecat worktrees use an underscore
#     separator before a base62 KSUID-style task ID (e.g.
#     "bridge-cse_01BpGd4zGnUQAfoDCNwHPxjx")
_HEX_ONLY_RE = re.compile(r"^[0-9a-f]{6,}$")
_HEX_SUFFIX_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*-[0-9a-f]{6,}$")
_POLECAT_WT_RE = re.compile(r"^.+_[A-Za-z0-9]{20,}$")

# Path segments that are NEVER themselves a project — used when walking up
# from a worktree basename to find the parent repo.
_GENERIC_CONTAINERS = {
    "src",
    "code",
    "projects",
    "repos",
    "work",
    "dev",
    "home",
    "opt",
    "users",
    "tmp",
    "var",
    "mnt",
    "media",
    ".aops",
    ".polecat",
    ".claude",
    ".git",
    "polecat",
    "polecats",
    "crew",
    "worktrees",
    "trees",
    "sessions",
    "checkouts",
}


def _get_session_id_from_path(session_path: Path) -> str | None:
    """Extract 8-char session ID from a session filename.

    Handles Claude (UUID.jsonl), Gemini (session-YYYY-MM-DDThh-mm-<8hex>.jsonl),
    and polecat naming (YYYYMMDD-HHMM-<8hex>-...-session.json).
    """
    name = session_path.stem
    if session_path.is_dir():
        return name[:8] if name else None
    # Gemini: session-2026-05-19T11-54-e015b808
    if name.startswith("session-") and "-" in name:
        return name.split("-")[-1][:8]
    # Polecat: 20260523-2029-ba992e1b-workspace-gemini-...
    parts = name.split("-")
    if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
        return parts[2][:8]
    # Claude: UUID
    return name[:8] if name else None


def _is_worktree_basename(name: str) -> bool:
    """True if `name` looks like a worktree directory's basename.

    Matches Claude Code's `<adjective>-<noun>-<hex>` pattern, polecat's
    `<project>-<8hex>` pattern, and bare hex strings.
    """
    if not name:
        return False
    return bool(
        _HEX_ONLY_RE.match(name) or _HEX_SUFFIX_RE.match(name) or _POLECAT_WT_RE.match(name)
    )


def _resolve_worktree_via_git(path_str: str) -> str | None:
    """Best-effort resolve a worktree path to its main repo basename.

    Uses `git -C <path> rev-parse --git-common-dir` which (for a worktree)
    points at `<main-repo>/.git` — the parent of which is the main repo.
    Returns None if the path isn't a git checkout, git isn't available, or
    anything else goes wrong. Pure best-effort; CI without filesystem
    access falls back to path-walking.
    """
    try:
        result = subprocess.run(
            ["git", "-C", path_str, "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    common_dir = result.stdout.strip()
    if not common_dir:
        return None
    # `--git-common-dir` may return a relative path; resolve relative to the
    # working directory we asked about.
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (Path(path_str) / common_path).resolve()
    # The main repo is the parent of the .git directory.
    if common_path.name == ".git":
        main_repo = common_path.parent
    else:
        main_repo = common_path
    name = main_repo.name
    if not name or _is_worktree_basename(name) or name.lower() in _GENERIC_CONTAINERS:
        return None
    return name


def _walk_up_for_project(parts: tuple[str, ...]) -> str | None:
    """Walk up `parts` (path components) and return the first ancestor that
    is neither generic (`worktrees`, `.claude`, `src`, ...) nor a
    worktree-style basename. Returns None if no such ancestor exists.
    """
    # Skip the last part (the worktree itself) — start from its parent.
    for segment in reversed(parts[:-1]):
        if not segment or segment == "/":
            continue
        if segment.lower() in _GENERIC_CONTAINERS:
            continue
        if _is_worktree_basename(segment):
            continue
        return segment
    return None


def _is_gemini_chat_jsonl(file_path: Path) -> bool:
    """Detect Gemini CLI chat-jsonl files.

    Gemini CLI's interactive chat history (post-2026) is written as JSON Lines
    where each line is a message of the form
    ``{"role": "user"|"model", "parts": [...]}``. The parts contain ``text``,
    ``functionCall``, or ``functionResponse`` entries — the Gemini API
    conversation schema. This is distinct from Claude's JSONL format and from
    the older Gemini ``.json`` chat dump (`messages: [...]`).

    Heuristics (any sufficient):
      1. Filename matches ``chats/session-*.jsonl`` anywhere in the path.
         Polecat bind-mounts the container's ``.gemini/tmp/workspace/chats/``
         to ``<sessions_repo>/polecats/<task>/<project>/chats/`` on the host,
         so files arriving via that path don't have ``.gemini/tmp/`` in them.
      2. First few non-empty lines include a ``{role, parts}`` dict or a
         ``{type: "user"|"gemini", content}`` message-style dict. Gemini CLI
         writes a metadata header (``{sessionId, projectHash, startTime, ...}``)
         and ``$set`` updates as the leading lines, so we must skip past them
         before declaring the file Claude-formatted.
    """
    if file_path.suffix.lower() != ".jsonl":
        return False

    name = file_path.name
    if "chats" in file_path.parts and name.startswith("session-"):
        return True

    try:
        with open(file_path, encoding="utf-8") as f:
            scanned = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    return False
                if not isinstance(obj, dict):
                    return False
                # Gemini CLI bookkeeping lines: metadata header + $set updates.
                # Skip past them — the file may have several before the first
                # conversational entry.
                if "sessionId" in obj and "role" not in obj and "type" not in obj:
                    scanned += 1
                    if scanned > 20:
                        return False
                    continue
                if "$set" in obj and len(obj) == 1:
                    scanned += 1
                    if scanned > 20:
                        return False
                    continue
                if obj.get("role") in ("user", "model") and isinstance(obj.get("parts"), list):
                    return True
                if (
                    obj.get("type") in ("user", "gemini")
                    and "content" in obj
                    and "message" not in obj
                ):
                    return True
                return False
    except OSError:
        return False
    return False


def normalize_gemini_project(dir_name: str) -> str:
    """Normalize a Gemini tmp directory name to a project name.

    Handles four patterns:
    - SHA-256 hash (64 hex chars): returns "gemini-{first 8 chars}"
    - Named with numeric suffix (e.g. "aops-1"): strips suffix
    - Named with 8-char hex suffix (e.g. "aops-6fbe707a"): strips suffix
    - Plain named (e.g. "buttermilk"): returns as-is
    """
    if _SHA256_RE.match(dir_name):
        return f"gemini-{dir_name[:8]}"
    # Strip numeric suffix (-1, -2, ...) or 8-char hex suffix (-6fbe707a)
    return re.sub(r"(-\d+|-[0-9a-f]{8})$", "", dir_name)


def extract_working_dir_from_entries(entries: list[Entry]) -> str | None:
    """Extract working directory from session entries.

    Looks for working directory information in:
    1. The structured ``cwd`` field on CC 2.1+ entries (authoritative)
    2. System messages with <env>Working directory: /path</env> format
    3. Early user messages that contain environment context

    Args:
        entries: List of Entry objects from a parsed session

    Returns:
        Working directory path string, or None if not found
    """
    # CC 2.1+: cwd is a first-class field on every user/tool-result entry.
    # Check this before falling back to text-scanning so worktree sessions
    # (where no "Working directory:" line appears in the transcript text) are
    # resolved correctly. No slice limit — this is a simple field access and
    # hook file entries (which have no timestamp) sort to the front after the
    # hook-merge pass, pushing real cwd-bearing entries beyond position 20.
    for entry in entries:
        if entry.cwd:
            return entry.cwd

    # Pattern to match <env>Working directory: /path</env>
    env_pattern = re.compile(r"<env>.*?Working directory:\s*([^\n<]+)", re.DOTALL | re.IGNORECASE)

    # Also match standalone "Working directory: /path" lines
    standalone_pattern = re.compile(r"Working directory:\s*(/[^\n]+)")

    for entry in entries[:20]:  # Only check first 20 entries for efficiency
        # Check message content
        text = ""
        if entry.message:
            content = entry.message.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")

        if not text:
            continue

        # Try env pattern first
        match = env_pattern.search(text)
        if match:
            return match.group(1).strip()

        # Try standalone pattern
        match = standalone_pattern.search(text)
        if match:
            return match.group(1).strip()

    return None


def extract_working_dir_from_content(content: str) -> str | None:
    """Extract working directory from text content.

    Looks for path patterns that suggest working directory, such as:
    - Explicit "Working directory: /path" statements
    - File path references that suggest a project root

    Args:
        content: Text content to search

    Returns:
        Working directory path string, or None if not found
    """
    # Match Working directory lines
    wd_match = re.search(r"Working directory:\s*(/[^\n<]+)", content, re.IGNORECASE)
    if wd_match:
        return wd_match.group(1).strip()

    # Match cwd or current directory references
    cwd_match = re.search(r"(?:cwd|current directory):\s*(/[^\n<]+)", content, re.IGNORECASE)
    if cwd_match:
        return cwd_match.group(1).strip()

    return None


def infer_project_from_working_dir(working_dir: str | None) -> str | None:
    """Infer project name from a working directory path.

    Extracts the final meaningful directory name from a path.
    Handles common patterns like:
    - /home/user/src/myproject -> myproject
    - /home/user/projects/client-work -> client-work
    - /opt/user/code -> code
    - /home/user/.polecat/polecat/aops-008c345f -> aops (polecat worktree)
    - /Users/x/.aops/brain/gallant-albattani-79257c -> brain
      (Claude Code worktree: walk up past the hex-suffixed basename)
    - /home/x/src/academicOps/.claude/worktrees/modest-jemison-1202c6 ->
      academicOps (Claude Code worktree under .claude/worktrees/)

    Args:
        working_dir: Full path to working directory

    Returns:
        Project name string, or None if cannot be inferred
    """
    if not working_dir:
        return None

    # Normalize path
    path = Path(working_dir)
    parts = path.parts

    if len(parts) < 2:
        return None

    # Handle polecat worktree paths: $POLECAT_HOME/polecat/{project}-{hash}
    # The project name is before the 8-char hash suffix
    if (".aops" in parts or ".polecat" in parts) and "polecat" in parts:
        project = parts[-1]
        # Polecat worktree format: {project}-{8char-hash}
        # e.g., "aops-008c345f" -> "aops"
        if len(project) > 9 and project[-9] == "-":
            # Check if suffix looks like a hash (alphanumeric)
            suffix = project[-8:]
            if suffix.isalnum():
                return project[:-9]
        return project

    # Get the last non-empty part
    project = parts[-1]

    # Worktree basename detection: hex-only or `<word(s)>-<hex>` suffix.
    # In a worktree the basename is a meaningless slug; the real project is
    # the parent repository. Try git first (authoritative), fall back to
    # walking up the path looking for a non-generic ancestor.
    if _is_worktree_basename(project):
        git_resolved = _resolve_worktree_via_git(working_dir)
        if git_resolved:
            return git_resolved
        walked = _walk_up_for_project(parts)
        if walked:
            return walked
        # No usable ancestor — refuse to return the meaningless hex slug.
        return None

    # Skip generic names and try parent
    if project.lower() in _GENERIC_CONTAINERS and len(parts) > 2:
        project = parts[-2]

    return project if project else None


def decode_claude_project_path(encoded_path: str) -> str | None:
    """Decode a Claude projects directory name to get the working directory.

    Claude Code stores sessions in ~/.claude/projects/{encoded-path}/ where
    the encoded path replaces / with - (e.g., -home-nic-src-myproject).

    Args:
        encoded_path: Encoded path like "-home-nic-src-myproject"

    Returns:
        Decoded path like "/home/nic/src/myproject", or None if invalid
    """
    if not encoded_path or not encoded_path.startswith("-"):
        return None

    # Replace leading - and all subsequent - with /
    decoded = encoded_path.replace("-", "/")
    return decoded


def parse_framework_reflection(text: str) -> dict[str, Any] | None:
    """Parse Framework Reflection section from markdown text.

    Extracts structured fields from the Framework Reflection format:
    - Prompts, Guidance received, Followed, Outcome, Accomplishments,
    - Friction points, Root cause, Proposed changes, Next step

    Accepts multiple heading styles:
    - ``## Framework Reflection`` (spec)
    - ``### Framework Reflection`` or ``#### Framework Reflection`` (heading variants)
    - ``**Framework Reflection**:`` or ``**Framework Reflection:**`` (bold-text drift)
    - ``Framework Reflection:`` preceded by a newline (bare text)

    When the body lacks structured ``**Field**: value`` lines, falls back to
    inferring outcome from keywords and treating bullet points as accomplishments.

    Args:
        text: Markdown text that may contain a Framework Reflection section

    Returns:
        Dict with parsed fields, or None if no reflection found
    """
    # Find the Framework Reflection section — try multiple heading styles in order.
    # Use [^\S\n]* (horizontal whitespace only) to avoid consuming newlines
    # that the body terminator needs to detect next sections.
    #
    # IMPORTANT: Do NOT use \n\n as a section terminator — agents routinely put
    # blank lines between **Field**: value entries, and \n\n would truncate the
    # capture at the first blank line. Instead, terminate at the next heading,
    # horizontal rule (---), or end of text.
    _SECTION_END = r"(?=\n#{1,4}\s|\n---|\Z)"
    patterns = [
        # Pattern 1: Markdown heading (## / ### / ####)
        rf"#{{2,4}}\s*Framework Reflection[^\S\n]*\n(.*?){_SECTION_END}",
        # Pattern 2: Bold-text with body on next line (**Framework Reflection:**\n...)
        rf"(?:^|\n)\*\*Framework Reflection:?\*\*[^\S\n]*:?[^\S\n]*\n(.*?){_SECTION_END}",
        # Pattern 3: Bold-text with inline body (**Framework Reflection**: text...)
        rf"(?:^|\n)\*\*Framework Reflection:?\*\*[^\S\n]*:?[^\S\n]*(.+?){_SECTION_END}",
        # Pattern 4: Bare text (Framework Reflection: ...)
        rf"(?:^|\n)Framework Reflection[^\S\n]*:[^\S\n]*\n?(.*?){_SECTION_END}",
    ]

    reflection_match = None
    for pattern in patterns:
        reflection_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if reflection_match:
            break

    if not reflection_match:
        return None

    reflection_text = reflection_match.group(1)

    # Parse individual fields
    result: dict[str, Any] = {}

    # Field patterns: **Field**: value or **Field** (if not success): value
    field_patterns = [
        (r"\*\*Prompts?\*\*:\s*(.+?)(?=\n\*\*|\Z)", "prompts"),
        (r"\*\*Guidance received\*\*:\s*(.+?)(?=\n\*\*|\Z)", "guidance_received"),
        (r"\*\*Followed\*\*:\s*(.+?)(?=\n\*\*|\Z)", "followed"),
        (r"\*\*Outcome\*\*:\s*(.+?)(?=\n\*\*|\Z)", "outcome"),
        (r"\*\*Accomplishments?\*\*:\s*(.+?)(?=\n\*\*|\Z)", "accomplishments"),
        # Broadened (aops-6a787364): catch in-the-wild bold friction labels —
        # **Friction.**, **Friction (real bug):**, **Friction**:, as well as the
        # canonical **Friction points**:. The label text between the bold markers
        # may carry punctuation/parentheticals, and the colon may sit inside or
        # after the bold span. Without this, off-template friction fell through to
        # _parse_unstructured_reflection and was blanket-dumped into accomplishments.
        (r"\*\*Friction[^*]*\*\*\s*:?\s*(.+?)(?=\n\*\*|\Z)", "friction_points"),
        (
            r"\*\*Root cause\*\*(?:\s*\([^)]*\))?\s*:\s*(.+?)(?=\n\*\*|\Z)",
            "root_cause",
        ),
        (r"\*\*Proposed changes?\*\*:\s*(.+?)(?=\n\*\*|\Z)", "proposed_changes"),
        (r"\*\*Next steps?\*\*:\s*(.+?)(?=\n\*\*|\Z)", "next_step"),
    ]

    for pattern, field_name in field_patterns:
        match = re.search(pattern, reflection_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Parse list fields (accomplishments, friction_points, proposed_changes)
            if field_name in ("accomplishments", "friction_points", "proposed_changes"):
                result[field_name] = _parse_list_field(value)
            else:
                result[field_name] = value

    # If no structured fields found, check for specific formats before fallback

    # Check for Quick Exit format: "Answered user's question: <summary>"
    if not result:
        quick_exit_match = re.search(
            r"Answered user's question:\s*[\"']?(.+?)[\"']?\s*$",
            reflection_text,
            re.IGNORECASE | re.MULTILINE,
        )
        if quick_exit_match:
            result = {
                "outcome": "success",
                "prompts": quick_exit_match.group(1).strip(),
                "quick_exit": True,  # Marker for Q&A-only sessions
            }

    # Check for brief status format: "AOPS status: [done|in progress|interrupted|error]"
    if not result:
        status_match = re.search(
            r"AOPS status:\s*(done|in progress|interrupted|error)",
            reflection_text,
            re.IGNORECASE,
        )
        if status_match:
            status_value = status_match.group(1).lower()
            outcome_map = {
                "done": "success",
                "in progress": "partial",
                "interrupted": "partial",
                "error": "failure",
            }
            result = {
                "outcome": outcome_map.get(status_value, status_value),
                "brief_status": True,  # Marker for brief status format
            }

    # Last resort: unstructured fallback (infer from bullets/keywords)
    if not result:
        result = _parse_unstructured_reflection(reflection_text) or {}

    if not result:
        return None

    # task-5a54f813: enrich the reflection with the supplementary blocks the
    # /dump quality bar requires. These may live inside the reflection body
    # or in the surrounding assistant message; we look in `text` (full
    # message) so blocks placed adjacent to the reflection still get
    # captured. See aops-core/skills/end_session/transcript-metadata-schema.md.
    outputs = parse_output_section(text)
    tasks_worked = parse_tasks_worked_section(text)
    references = parse_identifier_precis_pairs(reflection_text)
    thread_pickup = parse_thread_pickup_section(text)
    quality_warnings = assess_reflection_quality(reflection_text, outputs, tasks_worked, references)
    quality_warnings = quality_warnings + _assess_friction_misroute(result)

    if outputs is not None:
        result["outputs"] = outputs.get("outputs", [])
        result["output_explicit_none"] = outputs.get("explicit_none", False)
        result["output_none_reason"] = outputs.get("none_reason")
    if tasks_worked is not None:
        result["tasks_worked"] = tasks_worked
    if references:
        result["references"] = references
    if quality_warnings:
        result["quality_warnings"] = quality_warnings
    if thread_pickup:
        result["thread_pickup"] = thread_pickup

    return result


def parse_thread_pickup_section(text: str) -> dict[str, str] | None:
    """Parse Thread Pickup section from markdown text.

    Extracts thread pickup instructions as a mapping from thread name to action.

    Args:
        text: Markdown text that may contain a Thread Pickup section

    Returns:
        Dict mapping thread names to instructions, or None if not found
    """
    _SECTION_END = r"(?=\n#{1,6}\s|\n---|\Z)"
    pattern = rf"#{{2,6}} Thread Pickup[^\S\n]*\n(.*?){_SECTION_END}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    pickup_text = match.group(1)
    threads = {}

    for line in pickup_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]\s*(?:\*\*)?(.+?)(?:\*\*)?:\s*(.*)$", line)
        if m:
            threads[m.group(1).strip()] = m.group(2).strip()

    return threads if threads else None


def parse_session_handover(text: str) -> dict[str, Any] | None:
    """Parse Session Handover section from markdown text.

    Extracts structured fields from the new /dump handover format:
    - Session ID, Primary Task, PR, Branch, Issue, Follow-ups, Summary

    Args:
        text: Markdown text that may contain a Session Handover section

    Returns:
        Dict mapped to reflection schema, or None if no handover found
    """
    # Match Session Handover at H2-H6. Agents emit at varying levels in
    # practice (the abridged-transcript renderer wraps each turn in headings,
    # so an agent's "### Session Handover" gets pushed deeper). Trend review
    # 2026-05-08 found 100% of emitted handovers used `##### Session Handover`
    # while this regex only matched `###`, rendering them all parser-invisible.
    _SECTION_END = r"(?=\n#{1,6}\s|\n---|\Z)"
    pattern = rf"#{{2,6}} (?:Session|Emergency) Handover[^\S\n]*\n(.*?){_SECTION_END}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    handover_text = match.group(1)
    raw_fields = {}

    # Extract fields with regex
    field_map = {
        "session_id": r"- \*\*Session ID\*\*: (.*)",
        "task_id": r"- \*\*(?:Primary|Resume) Task\*\*: ([^\s(]+)",
        "pr_url": r"- \*\*PR\*\*: (.*)",
        "branch": r"- \*\*Branch\*\*: (.*)",
        "issue_url": r"- \*\*Issue\*\*: (.*)",
        "next_step": r"- \*\*(?:Follow-ups|Next)\*\*: (.*)",
        "summary": r"- \*\*Summary\*\*: (.*)",
    }

    for key, reg in field_map.items():
        f_match = re.search(reg, handover_text, re.IGNORECASE)
        if f_match:
            val = f_match.group(1).strip()
            if val.lower() != "none":
                raw_fields[key] = val

    if not raw_fields:
        return None

    # Map to reflection schema used by reflection_to_insights()
    reflection = {
        "outcome": "success",  # Default for /dump handover
        "summary": raw_fields.get("summary", ""),
        "accomplishments": [raw_fields.get("summary")] if raw_fields.get("summary") else [],
        "prompts": raw_fields.get("summary"),
        "next_step": raw_fields.get("next_step"),
        "session_id": raw_fields.get("session_id"),
        "task_id": raw_fields.get("task_id"),
        "pr_url": raw_fields.get("pr_url"),
        "branch": raw_fields.get("branch"),
        "handover": True,  # Marker for handover-originated insights
    }

    thread_pickup = parse_thread_pickup_section(text)
    if thread_pickup:
        reflection["thread_pickup"] = thread_pickup

    return reflection


_SECTION_END_RE = r"(?=\n#{1,4}\s|\n---|\Z)"

# Identifier shapes recognised by parse_identifier_precis_pairs.
_IDENTIFIER_PATTERNS = [
    (r"\btask-[0-9a-f]{6,}", "task"),
    (r"\bPR\s*#\d+", "pr"),
    (r"\bissue\s*#\d+", "issue"),
    (r"\b[\w.-]+/[\w.-]+#\d+", "pr_or_issue"),
    (r"\bcommit\s+[0-9a-f]{7,}", "commit"),
]


def parse_output_section(text: str) -> dict[str, Any] | None:
    """Parse a `## Output` (or `## Outputs`) section.

    Distinguishes "no artefact declared" (returns None — caller emits a
    missing-field warning) from "explicit none" (Output: none — <reason>,
    explicit_none=True). Extracts every URL into structured outputs.
    """
    pattern = rf"#{{2,4}}\s*Outputs?[^\S\n]*\n(.*?){_SECTION_END_RE}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        bare = re.search(r"(?:^|\n)Outputs?:\s*none\b[^\n]*", text, re.IGNORECASE)
        if bare:
            reason_match = re.search(r"none\s*[—\-:]\s*(.+)", bare.group(0), re.IGNORECASE)
            return {
                "outputs": [],
                "explicit_none": True,
                "none_reason": reason_match.group(1).strip() if reason_match else None,
            }
        return None

    body = match.group(1).strip()
    none_match = re.match(r"(?:Output:\s*)?none\b\s*[—\-:]?\s*(.*)", body, re.IGNORECASE)
    if none_match and not re.search(r"https?://", body):
        return {
            "outputs": [],
            "explicit_none": True,
            "none_reason": none_match.group(1).strip() or None,
        }

    outputs: list[dict[str, Any]] = []
    for url_match in re.finditer(r"https?://[^\s>)\]]+", body):
        url = url_match.group(0).rstrip(".,;)")
        outputs.append({"kind": _classify_output_url(url), "url": url})

    return {"outputs": outputs, "explicit_none": False, "none_reason": None}


def _classify_output_url(url: str) -> str:
    if "/pull/" in url:
        return "pr"
    if "/issues/" in url:
        return "issue"
    if "/commit/" in url:
        return "commit"
    if "github.com" in url:
        return "github"
    return "doc"


def parse_tasks_worked_section(text: str) -> list[dict[str, Any]] | None:
    """Parse `## Tasks worked` block into [{id, precis, action, action_raw}]."""
    pattern = rf"#{{2,4}}\s*Tasks worked[^\S\n]*\n(.*?){_SECTION_END_RE}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    body = match.group(1)
    items: list[dict[str, Any]] = []
    bullet_re = re.compile(
        r"^[\s]*[-*]\s*"
        r"(?P<id>[\w./#-]+)"
        r"(?:\s*\((?P<precis>[^)]+)\))?"
        r"(?:\s*[—\-:]\s*(?P<action>.+))?$",
        re.MULTILINE,
    )
    for m in bullet_re.finditer(body):
        ident = m.group("id").strip()
        precis = (m.group("precis") or "").strip() or None
        action_raw = (m.group("action") or "").strip() or None
        items.append(
            {
                "id": ident,
                "precis": precis,
                "action": _normalize_action(action_raw) if action_raw else None,
                "action_raw": action_raw,
            }
        )
    return items


# Priority order: most-specific verbs first so "updated, added schema" maps
# to "updated" rather than "created".
_ACTION_KEYWORD_GROUPS = [
    ("completed", ["completed", "complete", "done", "merged", "shipped"]),
    ("cancelled", ["cancelled", "canceled", "closed", "rejected"]),
    ("updated", ["updated", "update", "modified", "edited"]),
    ("created", ["created", "create", "added", "new"]),
    ("referenced", ["referenced", "noted"]),
]


def _normalize_action(action_text: str) -> str:
    lower = action_text.lower()
    for canonical, keywords in _ACTION_KEYWORD_GROUPS:
        for keyword in keywords:
            if re.search(rf"\b{keyword}\b", lower):
                return canonical
    return "referenced"


def parse_identifier_precis_pairs(text: str) -> list[dict[str, Any]]:
    """Extract every identifier (+optional precis) reference from text."""
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for pattern, kind in _IDENTIFIER_PATTERNS:
        full_re = re.compile(rf"({pattern})\s*(?:\(([^)]+)\))?", re.IGNORECASE)
        for m in full_re.finditer(text):
            ident = m.group(1).strip()
            precis = (m.group(2) or "").strip() or None
            key = (kind, ident.lower())
            if key in seen:
                continue
            seen.add(key)
            found.append({"type": kind, "id": ident, "precis": precis})
    return found


def assess_reflection_quality(
    reflection_text: str,
    outputs: dict[str, Any] | None,
    tasks_worked: list[dict[str, Any]] | None,
    references: list[dict[str, Any]],
) -> list[str]:
    """Return non-fatal quality warnings for a parsed reflection.

    See aops-core/skills/end_session/transcript-metadata-schema.md for the warning codes.
    """
    warnings: list[str] = []

    if outputs is None:
        warnings.append(
            "missing-output-section: no `## Output` block found "
            "(use `Output: none — <reason>` if no artefact was produced)"
        )
    elif not outputs.get("explicit_none") and not outputs.get("outputs"):
        warnings.append(
            "empty-output-section: `## Output` block contained no URLs and "
            "did not declare `none — <reason>`"
        )

    if tasks_worked is None:
        warnings.append(
            "missing-tasks-worked: no `## Tasks worked` block found "
            "(required source-of-truth list of session task activity)"
        )
    elif not tasks_worked:
        warnings.append("empty-tasks-worked: `## Tasks worked` block was empty")

    for ref in references:
        if not ref.get("precis"):
            warnings.append(
                f"bare-identifier: {ref['id']} appears without a parenthetical "
                "precis — every reference needs <60-char description"
            )

    suggestion_signals = [
        r"\bnew\s+(tool|command|skill|agent|feature)\b",
        r"\bwe should (build|add|create)\b",
        r"\b(propose|suggest)(ing)? (a|an)? new\b",
    ]
    for pat in suggestion_signals:
        if re.search(pat, reflection_text, re.IGNORECASE):
            warnings.append(
                "feature-suggestion: reflection appears to propose a new "
                "tool/feature; framework reflections must report concrete "
                "friction and bug reports, not feature work"
            )
            break

    return warnings


def _assess_friction_misroute(result: dict[str, Any]) -> list[str]:
    """Quality warnings for friction that likely landed in the wrong bucket.

    Two signatures of the parser/SKILL drift fixed in aops-6a787364:
    - ``inferred=True``: the structured parse matched nothing and the reflection
      fell through to the unstructured fallback (labels didn't match the parse
      contract) — the categorisation is a guess, not authored.
    - friction-marked text sitting in ``accomplishments`` while ``friction_points``
      is empty — friction was bucketed as an accomplishment.
    """
    warnings: list[str] = []
    if result.get("inferred"):
        warnings.append(
            "inferred-reflection: reflection had no structured **Field**: labels; "
            "categorisation was inferred from bullets/keywords. Emit the bold labels "
            "from SKILL.md (**Outcome**/**Accomplishments**/**Friction points**/"
            "**Proposed changes**)."
        )
    accomplishments = (
        result.get("accomplishments") or []
    )  # allow-fallback: reflection field is optional
    friction = result.get("friction_points") or []  # allow-fallback: reflection field is optional
    if not friction and any(
        re.search(r"\bfriction\b", str(a), re.IGNORECASE) for a in accomplishments
    ):
        warnings.append(
            "friction-in-accomplishments: an accomplishment mentions 'friction' "
            "while friction_points is empty — friction may be miscategorised."
        )
    return warnings


def _infer_outcome(text: str) -> str:
    """Infer outcome from content keywords in unstructured reflection text."""
    lower = text.lower()
    success_kw = ("fixed", "completed", "shipped", "merged", "success", "done", "resolved")
    failure_kw = ("failed", "error", "couldn't", "broken", "unable")
    if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in success_kw):
        return "success"
    if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in failure_kw):
        return "failure"
    # Partial indicators or default
    return "partial"


# Detect bullets whose leading label marks them as friction or proposed-change.
# These must NOT be blanket-dumped into accomplishments (aops-6a787364): an
# unstructured reflection still routes its friction to friction_points.
_FRICTION_BULLET_RE = re.compile(r"^\**\s*friction\b", re.IGNORECASE)
_PROPOSED_BULLET_RE = re.compile(r"^\**\s*proposed\b", re.IGNORECASE)
# Strip a leading "Friction …:" / "Proposed …:" label (only the colon form) so
# the routed item reads as the substantive content, not the label.
_FRICTION_LABEL_RE = re.compile(r"^\**\s*friction\b[^:\n]*:\s*", re.IGNORECASE)
_PROPOSED_LABEL_RE = re.compile(r"^\**\s*proposed\b[^:\n]*:\s*", re.IGNORECASE)


def _parse_unstructured_reflection(text: str) -> dict[str, Any] | None:
    """Fallback parser for reflections without structured **Field**: value lines.

    Treats bullet points as accomplishments and infers outcome from keywords,
    but routes friction-/proposed-labelled bullets to their own buckets so
    off-template friction does not get miscategorised as an accomplishment
    (aops-6a787364). Returns None if the text is empty/whitespace.
    """
    stripped = text.strip()
    if not stripped:
        return None

    result: dict[str, Any] = {"inferred": True}

    # Extract bullet points, routing each by its leading label.
    bullets = re.findall(r"^[\s]*[-*]\s+(.+)$", stripped, re.MULTILINE)
    if bullets:
        accomplishments: list[str] = []
        friction: list[str] = []
        proposed: list[str] = []
        for raw in bullets:
            b = raw.strip()
            if not b:
                continue
            if _FRICTION_BULLET_RE.match(b):
                friction.append(_FRICTION_LABEL_RE.sub("", b).strip() or b)
            elif _PROPOSED_BULLET_RE.match(b):
                proposed.append(_PROPOSED_LABEL_RE.sub("", b).strip() or b)
            else:
                accomplishments.append(b)
        result["accomplishments"] = accomplishments
        if friction:
            result["friction_points"] = friction
        if proposed:
            result["proposed_changes"] = proposed
    else:
        # No bullets — use the full text as a single accomplishment
        result["accomplishments"] = [stripped]

    result["outcome"] = _infer_outcome(stripped)
    result["summary"] = stripped

    return result


def _parse_list_field(value: str) -> list[str]:
    """Parse a field that may contain a list of items.

    Handles:
    - Single line comma-separated: "Item 1, Item 2, Item 3"
    - Bullet list: "- Item 1\n- Item 2"
    - Numbered list: "1. Item 1\n2. Item 2"
    - Single value: "Single item"
    - None values: "none", "N/A", "None needed"
    """
    # Check for "none" type values
    if re.match(r"^\s*(none|n/?a|none needed|nothing)\s*$", value, re.IGNORECASE):
        return []

    # PRE-PROCESS: Strip code fences if they wrap the whole value or individual lines
    # Strip wrapping code block: ```\ncontent\n```
    value = re.sub(r"^```\w*\n(.*?)\n```$", r"\1", value, flags=re.DOTALL)
    # Strip inline code block: ```content```
    value = re.sub(r"^```(.*?)```$", r"\1", value, flags=re.DOTALL)

    # Check for bullet or numbered list
    list_items = re.findall(r"^[\s]*[-*\d.]+\s*(.+)$", value, re.MULTILINE)
    if list_items:
        # Filter out bare code fences that often appear in bullet lists when agent
        # tries to include code blocks
        return [
            item.strip()
            for item in list_items
            if item.strip() and not item.strip().startswith("```")
        ]

    # Check for comma-separated (only if contains commas and not a single sentence)
    if "," in value and not re.search(r"\.\s", value):
        items = [item.strip() for item in value.split(",")]
        return [item for item in items if item]

    # Single value
    return [value] if value else []


def _extract_text_from_entry(entry: Entry) -> str:
    """Extract text content from an Entry object."""
    text = ""
    if entry.message:
        content = entry.message.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Handle content blocks
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
    elif entry.content:
        text = str(entry.content.get("content", ""))
    return text


def extract_reflection_from_entries(
    entries: list[Entry],
    agent_entries: dict[str, list[Entry]] | None = None,
) -> list[dict[str, Any]]:
    """Extract all Framework Reflections from session entries.

    Searches through assistant entries for Framework Reflection sections.
    Also searches through agent/subagent entries if provided.
    Returns ALL reflections found, preserving order (earliest first).

    Args:
        entries: List of Entry objects from a parsed session
        agent_entries: Optional dict mapping agent IDs to their entries

    Returns:
        List of parsed reflection dicts (may be empty if none found)
    """
    reflections = []

    # Search main entries in order (earliest first)
    for entry in entries:
        if entry.type != "assistant":
            continue

        text = _extract_text_from_entry(entry)
        if not text:
            continue

        reflection = parse_framework_reflection(text)
        if not reflection:
            reflection = parse_session_handover(text)

        if reflection:
            reflections.append(reflection)

    # Also search agent entries
    if agent_entries:
        # Collect all agent entries with their timestamps for sorting
        all_agent_entries = []
        for _agent_id, agent_entry_list in agent_entries.items():
            for entry in agent_entry_list:
                if entry.type == "assistant":
                    all_agent_entries.append(entry)

        # Sort by timestamp (oldest first) if available
        all_agent_entries.sort(
            key=lambda e: e.timestamp if e.timestamp else "",
            reverse=False,
        )

        for entry in all_agent_entries:
            text = _extract_text_from_entry(entry)
            if not text:
                continue

            reflection = parse_framework_reflection(text)
            if not reflection:
                reflection = parse_session_handover(text)

            if reflection:
                reflections.append(reflection)

    # Deduplicate reflections by content (handles continuations duplicating earlier cycles)
    unique_reflections = []
    for ref in reflections:
        if ref not in unique_reflections:
            unique_reflections.append(ref)

    return unique_reflections


def _synthesize_summary(reflection: dict[str, Any], outcome: str, project: str) -> str:
    """Synthesize a human-readable summary from reflection data.

    Args:
        reflection: Parsed reflection dict
        outcome: Normalized outcome (success/partial/failure)
        project: Project name

    Returns:
        Human-readable narrative summary of the session
    """
    accomplishments = reflection.get("accomplishments", [])
    friction_points = reflection.get("friction_points", [])

    # Build narrative based on outcome and accomplishments
    if not accomplishments:
        if outcome == "failure":
            return f"Session in {project} encountered issues without completing objectives."
        return f"Session in {project} completed."

    # Summarize accomplishments into a narrative
    if len(accomplishments) == 1:
        summary = accomplishments[0]
    else:
        # Combine first accomplishment with count of others
        summary = f"{accomplishments[0]}; plus {len(accomplishments) - 1} other accomplishment{'s' if len(accomplishments) > 2 else ''}"

    prefix = ""

    # Add friction note if present
    if friction_points and outcome != "success":
        suffix = (
            f" (encountered friction: {friction_points[0][:50]}...)"
            if len(friction_points[0]) > 50
            else f" (encountered friction: {friction_points[0]})"
        )
    else:
        suffix = ""

    return f"{prefix}{summary}{suffix}"


def reflection_to_insights(
    reflection: dict[str, Any],
    session_id: str,
    date: str,
    project: str,
    timestamp: datetime | None = None,
    usage_stats: UsageStats | None = None,
    session_duration_minutes: float | None = None,
    timeline_events: list[dict[str, Any]] | None = None,
    provider: str | None = None,
    session_path: Path | None = None,
    origin_override: dict[str, str | None] | None = None,
    session_ctx: dict | None = None,
    session_summary: SessionSummary | None = None,
) -> dict[str, Any]:
    """Convert parsed Framework Reflection to session insights format.

    Args:
        reflection: Parsed reflection dict from parse_framework_reflection
        session_id: Session ID (8-char hash)
        date: Date string (YYYY-MM-DD) - kept for filename generation
        project: Project name
        timestamp: Optional datetime for full ISO 8601 timestamp with tz
        usage_stats: Optional UsageStats for token_metrics field
        session_duration_minutes: Optional session duration for efficiency metrics
        timeline_events: Optional list of timeline event dicts from extract_timeline_events

    Returns:
        Insights dict compatible with insights_generator schema
    """
    # Map outcome to lowercase
    outcome = reflection.get("outcome", "partial")
    if isinstance(outcome, str):
        outcome = outcome.lower()
        # Normalize variations
        if outcome not in ("success", "partial", "failure"):
            if "success" in outcome:
                outcome = "success"
            elif "fail" in outcome:
                outcome = "failure"
            else:
                outcome = "partial"

    # Generate ISO 8601 timestamp with timezone
    if timestamp:
        date_iso = timestamp.isoformat()
    else:
        # Fall back to now if no timestamp provided
        date_iso = datetime.now().astimezone().replace(microsecond=0).isoformat()

    # Synthesize human-readable summary from accomplishments
    summary = _synthesize_summary(reflection, outcome, project)

    # Build token_metrics if usage_stats provided
    token_metrics = None
    if usage_stats and usage_stats.has_data():
        token_metrics = usage_stats.to_token_metrics(session_duration_minutes)

    # Build framework_reflections array with single reflection entry
    # This matches the schema in the session-insights-prompt spec (brain PKB)
    framework_reflection_entry = {
        "prompts": reflection.get("prompts"),
        "guidance_received": reflection.get("guidance_received"),
        "followed": reflection.get("followed"),
        "outcome": outcome,
        "accomplishments": reflection.get("accomplishments", []),
        "friction_points": reflection.get("friction_points", []),
        "root_cause": reflection.get("root_cause"),
        "proposed_changes": reflection.get("proposed_changes", []),
        "next_step": reflection.get("next_step"),
    }

    task_id = reflection.get("task_id") or os.environ.get("AOPS_TASK_ID")
    if not task_id and timeline_events:
        for event in timeline_events:
            if event.get("type") in (
                "task_create",
                "task_update",
                "task_complete",
                "task_release",
            ) and event.get("task_id"):
                task_id = event["task_id"]
                break

    # Determine stable project if we only have a UUID fragment
    stable_project = project
    if (
        not stable_project
        or re.match(r"^[0-9a-f]{8,}$", stable_project)
        or re.match(r"^[0-9a-f\-]{36}$", stable_project)
    ):
        if timeline_events:
            for event in timeline_events:
                if event.get("type") == "task_create" and event.get("project"):
                    stable_project = event["project"]
                    break

    # Infer surface/client/crew from session_path so offline conversion of
    # GHA/crew/polecat sessions doesn't fall back to live env (which usually
    # reports the converter shell, not the original runtime). When the caller
    # has already computed origin (e.g. transcript.py also scans entries for
    # Claude Desktop LAM markers), prefer that.
    if origin_override is not None:
        origin = origin_override
    elif session_path is not None:
        origin = session_naming.infer_session_origin_from_path(session_path, provider=provider)
    else:
        origin = {}

    result = {
        "session_id": session_id,
        "date": date_iso,
        "project": stable_project,
        "summary": summary,
        "outcome": outcome,
        "accomplishments": reflection.get("accomplishments", []),
        "friction_points": reflection.get("friction_points", []),
        "proposed_changes": reflection.get("proposed_changes", []),
        # Metadata (aops-d9ba7159, aops-eaf402f5)
        **session_naming.get_session_metadata(provider=provider, **origin),
        "repo": stable_project,
        "task_id": task_id,
        # Resolved task title (aops-62abcf9d): carried alongside task_id so
        # downstream consumers (catch-up timeline) need no PKB lookup. Best-effort:
        # None when unresolvable or PKB endpoint unconfigured.
        "task_title": resolve_task_title(task_id),
        # Framework reflections as array (schema-compliant)
        "framework_reflections": [framework_reflection_entry],
        # Token usage metrics (optional)
        "token_metrics": token_metrics,
    }

    # task-5a54f813 quality-bar fields. See
    # aops-core/skills/end_session/transcript-metadata-schema.md.
    if "outputs" in reflection:
        result["outputs"] = reflection.get("outputs", [])
        result["output_explicit_none"] = reflection.get("output_explicit_none", False)
        result["output_none_reason"] = reflection.get("output_none_reason")
    if "tasks_worked" in reflection:
        result["tasks_worked"] = reflection.get("tasks_worked", [])
    if "references" in reflection:
        result["references"] = reflection.get("references", [])
    if reflection.get("quality_warnings"):
        result["quality_warnings"] = reflection["quality_warnings"]
    if "thread_pickup" in reflection:
        result["thread_pickup"] = reflection["thread_pickup"]

    # Timeline events for path reconstruction (optional)
    if timeline_events:
        result["timeline_events"] = timeline_events
        # Pre-compute user prompt count for downstream consumers
        # (daily skill engagement classification)
        result["user_prompt_count"] = sum(
            1 for e in timeline_events if e.get("type") == "user_prompt"
        )
        # Elevate PR URL to root if found
        for event in timeline_events:
            if event.get("type") == "pr_create" and event.get("pr_url"):
                result["pr_url"] = event["pr_url"]
                break
    else:
        result["user_prompt_count"] = None

    if usage_stats:
        result["attribution"] = {
            "plugins": list(usage_stats.attribution["plugins"]),
            "skills": list(usage_stats.attribution["skills"]),
            "mcp_servers": usage_stats.attribution["mcp_servers"],
            "mcp_tools": usage_stats.attribution["mcp_tools"],
        }
        result["stop_reasons"] = usage_stats.stop_reasons
        result["thinking_turns"] = usage_stats.thinking_turns

    if session_ctx:
        for k, v in session_ctx.items():
            if k == "models":
                pass
            elif v is not None:
                result[k] = v

    if session_summary:
        if session_summary.session_type:
            result["session_type"] = session_summary.session_type
        if session_summary.gemini_version:
            result["gemini_version"] = session_summary.gemini_version
        if session_summary.details:
            if "gates" in session_summary.details:
                result["gates"] = session_summary.details["gates"]
            if "global_turn_count" in session_summary.details:
                result["global_turn_count"] = session_summary.details["global_turn_count"]
            if "main_agent_todos" in session_summary.details:
                result["main_agent"] = {"todos": session_summary.details["main_agent_todos"]}
            if "started_at" in session_summary.details:
                result["started_at"] = session_summary.details["started_at"]
            if "last_modified" in session_summary.details:
                result["last_modified"] = session_summary.details["last_modified"]
            if "ended_at" in session_summary.details:
                result["ended_at"] = session_summary.details["ended_at"]

        for _attr in (
            "agent",
            "commissioned_as",
            "parent_session",
            "launched_by",
            "subagent_type",
            "crew",
            "session_kind",
            "client",
            "surface",
            "provider",
        ):
            _val = getattr(session_summary, _attr, None)
            if _val:
                result[_attr] = _val

    return result


_TASK_TITLE_CACHE: dict[str, str | None] = {}


def resolve_task_title(task_id: str | None) -> str | None:
    """Best-effort resolve a task title from the PKB for a given task_id.

    Used so newly-generated transcript frontmatter can carry ``task_title``
    alongside ``task_id``/``pr_url`` (aops-62abcf9d), sparing downstream
    consumers (e.g. the catch-up timeline) a PKB lookup at read time.

    Best-effort by contract: returns ``None`` if ``task_id`` is falsy, if the
    PKB MCP endpoint is not configured (``PKB_MCP_URL`` unset — e.g. offline
    conversion or tests), or if the lookup fails for any reason. Never raises.
    Results are cached per-process (including ``None``) to avoid repeat
    round-trips for the same id.
    """
    if not task_id:
        return None
    if task_id in _TASK_TITLE_CACHE:
        return _TASK_TITLE_CACHE[task_id]

    title: str | None = None
    try:
        if os.environ.get("PKB_MCP_URL"):
            try:
                from polecat import pkb_bridge
            except ImportError:
                # aops-core/lib/transcript_parser.py -> aops-core -> framework root
                framework_root = Path(__file__).resolve().parent.parent.parent
                if str(framework_root) not in sys.path:
                    sys.path.insert(0, str(framework_root))
                from polecat import pkb_bridge

            task = pkb_bridge.get_task(task_id)
            if task and task.title:
                title = task.title
    except Exception as e:
        print(f"[resolve_task_title] PKB lookup failed for {task_id!r}: {e}", file=sys.stderr)
        title = None

    _TASK_TITLE_CACHE[task_id] = title
    return title


def extract_timeline_events(turns: list[Any], session_id: str) -> list[dict[str, Any]]:
    """Extract timeline events from parsed conversation turns.

    Scans assistant_sequence for task operations, user prompts,
    and skill invocations. Returns list of event dicts ready for JSON serialization.

    Emission is idempotent: events are deduped by a content-aware key so that
    upstream replays or repeated invocations cannot produce duplicate
    `user_prompt` / task-op events. The parser already drops Cowork
    `isReplay` entries and dedupes by UUID, so this is defence-in-depth.

    Args:
        turns: List of ConversationTurn objects from group_entries_into_turns
        session_id: 8-char session ID for context

    Returns:
        List of event dicts with timestamp, type, and description fields
    """
    events: list[dict[str, Any]] = []
    seen_keys: set[tuple] = set()

    def _emit(event: dict[str, Any]) -> None:
        # Dedupe key: timestamp + type + the most-identifying content field
        # for that event type. A duplicate prompt with a slightly different
        # timestamp would still be caught by parser-level UUID dedupe; here
        # we guard against exact replays from any other path.
        evt_type = event.get("type")
        if evt_type == "user_prompt":
            key = (event.get("timestamp"), evt_type, event.get("description"))
        elif evt_type in ("task_create", "task_complete", "task_release", "task_update"):
            key = (
                event.get("timestamp"),
                evt_type,
                event.get("task_id"),
                event.get("task_title"),
                event.get("new_status"),
                event.get("status"),
            )
        elif evt_type == "tool_call":
            key = (event.get("timestamp"), evt_type, event.get("tool"), event.get("is_error"))
        elif evt_type == "pr_create":
            key = (event.get("timestamp"), evt_type, event.get("pr_url"))
        else:
            key = (event.get("timestamp"), evt_type, event.get("description"))
        if key in seen_keys:
            return
        seen_keys.add(key)
        events.append(event)

    for turn in turns:
        # Handle both ConversationTurn dataclass and plain dict turns
        if isinstance(turn, dict):
            user_msg = turn.get("user_message")
            sequence = turn.get("assistant_sequence", [])
            start_time = turn.get("start_time")
        else:
            user_msg = turn.user_message
            sequence = turn.assistant_sequence
            start_time = turn.start_time

        ts = start_time.isoformat() if start_time else None

        # User prompts (no truncation, JSON-escaped by json.dumps downstream)
        if user_msg and not getattr(turn, "is_meta", False):
            _emit(
                {
                    "timestamp": ts,
                    "type": "user_prompt",
                    "description": user_msg,
                }
            )

        # Tool calls from assistant_sequence
        for item in sequence:
            if not isinstance(item, dict) or item.get("type") != "tool":
                continue
            tool = item.get("tool_name", "")

            _emit(
                {
                    "timestamp": ts,
                    "type": "tool_call",
                    "tool": tool,
                    "is_error": item.get("is_error", False),
                }
            )

            inp = item.get("tool_input", {})
            if not isinstance(inp, dict):
                continue

            if tool in ("run_shell_command", "Bash"):
                cmd = inp.get("command", "")
                if "gh pr create" in cmd:
                    result_text = item.get("result", "")
                    match = re.search(
                        r"(https://github\.com/[^\s/]+/[^\s/]+/pull/\d+)", result_text
                    )
                    if match:
                        _emit(
                            {
                                "timestamp": ts,
                                "type": "pr_create",
                                "pr_url": match.group(1),
                            }
                        )

            if "pkb__create_task" in tool:
                _emit(
                    {
                        "timestamp": ts,
                        "type": "task_create",
                        "task_id": None,  # not known until result
                        "task_title": inp.get("title", inp.get("task_title", "")),
                        "project": inp.get("project"),
                    }
                )
            elif "pkb__complete_task" in tool:
                _emit(
                    {
                        "timestamp": ts,
                        "type": "task_complete",
                        "task_id": inp.get("id", ""),
                    }
                )
            elif "pkb__release_task" in tool:
                _emit(
                    {
                        "timestamp": ts,
                        "type": "task_release",
                        "task_id": inp.get("id", ""),
                        "status": inp.get("status", ""),
                        "summary": inp.get("release_summary", inp.get("summary", "")),
                    }
                )
            elif "pkb__update_task" in tool:
                status = inp.get("status")
                if status:  # only record status changes
                    _emit(
                        {
                            "timestamp": ts,
                            "type": "task_update",
                            "task_id": inp.get("id", ""),
                            "new_status": status,
                        }
                    )

    return events


# Control envelopes / system wrappers that carry no user intent. These are
# injected by the harness (resume notifications, hook reminders, tool plumbing)
# and must be stripped before a user-prompt string is treated as "what the user
# was doing". Order-independent; applied repeatedly until stable is unnecessary
# because these tags do not nest within each other in practice.
_CONTROL_ENVELOPE_PATTERNS = [
    re.compile(r"<task-notification>.*?</task-notification>", re.DOTALL),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL),
    re.compile(r"<command-message>.*?</command-message>", re.DOTALL),
    re.compile(r"<tool-use-id>.*?</tool-use-id>", re.DOTALL),
    # Stray / self-closing control tags left behind after the blocks above.
    re.compile(
        r"</?(?:task-notification|system-reminder|tool-use-id|task-id|output-file|"
        r"status|summary|local-command-stdout|command-message)[^>]*>"
    ),
]

# Signatures of the standard polecat worker dispatch preamble. When present, the
# user's actual intent is the task spec that follows, not the boilerplate
# scaffolding (search-the-PKB instructions, step-by-step finish flow, etc.).
_WORKER_PREAMBLE_MARKERS = (
    "You are a polecat worker",
    "Your task has already been claimed",
)


def _strip_worker_preamble(text: str) -> str:
    """If ``text`` is a standard worker dispatch, return the task spec onward.

    The dispatch boilerplate precedes a ``## Your Task`` / ``## Task Body``
    heading; everything before it is fixed scaffolding shared by every worker
    session and tells you nothing about *this* session's intent.
    """
    if not any(marker in text[:600] for marker in _WORKER_PREAMBLE_MARKERS):
        return text
    heading = re.search(r"^#{1,3}\s+(?:Your Task|Task Body|Task)\b.*$", text, re.MULTILINE)
    if heading:
        return text[heading.start() :].strip()
    return text


def clean_prompt_text(text: str) -> str:
    """Strip control envelopes and worker-preamble scaffolding from a prompt.

    Used to derive ``initial_prompt`` — the user's own first substantive
    message — from a raw user-turn string. Returns ``""`` when nothing
    substantive remains (e.g. the turn was purely a ``<task-notification>``
    auto-resume).
    """
    if not text:
        return ""
    for pattern in _CONTROL_ENVELOPE_PATTERNS:
        text = pattern.sub("", text)
    text = _strip_worker_preamble(text)
    # Collapse the blank-line runs left by removed envelopes.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def extract_initial_prompt(timeline_events: list[dict[str, Any]] | None) -> str | None:
    """Return the user's first substantive prompt from timeline events.

    Scans ``user_prompt`` events in order, cleans each of control envelopes and
    worker-preamble scaffolding (see :func:`clean_prompt_text`), and returns the
    first one with real content. Returns ``None`` if no substantive prompt is
    found — callers should omit the field rather than write an empty string.
    """
    for event in timeline_events or []:
        if event.get("type") != "user_prompt":
            continue
        cleaned = clean_prompt_text(
            event.get("description") or ""
        )  # allow-fallback: description is optional; "" = no text to clean
        if cleaned:
            return cleaned
    return None


def format_reflection_header(reflection: dict[str, Any]) -> str:
    """Format Framework Reflection as markdown header for transcript.

    Args:
        reflection: Parsed reflection dict

    Returns:
        Formatted markdown string to display at top of transcript
    """
    lines = ["## Session Reflection\n"]

    if reflection.get("prompts"):
        lines.append(f"**Prompts**: {reflection['prompts']}")

    if reflection.get("outcome"):
        outcome = reflection["outcome"]
        # Add emoji indicator
        emoji = {"success": "✅", "partial": "⚠️", "failure": "❌"}.get(outcome.lower(), "❓")
        lines.append(f"**Outcome**: {emoji} {outcome}")

    if reflection.get("accomplishments"):
        lines.append("**Accomplishments**:")
        for item in reflection["accomplishments"]:
            lines.append(f"  - {item}")

    if reflection.get("friction_points"):
        lines.append("**Friction points**:")
        for item in reflection["friction_points"]:
            lines.append(f"  - {item}")

    if reflection.get("proposed_changes"):
        lines.append("**Proposed changes**:")
        for item in reflection["proposed_changes"]:
            lines.append(f"  - {item}")

    if reflection.get("next_step"):
        lines.append(f"**Next step**: {reflection['next_step']}")

    lines.append("\n---\n")
    return "\n".join(lines)


@dataclass
class TodoWriteState:
    """Current state of TodoWrite items in a session."""

    todos: list[dict[str, Any]]  # Full list of todo items
    counts: dict[str, int]  # {pending: n, in_progress: n, completed: n}
    in_progress_task: str | None  # Content of first in_progress item


@dataclass
class UsageStats:
    """Aggregated token usage statistics from a session or turn."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    server_tool_use: int = 0
    service_tier: str | None = None

    # Breakdowns by category
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)
    by_tool: dict[str, dict[str, int]] = field(default_factory=dict)
    by_agent: dict[str, dict[str, int]] = field(default_factory=dict)
    # Call-level skill attribution (aops-29d77844). Keyed by the Skill tool's
    # `input.skill` argument (e.g. "aops-core:planner"). Counts + tokens are
    # CALL-LEVEL ONLY: the work a skill prompt unfurls into stays attributed to
    # the calling agent in by_agent — skills are not isolated execution contexts.
    by_skill: dict[str, dict[str, int]] = field(default_factory=dict)

    # Aggregations (CC 2.1+)
    attribution: dict[str, Any] = field(
        default_factory=lambda: {
            "plugins": set(),
            "skills": set(),
            "mcp_servers": {},
            "mcp_tools": {},
        }
    )
    stop_reasons: dict[str, int] = field(default_factory=dict)
    thinking_turns: int = 0

    # Human-attention proxies (main session only; subagent-internal entries excluded).
    # user_messages: real user-role entries excluding tool_result wrappers and meta.
    # mid_session_corrections: user_messages that occur AFTER the first assistant tool_use
    # (i.e. interruptions, not the dispatch/initial prompt).
    user_messages: int = 0
    mid_session_corrections: int = 0

    def add_entry(
        self,
        entry: Entry,
        tool_name: str | None = None,
        agent_id: str | None = None,
        skill_name: str | None = None,
    ) -> None:
        """Add token usage from an entry to the aggregate stats.

        ``skill_name`` is the ``input.skill`` argument of a ``Skill`` tool call,
        accumulated into ``by_skill`` (call-level attribution, aops-29d77844).
        """
        if entry.input_tokens:
            self.input_tokens += entry.input_tokens
        if entry.output_tokens:
            self.output_tokens += entry.output_tokens
        if entry.cache_creation_input_tokens:
            self.cache_creation_input_tokens += entry.cache_creation_input_tokens
        if entry.cache_read_input_tokens:
            self.cache_read_input_tokens += entry.cache_read_input_tokens
        if entry.server_tool_use:
            v = entry.server_tool_use
            if isinstance(v, dict):
                v = sum(x for x in v.values() if isinstance(x, int))
            if isinstance(v, int) and not isinstance(v, bool):
                self.server_tool_use += v
        if entry.service_tier and not self.service_tier:
            self.service_tier = entry.service_tier

        if entry.stop_reason:
            self.stop_reasons[entry.stop_reason] = self.stop_reasons.get(entry.stop_reason, 0) + 1

        if entry.attribution_plugin:
            self.attribution["plugins"].add(entry.attribution_plugin)
        if entry.attribution_skill:
            self.attribution["skills"].add(entry.attribution_skill)
        if entry.attribution_mcp_server:
            self.attribution["mcp_servers"][entry.attribution_mcp_server] = (
                self.attribution["mcp_servers"].get(entry.attribution_mcp_server, 0) + 1
            )
        if entry.attribution_mcp_tool:
            self.attribution["mcp_tools"][entry.attribution_mcp_tool] = (
                self.attribution["mcp_tools"].get(entry.attribution_mcp_tool, 0) + 1
            )

        # fix Claude thinking-block counting: check for type=="thinking" in content array or entry.thoughts
        has_thinking = False
        if entry.thoughts:
            has_thinking = True
        elif isinstance(entry.message.get("content"), list):
            for block in entry.message["content"]:
                if isinstance(block, dict) and block.get("type") in (
                    "thinking",
                    "redacted_thinking",
                ):
                    has_thinking = True
                    break
        if has_thinking:
            self.thinking_turns += 1

        # Aggregate by model
        if entry.model:
            if entry.model not in self.by_model:
                self.by_model[entry.model] = {
                    "input": 0,
                    "output": 0,
                    "cache_create": 0,
                    "cache_read": 0,
                }
            self.by_model[entry.model]["input"] += entry.input_tokens or 0
            self.by_model[entry.model]["output"] += entry.output_tokens or 0
            self.by_model[entry.model]["cache_create"] += entry.cache_creation_input_tokens or 0
            self.by_model[entry.model]["cache_read"] += entry.cache_read_input_tokens or 0

        # Aggregate by tool
        if tool_name:
            if tool_name not in self.by_tool:
                self.by_tool[tool_name] = {"count": 0, "input": 0, "output": 0}
            self.by_tool[tool_name]["count"] += 1
            self.by_tool[tool_name]["input"] += entry.input_tokens or 0
            self.by_tool[tool_name]["output"] += entry.output_tokens or 0

        # Aggregate by skill (call-level). Mirrors by_tool per-name shape so a
        # consumer can read by_skill[name] identically to by_tool[name].
        if skill_name:
            if skill_name not in self.by_skill:
                self.by_skill[skill_name] = {"count": 0, "input": 0, "output": 0}
            self.by_skill[skill_name]["count"] += 1
            self.by_skill[skill_name]["input"] += entry.input_tokens or 0
            self.by_skill[skill_name]["output"] += entry.output_tokens or 0

        # Aggregate by agent (main vs subagents)
        agent_key = agent_id or "main"
        if agent_key not in self.by_agent:
            self.by_agent[agent_key] = {
                "input": 0,
                "output": 0,
                "cache_create": 0,
                "cache_read": 0,
            }
        self.by_agent[agent_key]["input"] += entry.input_tokens or 0
        self.by_agent[agent_key]["output"] += entry.output_tokens or 0
        self.by_agent[agent_key]["cache_create"] += entry.cache_creation_input_tokens or 0
        self.by_agent[agent_key]["cache_read"] += entry.cache_read_input_tokens or 0

    def has_data(self) -> bool:
        """Check if any usage data has been recorded."""
        return (
            self.input_tokens > 0
            or self.output_tokens > 0
            or self.cache_creation_input_tokens > 0
            or self.cache_read_input_tokens > 0
        )

    def format_summary(self) -> str:
        """Format usage stats as a compact summary string."""
        parts = []
        if self.input_tokens or self.output_tokens:
            parts.append(f"{self.input_tokens:,} in / {self.output_tokens:,} out")
        if self.cache_read_input_tokens:
            parts.append(f"{self.cache_read_input_tokens:,} cache read")
        if self.cache_creation_input_tokens:
            parts.append(f"{self.cache_creation_input_tokens:,} cache created")
        return ", ".join(parts) if parts else ""

    def to_token_metrics(self, session_duration_minutes: float | None = None) -> dict[str, Any]:
        """Convert UsageStats to token_metrics schema for insights JSON.

        Args:
            session_duration_minutes: Optional session duration for efficiency calculations

        Returns:
            Dictionary matching token_metrics schema:
            {
                "totals": {"input_tokens": int, ...},
                "by_model": {"model_id": {"input": int, "output": int}, ...},
                "by_agent": {"agent_name": {"input": int, "output": int}, ...},
                "efficiency": {"cache_hit_rate": float, ...}
            }
        """
        total_input = self.input_tokens + self.cache_read_input_tokens
        cache_hit_rate = self.cache_read_input_tokens / total_input if total_input > 0 else 0.0

        metrics: dict[str, Any] = {
            "totals": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cache_read_tokens": self.cache_read_input_tokens,
                "cache_create_tokens": self.cache_creation_input_tokens,
                "server_tool_use": self.server_tool_use,
                "service_tier": self.service_tier,
            },
            "by_model": self.by_model,
            "by_tool": self.by_tool,
            "by_skill": self.by_skill,
            "by_agent": self.by_agent,
            "attention": {
                "user_messages": self.user_messages,
                "mid_session_corrections": self.mid_session_corrections,
            },
            "efficiency": {
                "cache_hit_rate": round(cache_hit_rate, 3),
            },
        }

        # Add tokens_per_minute if duration is available
        if session_duration_minutes and session_duration_minutes > 0:
            total_tokens = self.input_tokens + self.output_tokens
            metrics["efficiency"]["tokens_per_minute"] = round(
                total_tokens / session_duration_minutes, 1
            )
            metrics["efficiency"]["session_duration_minutes"] = round(session_duration_minutes, 1)

        return metrics


def _remap_by_agent_keys(
    by_agent: dict[str, dict[str, int]],
    type_index: dict[str, str],
) -> dict[str, dict[str, int]]:
    """Rename UUID-keyed by_agent entries to human-readable subagent names.

    Args:
        by_agent: Mapping of agent file-id (UUID) → token stats. ``"main"`` is
            passed through unchanged.
        type_index: Mapping of agent file-id → subagent_type (e.g. ``"rbg"``)
            produced by ``subagent_transcript._build_subagent_type_index``.

    Returns:
        A new dict with names substituted for UUIDs where known. Multiple
        invocations of the same subagent are summed.
    """
    remapped: dict[str, dict[str, int]] = {}
    for key, stats in by_agent.items():
        new_key = type_index.get(key, key) if key != "main" else "main"
        if new_key not in remapped:
            remapped[new_key] = {k: 0 for k in stats}
        for stat_key, value in stats.items():
            remapped[new_key][stat_key] = remapped[new_key].get(stat_key, 0) + value
    return remapped


def normalize_cowork_event(data: dict) -> tuple[str, dict] | None:
    """Map a raw Cowork audit event to (entry_type, message_dict).

    Returns None for non-Cowork event types (caller keeps original type/message).
    Used by both Entry.from_dict (direct audit.jsonl parsing) and ingest_cowork.py.
    """
    entry_type = data.get("type")
    if entry_type == "message":
        role = data.get("role")
        normed_type = role if role in ("user", "assistant") else "unknown"
        content_val = data.get("content", "")
        message: dict = {
            "role": role,
            "content": [
                {"type": "text", "text": content_val if isinstance(content_val, str) else ""}
            ],
        }
        return normed_type, message
    if entry_type == "tool_call":
        message = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "input": data.get("args", {}),
                }
            ],
        }
        return "assistant", message
    if entry_type == "tool_result":
        message = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": data.get("tool_use_id"),
                    "content": data.get("output", ""),
                    "is_error": data.get("is_error", False),
                }
            ],
        }
        return "user", message
    return None


@dataclass
class Entry:
    """Represents a single JSONL entry from any source."""

    type: str
    uuid: str = ""
    parent_uuid: str = ""
    message: dict = field(default_factory=dict)
    content: dict = field(default_factory=dict)
    is_sidechain: bool = False
    is_meta: bool = False
    tool_use_result: dict = field(default_factory=dict)
    hook_context: dict = field(default_factory=dict)
    subagent_id: str | None = None
    summary_text: str | None = None
    timestamp: datetime | None = None

    # Hook-specific fields
    additional_context: str | None = None
    hook_event_name: str | None = None
    hook_exit_code: int | None = None
    hook_verdict: str | None = None  # Gate verdict from CanonicalHookOutput
    hook_system_message: str | None = None  # System message from gate
    hook_context_injection: str | None = None  # Context injection from gate
    hook_raw_input: dict | None = None  # Hook input payload (e.g. Stop's last_assistant_message)
    hook_duration_ms: int | None = None  # Hook execution duration (CC stop_hook_summary)
    hook_prevented_continuation: bool = False  # Stop hook blocked the agent
    hook_is_cc_summary: bool = False  # Synthetic entry from CC stop_hook_summary (dedupe marker)
    skills_matched: list[str] | None = None
    files_loaded: list[str] | None = None
    tool_name: str | None = None
    tool_input: dict | None = None  # Tool parameters for PreToolUse/PostToolUse hooks
    agent_id: str | None = None

    # Session metadata fields (CC 2.1+)
    session_kind: str | None = None
    user_type: str | None = None
    entrypoint: str | None = None
    cwd: str | None = None
    client_version: str | None = None
    git_branch: str | None = None
    permission_mode: str | None = None
    # Auto-mode classifier fields — present only on a `type:result` envelope entry
    # (headless `claude -p`). `permission_denials` is the structured record of
    # calls the auto-mode classifier blocked; `terminal_reason` flags death-by-denial.
    permission_denials: list = field(default_factory=list)
    terminal_reason: str | None = None
    stop_reason: str | None = None
    attribution_plugin: str | None = None
    attribution_skill: str | None = None
    attribution_mcp_server: str | None = None
    attribution_mcp_tool: str | None = None

    # Token tracking fields
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    model: str | None = None
    service_tier: str | None = None
    server_tool_use: int | None = None

    # Reasoning / thinking fields
    # Gemini: list of {"subject": str, "description": str, "timestamp": str}
    # Claude: list of {"type": "thinking"|"redacted_thinking", "thinking"|"data": str}
    thoughts: list[dict] | None = None
    thoughts_tokens: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        """Create Entry from JSONL dict."""
        entry_type = data.get("type", "unknown")
        message = data.get("message", {})
        content = data.get("content", {})

        # Cowork audit normalization (raw audit.jsonl — no message field yet)
        if not message:
            cowork = normalize_cowork_event(data)
            if cowork is not None:
                entry_type, message = cowork

        # Extract tokens from message.usage if present
        usage = message.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        cache_creation_input_tokens = usage.get("cache_creation_input_tokens")
        cache_read_input_tokens = usage.get("cache_read_input_tokens")
        model = message.get("model")
        service_tier = usage.get("service_tier")
        server_tool_use = usage.get("server_tool_use")

        # Determine stop_reason (can be top-level or in message)
        stop_reason = data.get("stopReason") or message.get("stop_reason")

        entry = cls(
            type=entry_type,
            uuid=data.get("uuid", data.get("id", "")),
            parent_uuid=data.get("parentUuid", ""),
            message=message,
            content=content if isinstance(content, dict) else {},
            is_sidechain=data.get("isSidechain", False),
            is_meta=data.get("isMeta", False),
            tool_use_result=data.get("toolUseResult", {}),
            hook_context=data.get("hook_context", {}),
            subagent_id=data.get("subagentId"),
            summary_text=data.get("summary"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            model=model,
            service_tier=service_tier,
            server_tool_use=server_tool_use,
            session_kind=data.get("sessionKind"),
            user_type=data.get("userType"),
            entrypoint=data.get("entrypoint"),
            cwd=data.get("cwd"),
            client_version=data.get("version"),
            git_branch=data.get("gitBranch"),
            permission_mode=data.get("permissionMode"),
            permission_denials=data.get("permission_denials")
            or data.get("permissionDenials")
            or [],  # allow-fallback: absent on pre-classifier sessions
            terminal_reason=data.get("terminal_reason") or data.get("terminalReason"),
            stop_reason=stop_reason,
            attribution_plugin=data.get("attributionPlugin"),
            attribution_skill=data.get("attributionSkill"),
            attribution_mcp_server=data.get("attributionMcpServer"),
            attribution_mcp_tool=data.get("attributionMcpTool"),
        )

        # Promote hook_non_blocking_error attachments to system_reminder so
        # they flow through the same hook rendering pipeline as our-log and
        # CC stop_hook_summary entries. Without this, failed hooks that CC
        # records as attachments are silently dropped from transcripts.
        if entry.type == "attachment":
            att = data.get("attachment", {})
            if isinstance(att, dict) and att.get("type") == "hook_non_blocking_error":
                entry.type = "system_reminder"
                entry.hook_event_name = att.get("hookEvent") or att.get("hookName", "Hook")
                entry.hook_exit_code = 1
                stderr = att.get("stderr", "")
                entry.additional_context = f"errors: {[stderr]}" if stderr else ""

        # Extract hook data from system_reminder entries
        if entry.type == "system_reminder":
            hook_output = data.get("hookSpecificOutput", {})
            if isinstance(hook_output, dict) and hook_output:
                entry.additional_context = hook_output.get("additionalContext", "")
                entry.hook_event_name = hook_output.get("hookEventName")
                entry.hook_exit_code = hook_output.get("exitCode")
                entry.skills_matched = hook_output.get("skillsMatched")
                entry.files_loaded = hook_output.get("filesLoaded")
                entry.tool_name = hook_output.get("toolName")
                entry.tool_input = hook_output.get("toolInput")
                entry.agent_id = hook_output.get("agentId")
                # Gate verdict/message from merged CanonicalHookOutput
                entry.hook_verdict = hook_output.get("verdict")
                entry.hook_system_message = hook_output.get("systemMessage")
                entry.hook_context_injection = hook_output.get("contextInjection")
                raw_input = hook_output.get("rawInput")
                if isinstance(raw_input, dict) and raw_input:
                    entry.hook_raw_input = raw_input
            # Fall back to content.additionalContext
            if not entry.additional_context and isinstance(entry.content, dict):
                entry.additional_context = entry.content.get("additionalContext", "")
            if not entry.hook_event_name and isinstance(entry.content, dict):
                entry.hook_event_name = entry.content.get("hookEventName")
            if entry.hook_exit_code is None and isinstance(entry.content, dict):
                entry.hook_exit_code = entry.content.get("exitCode")

        # Extract hook data from system entries with stop_hook_summary subtype
        if entry.type == "system" and data.get("subtype") == "stop_hook_summary":
            # Normalize to system_reminder for downstream processing.
            # This is Claude Code's own summary of the Stop hook run; the
            # richer payload (verdict / system_message / raw_input) lives in
            # our -hooks.jsonl Stop entry. We mark this as a CC summary so
            # the renderer can dedupe with the our-log Stop event.
            entry.type = "system_reminder"
            entry.hook_event_name = "Stop"
            entry.hook_is_cc_summary = True
            entry.hook_exit_code = 0 if not data.get("hookErrors") else 1
            entry.hook_prevented_continuation = bool(data.get("preventedContinuation"))
            hook_infos = data.get("hookInfos", []) or []
            durations = [h.get("durationMs") for h in hook_infos if h.get("durationMs")]
            if durations:
                entry.hook_duration_ms = sum(durations)
            errors = data.get("hookErrors") or []
            extra = []
            if entry.hook_prevented_continuation:
                extra.append("PREVENTED CONTINUATION")
            if errors:
                extra.append(f"errors: {errors}")
            entry.additional_context = " · ".join(extra) if extra else ""

        # Parse timestamp (Claude uses "timestamp", Cowork audit uses "_audit_timestamp")
        timestamp_str = data.get("timestamp") or data.get("_audit_timestamp")
        if timestamp_str:
            try:
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(timestamp_str)
                # Convert to local time immediately to ensure consistent display
                entry.timestamp = dt.astimezone()
            except (ValueError, TypeError):
                pass

        return entry


@dataclass
class SessionSummary:
    """Summary information about a session."""

    uuid: str
    summary: str = "Claude Code Session"
    artifact_type: str = "unknown"
    created_at: str = ""
    edited_files: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    # Metadata (aops-d9ba7159)
    machine: str | None = None
    hostname: str | None = None
    provider: str | None = None
    crew: str | None = None
    repo: str | None = None
    task_id: str | None = None
    task_title: str | None = None
    slug: str | None = None
    # Launch surface/client. surface = provider × launcher (e.g. claude-code-cli,
    # claude-code-desktop, claude-crew); client = which CLI/tool invoked it
    # (claude-code, claude-desktop, polecat, crew, github-actions).
    surface: str | None = None
    client: str | None = None

    # Context (CC 2.1+ / Gemini)
    session_kind: str | None = None
    user_type: str | None = None
    entrypoint: str | None = None
    cwd: str | None = None
    client_version: str | None = None
    git_branches: list[str] = field(default_factory=list)
    permission_modes: list[str] = field(default_factory=list)
    permission_denials: list = field(default_factory=list)
    terminal_reason: str | None = None
    models: list[str] = field(default_factory=list)
    session_type: str | None = None
    gemini_version: str | None = None
    outcome: str | None = None

    # Linkage and Identity fields
    agent: str | None = None
    commissioned_as: str | None = None
    parent_session: str | None = None
    launched_by: str | None = None
    subagent_type: str | None = None


def extract_session_context(entries: list[Entry]) -> dict[str, Any]:
    """Extract session-level metadata from entries.

    Returns first-seen values for categorical fields, and unique sets
    for fields that can change mid-session (git_branch, permission_mode, model).
    """
    ctx: dict[str, Any] = {
        "session_kind": None,
        "user_type": None,
        "entrypoint": None,
        "cwd": None,
        "client_version": None,
        "git_branches": [],
        "permission_modes": [],
        "permission_denials": [],
        "terminal_reason": None,
        "models": [],
    }
    branches = set()
    perms = set()
    models = set()

    has_queue_op = False
    for e in entries:
        if not ctx["session_kind"] and e.session_kind:
            ctx["session_kind"] = e.session_kind
        if not ctx["user_type"] and e.user_type:
            ctx["user_type"] = e.user_type
        if not ctx["entrypoint"] and e.entrypoint:
            ctx["entrypoint"] = e.entrypoint
        if not ctx["cwd"] and e.cwd:
            ctx["cwd"] = e.cwd
        if not ctx["client_version"] and e.client_version:
            ctx["client_version"] = e.client_version
        if e.git_branch:
            branches.add(e.git_branch)
        if e.permission_mode:
            perms.add(e.permission_mode)
        if e.model:
            models.add(e.model)
        if e.permission_denials:
            ctx["permission_denials"].extend(e.permission_denials)
        if e.terminal_reason and not ctx["terminal_reason"]:
            ctx["terminal_reason"] = e.terminal_reason
        if e.type == "queue-operation":
            has_queue_op = True

    # Sessions dispatched via the SDK task queue are worker/autonomous sessions,
    # not interactive ones. Mark them so classifiers can detect them without
    # needing a task_id (which queue-dispatched sessions often lack).
    if has_queue_op and not ctx["session_kind"]:
        ctx["session_kind"] = "queued"

    ctx["git_branches"] = sorted(list(branches))
    ctx["permission_modes"] = sorted(list(perms))
    ctx["models"] = sorted(list(models))
    return ctx


@dataclass
class TimingInfo:
    """Timing information for turns."""

    is_first: bool = False
    start_time_local: datetime | None = None
    offset_from_start: str | None = None
    duration: str | None = None
    total_tokens: int | None = None
    estimated_tokens: bool = False


@dataclass
class ConversationTurn:
    """A single conversation turn."""

    user_message: str | None = None
    assistant_sequence: list[dict[str, Any]] = field(default_factory=list)
    timing_info: TimingInfo | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    hook_context: dict[str, Any] = field(default_factory=dict)
    inline_hooks: list[dict[str, Any]] = field(default_factory=list)
    is_meta: bool = False  # True if this is system-injected context, not actual user input
    tool_timings: dict[str, dict] = field(default_factory=dict)
    # Token usage fields
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_create_tokens: int | None = None
    cache_read_tokens: int | None = None
    thoughts_tokens: int | None = None
    model: str | None = None


class SessionState(Enum):
    """Current processing state of a session."""

    PENDING_TRANSCRIPT = auto()  # Needs transcript generation
    PENDING_MINING = auto()  # Has transcript, needs Gemini mining
    PROCESSED = auto()  # Fully processed


@dataclass
class SessionInfo:
    """Information about a discovered session."""

    path: Path
    project: str
    session_id: str
    last_modified: datetime
    source: str = "claude"  # "claude", "gemini", or "antigravity"

    @property
    def project_display(self) -> str:
        """Human-readable project name."""
        # Convert "-home-nic-src-aOps" to "aOps"
        if self.project.startswith("-"):
            parts = self.project.split("-")
            return parts[-1] if parts else self.project
        return self.project


# --- Helper Functions ---


def _read_task_output_file(output_path: str) -> str | None:
    """Read content from a task agent output file."""
    try:
        path = Path(output_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def _is_subagent_jsonl(text: str) -> bool:
    """Check if text content looks like subagent JSONL output."""
    if not text or len(text) < 50:
        return False

    # Check first few lines for subagent markers
    lines = text.split("\n")[:5]
    for line in lines:
        # Strip line number prefix (e.g., "1→" or "     1→")
        stripped = line.lstrip()
        if "→" in stripped:
            # Extract JSON part after arrow
            json_part = stripped.split("→", 1)[-1].strip()
        else:
            json_part = stripped

        if not json_part:
            continue

        # Check for subagent markers in JSON
        if (
            '"isSidechain":true' in json_part
            or '"agentId":' in json_part
            or ('"type":"user"' in json_part and '"sessionId":' in json_part)
        ):
            return True

    return False


def _adjust_heading_levels(text: str, increase_by: int = 2) -> str:
    """Adjust markdown heading levels in text content."""
    if not text or increase_by <= 0:
        return text

    lines = text.split("\n")
    adjusted = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            adjusted.append(line)
            continue

        if in_code_block:
            adjusted.append(line)
            continue

        # Check if line starts with markdown heading
        if line.startswith("#"):
            # Count existing heading level
            level = 0
            for char in line:
                if char == "#":
                    level += 1
                else:
                    break

            # Only adjust if it looks like a heading (has space after #s)
            if level > 0 and len(line) > level and line[level] == " ":
                # Increase level, cap at 6 (max markdown heading)
                new_level = min(level + increase_by, 6)
                adjusted.append("#" * new_level + line[level:])
            else:
                adjusted.append(line)
        else:
            adjusted.append(line)

    return "\n".join(adjusted)


def _quote_block(text: str) -> str:
    """Wrap text in markdown blockquotes."""
    if not text:
        return ""
    return "\n".join(f"> {line}" for line in text.split("\n"))


def _parse_subagent_output(text: str, heading_level: int = 4) -> tuple[str, list[Entry]] | None:
    """Parse raw subagent JSONL output into formatted markdown."""
    if not text:
        return None

    entries: list[Entry] = []
    agent_id = None

    for line in text.split("\n"):
        # Strip line number prefix (e.g., "1→" or "     1→")
        stripped = line.strip()
        if not stripped:
            continue

        if "→" in stripped:
            # Extract JSON part after arrow
            json_part = stripped.split("→", 1)[-1].strip()
        else:
            json_part = stripped

        if not json_part or not json_part.startswith("{"):
            continue

        try:
            data = json.loads(json_part)
            entry = Entry.from_dict(data)
            entries.append(entry)

            # Capture agent ID from first entry
            if not agent_id and data.get("agentId"):
                agent_id = data["agentId"]
        except json.JSONDecodeError:
            continue

    if not entries:
        return None

    # Format entries using similar logic to _extract_sidechain but with heading levels
    output_parts = []

    for entry in entries:
        if entry.type == "assistant" and entry.message:
            content = entry.message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_content = block.get("text", "").strip()
                            if text_content:
                                # Adjust heading levels in subagent text
                                adjusted = _adjust_heading_levels(text_content, 2)
                                output_parts.append(adjusted + "\n")
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "Unknown")
                            tool_input = block.get("input", {})
                            # Compact tool representation
                            if tool_name in ("Read", "Write", "Edit"):
                                file_path = tool_input.get("file_path", "")
                                short_path = (
                                    file_path.split("/")[-1] if "/" in file_path else file_path
                                )
                                output_parts.append(f"- {tool_name}({short_path})\n")
                            elif tool_name == "Bash":
                                cmd = str(tool_input.get("command", ""))
                                if len(cmd) > 60:
                                    cmd = cmd[:57] + "..."
                                cmd = cmd.replace("`", "'")
                                output_parts.append(f"- Bash({cmd})\n")
                            else:
                                output_parts.append(f"- {tool_name}(...)\n")

    if not output_parts:
        return None

    # Build markdown with agent header and blockquotes
    markdown = ""
    # We use bold for subagent header inside quote instead of heading to avoid clutter
    if agent_id:
        markdown = f"**Subagent: {agent_id}**\n\n"
    else:
        markdown = "**Subagent Output**\n\n"

    content = "".join(output_parts)
    markdown += content

    # Wrap everything in quotes
    quoted_markdown = _quote_block(markdown)

    return quoted_markdown, entries


def _extract_task_notifications(text: str) -> list[dict[str, str]]:
    """Extract task-notification tags from text content."""
    notifications = []
    pattern = r"<task-notification>\s*<task-id>([^<]+)</task-id>\s*<output-file>([^<]+)</output-file>\s*<status>([^<]+)</status>\s*<summary>([^<]+)</summary>\s*</task-notification>"

    for match in re.finditer(pattern, text, re.DOTALL):
        notifications.append(
            {
                "task_id": match.group(1).strip(),
                "output_file": match.group(2).strip(),
                "status": match.group(3).strip(),
                "summary": match.group(4).strip(),
            }
        )

    return notifications


def _extract_exit_code_from_content(content: str, is_error: bool) -> int | None:
    """Extract exit code from tool result content.

    Exit codes appear in the content as "Exit code N\n..." prefix when is_error=True.
    For successful commands (is_error=False), exit code is implicitly 0.

    Args:
        content: Tool result content string
        is_error: Whether the tool result is marked as an error

    Returns:
        Exit code as integer, or None if not determinable
    """
    if not is_error:
        return 0  # Successful commands have exit code 0

    if not content:
        return None

    # Parse "Exit code N\n" prefix
    if content.startswith("Exit code "):
        # Find the number after "Exit code "
        rest = content[10:]  # Skip "Exit code "
        newline_pos = rest.find("\n")
        if newline_pos > 0:
            code_str = rest[:newline_pos].strip()
        else:
            code_str = rest.split()[0] if rest else ""

        try:
            return int(code_str)
        except (ValueError, IndexError):
            pass

    # If is_error but no explicit exit code, it's a non-zero exit
    return 1  # Default to 1 for errors without explicit code


def _estimate_tokens(text: str) -> int:
    """Estimate token count from raw text.

    Uses the standard ``len(text) // 4`` rough-equivalence: roughly four
    characters per token for English-and-code mixed text. Caller renders
    with a ``~`` prefix to flag the approximation.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _format_token_count(n: int) -> str:
    """Compact token-count format for inline transcript annotations.

    Examples: 87 -> "87", 1234 -> "1.2k", 12345 -> "12k", 1234567 -> "1.2M".
    """
    if n < 1000:
        return str(n)
    if n < 10_000:
        return f"{n / 1000:.1f}k"
    if n < 1_000_000:
        return f"{n // 1000}k"
    return f"{n / 1_000_000:.1f}M"


def _summarize_tool_input(tool_name: str, tool_input: dict) -> str:
    """Create a brief summary of tool input for error context."""
    if tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        if path:
            # Just show filename
            return path.split("/")[-1] if "/" in path else path
    elif tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))[:60]
        return cmd + "..." if len(cmd) >= 60 else cmd
    elif tool_name == "Glob":
        return tool_input.get("pattern", "")[:40]
    elif tool_name == "Grep":
        return tool_input.get("pattern", "")[:40]
    elif tool_name in ("Agent", "Task"):
        return tool_input.get("description", "")[:40]

    # Generic fallback: first string value
    for v in tool_input.values():
        if isinstance(v, str) and v:
            return v[:40] + "..." if len(v) > 40 else v
    return ""


class SessionProcessor:
    """Processes JSONL sessions into structured data."""

    def parse_session_file(
        self,
        file_path: str | Path,
        load_agents: bool = True,
        load_hooks: bool = True,
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """
        Parse session file (Claude JSONL, Gemini JSON, or Antigravity brain dir).

        Also loads related agent files and hook files.

        Returns:
            (session_summary, entries, agent_entries)
        """
        file_path = Path(file_path)

        # 1. Parse filename for metadata (backward compatibility and context)
        parsed = session_naming.parse_session_filename(str(file_path))

        # 2. Parse the content
        if file_path.is_dir():
            summary, entries, agents = self._parse_antigravity_brain(file_path)
        elif file_path.suffix.lower() == ".json":
            summary, entries, agents = self._parse_gemini_json(file_path)
        elif file_path.name == "audit.jsonl":
            summary, entries, agents = self._parse_jsonl_file(
                file_path, load_agents=False, load_hooks=False
            )
        elif _is_gemini_chat_jsonl(file_path):
            summary, entries, agents = self._parse_gemini_chat_jsonl(file_path)
        else:
            summary, entries, agents = self._parse_jsonl_file(
                file_path, load_agents=load_agents, load_hooks=load_hooks
            )

        # 2b. Load hook entries for non-Claude parsers (Gemini, Antigravity).
        # Claude's _parse_jsonl_file already loads hooks internally; the others
        # don't, so hook failures and gate output are invisible in their
        # transcripts without this.
        _claude_loaded_hooks = not (
            file_path.is_dir()
            or file_path.suffix.lower() == ".json"
            or file_path.name == "audit.jsonl"
            or _is_gemini_chat_jsonl(file_path)
        )
        if load_hooks and not _claude_loaded_hooks:
            hook_entries: list[Entry] = []
            for hook_file in self._find_hook_files(file_path):
                hook_entries.extend(self._load_hook_entries(hook_file))
            if hook_entries:
                entries.extend(hook_entries)
                entries.sort(
                    key=lambda e: e.timestamp if e.timestamp else datetime.min.replace(tzinfo=UTC),
                )
            entries = self._consolidate_hook_error_attachments(entries)

        # 3. Augment summary with metadata from filename and environment
        if parsed:
            summary.machine = summary.machine or parsed.machine
            summary.provider = summary.provider or parsed.provider
            summary.crew = summary.crew or parsed.crew
            summary.repo = summary.repo or parsed.repo
            summary.slug = summary.slug or parsed.slug

        # Fallback to environment/inference if missing
        summary.machine = summary.machine or os.environ.get("AOPS_MACHINE")
        summary.hostname = summary.hostname or session_naming.get_hostname()
        summary.provider = (
            summary.provider or session_naming.infer_provider_from_path(file_path) or "claude"
        )
        # Crew identity is data-about-the-session, not data-about-the-runtime.
        # Never fall back to POLECAT_CREW_NAME — for offline conversions (e.g.
        # sync_gha_sessions.py running inside a crew worker), the env reflects
        # the *transcribing* process, not the original session, and would taint
        # GHA-sourced transcripts with a bogus crew label (issue #768).
        #
        # Path-based inference via infer_session_origin_from_path is the only
        # correct signal: it returns crew=None for github/, polecats/, and
        # gemini paths, and only sets crew when the path is under crew/<name>/.
        # The filename-derived parsed.crew (set above) covers shortform names.
        if not summary.crew:
            origin = session_naming.infer_session_origin_from_path(
                file_path, provider=summary.provider
            )
            summary.crew = origin.get("crew")
        if not summary.repo:
            # We can't use get_repo_name() safely here as it might be a different repo
            # than the one we are running in.
            pass
        summary.task_id = summary.task_id or os.environ.get("AOPS_TASK_ID")
        if not summary.slug and entries:
            summary.slug = self.generate_session_slug(entries)

        if entries:
            valid_timestamps = [e.timestamp for e in entries if e.timestamp]
            if valid_timestamps:
                started_at = min(valid_timestamps)
                last_modified = max(valid_timestamps)
                if "started_at" not in summary.details:
                    summary.details["started_at"] = started_at.isoformat()
                if "last_modified" not in summary.details:
                    summary.details["last_modified"] = last_modified.isoformat()
                if "ended_at" not in summary.details:
                    summary.details["ended_at"] = last_modified.isoformat()

        return summary, entries, agents

    def parse_jsonl(
        self,
        file_path: str | Path,
        load_agents: bool = True,
        load_hooks: bool = True,
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Alias for parse_session_file (backward compatibility)."""
        return self.parse_session_file(file_path, load_agents=load_agents, load_hooks=load_hooks)

    def _parse_gemini_message_dict(self, msg: dict) -> list[Entry]:
        """Parse one Gemini message-style dict into one or two Entry objects.

        Handles the schema used by both the legacy bundled ``.json`` chat
        dump (``{messages: [...]}``) and the current Gemini CLI per-line
        chat-jsonl format (``session-*.jsonl`` under ``.gemini/tmp/<proj>/chats/``).

        Each message has shape::

            {"id", "timestamp", "type": "user"|"gemini"|...,
             "content": str | [parts], "toolCalls"?: [...], "tokens"?, "model"?, "thoughts"?}

        Non user/gemini types (e.g. ``info``) return an empty list.
        """
        msg_type = msg.get("type", "unknown")
        if msg_type not in ("user", "gemini"):
            return []

        timestamp_str = msg.get("timestamp")
        timestamp = None
        if timestamp_str:
            try:
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(timestamp_str)
                timestamp = dt.astimezone()
            except (ValueError, TypeError):
                pass

        entry_type = "assistant" if msg_type == "gemini" else "user"

        content_raw = msg.get("content", "")
        content_text = ""
        if isinstance(content_raw, str):
            content_text = content_raw
        elif isinstance(content_raw, list):
            text_parts = []
            for part in content_raw:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    if "text" in part:
                        text_parts.append(part["text"])
                    elif "content" in part:
                        text_parts.append(str(part["content"]))
            content_text = "".join(text_parts)

        content_blocks: list[dict] = []
        if content_text:
            content_blocks.append({"type": "text", "text": content_text})

        tool_calls = msg.get("toolCalls", [])
        tool_results_to_add: list[dict] = []

        if entry_type == "assistant" and tool_calls:
            for tool_call in tool_calls:
                call_id = tool_call.get("id")
                name = tool_call.get("name")
                args = tool_call.get("args", {})

                content_blocks.append(
                    {"type": "tool_use", "id": call_id, "name": name, "input": args}
                )

                result_data = tool_call.get("result", [])
                tool_output = ""
                is_error = False

                if result_data and isinstance(result_data, list):
                    first_res = result_data[0]
                    if "functionResponse" in first_res:
                        resp = first_res["functionResponse"].get("response", {})
                        if "output" in resp:
                            tool_output = str(resp["output"])
                        elif "error" in resp:
                            tool_output = str(resp["error"])
                            is_error = True
                        else:
                            tool_output = json.dumps(resp)
                    else:
                        tool_output = json.dumps(result_data)
                elif tool_call.get("status") == "error":
                    is_error = True
                    tool_output = tool_call.get("resultDisplay") or "Error executing tool"
                elif tool_call.get("resultDisplay"):
                    tool_output = tool_call.get("resultDisplay")

                tool_results_to_add.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "content": tool_output,
                        "is_error": is_error,
                    }
                )

        gemini_thoughts = msg.get("thoughts") if isinstance(msg.get("thoughts"), list) else None
        gemini_tokens = msg.get("tokens") or {}
        gemini_model = msg.get("model")

        out: list[Entry] = []
        out.append(
            Entry(
                type=entry_type,
                uuid=msg.get("id", ""),
                timestamp=timestamp,
                message={"content": content_blocks if content_blocks else content_text},
                content={"content": content_blocks if content_blocks else content_text},
                model=gemini_model,
                input_tokens=gemini_tokens.get("input") if gemini_tokens else None,
                output_tokens=gemini_tokens.get("output") if gemini_tokens else None,
                cache_read_input_tokens=gemini_tokens.get("cached") if gemini_tokens else None,
                thoughts=gemini_thoughts if gemini_thoughts else None,
                thoughts_tokens=gemini_tokens.get("thoughts") if gemini_tokens else None,
            )
        )

        if tool_results_to_add:
            out.append(
                Entry(
                    type="user",
                    uuid=f"result-{msg.get('id', '')}",
                    timestamp=timestamp,
                    message={"content": tool_results_to_add},
                    content={"content": tool_results_to_add},
                )
            )
        return out

    def _parse_gemini_json(
        self, file_path: Path
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Parse Gemini JSON session file (legacy bundled ``.json`` format)."""
        entries: list[Entry] = []
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return SessionSummary(uuid=file_path.stem), [], {}

        session_id = data.get("sessionId", file_path.stem)
        start_time_str = data.get("startTime")

        session_summary = SessionSummary(
            uuid=session_id,
            summary="Gemini CLI Session",
            created_at=start_time_str or "",
        )

        for msg in data.get("messages", []):
            entries.extend(self._parse_gemini_message_dict(msg))

        return session_summary, entries, {}

    def _parse_gemini_chat_jsonl(
        self, file_path: Path
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Parse Gemini CLI chat-jsonl session files.

        Each line is one message in the Gemini API conversation schema:

            {"role": "user"|"model", "parts": [...]}

        Where ``parts`` items are dicts with one of:
          - ``text``: free-form text
          - ``functionCall``: ``{"name": str, "args": dict}``
          - ``functionResponse``: ``{"name": str, "response": dict|str}``

        Some Gemini CLI variants annotate entries with ``timestamp``, ``id``,
        ``model``, or ``tokens`` — we read these when present but treat them
        as optional.

        Returns standard (summary, entries, agents) tuple. Tool results in a
        ``model`` entry's parts are routed to a synthetic ``user``-typed entry
        so downstream rendering treats them like Claude tool_results.
        """
        # Derive 8-char session id from filename: session-<...>-<8hex>.jsonl
        stem = file_path.stem
        if stem.startswith("session-") and "-" in stem:
            short_id = stem.split("-")[-1]
        else:
            short_id = stem

        entries: list[Entry] = []
        first_text: str | None = None
        first_ts: datetime | None = None
        project_hash: str | None = None

        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return SessionSummary(uuid=short_id), [], {}

        idx = 0
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue

            # Skip Gemini CLI bookkeeping lines: metadata header
            # ({sessionId, projectHash, startTime, ...}) and `$set` updates.
            if "$set" in obj and len(obj) == 1:
                continue
            if "sessionId" in obj and "role" not in obj and "type" not in obj:
                if not project_hash:
                    project_hash = obj.get("projectHash")
                if first_ts is None:
                    st = obj.get("startTime")
                    if isinstance(st, str):
                        try:
                            s = st.replace("Z", "+00:00") if st.endswith("Z") else st
                            first_ts = datetime.fromisoformat(s).astimezone()
                        except (ValueError, TypeError):
                            pass
                continue

            role = obj.get("role")
            parts = obj.get("parts")
            # Message-style schema (current Gemini CLI chat-jsonl):
            # {id, timestamp, type: "user"|"gemini"|"info", content, toolCalls?, ...}
            if role is None and obj.get("type") in ("user", "gemini"):
                msg_entries = self._parse_gemini_message_dict(obj)
                for me in msg_entries:
                    if me.timestamp and first_ts is None:
                        first_ts = me.timestamp
                    if me.type == "user" and first_text is None:
                        # Pull first user text for Original Request capture
                        c = me.message.get("content") if isinstance(me.message, dict) else None
                        if isinstance(c, list):
                            for blk in c:
                                if isinstance(blk, dict) and blk.get("type") == "text":
                                    t = (blk.get("text") or "").strip()
                                    if t:
                                        first_text = t
                                        break
                        elif isinstance(c, str) and c.strip():
                            first_text = c.strip()
                entries.extend(msg_entries)
                continue
            # Skip non-conversation lines (e.g. type=="info").
            if role not in ("user", "model") or not isinstance(parts, list):
                continue

            idx += 1
            entry_uuid = obj.get("id") or f"gemini-{short_id}-{idx}"

            timestamp = None
            ts_str = obj.get("timestamp")
            if isinstance(ts_str, str):
                try:
                    s = ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str
                    timestamp = datetime.fromisoformat(s).astimezone()
                except (ValueError, TypeError):
                    timestamp = None
            if timestamp and first_ts is None:
                first_ts = timestamp

            tokens = obj.get("tokens") or {}
            model_name = obj.get("model")

            text_chunks: list[str] = []
            tool_uses: list[dict] = []
            tool_results: list[dict] = []

            for i, part in enumerate(parts):
                if not isinstance(part, dict):
                    if isinstance(part, str):
                        text_chunks.append(part)
                    continue
                if "text" in part and isinstance(part["text"], str):
                    text_chunks.append(part["text"])
                elif "functionCall" in part and isinstance(part["functionCall"], dict):
                    fc = part["functionCall"]
                    call_id = fc.get("id") or f"{entry_uuid}-call-{i}"
                    tool_uses.append(
                        {
                            "type": "tool_use",
                            "id": call_id,
                            "name": fc.get("name", ""),
                            "input": fc.get("args", {}) or {},
                        }
                    )
                elif "functionResponse" in part and isinstance(part["functionResponse"], dict):
                    fr = part["functionResponse"]
                    call_id = fr.get("id") or f"{entry_uuid}-resp-{i}"
                    resp = fr.get("response")
                    is_error = False
                    if isinstance(resp, dict):
                        if "error" in resp:
                            tool_output = str(resp["error"])
                            is_error = True
                        elif "output" in resp:
                            tool_output = str(resp["output"])
                        else:
                            tool_output = json.dumps(resp)
                    else:
                        tool_output = "" if resp is None else str(resp)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call_id,
                            "content": tool_output,
                            "is_error": is_error,
                        }
                    )

            text = "".join(text_chunks).strip()

            # Capture first user-role text as Original Request
            if role == "user" and first_text is None and text:
                first_text = text

            # Build content blocks for the main entry
            content_blocks: list[dict] = []
            if text:
                content_blocks.append({"type": "text", "text": text})
            if tool_uses:
                content_blocks.extend(tool_uses)

            entry_type = "assistant" if role == "model" else "user"
            # If a user line carried only functionResponse parts, keep it as
            # a user entry whose content is the tool_results — matches the
            # Claude convention where tool_result blocks live in user entries.
            if role == "user" and tool_results and not content_blocks:
                main_content = tool_results
            else:
                main_content = content_blocks if content_blocks else text

            entry = Entry(
                type=entry_type,
                uuid=entry_uuid,
                timestamp=timestamp,
                message={"content": main_content},
                content={"content": main_content},
                model=model_name if isinstance(model_name, str) else None,
                input_tokens=tokens.get("input") if isinstance(tokens, dict) else None,
                output_tokens=tokens.get("output") if isinstance(tokens, dict) else None,
                cache_read_input_tokens=tokens.get("cached") if isinstance(tokens, dict) else None,
                thoughts_tokens=tokens.get("thoughts") if isinstance(tokens, dict) else None,
            )
            entries.append(entry)

            # If a model entry produced tool_results (rare — usually
            # functionResponse appears in user-role lines), append a synthetic
            # user entry to carry them so renderers see them after the call.
            if role == "model" and tool_results:
                entries.append(
                    Entry(
                        type="user",
                        uuid=f"result-{entry_uuid}",
                        timestamp=timestamp,
                        message={"content": tool_results},
                        content={"content": tool_results},
                    )
                )

        # Look for sidecar metadata in parent directory (~/.gemini/tmp/<project>/)
        sidecar_path = None
        for candidate in file_path.parent.parent.glob(f"*{short_id}*-session.json"):
            sidecar_path = candidate
            break

        sidecar_data = {}
        if sidecar_path and sidecar_path.exists():
            try:
                with open(sidecar_path, encoding="utf-8") as f:
                    sidecar_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        details = {}
        if sidecar_data:
            details["gates"] = sidecar_data.get("gates")
            details["global_turn_count"] = sidecar_data.get("global_turn_count")
            main_agent = sidecar_data.get("main_agent", {})
            details["main_agent_todos"] = {
                "completed": main_agent.get("todos_completed", 0),
                "total": main_agent.get("todos_total", 0),
            }
            details["started_at"] = sidecar_data.get("started_at")
            details["ended_at"] = sidecar_data.get("ended_at")
            if project_hash:
                details["project_hash"] = project_hash

        summary = SessionSummary(
            uuid=short_id,
            summary="Gemini CLI Session",
            created_at=first_ts.isoformat() if first_ts else "",
            session_type=sidecar_data.get("session_type"),
            gemini_version=sidecar_data.get("version"),
            task_id=sidecar_data.get("main_agent", {}).get("current_task"),
            details=details,
        )
        return summary, entries, {}

    def _parse_jsonl_file(
        self,
        file_path: Path,
        load_agents: bool = True,
        load_hooks: bool = True,
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Parse Claude Code JSONL session file."""
        entries = []
        session_summary = None
        session_uuid = file_path.stem

        # Track UUIDs of conversation entries we've already emitted so we can
        # skip Cowork-style replays. Cowork audit logs include both the
        # original user/assistant entry and a later "replay" copy with the
        # same UUID and a slightly later `_audit_timestamp` (the replay marks
        # itself with `isReplay: true`). Both arms must be deduped or every
        # downstream consumer (turns, timeline_events) sees the prompt twice.
        seen_uuids: set[str] = set()

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)

                    # Handle hook logs passed as main file
                    if file_path.name.endswith("-hooks.jsonl"):
                        data = self._map_hook_jsonl_to_entry_data(data)

                    # Drop replay entries outright — same UUID, same content,
                    # later timestamp; a pure duplicate of the original.
                    if data.get("isReplay") is True:
                        continue

                    entry = Entry.from_dict(data)

                    # Dedupe user/assistant entries by UUID (first occurrence
                    # wins). System events, hook entries, etc. are not
                    # deduped — they can legitimately repeat.
                    if entry.type in ("user", "assistant") and entry.uuid:
                        if entry.uuid in seen_uuids:
                            continue
                        seen_uuids.add(entry.uuid)

                    entries.append(entry)

                    # Extract summary if available
                    if entry.type == "summary":
                        summary_text = entry.content.get("summary", "Claude Code Session")
                        session_summary = SessionSummary(uuid=session_uuid, summary=summary_text)
                except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError):
                    continue

        # Create default summary if none found
        if not session_summary:
            session_summary = SessionSummary(uuid=session_uuid)

        # Load agent entries from agent-*.jsonl files
        agent_entries = {}
        if load_agents:
            agent_entries = self._load_agent_files(file_path)

        # Load hook entries if hook file(s) exist. A long session is split
        # across multiple per-minute hook files (router.sh rotates by clock
        # minute), so we must load all matching files, not just the first.
        if load_hooks:
            for hook_file in self._find_hook_files(file_path):
                entries.extend(self._load_hook_entries(hook_file))
            # Sort by timestamp to maintain chronological order
            entries.sort(
                key=lambda e: e.timestamp if e.timestamp else datetime.min.replace(tzinfo=UTC)
            )
            entries = self._merge_cc_stop_summaries(entries)

        entries = self._consolidate_hook_error_attachments(entries)

        return session_summary, entries, agent_entries

    @staticmethod
    def _consolidate_hook_error_attachments(entries: list[Entry]) -> list[Entry]:
        """Collapse identical hook_non_blocking_error entries session-wide.

        When every hook fails with the same traceback (e.g. an import error in
        router.py), the JSONL contains one attachment per hook invocation —
        easily 50+. We emit one consolidated entry at the position of the first
        occurrence and suppress the rest.

        Entries from our hook JSONL or CC's stop_hook_summary are NOT
        consolidated — they carry richer payloads that should render
        individually.
        """
        if not entries:
            return entries

        def _is_attachment_hook_error(e: Entry) -> bool:
            return (
                e.type == "system_reminder"
                and e.hook_exit_code is not None
                and e.hook_exit_code != 0
                and not e.hook_is_cc_summary
                and not e.hook_verdict
                and not e.hook_system_message
                and not e.hook_context_injection
            )

        # First pass: collect all attachment hook errors grouped by error text.
        groups: dict[str, list[Entry]] = {}
        for entry in entries:
            if _is_attachment_hook_error(entry):
                key = entry.additional_context or ""
                groups.setdefault(key, []).append(entry)

        if not groups:
            return entries

        # Build the consolidated entry for each error group. Track the UUID
        # of the first entry so we know where to insert it.
        first_uuids: dict[str, Entry] = {}  # error_key -> consolidated Entry
        consumed_uuids: set[str] = set()
        for group in groups.values():
            first = group[0]
            event_names: list[str] = []
            for e in group:
                name = e.hook_event_name or "Hook"
                if name not in event_names:
                    event_names.append(name)
            error_text = first.additional_context or ""
            if len(group) > 1:
                summary = f"{len(group)} hook failures ({', '.join(event_names)})\n\n{error_text}"
            else:
                summary = error_text
            consolidated = Entry(
                type="system_reminder",
                uuid=first.uuid,
                parent_uuid=first.parent_uuid,
                timestamp=first.timestamp,
                hook_event_name=", ".join(event_names),
                hook_exit_code=1,
                additional_context=summary,
            )
            first_uuids[first.uuid] = consolidated
            consumed_uuids.update(e.uuid for e in group)

        # Second pass: emit the consolidated entry at the first occurrence,
        # suppress all others.
        result: list[Entry] = []
        for entry in entries:
            if entry.uuid in first_uuids:
                result.append(first_uuids.pop(entry.uuid))
            elif entry.uuid in consumed_uuids:
                continue
            else:
                result.append(entry)
        return result

    # antigravity-cli (new format) step types that represent tool executions.
    # The step `type` is the tool identity and its `content` is the result;
    # we map each to a human-readable tool name for the renderer.
    _ANTIGRAVITY_TOOL_NAMES = {
        "VIEW_FILE": "ViewFile",
        "LIST_DIRECTORY": "ListDirectory",
        "GREP_SEARCH": "GrepSearch",
        "SEARCH_WEB": "SearchWeb",
        "READ_URL_CONTENT": "ReadUrl",
        "RUN_COMMAND": "RunCommand",
        "CODE_ACTION": "CodeAction",
        "MCP_TOOL": "McpTool",
        "GENERIC": "Task",
    }

    @staticmethod
    def _antigravity_step_timestamp(value: Any) -> datetime | None:
        """Parse an antigravity step ``created_at`` (ISO 8601, usually Z)."""
        if not isinstance(value, str) or not value:
            return None
        try:
            s = value.replace("Z", "+00:00") if value.endswith("Z") else value
            return datetime.fromisoformat(s).astimezone()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _antigravity_user_text(content: str) -> str:
        """Extract the real message from a USER_INPUT step.

        USER_INPUT content wraps the message in ``<USER_REQUEST>…</USER_REQUEST>``
        and trails system boilerplate (``<ADDITIONAL_METADATA>``, settings-change
        notices). Return just the request when present, else the raw content.
        """
        if not content:
            return ""
        m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.DOTALL)
        if m:
            return m.group(1).strip()
        return content.strip()

    @staticmethod
    def _antigravity_tool_desc(content: str) -> str:
        """Best-effort one-line label for an antigravity tool step."""
        if not content:
            return ""
        m = re.search(r"File Path:\s*`?([^`\n]+)`?", content)
        if m:
            return m.group(1).strip()
        m = re.search(r"Task Description:\s*([^\n]+)", content)
        if m:
            return m.group(1).strip()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("Created At:", "Completed At:")):
                continue
            return line[:120]
        return ""

    @staticmethod
    def _scrub_binary(content: str) -> str:
        """Collapse runs of binary / non-text data in antigravity tool output.

        Tool steps such as RUN_COMMAND piping a gzipped download, or a task log
        capturing a binary file, embed raw bytes that decode to U+FFFD
        replacement characters and C0/C1 control codes. Spinner glyphs (Braille
        Unicode U+2800-U+28FF) also leak into output. Real text (incl.
        non-Latin scripts and emoji — neither triggers the heuristic) passes
        through verbatim; any *line* that is dominantly binary is dropped, and
        consecutive binary lines collapse into a single
        ``[binary data omitted: N chars]`` placeholder so the transcript stays
        readable without discarding the surrounding evidence (headers, exit
        codes, ``<truncated N lines>`` markers).
        """

        def _is_suspect(c: str) -> bool:
            o = ord(c)
            # Braille spinner glyphs: U+2800-U+28FF; \n and \r are safe
            return (
                c == "�"
                or (o < 32 and c not in ("\t", "\n", "\r"))
                or 127 <= o <= 159
                or 0x2800 <= o <= 0x28FF
            )

        # Fast path: no binary signal at all → return unchanged.
        if not any(_is_suspect(c) for c in content):
            return content

        out: list[str] = []
        run = 0  # accumulated char count of the current binary run
        for line in content.split("\n"):
            bad = sum(1 for c in line if _is_suspect(c))
            if line and bad / len(line) > 0.15:
                run += len(line)
                continue
            if run:
                out.append(f"[binary data omitted: {run} chars]")
                run = 0
            out.append(line)
        if run:
            out.append(f"[binary data omitted: {run} chars]")
        return "\n".join(out)

    def _parse_antigravity_transcript_jsonl(
        self, brain_dir: Path, transcript_path: Path
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Parse an antigravity-cli structured transcript jsonl into entries.

        Each line is one step:
        ``{step_index, source, type, status, created_at, content, thinking, tool_calls}``.

        - USER_INPUT          → user text turn
        - PLANNER_RESPONSE    → assistant thinking + tool_use items (from tool_calls field)
        - tool steps          → user tool_result (paired with preceding PLANNER_RESPONSE tool_calls)
        - SYSTEM_MESSAGE/ERROR_MESSAGE → tool_result-style feedback turns
        - EPHEMERAL_MESSAGE / CONVERSATION_HISTORY → skipped (boilerplate/empty)
        """
        session_id = brain_dir.name
        entries: list[Entry] = []
        first_ts: datetime | None = None
        first_user: str | None = None
        model_name: str | None = None

        records: list[dict] = []
        try:
            with open(transcript_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        records.append(obj)
        except OSError:
            return SessionSummary(uuid=session_id), [], {}

        records.sort(key=lambda o: o.get("step_index", 0))

        def _add(entry_type: str, uuid: str, blocks: list[dict], ts, model=None) -> None:
            payload = {"content": blocks}
            entries.append(
                Entry(
                    type=entry_type,
                    uuid=uuid,
                    timestamp=ts,
                    message=payload,
                    content=payload,
                    model=model,
                )
            )

        def _unwrap_json_string(value: str) -> str:
            """Unwrap double-JSON-encoded strings (e.g., '\"gh pr view\"' → 'gh pr view')."""
            if not value or not isinstance(value, str):
                return value
            # Antigravity args are JSON-encoded strings: "\"gh pr view 1604 --comments\""
            # Strip outer quotes if present
            if value.startswith('"') and value.endswith('"'):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value

        # Track pending tool calls from PLANNER_RESPONSE to pair with tool results
        pending_tool_calls: list[tuple[str, dict]] = []  # [(tool_use_id, tool_call_dict)]

        for obj in records:
            rtype = obj.get("type")
            status = obj.get("status")
            content = obj.get("content") or ""
            ts = self._antigravity_step_timestamp(obj.get("created_at"))
            if ts and first_ts is None:
                first_ts = ts
            step = obj.get("step_index", len(entries))

            if rtype in ("EPHEMERAL_MESSAGE", "CONVERSATION_HISTORY"):
                continue

            if rtype == "USER_INPUT":
                mm = re.search(r"Model Selection`?\s*from\s*\S+\s*to\s*([^\.\n]+)", content)
                if mm and not model_name:
                    model_name = mm.group(1).strip()
                text = self._antigravity_user_text(content)
                if not text:
                    continue
                if first_user is None:
                    first_user = text
                _add("user", f"{session_id}-u-{step}", [{"type": "text", "text": text}], ts)
                continue

            if rtype == "PLANNER_RESPONSE":
                blocks = []

                # Add thinking block if present
                thinking = obj.get(
                    "thinking", ""
                )  # allow-fallback: thinking is optional in PLANNER_RESPONSE
                thinking = thinking.strip() if isinstance(thinking, str) else ""
                if thinking:
                    blocks.append({"type": "thinking", "thinking": thinking})

                # Process tool_calls into tool_use blocks
                tool_calls = obj.get("tool_calls", [])  # allow-fallback: tool_calls is optional
                if tool_calls and isinstance(tool_calls, list):
                    for idx, call in enumerate(tool_calls):
                        if not isinstance(call, dict):
                            continue

                        tool_name = call.get("name") or ""
                        args = call.get("args", {})

                        # Map antigravity tool names to readable names
                        if tool_name == "run_command":
                            display_name = "RunCommand"
                        elif tool_name == "view_file":
                            display_name = "ViewFile"
                        elif tool_name == "grep_search":
                            display_name = "GrepSearch"
                        else:
                            display_name = tool_name.title().replace("_", "")

                        # Build tool input from args - unwrap JSON strings
                        tool_input = {}
                        if isinstance(args, dict):
                            # Extract key fields: CommandLine, toolSummary, toolAction
                            cmd_line = _unwrap_json_string(
                                args.get("CommandLine", "")
                            )  # allow-fallback: optional arg
                            tool_summary = _unwrap_json_string(
                                args.get("toolSummary", "")
                            )  # allow-fallback: optional arg
                            tool_action = _unwrap_json_string(
                                args.get("toolAction", "")
                            )  # allow-fallback: optional arg
                            abs_path = _unwrap_json_string(
                                args.get("AbsolutePath", "")
                            )  # allow-fallback: optional arg

                            # Use toolSummary as the primary description
                            if tool_summary:
                                tool_input["description"] = tool_summary
                            elif tool_action:
                                tool_input["description"] = tool_action

                            # Add command line if present
                            if cmd_line:
                                tool_input["command"] = cmd_line

                            # Add file path if present
                            if abs_path:
                                tool_input["path"] = abs_path

                        # Generate unique tool_use_id for pairing with result
                        tid = f"{session_id}-t-{step}-{idx}"
                        blocks.append(
                            {
                                "type": "tool_use",
                                "id": tid,
                                "name": display_name,
                                "input": tool_input,
                            }
                        )

                        # Track this tool call for pairing with the next tool result
                        pending_tool_calls.append((tid, call))

                # Old format: no thinking/tool_calls fields; fall back to content as text.
                if not blocks:
                    text = content.strip()
                    if text:
                        blocks.append({"type": "text", "text": text})

                if blocks:
                    _add(
                        "assistant",
                        f"{session_id}-a-{step}",
                        blocks,
                        ts,
                        model=model_name,
                    )
                continue

            # Tool result steps - pair with pending tool calls
            if rtype in self._ANTIGRAVITY_TOOL_NAMES or rtype in (
                "SYSTEM_MESSAGE",
                "ERROR_MESSAGE",
            ):
                if not content.strip():
                    continue

                is_error = status == "ERROR" or rtype == "ERROR_MESSAGE"
                clean = self._scrub_binary(content)

                if pending_tool_calls:
                    # New format: PLANNER_RESPONSE declared tool_calls; use paired id.
                    tid, _call = pending_tool_calls.pop(0)
                    _add(
                        "user",
                        f"{session_id}-tr-{step}",
                        [
                            {
                                "type": "tool_result",
                                "tool_use_id": tid,
                                "content": clean,
                                "is_error": is_error,
                            }
                        ],
                        ts,
                    )
                else:
                    # Old format: no pending call; create tool_use + tool_result pair.
                    if rtype in self._ANTIGRAVITY_TOOL_NAMES:
                        name = self._ANTIGRAVITY_TOOL_NAMES[rtype]
                    elif rtype == "SYSTEM_MESSAGE":
                        name = "System"
                    else:
                        name = "Error"
                    tid = f"{session_id}-t-{step}"
                    desc = self._antigravity_tool_desc(clean)
                    tool_input = {"description": desc} if desc else {}
                    _add(
                        "assistant",
                        f"{session_id}-ac-{step}",
                        [{"type": "tool_use", "id": tid, "name": name, "input": tool_input}],
                        ts,
                        model=model_name,
                    )
                    _add(
                        "user",
                        f"{session_id}-tr-{step}",
                        [
                            {
                                "type": "tool_result",
                                "tool_use_id": tid,
                                "content": clean,
                                "is_error": is_error,
                            }
                        ],
                        ts,
                    )
                continue

            else:
                # Unknown step type — surface it rather than dropping silently.
                if content.strip():
                    clean = self._scrub_binary(content)
                    display_name = (rtype or "Unknown").title().replace("_", "")
                    _add(
                        "user",
                        f"{session_id}-unk-{step}",
                        [{"type": "text", "text": f"[{display_name}] {clean}"}],
                        ts,
                    )

        summary_text = (
            f"Antigravity Session: {first_user[:50]}" if first_user else "Antigravity Session"
        )
        session_summary = SessionSummary(
            uuid=session_id,
            summary=summary_text,
            created_at=first_ts.isoformat() if first_ts else "",
        )
        return session_summary, entries, {}

    def _parse_antigravity_brain(
        self, brain_dir: Path
    ) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """Parse Antigravity brain directory into structured data.

        Two on-disk layouts exist:

        1. antigravity-cli (current): a structured transcript jsonl under
           ``.system_generated/logs/transcript_full.jsonl`` (preferred) — the
           full step-by-step conversation. Parsed by
           ``_parse_antigravity_transcript_jsonl``.
        2. antigravity / IDE (older): top-level markdown artifacts
           (task.md, implementation_plan.md, walkthrough.md, audit_report.md,
           requirements_rubric.md) combined into a transcript-like format.

        The jsonl is preferred when present; otherwise we fall back to the
        markdown artifacts.
        """
        session_id = brain_dir.name

        logs_dir = brain_dir / ".system_generated" / "logs"
        for _name in ("transcript_full.jsonl", "transcript.jsonl"):
            tpath = logs_dir / _name
            if tpath.exists():
                summary, jsonl_entries, agents = self._parse_antigravity_transcript_jsonl(
                    brain_dir, tpath
                )
                if jsonl_entries:
                    return summary, jsonl_entries, agents
                break  # transcript present but empty → try markdown artifacts

        entries: list[Entry] = []

        # Get modification time for timestamp
        md_files = list(brain_dir.glob("*.md"))
        if not md_files:
            return (
                SessionSummary(uuid=session_id, summary="Empty Antigravity Session"),
                [],
                {},
            )

        # Use earliest file mtime as session start
        start_time = min(datetime.fromtimestamp(f.stat().st_mtime).astimezone() for f in md_files)

        # Define the order of files to process
        file_order = [
            "task.md",
            "implementation_plan.md",
            "walkthrough.md",
            "audit_report.md",
            "requirements_rubric.md",
        ]

        # Collect content from each file
        combined_content = []
        for filename in file_order:
            file_path = brain_dir / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8").strip()
                    if content:
                        # Add section header
                        section_name = filename.replace(".md", "").replace("_", " ").title()
                        combined_content.append(f"## {section_name}\n\n{content}")
                except OSError:
                    continue

        # Also include any other .md files not in the standard list
        for md_file in md_files:
            if md_file.name not in file_order:
                try:
                    content = md_file.read_text(encoding="utf-8").strip()
                    if content:
                        section_name = md_file.stem.replace("_", " ").title()
                        combined_content.append(f"## {section_name}\n\n{content}")
                except OSError:
                    continue

        if not combined_content:
            return (
                SessionSummary(uuid=session_id, summary="Empty Antigravity Session"),
                [],
                {},
            )

        # Create a single assistant entry with all content
        full_content = "\n\n---\n\n".join(combined_content)

        # Create entries that simulate a conversation
        # User entry: the task/request
        task_file = brain_dir / "task.md"
        user_prompt = "Antigravity session"
        if task_file.exists():
            try:
                task_content = task_file.read_text(encoding="utf-8").strip()
                # Extract first line or first 100 chars as the "prompt"
                first_line = task_content.split("\n")[0].strip()
                if first_line:
                    user_prompt = first_line[:200]
            except OSError:
                pass

        user_entry = Entry(
            type="user",
            uuid=f"{session_id}-user",
            message={"content": [{"type": "text", "text": user_prompt}]},
            timestamp=start_time,
        )
        entries.append(user_entry)

        # Assistant entry: the full content
        assistant_entry = Entry(
            type="assistant",
            uuid=f"{session_id}-assistant",
            message={"content": [{"type": "text", "text": full_content}]},
            timestamp=start_time,
        )
        entries.append(assistant_entry)

        # Create session summary
        session_summary = SessionSummary(
            uuid=session_id,
            summary=f"Antigravity Session: {user_prompt[:50]}",
            created_at=start_time.isoformat() if start_time else "",
        )

        return session_summary, entries, {}

    def _load_agent_files(self, main_file_path: Path) -> dict[str, list[Entry]]:
        """Load agent-*.jsonl files that belong to this session."""
        agent_entries: dict[str, list[Entry]] = {}

        session_dir = main_file_path.parent
        main_session_uuid = main_file_path.stem

        # Search locations for agent files:
        # 1. Same directory as session (legacy)
        # 2. {session_dir}/{session_uuid}/subagents/ (new Claude Code structure)
        agent_search_patterns = [
            session_dir.glob("agent-*.jsonl"),
            (session_dir / main_session_uuid / "subagents").glob("agent-*.jsonl"),
        ]

        for pattern in agent_search_patterns:
            if not isinstance(pattern, type(session_dir.glob("*"))):
                # Handle cases where folder might not exist
                continue

            for agent_file in pattern:
                agent_id = agent_file.stem.replace("agent-", "")

                # Check if this agent file belongs to the current session
                belongs_to_session = False
                try:
                    with open(agent_file, encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line:
                            first_entry_data = json.loads(first_line)
                            if first_entry_data.get("sessionId") == main_session_uuid:
                                belongs_to_session = True
                except (OSError, json.JSONDecodeError):
                    continue

                if not belongs_to_session:
                    continue

                # Load all entries from this agent file
                entries = []
                try:
                    with open(agent_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            data = json.loads(line)
                            entry = Entry.from_dict(data)
                            entries.append(entry)
                except (OSError, json.JSONDecodeError):
                    continue

                if entries:
                    agent_entries[agent_id] = entries

        return agent_entries

    def _find_hook_files(self, session_file_path: Path) -> list[Path]:
        """Find all hook files whose entries reference this session transcript.

        Hook logs rotate per clock-minute (router.sh writes one file per
        ``YYYYMMDD-HHMM-…-hooks.jsonl``), so a multi-minute session has
        multiple files. We return every file whose first matching record
        points at ``session_file_path``.

        Gemini sessions don't populate ``transcript_path`` in hook logs, so
        we also fall back to matching by ``session_short_hash`` against the
        8-char session ID extracted from the session filename.
        """
        session_path = Path(session_file_path)
        target = str(session_file_path)

        # Extract 8-char session ID for fallback matching (Gemini hooks have
        # transcript_path=None but do carry session_short_hash).
        session_id = _get_session_id_from_path(session_path)

        # Hooks are stored in {project_dir}-hooks/ (sibling directory with -hooks suffix)
        project_dir = session_path.parent
        hooks_sibling = project_dir.parent / (project_dir.name + "-hooks")

        # For Gemini chat files under chats/, also search the grandparent
        # where polecat places hook files alongside session metadata.
        grandparent = session_path.parent.parent

        search_locations = [
            hooks_sibling,  # New Claude Code location: {project}-hooks/
            session_path.parent,  # Same directory as session (legacy)
            session_path.parent / "hooks",  # Test location
            Path.home() / ".cache" / "aops" / "sessions",  # Legacy location
        ]
        if grandparent != project_dir and grandparent.exists():
            search_locations.append(grandparent)

        matches: list[Path] = []
        seen: set[Path] = set()
        for hook_dir in search_locations:
            if not hook_dir.exists():
                continue

            for hook_file in hook_dir.glob("*-hooks.jsonl"):
                if hook_file in seen:
                    continue
                try:
                    with open(hook_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                tp = data.get("transcript_path")
                                if tp == target:
                                    matches.append(hook_file)
                                    seen.add(hook_file)
                                    break
                                if (
                                    not tp
                                    and session_id
                                    and data.get("session_short_hash") == session_id
                                ):
                                    matches.append(hook_file)
                                    seen.add(hook_file)
                                    break
                            except json.JSONDecodeError:
                                continue
                except OSError:
                    continue

        return sorted(matches)

    @staticmethod
    def _map_hook_jsonl_to_entry_data(data: dict) -> dict:
        """Map our hook JSONL format to Entry-compatible dict.

        Our hook JSONL stores gate results under data["output"] (CanonicalHookOutput),
        NOT under data["hookSpecificOutput"] (Claude Code protocol). This method
        normalizes both schemas into a single hookSpecificOutput dict for Entry.from_dict().
        """
        hook_output = data.get("hookSpecificOutput") or {}

        # Merge CanonicalHookOutput fields (our JSONL schema)
        canon_output = data.get("output")
        if isinstance(canon_output, dict):
            if canon_output.get("verdict"):
                hook_output["verdict"] = canon_output["verdict"]
            if canon_output.get("system_message"):
                hook_output["systemMessage"] = canon_output["system_message"]
            if canon_output.get("context_injection"):
                hook_output["contextInjection"] = canon_output["context_injection"]

        # Map flat fields from our JSONL to CC-style names
        if not hook_output.get("hookEventName"):
            hook_output["hookEventName"] = data.get("hook_event", "Unknown")
        if "exit_code" in data and "exitCode" not in hook_output:
            hook_output["exitCode"] = data["exit_code"]
        if "tool_name" in data:
            hook_output["toolName"] = data["tool_name"]
        if "tool_input" in data:
            hook_output["toolInput"] = data["tool_input"]
        if "agent_id" in data:
            hook_output["agentId"] = data["agent_id"]
        # Carry raw_input through so the renderer can show what triggered
        # the hook (e.g. Stop's last_assistant_message, UserPromptSubmit's
        # prompt, Notification's message).
        raw_input = data.get("raw_input")
        if isinstance(raw_input, dict) and raw_input:
            hook_output["rawInput"] = raw_input

        return {
            "type": "system_reminder",
            "timestamp": data.get("logged_at"),
            "hookSpecificOutput": hook_output,
        }

    def _load_hook_entries(self, hook_file_path: Path) -> list[Entry]:
        """Load ALL hook entries from JSONL file."""
        entries = []

        with open(hook_file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_data = self._map_hook_jsonl_to_entry_data(data)
                entries.append(Entry.from_dict(entry_data))

        return entries

    @staticmethod
    def _merge_cc_stop_summaries(entries: list[Entry]) -> list[Entry]:
        """Fold Claude Code's ``stop_hook_summary`` echo into our Stop entry.

        The same Stop event is logged twice: once by our router (rich:
        verdict, system_message, raw_input.last_assistant_message) and once
        by Claude Code itself (lean: durationMs, preventedContinuation).
        We merge the CC fields onto the our-log entry and drop the CC
        duplicate so the transcript shows a single, complete record.
        """
        if not entries:
            return entries

        cc_window = timedelta(seconds=10)
        result: list[Entry] = []
        # Pre-index our-log Stop entries by timestamp so we can merge in
        # under O(n) per CC summary without quadratic scans.
        our_stops: list[Entry] = [
            e
            for e in entries
            if e.type == "system_reminder"
            and e.hook_event_name == "Stop"
            and not e.hook_is_cc_summary
        ]

        def _find_match(cc_entry: Entry) -> Entry | None:
            if cc_entry.timestamp is None:
                return None
            for s in our_stops:
                if s.timestamp is None:
                    continue
                if (
                    abs((s.timestamp - cc_entry.timestamp).total_seconds())
                    <= cc_window.total_seconds()
                ):
                    return s
            return None

        for entry in entries:
            if (
                entry.type == "system_reminder"
                and entry.hook_event_name == "Stop"
                and entry.hook_is_cc_summary
            ):
                match = _find_match(entry)
                if match is not None:
                    # Carry CC-only fields onto the rich entry; drop the CC echo.
                    if entry.hook_duration_ms and not match.hook_duration_ms:
                        match.hook_duration_ms = entry.hook_duration_ms
                    if entry.hook_prevented_continuation:
                        match.hook_prevented_continuation = True
                    if entry.additional_context and not match.additional_context:
                        match.additional_context = entry.additional_context
                    continue
            result.append(entry)

        return result

    def group_entries_into_turns(
        self,
        entries: list[Entry],
        agent_entries: dict[str, list[Entry]] | None = None,
        full_mode: bool = False,
    ) -> list[ConversationTurn | dict]:
        """Group JSONL entries into conversational turns."""
        main_entries = [e for e in entries if not e.is_sidechain]
        sidechain_entries = [e for e in entries if e.is_sidechain]

        sidechain_groups = self._group_sidechain_entries(sidechain_entries)

        turns: list[dict] = []
        current_turn: dict = {}
        conversation_start_time = None

        for i, entry in enumerate(main_entries):
            if entry.type == "user":
                # Check if this is a command invocation that might need next entry for args
                message = entry.message or {}
                content_raw = message.get("content", "")
                if isinstance(content_raw, list):
                    content_raw = "\n".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content_raw
                    )

                # For command invocations, check next entry for ARGUMENTS
                next_meta_content = ""
                if self._is_command_invocation(content_raw) and i + 1 < len(main_entries):
                    next_entry = main_entries[i + 1]
                    if next_entry.type == "user" and next_entry.is_meta:
                        next_meta_content = self._extract_user_content(next_entry)

                # Now extract user content with access to next meta content
                user_content = self._extract_user_content(entry, next_meta_content)
                if not user_content.strip() or "tool_use_id" in str(entry.message):
                    continue

                if current_turn:
                    turns.append(current_turn)

                if conversation_start_time is None:
                    conversation_start_time = entry.timestamp

                current_turn = {
                    "user_message": user_content,
                    "is_meta": entry.is_meta,  # Track if this is injected context
                    "assistant_sequence": [],
                    "start_time": entry.timestamp,
                    "end_time": entry.timestamp,
                    "hook_context": entry.hook_context,
                    "inline_hooks": [],
                    "turn_entries": [entry],  # Track entries for token aggregation
                }

            elif entry.type == "system_reminder":
                hook_turn = {
                    "type": "hook_context",
                    "hook_event_name": entry.hook_event_name,
                    "content": entry.additional_context or "",
                    "exit_code": entry.hook_exit_code,
                    "skills_matched": entry.skills_matched,
                    "files_loaded": entry.files_loaded,
                    "tool_name": entry.tool_name,
                    "tool_input": entry.tool_input,
                    "agent_id": entry.agent_id,
                    "hook_context_injection": entry.hook_context_injection,
                    "hook_verdict": entry.hook_verdict,
                    "hook_system_message": entry.hook_system_message,
                    "hook_raw_input": entry.hook_raw_input,
                    "hook_duration_ms": entry.hook_duration_ms,
                    "hook_prevented_continuation": entry.hook_prevented_continuation,
                    "hook_is_cc_summary": entry.hook_is_cc_summary,
                    "start_time": entry.timestamp,
                    "end_time": entry.timestamp,
                }
                if current_turn and current_turn.get("user_message"):
                    # Position the hook relative to the agent's work in the
                    # current turn: anything that fires after assistant items
                    # have started landing is a "post-turn" hook (e.g. Stop,
                    # PostToolUse on the final tool call). The renderer uses
                    # this flag to place hooks chronologically rather than
                    # bunching them at the top of the turn.
                    hook_turn["is_post_turn"] = bool(current_turn.get("assistant_sequence"))
                    current_turn["inline_hooks"].append(hook_turn)
                else:
                    turns.append(hook_turn)

            elif entry.type == "summary":
                summary_text = entry.summary_text or ""
                if summary_text:
                    summary_turn = {
                        "type": "summary",
                        "content": summary_text,
                        "subagent_id": entry.subagent_id,
                        "start_time": entry.timestamp,
                        "end_time": entry.timestamp,
                    }
                    turns.append(summary_turn)

            elif entry.type == "assistant":
                if not current_turn:
                    continue

                message = entry.message or {}
                content = message.get("content", [])

                if not isinstance(content, list):
                    content = [content]

                # Emit Gemini-style thoughts (carried on Entry) before any text/tool
                # blocks so the reasoning shows up adjacent to its turn.
                if entry.thoughts:
                    current_turn["assistant_sequence"].append(
                        {
                            "type": "thinking",
                            "source": "gemini",
                            "thoughts": entry.thoughts,
                            "model": entry.model,
                            "subagent_id": entry.subagent_id,
                        }
                    )

                for block in content:
                    if isinstance(block, dict):
                        # Claude extended-thinking blocks
                        if block.get("type") in ("thinking", "redacted_thinking"):
                            think_text = block.get("thinking") or block.get("text") or ""
                            if block.get("type") == "redacted_thinking":
                                think_text = think_text or "[redacted]"
                            if think_text:
                                current_turn["assistant_sequence"].append(
                                    {
                                        "type": "thinking",
                                        "source": "claude",
                                        "redacted": block.get("type") == "redacted_thinking",
                                        "thoughts": [{"subject": "", "description": think_text}],
                                        "model": entry.model,
                                        "subagent_id": entry.subagent_id,
                                    }
                                )
                            continue
                        if block.get("type") == "text":
                            text_content = block.get("text", "").strip()
                            if text_content:
                                current_turn["assistant_sequence"].append(
                                    {
                                        "type": "text",
                                        "content": text_content,
                                        "subagent_id": entry.subagent_id,
                                    }
                                )
                        elif block.get("type") == "tool_use":
                            tool_op = self._format_tool_operation(block)
                            if tool_op:
                                tool_item = {
                                    "type": "tool",
                                    "content": tool_op,
                                    "tool_name": block.get("name", ""),
                                    "tool_input": block.get("input", {}),
                                }

                                tool_id = block.get("id")
                                tool_name = block.get("name", "")

                                if tool_id:
                                    # Get comprehensive result info including exit code
                                    result_info = self._get_tool_result_info(tool_id, entries)
                                    if result_info:
                                        if result_info.get("is_error"):
                                            tool_item["error"] = result_info.get("content", "")[
                                                :500
                                            ]
                                        else:
                                            tool_item["result"] = result_info.get("content", "")
                                        # Always capture exit code if available
                                        if result_info.get("exit_code") is not None:
                                            tool_item["exit_code"] = result_info["exit_code"]
                                        tool_item["is_error"] = result_info.get("is_error", False)
                                        if result_info.get("result_tokens") is not None:
                                            tool_item["result_tokens"] = result_info[
                                                "result_tokens"
                                            ]

                                if tool_name in ("Agent", "Task") and tool_id:
                                    agent_id = self._extract_agent_id_from_result(tool_id, entries)
                                    if agent_id and agent_entries and agent_id in agent_entries:
                                        tool_item["sidechain_summary"] = self._extract_sidechain(
                                            agent_entries[agent_id]
                                        )
                                        # Track which agent was rendered inline
                                        tool_item["rendered_agent_id"] = agent_id
                                    else:
                                        related_sidechain = self._find_related_sidechain(
                                            entry, sidechain_groups
                                        )
                                        if related_sidechain:
                                            tool_item["sidechain_summary"] = (
                                                self._summarize_sidechain(related_sidechain)
                                            )

                                current_turn["assistant_sequence"].append(tool_item)
                    else:
                        text_content = str(block).strip()
                        if text_content:
                            current_turn["assistant_sequence"].append(
                                {
                                    "type": "text",
                                    "content": text_content,
                                    "subagent_id": entry.subagent_id,
                                }
                            )

                if entry.timestamp and current_turn:
                    current_turn["end_time"] = entry.timestamp

                # Track assistant entry for token aggregation
                if current_turn and "turn_entries" in current_turn:
                    current_turn["turn_entries"].append(entry)

        if current_turn and (
            current_turn.get("user_message") or current_turn.get("assistant_sequence")
        ):
            turns.append(current_turn)

        # Add timing information
        first_user_turn_found = False
        for turn in turns:
            if conversation_start_time and turn.get("start_time"):
                is_user_turn = turn.get("type") not in ("hook_context", "summary")

                # Aggregate tokens from turn entries
                turn_entries = turn.get("turn_entries", [])
                token_stats = self._aggregate_turn_tokens(turn_entries)

                # Store all token types for display
                if token_stats["input"] is not None:
                    turn["input_tokens"] = token_stats["input"]
                if token_stats["output"] is not None:
                    turn["output_tokens"] = token_stats["output"]
                if token_stats["cache_create"] is not None:
                    turn["cache_create_tokens"] = token_stats["cache_create"]
                if token_stats["cache_read"] is not None:
                    turn["cache_read_tokens"] = token_stats["cache_read"]
                if token_stats.get("thoughts") is not None:
                    turn["thoughts_tokens"] = token_stats["thoughts"]
                if token_stats.get("model"):
                    turn["model"] = token_stats["model"]

                if is_user_turn and not first_user_turn_found:
                    first_user_turn_found = True
                    turn["timing_info"] = TimingInfo(
                        is_first=True,
                        start_time_local=turn["start_time"],
                        offset_from_start=None,
                        duration=self._calculate_duration(
                            turn.get("start_time"), turn.get("end_time")
                        ),
                    )
                else:
                    offset_seconds = (turn["start_time"] - conversation_start_time).total_seconds()
                    turn["timing_info"] = TimingInfo(
                        is_first=False,
                        start_time_local=None,
                        offset_from_start=self._format_time_offset(offset_seconds),
                        duration=self._calculate_duration(
                            turn.get("start_time"), turn.get("end_time")
                        ),
                    )

        # Convert to ConversationTurn objects
        conversation_turns: list[ConversationTurn | dict] = []
        for turn in turns:
            if turn.get("type") in ("hook_context", "summary"):
                conversation_turns.append(turn)
            elif turn.get("user_message", "").strip() or turn.get("assistant_sequence"):
                conversation_turns.append(
                    ConversationTurn(
                        user_message=turn.get("user_message"),
                        assistant_sequence=turn.get("assistant_sequence", []),
                        timing_info=turn.get("timing_info"),
                        start_time=turn.get("start_time"),
                        end_time=turn.get("end_time"),
                        hook_context=turn.get("hook_context", {}),
                        inline_hooks=turn.get("inline_hooks", []),
                        is_meta=turn.get("is_meta", False),
                        input_tokens=turn.get("input_tokens"),
                        output_tokens=turn.get("output_tokens"),
                        cache_create_tokens=turn.get("cache_create_tokens"),
                        cache_read_tokens=turn.get("cache_read_tokens"),
                        thoughts_tokens=turn.get("thoughts_tokens"),
                        model=turn.get("model"),
                    )
                )

        return conversation_turns

    def _extract_first_user_request(
        self, entries: list[Entry], max_length: int = 500
    ) -> str | None:
        """Extract the first substantive user request from session entries."""
        for i, entry in enumerate(entries):
            if entry.type != "user":
                continue

            # Skip meta messages
            if entry.is_meta:
                continue

            # Extract content using standard helper
            next_meta = ""
            if i + 1 < len(entries) and entries[i + 1].is_meta:
                next_meta = self._extract_user_content(entries[i + 1])

            content = self._extract_user_content(entry, next_meta)
            if not content:
                continue

            # Skip command-only messages (though _extract_user_content might have expanded them)
            # If it's a command invocation, we want the ARGUMENTS part if possible.
            if self._is_command_invocation(content):
                # If it's something like /do, it might be the intent
                if content.startswith("/do "):
                    content = content[4:]
                elif content.startswith("/ask "):
                    content = content[5:]
                else:
                    # Skip other commands like /commit
                    continue

            # Skip very short messages
            if len(content.strip()) < 10:
                continue

            content = content.strip()
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content

        return None

    def _generate_context_summary(
        self, entries: list[Entry], agent_entries: dict[str, list[Entry]] | None = None
    ) -> str | None:
        """Generate enhanced Context Summary with aggregated session metadata.

        Analyzes session entries to extract and summarize:
        - Skills/workflows invoked
        - Tasks claimed/completed
        - Files modified
        - Key tools used
        - Subagents spawned

        Returns formatted markdown string or None if no useful metadata found.
        """
        # Aggregate metadata
        skills_invoked = set()
        files_modified = set()
        key_tools: dict[str, int] = {}
        task_operations = []

        # Scan entries for metadata
        for entry in entries:
            # Extract skills/workflows from tool use
            if entry.type == "assistant" and entry.message:
                content = entry.message.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            tool_input = block.get("input", {})

                            # Track tool usage
                            if tool_name:
                                key_tools[tool_name] = key_tools.get(tool_name, 0) + 1

                            # Track skills invoked
                            if tool_name == "Skill":
                                skill = tool_input.get("skill", "")
                                if skill:
                                    skills_invoked.add(skill)

                            # Track file modifications
                            if tool_name in ["Edit", "Write"]:
                                file_path = tool_input.get("file_path", "")
                                if file_path:
                                    # Store basename only for readability
                                    files_modified.add(Path(file_path).name)

                            # Track task operations (simplified - just check for task-related tools)
                            if "task" in tool_name.lower():
                                task_operations.append(tool_name)

        # Build summary sections
        summary_parts = []

        if skills_invoked:
            skills_str = ", ".join(f"`{s}`" for s in sorted(skills_invoked))
            summary_parts.append(f"**Skills/Workflows**: {skills_str}")

        if key_tools:
            # Show top 5 most used tools
            top_tools = sorted(key_tools.items(), key=lambda x: x[1], reverse=True)[:5]
            tools_str = ", ".join([f"{name} ({count})" for name, count in top_tools])
            summary_parts.append(f"**Tools Used**: {tools_str}")

        if files_modified:
            if len(files_modified) <= 5:
                files_str = ", ".join(f"`{f}`" for f in sorted(files_modified))
                summary_parts.append(f"**Files Modified**: {files_str}")
            else:
                shown = list(sorted(files_modified))[:3]
                files_str = ", ".join(f"`{f}`" for f in shown)
                summary_parts.append(
                    f"**Files Modified**: {files_str} (+{len(files_modified) - 3} more)"
                )

        if agent_entries and len(agent_entries) > 0:
            summary_parts.append(f"**Subagents**: {len(agent_entries)} spawned")

        # Aggregate and display usage stats
        usage_stats = self._aggregate_session_usage(entries, agent_entries)
        if usage_stats.has_data():
            usage_summary = usage_stats.format_summary()
            summary_parts.append(f"**Token Usage**: {usage_summary}")

            # Add model breakdown if multiple models used
            if len(usage_stats.by_model) > 1:
                model_parts = []
                for model, stats in sorted(usage_stats.by_model.items()):
                    total = stats["input"] + stats["output"]
                    if total > 0:
                        # Shorten model names for display
                        short_name = model.replace("claude-", "").replace("-20251001", "")
                        model_parts.append(f"{short_name}: {total:,}")
                if model_parts:
                    summary_parts.append(f"**By Model**: {', '.join(model_parts)}")

            # Add agent breakdown if subagents used
            if len(usage_stats.by_agent) > 1:
                agent_parts = []
                for agent_id, stats in sorted(usage_stats.by_agent.items()):
                    total = stats["input"] + stats["output"]
                    if total > 0:
                        display_id = "main" if agent_id == "main" else agent_id[:7]
                        agent_parts.append(f"{display_id}: {total:,}")
                if agent_parts:
                    summary_parts.append(f"**By Agent**: {', '.join(agent_parts)}")

        if not summary_parts:
            return None

        return "**Context Summary**\n\n" + "\n".join(summary_parts) + "\n\n"

    def _extract_session_context(
        self,
        turns: list[ConversationTurn | dict],
        max_turns: int = 10,
    ) -> dict[str, list[dict[str, str]]]:
        """Collect injected/read context that landed early in the session.

        Three categories:
          - ``system_reminders``: ``system-reminder`` style additionalContext
            blocks (hook ``additional_context`` without an explicit
            ``contextInjection`` payload).
          - ``hook_injections``: gate-style ``contextInjection`` payloads from
            CanonicalHookOutput, plus any files the hook recorded as loaded
            (CLAUDE.md, MEMORY.md, hydration files, etc.).
          - ``early_reads``: files the agent read with the ``Read`` tool in
            the first ``max_turns`` conversation turns.

        Each item is a ``{"label": ..., "content": ...}`` (or
        ``{"path": ..., "content": ...}``) dict ready for rendering.
        Sessions with no qualifying entries return empty lists for every
        category — the caller is expected to omit the section in that case.
        """
        system_reminders: list[dict[str, str]] = []
        hook_injections: list[dict[str, str]] = []
        early_reads: list[dict[str, str]] = []

        # Track de-duplication for files (a hook may record `filesLoaded` and
        # the same path may appear again as a Read in the early turns).
        seen_read_paths: set[str] = set()

        def _record_hook(hook: dict) -> None:
            event_name = hook.get("hook_event_name") or "Hook"
            tool_name = hook.get("tool_name")
            agent_id = hook.get("agent_id")
            label_suffix = ""
            if tool_name:
                label_suffix = f": {tool_name}"
            elif agent_id:
                label_suffix = f": agent-{agent_id}"
            label = f"{event_name}{label_suffix}"

            files_loaded = hook.get("files_loaded") or []
            injection = hook.get("hook_context_injection")
            additional = (hook.get("content") or "").strip()

            if injection:
                hook_injections.append(
                    {
                        "label": label,
                        "content": injection,
                        "files_loaded": ", ".join(files_loaded) if files_loaded else "",
                    }
                )
            elif files_loaded:
                # Hook reported files loaded but no inline context payload —
                # still useful to surface (e.g. CLAUDE.md echo, MEMORY.md).
                hook_injections.append(
                    {
                        "label": label,
                        "content": "",
                        "files_loaded": ", ".join(files_loaded),
                    }
                )

            if additional:
                system_reminders.append({"label": label, "content": additional})

        user_turn_count = 0
        for turn in turns:
            # Standalone hook_context turn dict (system_reminder before any
            # user message) — always part of bootstrap context.
            if isinstance(turn, dict) and turn.get("type") == "hook_context":
                _record_hook(turn)
                continue

            # Skip non-conversation dicts (e.g. summary entries).
            if isinstance(turn, dict):
                continue

            # ConversationTurn — count it and stop once we've covered the
            # first ``max_turns`` substantive turns.
            user_turn_count += 1
            if user_turn_count > max_turns:
                break

            # Inline hooks attached to this user turn (PreToolUse / Stop /
            # UserPromptSubmit context injections).
            for hook in turn.inline_hooks or []:
                _record_hook(hook)

            # Read tool calls — surface filenames + (in full mode) the body
            # of each early read.
            for item in turn.assistant_sequence or []:
                if item.get("type") != "tool":
                    continue
                if item.get("tool_name") != "Read":
                    continue
                tool_input = item.get("tool_input") or {}
                file_path = tool_input.get("file_path", "")
                if not file_path or file_path in seen_read_paths:
                    continue
                seen_read_paths.add(file_path)
                # ``result`` is only populated when include_tool_results=True
                # (full variant); in abridged the body is irrelevant.
                early_reads.append(
                    {
                        "path": file_path,
                        "content": item.get("result") or "",
                    }
                )

        return {
            "system_reminders": system_reminders,
            "hook_injections": hook_injections,
            "early_reads": early_reads,
        }

    @staticmethod
    def _render_hook(hook: dict, full_mode: bool) -> str:
        """Render a single hook event in unified format.

        All hooks (PreToolUse, PostToolUse, Stop, Notification, etc.) share
        one shape: a single ``> 🪝 …`` header line carrying every piece of
        metadata (event, tool/agent, verdict, duration, skills, files,
        +ctx), followed by blockquoted bodies for any multi-line payload —
        system message, last-assistant tail (Stop), submitted prompt
        (UserPromptSubmit), notification text, and injected context.

        No-op hooks (default ``allow`` verdict, no message, no payload) are
        suppressed entirely — the hook log is the source of truth for those.
        """
        event_name = hook.get("hook_event_name") or "Hook"
        exit_code = hook.get("exit_code")
        content = (hook.get("content") or "").strip()
        skills_matched = hook.get("skills_matched")
        files_loaded = hook.get("files_loaded")
        tool_name = hook.get("tool_name")
        agent_id = hook.get("agent_id")
        tool_input = hook.get("tool_input")
        hook_verdict = hook.get("hook_verdict")
        hook_system_message = hook.get("hook_system_message")
        hook_context_injection = hook.get("hook_context_injection")
        hook_raw_input = hook.get("hook_raw_input") or {}
        duration_ms = hook.get("hook_duration_ms")
        prevented = hook.get("hook_prevented_continuation", False)

        is_blocking = hook_verdict in ("deny", "block", "request-changes")
        noteworthy_verdict = hook_verdict if hook_verdict and hook_verdict != "allow" else None
        is_error = exit_code is not None and exit_code != 0

        # Pull lifecycle-event payloads (prompt / notification text) up front so
        # they count as "this hook did something" for suppression purposes.
        prompt_text = ""
        if event_name == "UserPromptSubmit" and isinstance(hook_raw_input, dict):
            p = hook_raw_input.get("prompt")
            if isinstance(p, str) and p.strip():
                prompt_text = p.strip()
        notification_text = ""
        if event_name == "Notification" and isinstance(hook_raw_input, dict):
            n = hook_raw_input.get("message")
            if isinstance(n, str) and n.strip():
                notification_text = n.strip()
        last_assistant_tail = ""
        if event_name == "Stop" and isinstance(hook_raw_input, dict):
            last = hook_raw_input.get("last_assistant_message")
            if isinstance(last, str) and last.strip():
                last_assistant_tail = last.strip()

        has_payload = bool(
            hook_system_message
            or hook_context_injection
            or skills_matched
            or files_loaded
            or noteworthy_verdict
            or is_blocking
            or is_error
            or prevented
            or prompt_text
            or notification_text
            or last_assistant_tail
            or content
        )
        if not has_payload:
            return ""

        # One-line metadata header.
        bits: list[str] = [f"🪝 {event_name}"]
        if tool_name:
            bits.append(f"`{tool_name}`")
        elif agent_id:
            bits.append(f"agent-{agent_id}")
        if is_blocking:
            bits.append(f"🛑 `{hook_verdict}`")
        elif noteworthy_verdict:
            bits.append(f"verdict `{noteworthy_verdict}`")
        elif is_error:
            bits.append(f"exit {exit_code}")
        if prevented:
            bits.append("🛑 prevented-continuation")
        if duration_ms:
            bits.append(f"{duration_ms}ms")
        if skills_matched:
            bits.append("skills: " + ", ".join(f"`{s}`" for s in skills_matched))
        if files_loaded:
            bits.append("loaded: " + ", ".join(f"`{fp.split('/')[-1]}`" for fp in files_loaded))
        if hook_context_injection:
            bits.append(f"+ctx {len(hook_context_injection):,}c")
        out = "> " + " — ".join(bits) + "\n"

        def _add_block(label: str, body: str, limit: int) -> str:
            body = body.strip()
            if not body:
                return ""
            shown = body if full_mode or len(body) <= limit else body[:limit] + "..."
            quoted = _quote_block(_adjust_heading_levels(shown.strip(), 4))
            prefix = f"> _{label}:_\n" if label else ""
            return f">\n{prefix}{quoted}\n"

        if tool_input and tool_name:
            tool_summary = _summarize_tool_input(tool_name, tool_input)
            if tool_summary:
                out += f"> **{tool_name}**: `{tool_summary}`\n"
        if prompt_text and full_mode:
            out += _add_block("prompt", prompt_text, 300)
        if notification_text:
            out += _add_block("notification", notification_text, 300)
        if hook_system_message:
            out += _add_block("→ user", hook_system_message.strip(), 600)
        if last_assistant_tail:
            tail = last_assistant_tail
            if len(tail) > 240:
                tail = "…" + tail[-240:]
            out += _add_block("triggered after", tail, len(tail))
        if content:
            out += _add_block("", content, 300)
        if hook_context_injection:
            inj = hook_context_injection
            limit = 1200 if full_mode else 300
            out += _add_block(f"→ agent context ({len(inj):,} chars)", inj, limit)

        return out + "\n"

    @staticmethod
    def _keep_hook(h: dict) -> bool:
        """Return True if this hook turn should be rendered in the transcript.

        CC's own ``stop_hook_summary`` echoes the same Stop event our router
        already logs with richer payload. Suppress the echo when it carries no
        extra signal (no errors, no prevented-continuation flag, no duration).
        All non-CC-summary hooks are always kept.
        """
        if not h.get("hook_is_cc_summary"):
            return True
        return bool(
            h.get("hook_prevented_continuation") or h.get("content") or h.get("hook_duration_ms")
        )

    @staticmethod
    def _render_session_context(
        ctx: dict[str, list[dict[str, str]]],
        variant: str,
    ) -> str:
        """Render the Session Context section.

        Returns "" when there is nothing to surface.

        ``abridged``: bullet list per category (filenames + one-line label).
        ``full``: each item rendered with its body, large bodies wrapped in
        ``<details>`` blocks.
        """
        system_reminders = ctx.get("system_reminders", [])
        hook_injections = ctx.get("hook_injections", [])
        early_reads = ctx.get("early_reads", [])

        if not system_reminders and not hook_injections and not early_reads:
            return ""

        full_mode = variant == "full"
        out: list[str] = ["## Session Context\n"]

        def _is_binary(text: str) -> bool:
            # Heuristic: real binary Reads come back with a NUL byte or as
            # base64; treat those as opaque so we list the filename only.
            if not text:
                return False
            if "\x00" in text[:2048]:
                return True
            return False

        def _wrap_body(label: str, body: str) -> str:
            body = body.rstrip()
            if not body:
                return f"### {label}\n\n_(empty)_\n\n"
            if len(body) > 500:
                # Long bodies go inside <details> so the section stays
                # navigable.
                return (
                    f"### {label}\n\n"
                    f"<details>\n<summary>{len(body):,} chars</summary>\n\n"
                    f"```\n{body}\n```\n\n"
                    f"</details>\n\n"
                )
            return f"### {label}\n\n```\n{body}\n```\n\n"

        if hook_injections:
            out.append("**Hook context injections** (software-injected):\n")
            if full_mode:
                out.append("")
                for item in hook_injections:
                    label = item["label"]
                    files_loaded = item.get("files_loaded", "")
                    body_parts = []
                    if files_loaded:
                        body_parts.append(f"_Files loaded:_ {files_loaded}")
                    if item["content"]:
                        body_parts.append(item["content"])
                    body = "\n\n".join(body_parts)
                    out.append(_wrap_body(label, body))
            else:
                for item in hook_injections:
                    files_loaded = item.get("files_loaded", "")
                    char_count = len(item["content"])
                    detail_bits = []
                    if files_loaded:
                        # Show basenames only for readability.
                        bases = ", ".join(
                            f"`{p.split('/')[-1]}`" for p in files_loaded.split(", ") if p
                        )
                        detail_bits.append(f"loaded {bases}")
                    if char_count:
                        detail_bits.append(f"{char_count:,} chars injected")
                    suffix = f" — {'; '.join(detail_bits)}" if detail_bits else ""
                    out.append(f"- {item['label']}{suffix}")
                out.append("")

        if system_reminders:
            out.append("**System reminders** (software-injected):\n")
            if full_mode:
                out.append("")
                for item in system_reminders:
                    out.append(_wrap_body(item["label"], item["content"]))
            else:
                for item in system_reminders:
                    char_count = len(item["content"])
                    out.append(f"- {item['label']} — {char_count:,} chars")
                out.append("")

        if early_reads:
            out.append("**Early file reads** (agent-read):\n")
            if full_mode:
                out.append("")
                for item in early_reads:
                    path = item["path"]
                    content = item["content"]
                    if _is_binary(content):
                        out.append(f"### {path}\n\n_(binary content omitted)_\n\n")
                    else:
                        out.append(_wrap_body(path, content))
            else:
                for item in early_reads:
                    path = item["path"]
                    basename = path.split("/")[-1]
                    out.append(f"- `{basename}` — `{path}`")
                out.append("")

        # Always end with a blank line so the next section starts cleanly.
        rendered = "\n".join(out).rstrip() + "\n\n"
        return rendered

    def format_session_as_markdown(
        self,
        session: SessionSummary,
        entries: list[Entry],
        agent_entries: dict[str, list[Entry]] | None = None,
        include_tool_results: bool = True,
        variant: str = "full",
        source_file: str | Path | None = None,
        reflection_header: str | None = None,
        usage_stats: UsageStats | None = None,
        session_duration_minutes: float | None = None,
    ) -> str:
        """Format session entries as readable markdown."""
        session_uuid = session.uuid
        details = session.details or {}

        first_timestamp = None
        for entry in entries:
            if entry.timestamp:
                first_timestamp = entry.timestamp
                break
        date_str = first_timestamp.isoformat() if first_timestamp else "unknown"

        full_mode = variant == "full"
        turns = self.group_entries_into_turns(entries, agent_entries, full_mode=full_mode)

        markdown = ""
        turn_number = 0
        rendered_agent_ids: set[str] = set()

        for turn in turns:
            if isinstance(turn, dict) and turn.get("type") == "hook_context":
                if not self._keep_hook(turn):
                    continue
                markdown += self._render_hook(turn, full_mode)
                continue

            # Skip old-style summary entries (now handled by _generate_context_summary)
            if isinstance(turn, dict) and turn.get("type") == "summary":
                continue

            turn_number += 1

            # Retrieve assistant_sequence early so we can count tool calls for the meta line
            assistant_sequence = (
                turn.assistant_sequence
                if isinstance(turn, ConversationTurn)
                else turn.get("assistant_sequence", [])
            )

            timing_info = (
                turn.timing_info if isinstance(turn, ConversationTurn) else turn.get("timing_info")
            )

            # Build per-turn meta line (shown below the heading, not crammed into it)
            meta_parts = []
            if timing_info:
                if timing_info.is_first and timing_info.start_time_local:
                    ts = timing_info.start_time_local
                    meta_parts.append(ts.strftime("%Y-%m-%d %H:%M:%S"))
                elif timing_info.offset_from_start:
                    meta_parts.append(f"+{timing_info.offset_from_start}")
                if timing_info.duration:
                    meta_parts.append(f"took {timing_info.duration}")

                if isinstance(turn, ConversationTurn):
                    input_tokens = turn.input_tokens
                    output_tokens = turn.output_tokens
                    cache_read = turn.cache_read_tokens
                    cache_create = turn.cache_create_tokens
                    thoughts_tokens = turn.thoughts_tokens
                    turn_model = turn.model
                else:
                    input_tokens = turn.get("input_tokens")
                    output_tokens = turn.get("output_tokens")
                    cache_read = turn.get("cache_read_tokens")
                    cache_create = turn.get("cache_create_tokens")
                    thoughts_tokens = turn.get("thoughts_tokens")
                    turn_model = turn.get("model")
                if turn_model:
                    meta_parts.append(f"model={turn_model}")
                if input_tokens is not None and output_tokens is not None:
                    meta_parts.append(f"{input_tokens:,} in / {output_tokens:,} out")
                    if cache_read:
                        meta_parts.append(f"{cache_read:,} cache↓")
                    if cache_create:
                        meta_parts.append(f"{cache_create:,} cache↑")
                    if thoughts_tokens:
                        meta_parts.append(f"{thoughts_tokens:,} think")

            tool_count = sum(1 for item in assistant_sequence if item.get("type") == "tool")
            if tool_count:
                meta_parts.append(f"{tool_count} tool call{'s' if tool_count != 1 else ''}")

            timing_meta = f"_{' · '.join(meta_parts)}_\n\n" if meta_parts else ""

            user_message = (
                turn.user_message
                if isinstance(turn, ConversationTurn)
                else turn.get("user_message")
            )
            is_meta = (
                turn.is_meta if isinstance(turn, ConversationTurn) else turn.get("is_meta", False)
            )
            if user_message:
                if is_meta:
                    command_name = self._extract_command_name(user_message)
                    markdown += f"## User (Turn {turn_number})\n\n{timing_meta}"
                    markdown += f"**Invoked: {command_name}**\n\n"
                    if full_mode:
                        markdown += f"```markdown\n{user_message}\n```\n\n"
                    else:
                        if len(user_message) > 500:
                            display_content = user_message[:500] + "... [truncated]"
                        else:
                            display_content = user_message
                        markdown += f"```markdown\n{display_content}\n```\n\n"
                else:
                    # Extract summary for heading (first non-empty line)
                    summary = user_message.split("\n")[0].strip()
                    if len(summary) > 60:
                        summary = summary[:57] + "..."

                    # Body: demote headings and wrap in blockquote so user content
                    # can't corrupt the transcript's own heading structure
                    if not full_mode and len(user_message) > 500:
                        body = _quote_block(_adjust_heading_levels(user_message[:500], 2))
                        body += "\n> ... [truncated]"
                    else:
                        body = _quote_block(_adjust_heading_levels(user_message, 2))

                    markdown += (
                        f"## User (Turn {turn_number}) — {summary}\n\n{timing_meta}{body}\n\n"
                    )

                inline_hooks = (
                    turn.inline_hooks
                    if isinstance(turn, ConversationTurn)
                    else turn.get("inline_hooks", [])
                )
                # Split into hooks that fired BEFORE any assistant work (pre)
                # and ones that fired during/after the agent's tool calls
                # (post). Post-turn hooks render after the assistant sequence
                # so chronology survives in the markdown.
                pre_turn_hooks = [h for h in inline_hooks if not h.get("is_post_turn")]
                post_turn_hooks = [h for h in inline_hooks if h.get("is_post_turn")]

                pre_turn_hooks = [h for h in pre_turn_hooks if self._keep_hook(h)]
                post_turn_hooks = [h for h in post_turn_hooks if self._keep_hook(h)]

                for hook in pre_turn_hooks:
                    markdown += self._render_hook(hook, full_mode)
            else:
                post_turn_hooks = []

            if assistant_sequence:
                in_actions_section = False
                agent_header_emitted = False

                for item in assistant_sequence:
                    item_type = item.get("type")
                    content = item.get("content", "")
                    subagent_id = item.get("subagent_id")

                    if item_type == "thinking":
                        if in_actions_section:
                            in_actions_section = False
                            markdown += "\n"

                        if not agent_header_emitted:
                            if subagent_id:
                                markdown += f"## Agent ({subagent_id})\n\n"
                            else:
                                markdown += f"## Agent (Turn {turn_number})\n\n"
                            agent_header_emitted = True

                        thoughts = (
                            item.get("thoughts") or []
                        )  # allow-fallback: absent for non-thinking models
                        if thoughts:
                            label = (
                                "Model thoughts"
                                if item.get("source") == "gemini"
                                else "Extended thinking"
                            )
                            if full_mode:
                                markdown += f"<details><summary>💭 {label}</summary>\n\n"
                                for t in thoughts:
                                    subj = (t.get("subject") or "").strip()
                                    desc = (t.get("description") or "").strip()
                                    if subj and desc:
                                        markdown += f"> **{subj}** — {desc}\n>\n"
                                    elif desc:
                                        # Quote each line for safety
                                        for line in desc.splitlines() or [desc]:
                                            markdown += f"> {line}\n"
                                        markdown += ">\n"
                                    elif subj:
                                        markdown += f"> **{subj}**\n>\n"
                                markdown += "\n</details>\n\n"
                            else:
                                # Abridged: subjects only (compact)
                                subjects = [
                                    (t.get("subject") or "").strip()
                                    for t in thoughts
                                    if (t.get("subject") or "").strip()
                                ]
                                if subjects:
                                    joined = "; ".join(subjects)
                                    markdown += f"_💭 {label}: {joined}_\n\n"
                                else:
                                    markdown += f"_💭 {label}: {len(thoughts)} block(s)_\n\n"
                        continue

                    if item_type == "text":
                        if in_actions_section:
                            in_actions_section = False
                            markdown += "\n"

                        if not agent_header_emitted:
                            if subagent_id:
                                markdown += f"## Agent ({subagent_id})\n\n"
                            else:
                                markdown += f"## Agent (Turn {turn_number})\n\n"
                            agent_header_emitted = True

                        notifications = _extract_task_notifications(content)
                        if notifications:
                            markdown += f"{content}\n\n"
                            for notif in notifications:
                                task_output = _read_task_output_file(notif["output_file"])
                                if task_output:
                                    if _is_subagent_jsonl(task_output):
                                        parsed = _parse_subagent_output(
                                            task_output, heading_level=4
                                        )
                                        if parsed:
                                            subagent_markdown, _ = parsed
                                            markdown += f"### Task Agent ({notif['task_id']})\n\n"
                                            markdown += subagent_markdown + "\n"
                                        else:
                                            markdown += (
                                                f"### Task Agent Output ({notif['task_id']})\n\n"
                                            )
                                            markdown += f"```\n{task_output}\n```\n\n"
                                    else:
                                        markdown += (
                                            f"### Task Agent Output ({notif['task_id']})\n\n"
                                        )
                                        markdown += f"```\n{task_output}\n```\n\n"
                        else:
                            # Demote headings to avoid breaking transcript structure
                            markdown += f"{_adjust_heading_levels(content, 2)}\n\n"

                    elif item_type == "tool":
                        if not in_actions_section:
                            in_actions_section = True

                        # Format exit code suffix for display
                        exit_code = item.get("exit_code")
                        tool_name = item.get("tool_name", "")
                        is_error = item.get("is_error", False)
                        exit_suffix = ""

                        # Show exit code only for Bash tools (P#8: explicit, not inferred)
                        if exit_code is not None and tool_name == "Bash":
                            exit_suffix = f" → exit {exit_code}"
                        # Show error indicator when no exit code but is_error is True
                        elif is_error:
                            exit_suffix = " → error"

                        # Per-tool result-size annotation. The estimate is
                        # ``len(content) // 4`` (no tokenizer dep), so the
                        # ``~`` prefix is load-bearing — it tells the reader
                        # this is an approximation, not a billed count.
                        result_tokens = item.get("result_tokens")
                        token_suffix = (
                            f" [~{_format_token_count(result_tokens)} tok]"
                            if isinstance(result_tokens, int) and result_tokens > 0
                            else ""
                        )

                        # Track if we render subagent content from result
                        # to avoid duplication with sidechain_summary
                        rendered_subagent_from_result = False

                        if item.get("error"):
                            content = content.rstrip("\n")
                            # Include exit code in error display
                            exit_info = f" (exit {exit_code})" if exit_code else ""
                            error_text = str(item["error"]).replace("`", "'")
                            markdown += f"- **❌ ERROR{exit_info}:** {content.lstrip('- ')}: `{error_text}`\n"
                        elif include_tool_results and item.get("result"):
                            result_text = item["result"]
                            tool_call = content.strip().lstrip("- ").rstrip("\n")
                            display_call = f"{tool_call}{exit_suffix}{token_suffix}"

                            if _is_subagent_jsonl(result_text):
                                parsed = _parse_subagent_output(result_text, heading_level=4)
                                if parsed:
                                    subagent_markdown, _ = parsed
                                    markdown += f"- **Tool:** {display_call}\n\n"
                                    markdown += subagent_markdown + "\n"
                                    rendered_subagent_from_result = True
                                else:
                                    markdown += (
                                        f"- **Tool:** {display_call}\n```\n{result_text}\n```\n\n"
                                    )
                            else:
                                result_text = self._maybe_pretty_print_json(result_text)
                                code_lang = (
                                    "json" if result_text.strip().startswith(("{", "[")) else ""
                                )
                                markdown += f"- **Tool:** {display_call}\n```{code_lang}\n{result_text}\n```\n\n"
                        else:
                            # Abridged mode - show tool call with exit/token suffix.
                            inline_suffix = exit_suffix + token_suffix
                            if inline_suffix:
                                lines = content.rstrip("\n").split("\n")
                                if lines:
                                    lines[0] = lines[0].rstrip() + inline_suffix
                                    content = "\n".join(lines) + "\n"
                            markdown += content

                        # Only render sidechain_summary if we didn't already
                        # render subagent content from the tool result
                        # (avoids duplication when both exist)
                        should_render_sidechain = (
                            item.get("sidechain_summary") and not rendered_subagent_from_result
                        )

                        if should_render_sidechain:
                            tool_input = item.get("tool_input", {})
                            agent_type = tool_input.get("subagent_type", "unknown")
                            agent_desc = tool_input.get("description", "")
                            if item.get("rendered_agent_id"):
                                rendered_agent_ids.add(item["rendered_agent_id"])

                            desc_part = f" ({agent_desc})" if agent_desc else ""
                            markdown += f"\n### Subagent: {agent_type}{desc_part}\n\n"

                            adjusted_summary = _adjust_heading_levels(item["sidechain_summary"], 2)
                            lines = adjusted_summary.split("\n")
                            condensed = "\n".join(line for line in lines if line.strip())
                            # Quote the subagent summary/content
                            markdown += _quote_block(condensed) + "\n\n"

            # Hooks that fired AFTER the agent's last assistant entry
            # (Stop, terminal PostToolUse, etc.) — render at the bottom of
            # the turn so their chronological position is preserved.
            for hook in post_turn_hooks:
                markdown += self._render_hook(hook, full_mode)

        edited_files = details.get("edited_files", session.edited_files)
        files_list = edited_files if edited_files and isinstance(edited_files, list) else []

        provider = (session.provider or "claude").lower()
        provider_label = {
            "claude": "Claude Code",
            "gemini": "Gemini CLI",
            "github": "GitHub Agent",
            "jules": "Jules",
            "codex": "Codex",
            "copilot": "Copilot",
        }.get(provider, provider.title())
        title = session.summary or f"{provider_label} Session"
        permalink = f"sessions/{provider}/{session_uuid[:8]}-{variant}"

        files_yaml = ""
        if files_list:
            files_yaml = "files_modified:\n"
            for f in files_list:
                files_yaml += f"  - {f}\n"

        source_yaml = f'source_file: "{source_file}"\n' if source_file else ""

        stats_yaml = ""
        if usage_stats and usage_stats.has_data():
            total_tool_calls = sum(v.get("count", 0) for v in usage_stats.by_tool.values())
            stats_yaml = "stats:\n"
            stats_yaml += f"  input_tokens: {usage_stats.input_tokens}\n"
            stats_yaml += f"  output_tokens: {usage_stats.output_tokens}\n"
            if usage_stats.cache_read_input_tokens:
                stats_yaml += f"  cache_read_tokens: {usage_stats.cache_read_input_tokens}\n"
            if usage_stats.cache_creation_input_tokens:
                stats_yaml += f"  cache_created_tokens: {usage_stats.cache_creation_input_tokens}\n"
            if total_tool_calls:
                stats_yaml += f"  tool_calls: {total_tool_calls}\n"
            if session_duration_minutes is not None:
                stats_yaml += f"  duration_minutes: {session_duration_minutes:.1f}\n"

        metadata_yaml = ""
        if session.machine:
            metadata_yaml += f"machine: {session.machine}\n"
        if session.hostname:
            metadata_yaml += f"hostname: {session.hostname}\n"
        if session.provider:
            metadata_yaml += f"provider: {session.provider}\n"
        if session.surface:
            metadata_yaml += f"surface: {session.surface}\n"
        if session.client:
            metadata_yaml += f"client: {session.client}\n"
        if session.crew:
            metadata_yaml += f"crew: {session.crew}\n"
        if session.repo:
            metadata_yaml += f"repo: {session.repo}\n"
        if session.task_id:
            metadata_yaml += f"task_id: {session.task_id}\n"
        # task_title (aops-62abcf9d): resolved best-effort from task_id so future
        # readers (catch-up timeline) do not need to round-trip to the PKB. Falls
        # back to whatever is on the summary, then a fresh PKB lookup if absent.
        task_title = session.task_title or resolve_task_title(session.task_id)
        if task_title:
            safe_title = task_title.replace('"', "'").replace("\n", " ").strip()
            metadata_yaml += f'task_title: "{safe_title}"\n'
        if session.slug:
            metadata_yaml += f"slug: {session.slug}\n"
        if session.session_kind:
            metadata_yaml += f"session_kind: {session.session_kind}\n"
        if session.user_type:
            metadata_yaml += f"user_type: {session.user_type}\n"
        if session.entrypoint:
            metadata_yaml += f"entrypoint: {session.entrypoint}\n"
        if session.client_version:
            metadata_yaml += f"client_version: {session.client_version}\n"
        if session.git_branches:
            if len(session.git_branches) == 1:
                metadata_yaml += f"git_branch: {session.git_branches[0]}\n"
            else:
                metadata_yaml += f"git_branches: [{', '.join(session.git_branches)}]\n"
        if session.permission_modes:
            if len(session.permission_modes) == 1:
                metadata_yaml += f"permission_mode: {session.permission_modes[0]}\n"
            else:
                metadata_yaml += f"permission_modes: [{', '.join(session.permission_modes)}]\n"
        # Auto-mode classifier decisions (headless result envelope). Allows are silent;
        # only denials and a death-by-denial termination are recorded.
        if session.permission_denials:
            metadata_yaml += f"auto_mode_denials: {len(session.permission_denials)}\n"
        if session.terminal_reason:
            metadata_yaml += f"terminal_reason: {session.terminal_reason}\n"
        if session.models:
            metadata_yaml += f"models: [{', '.join(session.models)}]\n"
        if session.session_type:
            metadata_yaml += f"session_type: {session.session_type}\n"
        if session.gemini_version:
            metadata_yaml += f"gemini_version: {session.gemini_version}\n"
        if session.outcome:
            metadata_yaml += f"outcome: {session.outcome}\n"

        frontmatter = f"""---
title: "{title} ({variant})"
type: session
permalink: {permalink}
tags:
  - {provider}-session
  - transcript
  - {variant}
date: {date_str}
session_id: {session_uuid}
{metadata_yaml}{source_yaml}{stats_yaml}{files_yaml}---

"""

        header = f"# {title}\n\n"

        # The previous out-of-chronological-order top summary (Overview /
        # Session Context / Session Reflection) has been removed — reflection
        # extraction still lands in the insights JSON via _process_reflection,
        # but the markdown stays purely chronological. The ``reflection_header``
        # parameter is kept for caller compatibility; it is intentionally unused.
        _ = reflection_header
        # Write-time secret scrub (aops-9f290e36): tool output / bash stdout can
        # carry an env dump or echoed credential into this git-tracked artifact.
        return redact_secrets(frontmatter + header + markdown)

    def _group_sidechain_entries(
        self, sidechain_entries: list[Entry]
    ) -> dict[datetime, list[Entry]]:
        """Group sidechain entries by conversation thread."""
        groups: dict[datetime, list[Entry]] = {}
        for entry in sidechain_entries:
            timestamp = entry.timestamp
            if timestamp:
                minute_key = timestamp.replace(second=0, microsecond=0)
                if minute_key not in groups:
                    groups[minute_key] = []
                groups[minute_key].append(entry)
        return groups

    def _find_related_sidechain(
        self, main_entry: Entry, sidechain_groups: dict[datetime, list[Entry]]
    ) -> list[Entry] | None:
        """Find sidechain entries related to a main thread tool use."""
        if not main_entry.timestamp:
            return None

        main_minute = main_entry.timestamp.replace(second=0, microsecond=0)
        for time_offset in [0, 1]:
            check_time = main_minute + timedelta(minutes=time_offset)
            if check_time in sidechain_groups:
                return sidechain_groups[check_time]
        return None

    def _summarize_sidechain(self, sidechain_entries: list[Entry]) -> str:
        """Create a summary of what happened in the sidechain."""
        if not sidechain_entries:
            return "No sidechain details available"

        tool_count = 0
        file_operations = []
        for entry in sidechain_entries:
            if entry.type == "assistant" and entry.message:
                content = entry.message.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_count += 1
                            tool_name = block.get("name", "")
                            if tool_name in ["Read", "Edit", "Write", "Grep"]:
                                tool_input = block.get("input", {})
                                file_path = tool_input.get("file_path", "")
                                if file_path:
                                    file_operations.append(f"{tool_name}: {file_path}")

        summary_parts = []
        if tool_count > 0:
            summary_parts.append(f"Executed {tool_count} tool operations")
        if file_operations:
            shown_ops = file_operations[:3]
            summary_parts.append("Key operations: " + ", ".join(shown_ops))
            if len(file_operations) > 3:
                summary_parts.append(f"... and {len(file_operations) - 3} more")
        return "; ".join(summary_parts) if summary_parts else "Parallel task execution"

    def _extract_sidechain(self, sidechain_entries: list[Entry]) -> str:
        """Extract full conversation from sidechain entries.

        Deduplicates text content and tool operations to avoid showing the same content twice.
        Groups consecutive calls to the same tool for readability.
        """
        if not sidechain_entries:
            return "No sidechain details available"
        output_parts: list[str] = []
        seen_texts: set[str] = set()
        seen_tool_keys: set[str] = set()  # Track unique tool calls

        # First pass: collect all items in order, marking text vs tool
        items: list[tuple[str, Any]] = []  # (type, content)
        for entry in sidechain_entries:
            if entry.type == "assistant" and entry.message:
                content = entry.message.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text = block.get("text", "").strip()
                                if text and text not in seen_texts:
                                    seen_texts.add(text)
                                    items.append(("text", text))
                            elif block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                tool_input = block.get("input", {})
                                # Create a unique key for deduplication
                                tool_key = f"{tool_name}:{str(tool_input)}"
                                if tool_key not in seen_tool_keys:
                                    seen_tool_keys.add(tool_key)
                                    items.append(("tool", block))

        # Second pass: group consecutive tool calls of the same type
        i = 0
        while i < len(items):
            item_type, content = items[i]

            if item_type == "text":
                output_parts.append(content + "\n")
                i += 1
            elif item_type == "tool":
                # Collect consecutive tools of the same name
                tool_name = content.get("name", "")
                tool_group = [content]
                j = i + 1
                while j < len(items):
                    next_type, next_content = items[j]
                    if next_type == "tool" and next_content.get("name") == tool_name:
                        tool_group.append(next_content)
                        j += 1
                    else:
                        break

                # Format the group
                formatted = self._format_condensed_tool_group(tool_name, tool_group)
                output_parts.append(formatted)
                i = j
            else:
                i += 1

        return "\n".join(output_parts)

    def _extract_agent_id_from_result(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Find the agentId from the tool result."""
        for entry in all_entries:
            if entry.type != "user":
                continue

            message = entry.message or {}
            content = message.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result" and block.get("tool_use_id") == tool_id:
                        if isinstance(entry.tool_use_result, dict):
                            return entry.tool_use_result.get("agentId")

        return None

    def _get_tool_result(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Get successful tool result content."""
        for entry in all_entries:
            if entry.type != "user":
                continue

            message = entry.message or {}
            content = message.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if (
                        block.get("type") == "tool_result"
                        and block.get("tool_use_id") == tool_id
                        and not block.get("is_error")
                    ):
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    texts.append(item.get("text", ""))
                            return "\n".join(texts)
                        if isinstance(result_content, str):
                            return result_content
        return None

    def _get_tool_error(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Get error message if tool failed."""
        for entry in all_entries:
            if entry.type != "user":
                continue

            message = entry.message or {}
            content = message.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if (
                        block.get("type") == "tool_result"
                        and block.get("tool_use_id") == tool_id
                        and block.get("is_error")
                    ):
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    texts.append(item.get("text", ""))
                            return "\n".join(texts)[:500]
                        if isinstance(result_content, str):
                            return result_content[:500]
        return None

    def _get_tool_result_info(
        self, tool_id: str, all_entries: list[Entry]
    ) -> dict[str, Any] | None:
        """Get comprehensive tool result info including exit code.

        Returns a dict with:
            - content: The result content string
            - is_error: Whether it was an error
            - exit_code: Extracted exit code (int or None)
            - result_tokens: Approximate token count for the result payload
              (len(content) // 4, the standard rough-equivalence ratio used
              when no tokenizer is available). Marked ``~`` at render time.
        """
        for entry in all_entries:
            if entry.type != "user":
                continue

            message = entry.message or {}
            content = message.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result" and block.get("tool_use_id") == tool_id:
                        is_error = block.get("is_error", False)
                        result_content = block.get("content", "")

                        # Handle list content
                        if isinstance(result_content, list):
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    texts.append(item.get("text", ""))
                            result_content = "\n".join(texts)

                        # Extract exit code
                        exit_code = _extract_exit_code_from_content(
                            result_content if isinstance(result_content, str) else "",
                            is_error,
                        )

                        text_for_tokens = result_content if isinstance(result_content, str) else ""
                        result_tokens = _estimate_tokens(text_for_tokens)

                        return {
                            "content": result_content,
                            "is_error": is_error,
                            "exit_code": exit_code,
                            "result_tokens": result_tokens,
                        }
        return None

    def _extract_user_content(self, entry: Entry, next_meta_content: str = "") -> str:
        """Extract clean user content from entry.

        Args:
            entry: User entry to extract content from
            next_meta_content: Optional next meta entry content (for extracting ARGUMENTS:)
        """

        message = entry.message or {}
        content = message.get("content", "")

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            content = "\n".join(text_parts)

        content = content.strip()

        # Parse command invocations to show the full user input
        if self._is_command_invocation(content):
            return self._format_command_invocation(content, next_meta_content)

        # Filter out system-only pseudo-commands (like local-command-stdout)
        if self._is_system_pseudo_command(content):
            return ""

        # Don't condense meta content here - let the main formatting handle it
        return content

    def _is_command_invocation(self, content: str) -> bool:
        """Check if content is a user command invocation (e.g., /meta)."""
        return "<command-name>" in content

    def _is_system_pseudo_command(self, content: str) -> bool:
        """Check if content is a system-only pseudo-command (not user input)."""
        if not content:
            return False

        # These are system-generated, not user input
        system_patterns = [
            "<local-command-stdout>",
            "</local-command-stdout>",
        ]

        # If content ONLY contains system patterns (no command-name/args), filter it
        for pattern in system_patterns:
            if pattern in content and "<command-name>" not in content:
                return True

        return False

    def _format_command_invocation(self, content: str, next_meta_content: str = "") -> str:
        """Format a command invocation to show the user's full input.

        Args:
            content: First user entry content
            next_meta_content: Optional next meta entry content (may contain ARGUMENTS:)
        """

        # Extract command name: <command-name>foo</command-name>
        name_match = re.search(r"<command-name>([^<]+)</command-name>", content)
        command_name = name_match.group(1).strip() if name_match else "unknown"

        # Add slash prefix if not present
        if not command_name.startswith("/"):
            command_name = f"/{command_name}"

        # Extract command args: <command-args>...</command-args>
        args_match = re.search(r"<command-args>(.*?)</command-args>", content, re.DOTALL)
        command_args = args_match.group(1).strip() if args_match else ""

        # If no args in first entry, check for ARGUMENTS: in next meta entry
        if not command_args and next_meta_content:
            # Look for "ARGUMENTS: <text>" at end of skill expansion
            args_from_meta = re.search(
                r"\nARGUMENTS:\s*(.+?)(?:\n|$)", next_meta_content, re.DOTALL
            )
            if args_from_meta:
                command_args = args_from_meta.group(1).strip()

        # Format as the user would have typed it
        if command_args:
            return f"{command_name} {command_args}"
        return command_name

    def _extract_command_name(self, content: str) -> str:
        """Extract command or skill name from expanded content."""

        # Pattern 1: "Base directory for this skill: /path/to/skills/foo"
        if content.startswith("Base directory for this skill:"):
            first_line = content.split("\n")[0]
            if "/skills/" in first_line:
                skill_path = first_line.split(":", 1)[1].strip()
                parts = skill_path.rstrip("/").split("/")
                for i, part in enumerate(parts):
                    if part == "skills" and i + 1 < len(parts):
                        return f"/{parts[i + 1]} (skill)"

        # Pattern 2: Wikilink to skill file [[skills/foo/SKILL.md|...]]
        skill_match = re.search(r"\[\[skills/([^/]+)/SKILL\.md", content)
        if skill_match:
            return f"/{skill_match.group(1)} (skill)"

        # Pattern 3: Wikilink to command [[commands/foo.md|...]]
        cmd_match = re.search(r"\[\[commands/([^/\]]+)\.md", content)
        if cmd_match:
            return f"/{cmd_match.group(1)} (command)"

        # Pattern 4: Content starting with markdown heading (command expansion)
        if content.startswith("##"):
            lines = content.split("\n")
            title = lines[0].strip("# ").strip()
            return f"/{title.lower().replace(' ', '-')} (command)"

        # Pattern 5: First markdown heading in content
        heading_match = re.search(r"^#+ (.+)$", content, re.MULTILINE)
        if heading_match:
            title = heading_match.group(1).strip()
            # Truncate long titles
            if len(title) > 40:
                title = title[:37] + "..."
            return f"{title}"

        # Pattern 6: Look for "skill" or "command" mentions in first 200 chars
        first_chunk = content[:200].lower()
        if "skill" in first_chunk:
            return "skill expansion"
        if "command" in first_chunk:
            return "command expansion"

        return "context injection"

    def _calculate_duration(self, start_time: datetime | None, end_time: datetime | None) -> str:
        """Calculate human-friendly duration."""
        if not start_time or not end_time:
            return "Unknown duration"

        duration_seconds = (end_time - start_time).total_seconds()
        return self._format_duration(duration_seconds)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-friendly format."""
        if seconds < 1:
            return "< 1 second"
        if seconds < 60:
            return f"{int(seconds)} second{'s' if int(seconds) != 1 else ''}"
        if seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            if remaining_seconds == 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"

    def _format_time_offset(self, seconds: float) -> str:
        """Format time offset from conversation start."""
        return self._format_duration(seconds)

    def _aggregate_turn_tokens(self, turn_entries: list[Entry]) -> dict[str, int | str | None]:
        """Sum all token types from entries in a turn.

        Returns dict with input, output, cache_create, cache_read token counts.
        Values are None if no tokens found for that type.
        """
        total_input = 0
        total_output = 0
        total_cache_create = 0
        total_cache_read = 0
        total_thoughts = 0
        has_tokens = False
        model = None

        for entry in turn_entries:
            if entry.input_tokens is not None:
                total_input += entry.input_tokens
                has_tokens = True
            if entry.output_tokens is not None:
                total_output += entry.output_tokens
                has_tokens = True
            if entry.cache_creation_input_tokens is not None:
                total_cache_create += entry.cache_creation_input_tokens
            if entry.cache_read_input_tokens is not None:
                total_cache_read += entry.cache_read_input_tokens
            if entry.thoughts_tokens is not None:
                total_thoughts += entry.thoughts_tokens
            # Capture the assistant model name for the turn (last assistant entry wins)
            if entry.model and entry.type == "assistant":
                model = entry.model

        if has_tokens:
            return {
                "input": total_input,
                "output": total_output,
                "cache_create": total_cache_create if total_cache_create > 0 else None,
                "cache_read": total_cache_read if total_cache_read > 0 else None,
                "thoughts": total_thoughts if total_thoughts > 0 else None,
                "model": model,
            }
        return {
            "input": None,
            "output": None,
            "cache_create": None,
            "cache_read": None,
            "thoughts": None,
            "model": model,
        }

    def _aggregate_session_usage(
        self,
        entries: list[Entry],
        agent_entries: dict[str, list[Entry]] | None = None,
    ) -> UsageStats:
        """Aggregate token usage across all entries in a session.

        Scans all main and subagent entries to compute:
        - Total input/output/cache tokens
        - Breakdown by model
        - Breakdown by tool (extracted from tool_use blocks)
        - Breakdown by agent (main vs subagent IDs)

        Args:
            entries: Main session entries
            agent_entries: Optional dict mapping agent IDs to their entries

        Returns:
            UsageStats with aggregated data
        """
        stats = UsageStats()

        # Process main entries
        seen_assistant_tool_use = False
        for entry in entries:
            tool_name = None
            skill_name = None
            # Extract tool name from assistant tool_use blocks
            if entry.type == "assistant" and entry.message:
                content = entry.message.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name")
                            if tool_name == "Skill" and isinstance(block.get("input"), dict):
                                skill_name = block["input"].get("skill")
                            break

            # Attention counters: count real user messages on the main session.
            # Excludes tool_result wrappers (Claude's convention is to carry tool_result
            # blocks inside user-role entries) and meta entries.
            if entry.type == "user" and not entry.is_meta and not entry.is_sidechain:
                content = entry.message.get("content", []) if entry.message else []
                if isinstance(content, str):
                    is_real_user_message = bool(content.strip())
                elif isinstance(content, list):
                    is_real_user_message = any(
                        (isinstance(b, dict) and b.get("type") != "tool_result")
                        or (isinstance(b, str) and b.strip())
                        for b in content
                    )
                else:
                    is_real_user_message = False
                if is_real_user_message:
                    stats.user_messages += 1
                    if seen_assistant_tool_use:
                        stats.mid_session_corrections += 1

            if tool_name and not seen_assistant_tool_use:
                seen_assistant_tool_use = True

            stats.add_entry(entry, tool_name=tool_name, agent_id=None, skill_name=skill_name)

        # Process subagent entries
        if agent_entries:
            for agent_id, agent_entry_list in agent_entries.items():
                for entry in agent_entry_list:
                    tool_name = None
                    skill_name = None
                    if entry.type == "assistant" and entry.message:
                        content = entry.message.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tool_name = block.get("name")
                                    if tool_name == "Skill" and isinstance(
                                        block.get("input"), dict
                                    ):
                                        skill_name = block["input"].get("skill")
                                    break

                    stats.add_entry(
                        entry, tool_name=tool_name, agent_id=agent_id, skill_name=skill_name
                    )

        if agent_entries:
            from .subagent_transcript import _build_subagent_type_index

            # Remap by_agent UUIDs → subagent names (rbg/pauli/marsha/…) so the
            # overwhelm-dashboard Insights view can attribute cost per agent
            # without re-resolving hashes. Unknown UUIDs are preserved verbatim
            # (fall back rather than crash). When two invocations of the same
            # subagent appear, sum their stats.
            type_index = _build_subagent_type_index(entries)
            if type_index:
                stats.by_agent = _remap_by_agent_keys(stats.by_agent, type_index)

        return stats

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (~1 token per 4 characters)."""
        return _estimate_tokens(text)

    def _format_compact_args(self, tool_input: dict[str, Any], max_length: int = 60) -> str:
        """Format tool arguments as compact Python-like syntax."""
        if not tool_input:
            return ""

        args = []
        for key, value in tool_input.items():
            if key == "description":
                continue
            if (
                key in ("old_string", "new_string", "prompt", "content")
                and isinstance(value, str)
                and len(value) > 100
            ):
                continue

            if isinstance(value, str):
                if len(value) > max_length:
                    if "/" in value and key in ("file_path", "path"):
                        value = value.split("/")[-1]
                    else:
                        value = value[: max_length - 3] + "..."
                value = value.replace('"', '\\"').replace("\n", "\\n").replace("`", "'")
                args.append(f'{key}="{value}"')
            elif isinstance(value, bool):
                args.append(f"{key}={value!s}")
            elif isinstance(value, int | float):
                args.append(f"{key}={value}")
            elif isinstance(value, list):
                if len(value) > 3:
                    args.append(f"{key}=[{len(value)} items]")
                else:
                    args.append(f"{key}={value}")
            elif isinstance(value, dict):
                args.append(f"{key}={{...{len(value)} keys}}")
            else:
                args.append(f"{key}=...")

        return ", ".join(args)

    def _format_tool_operation(self, tool_block: dict[str, Any]) -> str:
        """Format a single tool operation."""
        tool_name = tool_block.get("name", "Unknown")
        tool_input = tool_block.get("input", {})

        if tool_name == "TodoWrite":
            return self._format_todowrite_operation(tool_input)

        # Make Skill invocations prominent
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "unknown")
            return f"- **🔧 Skill invoked: `{skill_name}`**\n"

        # Make SlashCommand invocations prominent
        if tool_name == "SlashCommand":
            command = tool_input.get("command", "unknown")
            return f"- **📋 Command: `{command}`**\n"

        description = tool_input.get("description", "")

        args = self._format_compact_args(tool_input, max_length=60)
        tool_call = f"{tool_name}({args})" if args else f"{tool_name}()"

        if description:
            return f"- {description}: {tool_call}\n"
        return f"- {tool_call}\n"

    def _format_todowrite_operation(self, tool_input: dict[str, Any]) -> str:
        """Format TodoWrite operations in compact checkbox format."""
        todos = tool_input.get("todos", [])

        result = f"- **TodoWrite** ({len(todos)} items):\n"

        for todo in todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "No description")

            if status == "completed":
                symbol = "✓"
            elif status == "in_progress":
                symbol = "▶"
            else:
                symbol = "□"

            content_preview = self._truncate_for_display(content, 80)

            result += f"  {symbol} {content_preview}\n"

        return result

    def _format_condensed_tool_group(
        self, tool_name: str, tool_blocks: list[dict[str, Any]]
    ) -> str:
        """Format a group of consecutive same-tool calls in condensed format.

        For tools like Read, Glob, Grep - shows multiple calls on one line.
        E.g., "- Read: file1.py, file2.py, file3.py"
        """
        if len(tool_blocks) == 1:
            return self._format_tool_operation(tool_blocks[0])

        # Extract key info based on tool type
        if tool_name == "Read":
            files = []
            for block in tool_blocks:
                tool_input = block.get("input", {})
                path = tool_input.get("file_path", "")
                if path:
                    # Show just filename
                    filename = path.split("/")[-1]
                    files.append(filename)
            if files:
                return f"- Read: {', '.join(files)}\n"

        elif tool_name == "Glob":
            patterns = []
            for block in tool_blocks:
                tool_input = block.get("input", {})
                pattern = tool_input.get("pattern", "")
                if pattern:
                    patterns.append(f"`{pattern}`")
            if patterns:
                return f"- Glob: {', '.join(patterns)}\n"

        elif tool_name == "Grep":
            patterns = []
            for block in tool_blocks:
                tool_input = block.get("input", {})
                pattern = tool_input.get("pattern", "")
                if pattern:
                    if len(pattern) > 30:
                        pattern = pattern[:27] + "..."
                    patterns.append(f"`{pattern}`")
            if patterns:
                return f"- Grep: {', '.join(patterns)}\n"

        elif tool_name == "Edit":
            files = set()
            for block in tool_blocks:
                tool_input = block.get("input", {})
                path = tool_input.get("file_path", "")
                if path:
                    filename = path.split("/")[-1]
                    files.add(filename)
            if files:
                count = len(tool_blocks)
                return f"- Edit ({count}x): {', '.join(sorted(files))}\n"

        # Fallback: show count and first example
        first_block = tool_blocks[0]
        first_formatted = self._format_tool_operation(first_block).rstrip("\n")
        return f"{first_formatted} (+{len(tool_blocks) - 1} more)\n"

    def _extract_filename(self, path: str) -> str:
        """Extract just the filename from a path."""
        if not path:
            return ""
        return path.split("/")[-1]

    def _maybe_pretty_print_json(self, text: str) -> str:
        """Try to pretty-print JSON."""
        text = text.strip()
        if not text:
            return text
        if not (text.startswith("{") or text.startswith("[")):
            return text
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return text

    def _truncate_for_display(self, text: str, max_length: int) -> str:
        """Truncate text for display."""
        text = text.replace("\\n", "\n")

        if len(text) <= max_length:
            return text

        truncated = text[:max_length]

        if len(text) > max_length and text[max_length] != " ":
            last_space = truncated.rfind(" ")
            if last_space > max_length * 0.7:
                truncated = truncated[:last_space]

        return truncated + "..."

    def generate_session_slug(self, entries: list[Entry], max_words: int = 3) -> str:
        """Generate a brief slug from the first substantive user message.

        Args:
            entries: List of Entry objects
            max_words: Maximum words in slug (default 3)

        Returns:
            Kebab-case slug like 'session-storage-fix' or 'transcript-update'
        """
        # Find first user message that isn't a command or tool result
        for entry in entries:
            if entry.type == "user":
                content = ""
                # Get content from message dict or content dict
                if entry.message:
                    raw = entry.message.get("content", "")
                    # Handle content that might be a list (tool results)
                    if isinstance(raw, list):
                        continue
                    content = str(raw)
                elif entry.content:
                    content = str(entry.content.get("content", ""))

                # Skip command invocations, tool results, system messages
                if (
                    content.startswith("<command")
                    or content.startswith("[{")
                    or content.startswith("Caveat:")
                    or content.startswith("<local-command")
                    or content.startswith("<system")
                ):
                    continue

                # Skip very short messages
                if len(content) < 10:
                    continue

                # Extract meaningful words (skip common words)
                stop_words = {
                    "the",
                    "a",
                    "an",
                    "is",
                    "are",
                    "was",
                    "were",
                    "be",
                    "been",
                    "to",
                    "of",
                    "and",
                    "in",
                    "that",
                    "have",
                    "i",
                    "it",
                    "for",
                    "not",
                    "on",
                    "with",
                    "he",
                    "as",
                    "you",
                    "do",
                    "at",
                    "this",
                    "but",
                    "his",
                    "by",
                    "from",
                    "they",
                    "we",
                    "say",
                    "her",
                    "she",
                    "or",
                    "will",
                    "my",
                    "one",
                    "all",
                    "would",
                    "there",
                    "their",
                    "what",
                    "so",
                    "up",
                    "out",
                    "if",
                    "about",
                    "who",
                    "get",
                    "which",
                    "go",
                    "me",
                    "when",
                    "make",
                    "can",
                    "like",
                    "time",
                    "no",
                    "just",
                    "him",
                    "know",
                    "take",
                    "people",
                    "into",
                    "year",
                    "your",
                    "good",
                    "some",
                    "could",
                    "them",
                    "see",
                    "other",
                    "than",
                    "then",
                    "now",
                    "look",
                    "only",
                    "come",
                    "its",
                    "over",
                    "think",
                    "also",
                    "back",
                    "after",
                    "use",
                    "two",
                    "how",
                    "our",
                    "work",
                    "first",
                    "well",
                    "way",
                    "even",
                    "new",
                    "want",
                    "because",
                    "any",
                    "these",
                    "give",
                    "day",
                    "most",
                    "us",
                    "please",
                    "help",
                    "let",
                    "need",
                    "should",
                }

                # Clean and tokenize
                words = re.findall(r"[a-zA-Z]+", content.lower())
                meaningful = [w for w in words if w not in stop_words and len(w) > 2]

                if meaningful:
                    slug_words = meaningful[:max_words]
                    return "-".join(slug_words)

        return "session"
