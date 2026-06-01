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
from pathlib import Path

# Known artifact variants and their extensions
ARTIFACT_TYPES = {
    "transcript-full": {"variant": "-full", "ext": ".md", "subdir": "transcripts"},
    "transcript-abridged": {"variant": "-abridged", "ext": ".md", "subdir": "transcripts"},
    "insights": {"variant": "", "ext": ".json", "subdir": "summaries"},
    "hooks": {"variant": "-hooks", "ext": ".jsonl", "subdir": "hooks"},
    "client": {"variant": "-client", "ext": ".jsonl", "subdir": "client-logs"},
}

# Known providers/clients (used as shortform terminators for parsing).
#
# Two sources, merged at first access:
#   - Built-in LLM CLIs (claude, gemini): framework primitives, always present.
#   - external_agents map in $AOPS_SESSIONS/polecat.yaml: the operator-curated
#     list of dispatch targets (github, jules, codex, copilot, ...).
#
# Lazy resolution because session_naming is imported during test collection,
# before fixtures stage a config file.
_BUILTIN_PROVIDERS: frozenset[str] = frozenset({"claude", "gemini"})
_PROVIDERS_CACHE: set[str] | None = None


def _load_providers() -> set[str]:
    global _PROVIDERS_CACHE
    if _PROVIDERS_CACHE is None:
        # Local import to avoid circular dependencies and to keep this module
        # importable in environments without polecat_config (it will hard-fail
        # only when a caller actually exercises filename parsing).
        from lib.polecat_config import load_polecat_config

        cfg = load_polecat_config()
        _PROVIDERS_CACHE = set(_BUILTIN_PROVIDERS) | {
            name for name, agent in cfg.external_agents.items() if agent.enabled
        }
    return _PROVIDERS_CACHE


def _reset_providers_cache() -> None:
    """Test-only hook: drop cached providers so the next access re-reads YAML."""
    global _PROVIDERS_CACHE
    _PROVIDERS_CACHE = None


def __getattr__(name: str):
    if name == "PROVIDERS":
        return _load_providers()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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

    def base_name(self) -> str:
        """Reconstruct canonical base name (without variant/extension)."""
        shortform_parts = [p for p in (self.crew, self.repo, self.machine, self.provider) if p]
        shortform = "-".join(shortform_parts)
        return f"{self.date}-{self.time}-{self.session_id}-{shortform}-{self.slug}"


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


def get_surface() -> str:
    """Identify the runtime surface this session is executing on.

    Surface = provider × launcher. Used by the overwhelm-dashboard Insights view
    to group cost/yield by where work actually ran ("rbg on github actions" vs
    "rbg on claude polecat"). See Safeguard ROI v0 epic (aops-85b082c5).

    Returns one of:
        - ``github-actions``: $GITHUB_ACTIONS=true (CI runner)
        - ``{provider}-crew``: $AOPS_POLECAT_CONTAINER set with $POLECAT_CREW_NAME
        - ``{provider}-polecat``: $AOPS_POLECAT_CONTAINER set, no crew name
        - ``claude-code-cli`` / ``gemini-cli``: bare terminal session
    """
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"

    provider = get_provider_name()
    # Resolved dispatcher signals, not a self-identifying session-type label
    # (aops-b368109a): any polecat container is marked by AOPS_POLECAT_CONTAINER;
    # crew is further distinguished by the crew-name signal.
    if os.environ.get("AOPS_POLECAT_CONTAINER"):
        if os.environ.get("POLECAT_CREW_NAME"):
            return f"{provider}-crew"
        return f"{provider}-polecat"

    if provider == "gemini":
        return "gemini-cli"
    return "claude-code-cli"


def get_client() -> str:
    """Identify the launching tool/client for this session.

    Returns one of: ``claude-code``, ``gemini-cli``, ``polecat``, ``crew``,
    ``github-actions``. Coarser than ``surface``; useful for "which CLI was
    invoked" filtering independent of provider.
    """
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"

    # Resolved dispatcher signals, not a session-type label (aops-b368109a).
    if os.environ.get("AOPS_POLECAT_CONTAINER"):
        return "crew" if os.environ.get("POLECAT_CREW_NAME") else "polecat"

    provider = get_provider_name()
    if provider == "gemini":
        return "gemini-cli"
    return "claude-code"


