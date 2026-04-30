"""Session naming module - single source of truth for session artifact filenames.

Implements the naming convention from the session-naming-convention spec (brain PKB):
    {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}

All session artifact filename generation MUST go through this module.
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
from dataclasses import dataclass
from datetime import datetime

# Known artifact variants and their extensions
ARTIFACT_TYPES = {
    "transcript-full": {"variant": "-full", "ext": ".md", "subdir": "transcripts"},
    "transcript-abridged": {"variant": "-abridged", "ext": ".md", "subdir": "transcripts"},
    "insights": {"variant": "", "ext": ".json", "subdir": "summaries"},
    "hooks": {"variant": "-hooks", "ext": ".jsonl", "subdir": "hooks"},
    "client": {"variant": "-client", "ext": ".jsonl", "subdir": "client-logs"},
}

# Known providers (used as shortform terminators for parsing)
PROVIDERS = {"claude", "gemini"}

# Known variants (used for parsing)
VARIANTS = {"-full", "-abridged", "-hooks", "-client", "-enforcer"}


@dataclass
class ParsedFilename:
    """Components extracted from a session filename."""

    date: str  # YYYYMMDD
    time: str  # HHMM
    session_id: str  # 8-char hash
    crew: str | None  # crew name or None
    repo: str  # repository name
    machine: str | None  # machine short name (None for new format)
    provider: str | None  # "claude" or "gemini" (None for new format)
    slug: str  # content slug
    variant: str  # "-full", "-abridged", "-hooks", "-client", or ""
    ext: str  # ".md", ".json", ".jsonl"


def get_session_short_hash(session_id: str) -> str:
    """Get 8-character identifier from session ID.

    For standard UUIDs or long IDs, uses the first 8 alphanumeric chars.
    Falls back to SHA-256 hash for short/non-standard IDs.

    Args:
        session_id: Full session identifier

    Returns:
        8-character lowercase string
    """
    if not session_id or session_id == "unknown":
        raise ValueError(f"Invalid session_id: {session_id!r}. Callers must guard before calling.")

    if len(session_id) >= 8:
        prefix = session_id[:8].lower()
        if all(c in "0123456789abcdefghijklmnopqrstuvwxyz" for c in prefix):
            return prefix

    return hashlib.sha256(session_id.encode()).hexdigest()[:8]


def derive_polecat_session_id(task_id: str) -> str:
    """Derive session hash from task ID for polecat sessions.

    For task IDs like 'aops-a1b2c3d4-fix-something', extracts the
    8-char hex hash portion. For other formats, hashes the full ID.

    Args:
        task_id: Full task ID string

    Returns:
        8-character hex string
    """
    parts = task_id.split("-")
    for part in parts:
        if len(part) == 8 and all(c in "0123456789abcdef" for c in part.lower()):
            return part.lower()
    return hashlib.sha256(task_id.encode()).hexdigest()[:8]


def get_machine_name() -> str:
    """Get short machine name for filename shortform.

    Uses $AOPS_MACHINE if set, falls back to short hostname.

    Returns:
        Lowercase machine name string
    """
    machine = os.environ.get("AOPS_MACHINE")
    if machine:
        return _sanitize(machine)
    return _sanitize(socket.gethostname().split(".")[0])


def get_hostname() -> str:
    """Get raw OS hostname for session metadata.

    Unlike get_machine_name(), this returns the unsanitized hostname
    from socket.gethostname() without falling back to $AOPS_MACHINE.
    Used to stamp session summaries with "where was this running?".

    Returns:
        Hostname string (e.g. "nics-macbook.local", "camus-server")
    """
    return socket.gethostname()


def get_repo_name(project_dir: str | None = None) -> str:
    """Get repository name from project directory.

    Uses the provided path, $CLAUDE_PROJECT_DIR, or cwd.

    Args:
        project_dir: Optional explicit project directory path

    Returns:
        Lowercase repository basename
    """
    if project_dir is None:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # Use basename of the directory
    basename = os.path.basename(os.path.normpath(project_dir))
    return _sanitize(basename)


def resolve_crew_name() -> str | None:
    """Resolve crew name from environment.

    Reads $POLECAT_CREW_NAME. Returns None (manual/polecat-run session) if unset
    or empty. Call this explicitly at runtime call sites — keep pure naming
    functions env-free so tests don't leak host env.
    """
    name = os.environ.get("POLECAT_CREW_NAME")
    return name or None


def get_session_shortform(
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
) -> str:
    """Generate the shortform component: {crew}-{repo}.

    Environmental context (machine, provider) is no longer included in the
    filename. It belongs in the file frontmatter/metadata.

    Args:
        crew_name: Crew name (None for manual/polecat-run sessions)
        repo: Repository name (auto-detected if None)
        machine: Ignored (legacy parameter)
        provider: Ignored (legacy parameter)

    Returns:
        Shortform string like "gloria-academicops"
    """
    if repo is None:
        repo = get_repo_name()

    parts = []
    if crew_name:
        parts.append(_sanitize(crew_name, allow_dashes=False))
    parts.append(_sanitize(repo, allow_dashes=False))

    return "-".join(parts)


def _format_task_prefix(task_id: str | None) -> str:
    """Derive a grep-friendly ``task-XXXXXXXX-`` prefix from a task ID.

    Uses the same logic as :func:`derive_polecat_session_id` to extract an 8-char
    hex shortform from a full task ID like ``task-c36a6b0c-some-slug``. Falls
    back to SHA-256[:8] for non-hex IDs.

    Returns an empty string when ``task_id`` is None/empty so the prefix is a
    no-op for non-task sessions.
    """
    if not task_id:
        return ""
    short = derive_polecat_session_id(task_id)
    return f"task-{short}-"


def generate_session_filename(
    session_id: str,
    timestamp: datetime | None = None,
    slug: str = "session",
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
    artifact_type: str = "transcript-full",
    shortform: str | None = None,
    task_id: str | None = None,
) -> str:
    """Generate a session artifact filename following the naming convention.

    Format: {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}
    where shortform is {crew}-{repo} (or provided override).

    Args:
        session_id: Full session ID (will be shortened to 8 chars)
        timestamp: Session start time (defaults to now)
        slug: Content slug, kebab-case (default "session")
        crew_name: Crew name or None for non-crew sessions
        repo: Repository name (auto-detected if None)
        machine: Ignored (moved to frontmatter)
        provider: Ignored (moved to frontmatter)
        artifact_type: One of ARTIFACT_TYPES keys
        shortform: Optional explicit shortform override

    Returns:
        Filename string (no directory prefix)
    """
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(
            f"Unknown artifact_type: {artifact_type}. Must be one of {list(ARTIFACT_TYPES.keys())}"
        )

    if timestamp is None:
        timestamp = datetime.now().astimezone()

    short_id = get_session_short_hash(session_id)
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M")
    if shortform is None:
        shortform = get_session_shortform(crew_name, repo)
    safe_slug = _sanitize_slug(slug)
    art = ARTIFACT_TYPES[artifact_type]
    task_prefix = _format_task_prefix(task_id)

    return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_prefix}{safe_slug}{art['variant']}{art['ext']}"


def generate_base_name(
    session_id: str,
    timestamp: datetime | None = None,
    slug: str = "session",
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
    shortform: str | None = None,
    task_id: str | None = None,
) -> str:
    """Generate the base name shared across all artifacts for a session.

    Returns: {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}
    """
    if timestamp is None:
        timestamp = datetime.now().astimezone()

    short_id = get_session_short_hash(session_id)
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M")
    if shortform is None:
        shortform = get_session_shortform(crew_name, repo)
    safe_slug = _sanitize_slug(slug)
    task_prefix = _format_task_prefix(task_id)

    return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_prefix}{safe_slug}"


def get_artifact_subdir(artifact_type: str) -> str:
    """Get the subdirectory within AOPS_SESSIONS for an artifact type.

    Args:
        artifact_type: One of ARTIFACT_TYPES keys

    Returns:
        Subdirectory name (e.g., "transcripts", "summaries")
    """
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unknown artifact_type: {artifact_type}")
    return ARTIFACT_TYPES[artifact_type]["subdir"]


def parse_session_filename(filename: str) -> ParsedFilename | None:
    """Parse a session filename into its components.

    Handles both:
    Old: {YYYYMMDD}-{HHMM}-{session_id}-{crew}-{repo}-{machine}-{provider}-{slug}{-variant}.{ext}
    New: {YYYYMMDD}-{HHMM}-{session_id}-{crew}-{repo}-{slug}{-variant}.{ext}

    **Known limitation — new format is structurally ambiguous**: crew and repo
    cannot be reliably distinguished from a multi-word slug without a delimiter.
    The heuristic used (>=6 parts → assume crew+repo; <6 parts → repo only) will
    misparse manual sessions with multi-word slugs (e.g. `date-time-id-repo-fix-the-bug`
    → crew=repo, repo=fix, slug=bug). Frontmatter is authoritative for all metadata;
    treat parsed crew/repo as low-confidence when machine/provider are both None.

    Args:
        filename: Filename string (with or without directory prefix)

    Returns:
        ParsedFilename dataclass, or None if the filename doesn't match the convention
    """
    # Strip directory prefix
    basename = os.path.basename(filename)

    # Extract extension
    ext = ""
    if basename.endswith(".jsonl"):
        ext = ".jsonl"
        body = basename[:-6]
    elif basename.endswith(".json"):
        ext = ".json"
        body = basename[:-5]
    elif basename.endswith(".md"):
        ext = ".md"
        body = basename[:-3]
    else:
        return None

    # Extract variant from end of body
    variant = ""
    for v in VARIANTS:
        if body.endswith(v):
            variant = v
            body = body[: -len(v)]
            break

    # Split on dashes
    parts = body.split("-")

    # Need at minimum: YYYYMMDD, HHMM, session_id, repo, slug(1+ words)
    # New format minimum parts: 5 (date, time, id, repo, slug)
    if len(parts) < 5:
        return None

    # Extract fixed-position components
    date = parts[0]
    time = parts[1]

    # Validate date and time format
    if not (len(date) == 8 and date.isdigit()):
        return None
    if not (len(time) == 4 and time.isdigit()):
        return None

    session_id = parts[2]
    if len(session_id) != 8:
        return None

    # Detect if old format by looking for a provider
    provider_idx = None
    for i in range(3, len(parts)):
        if parts[i] in PROVIDERS:
            provider_idx = i
            break

    if provider_idx is not None:
        # OLD FORMAT
        shortform_parts = parts[3:provider_idx]
        provider = parts[provider_idx]

        if len(shortform_parts) < 2:
            return None

        if len(shortform_parts) >= 3:
            crew = shortform_parts[0]
            machine = shortform_parts[-1]
            repo = "-".join(shortform_parts[1:-1])
        else:
            crew = None
            repo = shortform_parts[0]
            machine = shortform_parts[1]

        slug_parts = parts[provider_idx + 1 :]
        slug = "-".join(slug_parts) if slug_parts else "session"
    else:
        # NEW FORMAT
        # Parts: [date, time, id, crew?, repo, slug...]
        # We can't perfectly distinguish crew-repo-slug from repo-slug without
        # a delimiter. We'll use a simple heuristic based on the number of parts.
        # If we have 5 parts, it's [date, time, id, repo, slug]
        # If we have 6+ parts, we'll check if parts[3] looks like a crew name.
        # For now, we'll assume the first part of shortform is repo if only 1 part
        # between id and slug-start.

        # We'll assume the slug starts at parts[4] if there are at least 5 parts
        # and we don't know any better.

        # Actually, let's keep it simple: assume 1 part for shortform (repo)
        # unless we find a reason to think otherwise.

        # Wait, if I assume 1 part for shortform, then:
        # id-academicops-fix-bug -> repo=academicops, slug=fix-bug
        # id-gloria-academicops-fix-bug -> repo=gloria, slug=academicops-fix-bug (WRONG)

        # If I assume 2 parts for shortform?
        # id-academicops-fix-bug -> crew=academicops, repo=fix, slug=bug (WRONG)

        # This is indeed ambiguous. But since frontmatter is authoritative,
        # we'll just do our best. I'll assume 1 part for now as it's the most common (no crew).
        # Better heuristic: if we have 6+ parts, assume parts[3] is crew and parts[4] is repo.

        if len(parts) >= 6:
            crew = parts[3]
            repo = parts[4]
            slug_parts = parts[5:]
        else:
            crew = None
            repo = parts[3]
            slug_parts = parts[4:]

        slug = "-".join(slug_parts) if slug_parts else "session"
        machine = None
        provider = None

    return ParsedFilename(
        date=date,
        time=time,
        session_id=session_id,
        crew=crew,
        repo=repo,
        machine=machine,
        provider=provider,
        slug=slug,
        variant=variant,
        ext=ext,
    )


# --- Private helpers ---


def _sanitize(s: str, *, allow_dashes: bool = True) -> str:
    """Sanitize a string for use in filenames.

    Lowercases, replaces non-alphanumeric chars with dashes,
    collapses multiple dashes, strips leading/trailing dashes.

    Args:
        s: String to sanitize.
        allow_dashes: If False, remove all dashes from the result.
            Used for shortform components (crew, repo, machine) where dashes
            serve as inter-component delimiters and must not appear within
            individual components.
    """
    s = s.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    if not allow_dashes:
        s = s.replace("-", "")
    return s


def _sanitize_slug(slug: str, max_words: int = 5) -> str:
    """Sanitize and truncate a slug.

    Args:
        slug: Raw slug string
        max_words: Maximum number of words to keep

    Returns:
        Kebab-case slug, max max_words words
    """
    slug = _sanitize(slug)
    words = [w for w in slug.split("-") if w]
    if len(words) > max_words:
        words = words[:max_words]
    return "-".join(words) or "session"


def get_provider_name() -> str:
    """Detect whether current session is Claude or Gemini.

    Returns:
        "gemini" if Gemini session detected, "claude" otherwise
    """
    if os.environ.get("GEMINI_SESSION_ID"):
        return "gemini"

    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if session_id.startswith("gemini-"):
        return "gemini"

    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR", "")
    if "/.gemini/" in state_dir:
        return "gemini"

    return "claude"


def get_session_filename(
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
    project: str | None = None,
    slug: str | None = None,
    suffix: str = ".json",
) -> str:
    """Generate a unified filename for session-related files.

    Format: YYYYMMDD-HH-[project-][shorthash][-slug][suffix]

    Args:
        session_id: Session identifier
        date: Date in YYYY-MM-DD format or ISO 8601 (defaults to now)
        hour: 2-digit hour (defaults to extraction from date or now)
        project: Optional project name to include
        slug: Optional descriptive slug
        suffix: File extension/suffix (including dot)

    Returns:
        Formatted filename string
    """
    # 1. Extract date and hour components
    if date is None:
        now = datetime.now().astimezone()
        date_compact = now.strftime("%Y%m%d")
        if hour is None:
            hour = now.strftime("%H")
    elif "T" in date:
        # ISO 8601 format: 2026-01-24T17:30:00+10:00
        dt = datetime.fromisoformat(date)
        date_compact = dt.strftime("%Y%m%d")
        if hour is None:
            hour = dt.strftime("%H")
    else:
        # Simple YYYY-MM-DD format
        date_compact = date.replace("-", "")
        if hour is None:
            hour = datetime.now().astimezone().strftime("%H")

    # 2. Get short hash
    short_hash = get_session_short_hash(session_id)

    # 3. Build parts list
    parts = [date_compact, hour]
    if project:
        parts.append(project)
    parts.append(short_hash)
    if slug:
        parts.append(slug)

    # 4. Join and append suffix
    base = "-".join(parts)
    return f"{base}{suffix}"


def get_hook_log_filename(
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
) -> str:
    """Generate a unified filename for hook logs.

    Format: YYYYMMDD-HH-shorthash-hooks.jsonl
    """
    return get_session_filename(
        session_id=session_id,
        date=date,
        hour=hour,
        suffix="-hooks.jsonl",
    )


def get_gate_filename(
    gate: str,
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
) -> str:
    """Generate a unified filename for gate context files.

    Format: YYYYMMDD-HH-shorthash-gate.md
    """
    return get_session_filename(
        session_id=session_id,
        date=date,
        hour=hour,
        suffix=f"-{gate}.md",
    )