def get_session_metadata(
    *,
    provider: str | None = None,
    surface: str | None = None,
    client: str | None = None,
    crew: str | None = None,
) -> dict[str, str | None]:
    """Return the canonical session-metadata block stamped onto summary JSON.

    Mirrors the fields read by the overwhelm-dashboard Insights view:
    machine, hostname, provider, surface, client, crew. ``provider`` may be
    overridden by callers that have detected it from a transcript path (e.g.
    the offline transcript→summary converter reading a ``.gemini/`` file from
    a shell whose env vars don't advertise gemini).

    Args:
        provider: Optional override for provider. When ``None`` (the default),
            falls back to ``get_provider_name()``.
        surface: Optional override for surface. When set, bypasses env-based
            detection (used by the offline converter which reads sessions long
            after the runtime env has been torn down — e.g. GHA jsonl files
            persisted under ``$AOPS_SESSIONS/github/``).
        client: Optional override for client. Same semantics as ``surface``.
        crew: Optional override for crew. Same semantics as ``surface``.
    """
    eff_provider = provider or get_provider_name()
    # When provider is overridden, recompute surface/client with that provider
    # in scope so the trio stays internally consistent.
    if provider is not None:
        original_env = os.environ.get("AOPS_PROVIDER_OVERRIDE")
        os.environ["AOPS_PROVIDER_OVERRIDE"] = provider
        try:
            detected_surface = _surface_with_provider(eff_provider)
            detected_client = _client_with_provider(eff_provider)
        finally:
            if original_env is None:
                os.environ.pop("AOPS_PROVIDER_OVERRIDE", None)
            else:
                os.environ["AOPS_PROVIDER_OVERRIDE"] = original_env
    else:
        detected_surface = get_surface()
        detected_client = get_client()

    return {
        "machine": os.environ.get("AOPS_MACHINE"),
        "hostname": get_hostname(),
        "provider": eff_provider,
        "surface": surface if surface is not None else detected_surface,
        "client": client if client is not None else detected_client,
        "crew": crew if crew is not None else resolve_crew_name(),
    }


def infer_provider_from_path(path: Path | str) -> str | None:
    """Return 'gemini', 'claude', or None inferred from a session file path."""
    s = str(path)
    if ".gemini/" in s:
        return "gemini"
    if "chats/session-" in s and (s.endswith(".json") or s.endswith(".jsonl")):
        return "gemini"
    if ".claude/" in s:
        return "claude"
    return None


def infer_session_origin_from_path(
    session_path: Path | str,
    *,
    provider: str | None = None,
) -> dict[str, str | None]:
    """Infer surface/client/crew from a persisted session file path.

    Used by the offline transcript→summary converter, which reads jsonl/json
    files long after the original runtime env (``GITHUB_ACTIONS``,
    ``AOPS_POLECAT_CONTAINER``, ``POLECAT_CREW_NAME``) is gone. Without this,
    every offline-converted summary stamps ``surface: claude-code-cli`` even
    for GHA/crew/polecat sessions.

    Path → (surface, client, crew) mapping:

    - ``$AOPS_SESSIONS/github/<repo>/<run_id>/<attempt>/...`` →
      surface=``github-actions``, client=``github-actions``, crew=None
    - ``$AOPS_SESSIONS/crew/<crew_name>/...`` →
      surface=``{provider}-crew``, client=``crew``, crew=``<crew_name>``
    - ``$AOPS_SESSIONS/polecats/<task_id>/...`` →
      surface=``{provider}-polecat``, client=``polecat``, crew=None
    - ``~/.gemini/...`` or any ``.gemini/`` segment →
      surface=``gemini-cli``, client=``gemini-cli``, crew=None
    - default →
      surface=``claude-code-cli``, client=``claude-code``, crew=None

    Args:
        session_path: Path to the persisted session file.
        provider: Provider override for ``{provider}-crew``/``{provider}-polecat``
            shortforms. Defaults to ``"claude"`` when not specified.

    Returns:
        ``{"surface": ..., "client": ..., "crew": ...}`` — fields suitable to
        forward as overrides to :func:`get_session_metadata`.
    """
    p = Path(session_path)
    parts = p.parts
    path_str = str(p)
    eff_provider = provider or "claude"

    # GHA: $AOPS_SESSIONS/github/<repo>/<run_id>/<attempt>/...
    if "github" in parts:
        return {"surface": "github-actions", "client": "github-actions", "crew": None}

    # Crew: $AOPS_SESSIONS/crew/<crew_name>/...
    if "crew" in parts:
        idx = parts.index("crew")
        crew_name = parts[idx + 1] if len(parts) > idx + 1 else None
        return {
            "surface": f"{eff_provider}-crew",
            "client": "crew",
            "crew": crew_name,
        }

    # Polecat: $AOPS_SESSIONS/polecats/<task_id>/...
    if "polecats" in parts:
        return {
            "surface": f"{eff_provider}-polecat",
            "client": "polecat",
            "crew": None,
        }

    # Gemini CLI (incl. ~/.gemini/tmp/.../chats/session-*.json)
    if ".gemini" in path_str or "/gemini/" in path_str:
        return {"surface": "gemini-cli", "client": "gemini-cli", "crew": None}

    # Default: bare Claude Code CLI
    if eff_provider == "gemini":
        return {"surface": "gemini-cli", "client": "gemini-cli", "crew": None}
    return {"surface": "claude-code-cli", "client": "claude-code", "crew": None}


# Detection signals for a Claude Desktop GUI "Local Agent Mode" (LAM) session.
# The desktop app caches plugins under
# ~/Library/Application Support/Claude/local-agent-mode-sessions/ and the CLI
# it shells out to writes its JSONL to ~/.claude/projects/<workspace>/ — same
# place as a terminal launch — so the path itself tells us nothing. The LAM
# path does leak into the JSONL via:
#   1. The "Base directory for this skill: <path>" line injected as a
#      system reminder when a /skill is invoked. This is software-emitted,
#      not user-typable, so it is the highest-confidence signal.
#   2. The `cwd` field claude-code stamps on each entry, which on LAM points
#      into the desktop's session sandbox.
# We deliberately do NOT scan plain user/assistant text for the path — users
# can mention "local-agent-mode-sessions" in chat (as in this very session)
# and that should not produce a false positive.
_LAM_PATH_MARKER = "Library/Application Support/Claude/local-agent-mode-sessions"
_LAM_SKILL_PREFIX = "Base directory for this skill: "


def infer_session_origin_from_entries(
    entries: list,
    base_origin: dict[str, str | None] | None = None,
    *,
    max_scan: int = 50,
) -> dict[str, str | None]:
    """Upgrade an origin dict by scanning JSONL entries for Claude Desktop LAM.

    Claude Code launched from inside Claude Desktop's "Local Agent Mode" writes
    its JSONL to the same ``~/.claude/projects/...`` location as a terminal
    launch, so :func:`infer_session_origin_from_path` cannot distinguish them.

    Two high-confidence signals trigger an upgrade to
    ``surface=claude-code-desktop`` / ``client=claude-desktop``:

    1. ``entry.cwd`` contains the LAM plugin-cache path.
    2. Any content text contains the software-injected skill-invocation
       header ``"Base directory for this skill: ..."`` whose path includes
       the LAM marker.

    Plain conversational text mentioning the marker is intentionally ignored
    — users can type the path into chat without it implying a LAM launch.

    Crew/polecat/GHA path detection takes priority — if the path already
    pinned a more specific surface, we leave it alone.
    """
    origin = (
        dict(base_origin)
        if base_origin
        else {
            "surface": "claude-code-cli",
            "client": "claude-code",
            "crew": None,
        }
    )

    if origin.get("surface") != "claude-code-cli":
        return origin

    for entry in (entries or [])[:max_scan]:
        if _entry_signals_lam(entry):
            origin["surface"] = "claude-code-desktop"
            origin["client"] = "claude-desktop"
            return origin

    return origin


def _entry_signals_lam(entry) -> bool:
    """True if an entry carries a high-confidence Claude Desktop LAM signal."""
    cwd = getattr(entry, "cwd", None)
    if isinstance(cwd, str) and _LAM_PATH_MARKER in cwd:
        return True

    for text in _iter_entry_text(entry):
        idx = text.find(_LAM_SKILL_PREFIX)
        if idx < 0:
            continue
        # The path follows the prefix on the same line; require the LAM
        # marker to appear within a reasonable window so chat that quotes
        # the prefix doesn't match a far-away mention by accident.
        tail = text[idx : idx + 1024]
        if _LAM_PATH_MARKER in tail:
            return True
    return False


def _iter_entry_text(entry):
    """Yield every text fragment carried by an entry's message content."""
    msg = getattr(entry, "message", None)
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        yield content
        return
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                for key in ("text", "content", "input"):
                    val = block.get(key)
                    if isinstance(val, str):
                        yield val
                    elif isinstance(val, dict):
                        for sub in val.values():
                            if isinstance(sub, str):
                                yield sub
            elif isinstance(block, str):
                yield block


def _surface_with_provider(provider: str) -> str:
    """Internal: surface detection with an explicit provider value."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"
    # Resolved dispatcher signals, not a session-type label (aops-b368109a).
    if os.environ.get("AOPS_POLECAT_CONTAINER"):
        if os.environ.get("POLECAT_CREW_NAME"):
            return f"{provider}-crew"
        return f"{provider}-polecat"
    if provider == "gemini":
        return "gemini-cli"
    return "claude-code-cli"


def _client_with_provider(provider: str) -> str:
    """Internal: client detection with an explicit provider value."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"
    # Resolved dispatcher signals, not a session-type label (aops-b368109a).
    if os.environ.get("AOPS_POLECAT_CONTAINER"):
        return "crew" if os.environ.get("POLECAT_CREW_NAME") else "polecat"
    if provider == "gemini":
        return "gemini-cli"
    return "claude-code"


def get_session_shortform(
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
) -> str:
    """Generate the shortform component: ``{crew?}-{repo}-{provider?}``.

    Provider is included in the filename so the runtime that produced the
    artefact (claude, gemini, github, jules…) is visible at a glance.
    Frontmatter remains authoritative for canonical metadata.

    Args:
        crew_name: Crew name (None for manual/polecat-run sessions)
        repo: Repository name (auto-detected if None)
        machine: Ignored (legacy parameter — kept for callsite compatibility)
        provider: Provider/client name (auto-detected if None)

    Returns:
        Shortform string like "gloria-academicops-gemini" or "academicops-claude"
    """
    if repo is None:
        repo = get_repo_name()
    if provider is None:
        provider = get_provider_name()

    parts = []
    if crew_name:
        parts.append(_sanitize(crew_name, allow_dashes=False))
    parts.append(_sanitize(repo, allow_dashes=False))
    if provider:
        parts.append(_sanitize(provider, allow_dashes=False))

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
    slug: str | None = None,
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
    artifact_type: str = "transcript-full",
    shortform: str | None = None,
    task_id: str | None = None,
) -> str:
    """Generate a session artifact filename following the naming convention.

    Format: ``{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}``
    where shortform is ``{crew?}-{repo}-{provider}`` (or a provided override).
    When slug is None, the slug component is omitted for deterministic naming.

    Args:
        session_id: Full session ID (will be shortened to 8 chars)
        timestamp: Session start time (defaults to now)
        slug: Content slug, kebab-case. None omits the slug for deterministic naming.
        crew_name: Crew name or None for non-crew sessions
        repo: Repository name (auto-detected if None)
        machine: Ignored (kept for legacy callsite compatibility)
        provider: Provider/client name (auto-detected if None)
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
        shortform = get_session_shortform(crew_name, repo, provider=provider)
    art = ARTIFACT_TYPES[artifact_type]

    if slug is not None:
        safe_slug = _sanitize_slug(slug, shortform=shortform)
        task_prefix = _format_task_prefix(task_id)
        return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_prefix}{safe_slug}{art['variant']}{art['ext']}"
    else:
        task_part = _format_task_prefix(task_id).rstrip("-")
        if task_part:
            return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_part}{art['variant']}{art['ext']}"
        return f"{date_str}-{time_str}-{short_id}-{shortform}{art['variant']}{art['ext']}"


def generate_base_name(
    session_id: str,
    timestamp: datetime | None = None,
    slug: str | None = None,
    crew_name: str | None = None,
    repo: str | None = None,
    machine: str | None = None,
    provider: str | None = None,
    shortform: str | None = None,
    task_id: str | None = None,
) -> str:
    """Generate the base name shared across all artifacts for a session.

    Returns: {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}
    When slug is None, the slug component is omitted for deterministic naming.
    """
    if timestamp is None:
        timestamp = datetime.now().astimezone()

    short_id = get_session_short_hash(session_id)
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M")
    if shortform is None:
        shortform = get_session_shortform(crew_name, repo, provider=provider)

    if slug is not None:
        safe_slug = _sanitize_slug(slug, shortform=shortform)
        task_prefix = _format_task_prefix(task_id)
        return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_prefix}{safe_slug}"
    else:
        task_part = _format_task_prefix(task_id).rstrip("-")
        if task_part:
            return f"{date_str}-{time_str}-{short_id}-{shortform}-{task_part}"
        return f"{date_str}-{time_str}-{short_id}-{shortform}"


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

    # Detect provider token (claude/gemini/github/jules/...) in shortform
    providers = _load_providers()
    provider_idx = None
    for i in range(3, len(parts)):
        if parts[i] in providers:
            provider_idx = i
            break

    if provider_idx is not None:
        # Shortform with provider. Two layouts coexist:
        #   v4 legacy (with machine): {crew?}-{repo}-{machine}-{provider}
        #   current      (no machine): {crew?}-{repo}-{provider}
        # Disambiguate by count of shortform tokens.
        shortform_parts = parts[3:provider_idx]
        provider = parts[provider_idx]

        if len(shortform_parts) == 0:
            return None

        if len(shortform_parts) == 1:
            # current, no crew: [repo]
            crew = None
            repo = shortform_parts[0]
            machine = None
        elif len(shortform_parts) == 2:
            # current, with crew: [crew, repo]
            # (v4 legacy no-crew [repo, machine] is rare and obsolete; frontmatter
            # is authoritative for real values.)
            crew = shortform_parts[0]
            repo = shortform_parts[1]
            machine = None
        else:
            # v4 legacy with crew + machine: [crew, repo..., machine]
            crew = shortform_parts[0]
            machine = shortform_parts[-1]
            repo = "-".join(shortform_parts[1:-1])

        slug_parts = parts[provider_idx + 1 :]
        slug = "-".join(slug_parts) if slug_parts else "session"
    else:
        # No provider in name (very-old or hand-written file). Best-effort:
        # assume [crew, repo, slug...] if 6+ parts, else [repo, slug...].
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


def _sanitize_slug(slug: str, max_words: int = 5, shortform: str | None = None) -> str:
    """Sanitize and truncate a slug.

    Args:
        slug: Raw slug string
        max_words: Maximum number of words to keep
        shortform: Optional shortform string (e.g. ``"jewelle-academicops"``)
            whose component tokens get stripped from the slug to avoid
            repetition like ``jewelle-crewjewelle-...``. A slug token is
            dropped when it *contains* any shortform token as a substring
            — which catches both bare repeats (``jewelle``) and run-on
            forms produced by separator-less first messages
            (``crewjewelle``, ``aopsmaintenance``).

    Returns:
        Kebab-case slug, max max_words words
    """
    slug = _sanitize(slug)
    words = [w for w in slug.split("-") if w]

    if shortform:
        shortform_tokens = {t for t in _sanitize(shortform).split("-") if len(t) >= 3}
        if shortform_tokens:
            filtered = [w for w in words if not any(tok in w for tok in shortform_tokens)]
            # Only apply the filter if it leaves us with something — never
            # let dedupe drop the slug entirely.
            if filtered:
                words = filtered

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

    # Legacy fallback: polecat now emits "{hash}-gemini" but older sessions
    # or hand-set AOPS_SESSION_IDs may still use "gemini-" prefix.
    session_id = os.environ.get("AOPS_SESSION_ID", "")
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
