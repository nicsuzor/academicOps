#!/usr/bin/env python3
"""
claude_code_tracer.py — OpenInference tracer for Claude Code hooks.

Ships Claude Code activities as OpenTelemetry / OpenInference traces to Phoenix or an OTLP collector.

Trace model:
  - Each user prompt → one trace (CHAIN root + TOOL/RETRIEVER/AGENT children + LLM children)
  - Exiting the session completes the current in-progress trace
  - Traces are linked by session.id attribute

Hook events:
  user_prompt_submit — start a new trace; complete previous trace if in progress
  pre_tool           — record current tool start (fallback trace creation if UserPromptSubmit unavailable)
  post_tool          — send a TOOL/RETRIEVER/AGENT span for the completed tool call
  post_tool_failure  — send an error TOOL/RETRIEVER/AGENT span for a failed tool call
  stop               — complete the current trace and clean up session state

Config priority (highest first):
  1. Env vars: GENAI_ENGINE_API_KEY, GENAI_ENGINE_TASK_ID, GENAI_ENGINE_TRACE_ENDPOINT
  2. Silent no-op if nothing configured
"""

import contextlib
import fcntl
import json
import logging
import os
import re
import socket
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging — stderr only so stdout stays clean for Claude hooks
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="[claude_code_tracer] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("claude_code_tracer")


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------


def _load_config_file(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to read config %s: %s", path, e)
    return {}


def _load_polecat_config() -> dict:
    sessions = os.environ.get("AOPS_SESSIONS")
    cfg_path = os.path.join(sessions, "polecat.yaml") if sessions else None
    if cfg_path and os.path.exists(cfg_path):
        try:
            import yaml

            with open(cfg_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log.debug("Failed to read polecat config %s: %s", cfg_path, e)
    return {}


DEFAULT_CANONICAL_ALIASES = {
    "aops": "academicOps",
    "academicops": "academicOps",
    "academic_ops": "academicOps",
}


def resolve_canonical_project(project: str | None, config: dict | None = None) -> str | None:
    """Resolve a project name or alias to its canonical project slug.

    Reads aliases configured in polecat.yaml:
    - `projects.<slug>.aliases`: list of alias strings or single alias string
    - top-level `aliases:` dict: mapping from alias to canonical slug (e.g. `aops: academicOps`),
      or canonical slug to alias list (e.g. `academicOps: [aops, academicops]`).

    If `project` matches a canonical slug or an alias (checked case-insensitively if exact
    case does not hit), returns the canonical slug.
    Also handles `<alias>-<task_id>` prefixes by canonicalizing the prefix.
    If no alias matches in config, checks default canonical aliases.
    If no alias matches, returns `project`.
    """
    if not project:
        return project

    if config is None:
        config = _load_polecat_config()

    project_str = str(project).strip()
    if not project_str:
        return project

    if project_str in DEFAULT_CANONICAL_ALIASES:
        return DEFAULT_CANONICAL_ALIASES[project_str]
    for k, v in DEFAULT_CANONICAL_ALIASES.items():
        if k.lower() == project_str.lower():
            return v

    projects = config.get("projects", {}) if config else {}
    if isinstance(projects, dict) and project_str in projects:
        return project_str

    if isinstance(projects, dict):
        for slug, p_cfg in projects.items():
            if isinstance(p_cfg, dict):
                aliases = p_cfg.get("aliases") or p_cfg.get("alias")
                if isinstance(aliases, str) and aliases == project_str:
                    return str(slug)
                elif isinstance(aliases, (list, tuple, set)) and project_str in aliases:
                    return str(slug)

        for slug, p_cfg in projects.items():
            if str(slug).lower() == project_str.lower():
                return str(slug)
            if isinstance(p_cfg, dict):
                aliases = p_cfg.get("aliases") or p_cfg.get("alias")
                if isinstance(aliases, str) and aliases.lower() == project_str.lower():
                    return str(slug)
                elif isinstance(aliases, (list, tuple, set)):
                    if any(str(a).lower() == project_str.lower() for a in aliases):
                        return str(slug)

    top_aliases = config.get("aliases", {}) if config else {}
    if isinstance(top_aliases, dict):
        if project_str in top_aliases and isinstance(top_aliases[project_str], str):
            return str(top_aliases[project_str])

        for target, val in top_aliases.items():
            if isinstance(val, str):
                if target == project_str:
                    return str(val)
                if val == project_str:
                    return str(val)
                if target.lower() == project_str.lower():
                    return str(val)
                if val.lower() == project_str.lower():
                    return str(target)
            elif isinstance(val, (list, tuple, set)):
                if project_str in val or any(str(a).lower() == project_str.lower() for a in val):
                    return str(target)

        for k, v in top_aliases.items():
            if k.lower() == project_str.lower() and isinstance(v, str):
                return str(v)

    if "-" in project_str:
        prefix, rest = project_str.split("-", 1)
        canon_prefix = resolve_canonical_project(prefix, config)
        if canon_prefix and canon_prefix != prefix:
            return f"{canon_prefix}-{rest}"

    if project_str in DEFAULT_CANONICAL_ALIASES:
        return DEFAULT_CANONICAL_ALIASES[project_str]
    for k, v in DEFAULT_CANONICAL_ALIASES.items():
        if k.lower() == project_str.lower():
            return v

    return project_str


def resolve_project_from_dir(cwd: str) -> str:
    """Resolve project name from git metadata, worktree layout, or directory structure."""
    if not cwd:
        return ""
    try:
        p = Path(cwd).resolve()

        # 1. Check if git worktree file exists (.git file with gitdir pointer)
        git_target = p / ".git"
        if git_target.is_file():
            try:
                text = git_target.read_text(encoding="utf-8").strip()
                if text.startswith("gitdir:"):
                    gitdir_path = Path(text.split(":", 1)[1].strip())
                    if not gitdir_path.is_absolute():
                        gitdir_path = (p / gitdir_path).resolve()
                    for parent in (gitdir_path, *gitdir_path.parents):
                        if parent.name == ".git":
                            repo_name = parent.parent.name
                            if repo_name and repo_name not in ("/", "\\", ".", "workspace"):
                                return repo_name
            except Exception:
                pass

        # 2. Check worktree path convention: .../worktrees/<project>/<branch>
        parts = p.parts
        if "worktrees" in parts:
            idx = parts.index("worktrees")
            if idx + 1 < len(parts):
                cand = parts[idx + 1]
                if cand and cand not in ("/", "\\", "."):
                    return cand

        # 3. Check enclosing git repo
        for parent in (p, *p.parents):
            if (parent / ".git").is_dir():
                repo_name = parent.name
                if repo_name and repo_name not in ("/", "\\", ".", "workspace"):
                    return repo_name
                if repo_name == "workspace":
                    try:
                        import subprocess

                        out = subprocess.check_output(
                            ["git", "-C", str(parent), "config", "--get", "remote.origin.url"],
                            text=True,
                            timeout=2,
                            stderr=subprocess.DEVNULL,
                        ).strip()
                        if out:
                            remote_name = (
                                out.rstrip("/").removesuffix(".git").split("/")[-1].split(":")[-1]
                            )
                            if remote_name and remote_name not in ("/", "\\", "."):
                                return remote_name
                    except Exception:
                        pass
                break
    except Exception:
        pass
    return ""


def resolve_checkout_root(cwd: str | None = None) -> str:
    """Resolve the git checkout root directory from cwd, or return cwd."""
    if not cwd:
        return ""
    try:
        p = Path(cwd).resolve()
        for parent in (p, *p.parents):
            if (parent / ".git").exists():
                return str(parent)
    except Exception:
        pass
    return str(Path(cwd).resolve()) if cwd else ""


def resolve_project_name(
    data: dict | None = None,
    project: str = "",
    config: dict | None = None,
) -> str:
    """Resolve project name to the single Phoenix project 'academicOps',
    honoring explicit overrides (or non-default PHOENIX_PROJECT_NAME)
    and never deriving project name from directory or cwd.
    """
    if project and project.strip() and project.strip().lower() != "default":
        return project.strip()
    if (
        env_phoenix := os.environ.get("PHOENIX_PROJECT_NAME", "").strip()
    ) and env_phoenix.lower() != "default":
        return env_phoenix
    return "academicOps"


def resolve_cwd(data: dict | None = None, state: dict | None = None) -> str:
    """Resolve the working directory path for this session.

    Priority:
    1. data['cwd'] (hook payload) or data['workspacePaths'] / data['workspace_paths']
    2. state['cwd'] (cached session state)
    3. CLAUDE_PROJECT_DIR env var
    4. os.getcwd()
    """
    cwd = ""
    if data and isinstance(data, dict):
        cwd = str(data.get("cwd") or "").strip()
        if not cwd:
            wp = data.get("workspacePaths") or data.get("workspace_paths")
            if isinstance(wp, (list, tuple)) and wp:
                cwd = str(wp[0]).strip()
            elif isinstance(wp, str) and wp.strip():
                cwd = wp.strip()
    if not cwd and state and isinstance(state, dict):
        cwd = str(state.get("cwd") or "").strip()
    if not cwd:
        cwd = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if not cwd:
        try:
            cwd = os.getcwd()
        except Exception:
            cwd = ""
    if cwd:
        try:
            return str(Path(cwd).resolve())
        except Exception:
            return cwd
    return ""


_TASK_ID_RE = re.compile(
    r"^(?:[a-z][a-z0-9-]*[_-])?[0-9a-f]{8}$"
    r"|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    r"|^wf-[a-z0-9-]+$"
    r"|^[a-z]+-[0-9a-f]{8}$"
    r"|^(?:engine-)?task-\d+$"
    r"|^[a-z][a-z0-9_.-]*[_-][0-9a-f]{6,}$",
    re.IGNORECASE,
)
_KNOWN_NON_TASK_IDS = {"ns", "default", "academicops", "aops"}


def is_valid_task_id(task_id: str) -> bool:
    """Return True if task_id resembles an actual task/epic ID rather than a namespace/placeholder."""
    if not task_id:
        return False
    tid = task_id.strip()
    if tid.lower() in _KNOWN_NON_TASK_IDS:
        return False
    if _TASK_ID_RE.match(tid):
        return True
    if re.match(r"^(?:task|epic|aops|wf)[_-][a-zA-Z0-9_-]+$", tid, re.IGNORECASE):
        return True
    return False


def resolve_client_agent_name(data: dict | None = None) -> str:
    """Extract agent name reported in client hook payload, if present."""
    if data and isinstance(data, dict):
        for k in ("agent_name", "agent", "agent_type", "subagent_type", "role"):
            val = str(data.get(k) or "").strip()
            if val:
                if ":" in val:
                    val = val.split(":", 1)[1].strip()
                if val:
                    return val
    return ""


def resolve_agent_name(
    data: dict | None = None,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Resolve agent name: client-reported payload field(s), then AOPS_AGENT_NAME env var, else empty string.

    No settings-file scan, directory heuristics, or default fallback.
    """
    client_name = resolve_client_agent_name(data)
    if client_name:
        return client_name
    return os.environ.get("AOPS_AGENT_NAME", "").strip()


def discover_config(data: dict | None = None) -> dict | None:
    """Returns config dict with keys: api_key, task_id, endpoint, protocol (optional), project_name, cwd, agent_name.
    Returns None if not configured (silent no-op)."""
    api_key = (
        os.environ.get("GENAI_ENGINE_API_KEY")
        or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS", "")
    )
    endpoint = (
        os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "")
    )
    protocol = (
        os.environ.get("GENAI_ENGINE_TRACE_PROTOCOL")
        or os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "")
    )

    if not endpoint:
        return None

    project_name = resolve_project_name(data)

    task_id_candidates: list[Any] = []
    if data and isinstance(data, dict):
        if "task_id" in data:
            task_id_candidates.append(data["task_id"])
        if "taskId" in data:
            task_id_candidates.append(data["taskId"])
    task_id_candidates.extend(
        [
            os.environ.get("AOPS_TASK_ID"),
            os.environ.get("POLECAT_TARGET_TASK"),
            os.environ.get("POLECAT_TASK"),
            os.environ.get("GENAI_ENGINE_TASK_ID"),
        ]
    )

    task_id = ""
    for candidate in task_id_candidates:
        if not candidate or not isinstance(candidate, str):
            continue
        c = candidate.strip()
        if not c:
            continue
        canon_task = resolve_canonical_project(c)
        if c == project_name or canon_task == project_name or not is_valid_task_id(c):
            continue
        task_id = c
        break

    cwd = resolve_cwd(data)
    agent_name = resolve_agent_name(data)

    cfg = {
        "api_key": api_key,
        "task_id": task_id,
        "endpoint": endpoint,
        "project_name": project_name,
        "cwd": cwd,
        "agent_name": agent_name,
    }
    if protocol:
        cfg["protocol"] = protocol
    return cfg


def resolve_session_id(
    data: dict,
    payload_key: str,
    *,
    prefer_env: bool = False,
) -> str | None:
    """Resolve a session identifier for a hook event, or None.

    ``session.id`` is the OpenInference span attribute Phoenix groups traces
    by (docs/phoenix/tracing/concepts-tracing/otel-openinference/context-managers.mdx:
    "The `using_session` context manager sets the `session.id` attribute on
    every span within its scope, which is used by Phoenix to group traces
    into sessions."). A fabricated fallback like ``"unknown"`` silently
    merges every session lacking an id into one bucket — the opposite of
    groupability, and a "No defaults" axiom violation.

    Two distinct identifiers are in play and this function resolves either,
    selected by ``prefer_env``:

    - **State key** (``prefer_env=False``, the default): the hook payload's
      own id (``session_id`` for claude, ``conversationId`` for agy).
      Subagent-tool dispatches get their OWN distinct payload session id
      (verified empirically — see field test in PR #2461/#2462 discussion:
      subagent hook payloads carry a UUID different from the parent's), so
      this value MUST stay per-process to avoid two concurrent subagents
      clobbering one state file (``_state_path`` keys the state file, and
      ``_session_lock`` keys the lock, by exactly this value).
    - **Phoenix grouping id** (``prefer_env=True``): the id stamped on the
      ``session.id`` span attribute so a whole multi-agent working session —
      root turn plus every subagent it dispatches — lands in ONE Phoenix
      session. ``$AOPS_SESSION_ID`` is written at each session's SessionStart
      into ``CLAUDE_ENV_FILE`` (handlers.py:_export_session_id)
      and inherited via the environment by every descendant subagent
      process — empirically confirmed: a live subagent process in this
      session has ``AOPS_SESSION_ID`` in its environment equal to
      ``CLAUDE_CODE_SESSION_ID`` of the root session, even though its own
      hook payload's ``session_id`` is a different UUID. Preferring it here
      is what makes subagent spans group under the root session instead of
      each subagent appearing as its own disconnected session.

    Either way, payload and env are the only two sources: there is no third,
    state-file fallback for the state-key role, since the state file is
    itself keyed by the id being resolved (``_state_path``) — it cannot
    supply the id needed to look itself up.

    Returns None when no real id is available at all; callers must skip
    span emission and log a warning naming the missing field rather than
    proceeding with a magic string.
    """
    payload_value = (
        data.get(payload_key)
        or data.get("session_id")
        or data.get("conversationId")
        or data.get("conversation_id")
    )
    env_value = os.environ.get("AOPS_SESSION_ID")
    if prefer_env:
        if env_value:
            return env_value
        if payload_value:
            return str(payload_value)
        return None
    if payload_value:
        return str(payload_value)
    if env_value:
        return env_value
    return None


def _phoenix_session_id(state: dict) -> str:
    """Return the Phoenix-grouping session id cached on *state* at init.

    Falls back to the state-key ``session_id`` for state files written
    before ``phoenix_session_id`` existed, so old in-flight sessions still
    export rather than crashing mid-turn.
    """
    return state.get("phoenix_session_id") or state["session_id"]


def _resolve_agent_and_parent_ids(
    state: dict,
    data: dict | None = None,
    payload_key: str = "session_id",
) -> tuple[str, str | None, str | None]:
    """Resolve (phoenix_session_id, local_agent_id, parent_session_id).

    A hook fired inside an in-process subagent carries the main thread's
    ``session_id`` and the subagent's own ``agent_id``; the agent id wins.
    """
    phoenix_session_id = _phoenix_session_id(state)
    local_agent_id = None
    if data:
        local_agent_id = _subagent_id(data) or resolve_session_id(
            data, payload_key, prefer_env=False
        )
    if not local_agent_id:
        local_agent_id = state.get("session_id") or phoenix_session_id

    parent_session_id = None
    if local_agent_id and phoenix_session_id and local_agent_id != phoenix_session_id:
        parent_session_id = phoenix_session_id

    return phoenix_session_id, local_agent_id, parent_session_id


def _subagent_id(data: dict) -> str | None:
    """The ``agent_id`` of the in-process subagent a hook fired inside, or None.

    Claude Code adds ``agent_id`` and ``agent_type`` to the payload of every
    tool hook a subagent fires, and to SubagentStart/SubagentStop; its
    ``session_id`` stays the main thread's. Main-thread payloads carry no
    ``agent_id`` (a ``--agent`` session carries ``agent_type`` alone).
    """
    return str(data.get("agent_id") or "").strip() or None


def _subagent_name(agent_type: Any) -> str:
    """Agent name from a subagent's type, without its plugin prefix ('ida:james' -> 'james')."""
    name = str(agent_type or "").strip()
    return name.split(":", 1)[1] if ":" in name else name


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------

STATE_DIR = Path.home() / ".claude" / "tracer"
STATE_MAX_AGE_S = 48 * 3600


def _state_path(session_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = (STATE_DIR / f"{session_id}.json").resolve()
    if not path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return path


def _load_state(session_id: str) -> dict:
    path = _state_path(session_id)
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to load state for %s: %s", session_id, e)
    return {}


def _save_state(session_id: str, state: dict) -> None:
    try:
        _state_path(session_id).write_text(json.dumps(state))
    except Exception as e:
        log.warning("Failed to save state for %s: %s", session_id, e)


def _delete_state(session_id: str) -> None:
    try:
        p = _state_path(session_id)
        if p.exists():
            p.unlink()
    except Exception as e:
        log.debug("Failed to delete state for %s: %s", session_id, e)


def _cleanup_stale_states() -> None:
    try:
        now = time.time()
        for p in STATE_DIR.glob("*.json"):
            if now - p.stat().st_mtime > STATE_MAX_AGE_S:
                p.unlink()
    except Exception as e:
        log.debug("Stale state cleanup failed: %s", e)


def _new_trace_id() -> str:
    import secrets

    return secrets.token_hex(16)


def _new_span_id() -> str:
    import secrets

    return secrets.token_hex(8)


@contextlib.contextmanager
def _session_lock(session_id: str):
    """Exclusive per-session file lock.

    Serialises concurrent hook executions so state updates are thread/process safe.
    This is necessary because Claude Code can run multiple tools in parallel,
    which causes multiple PostToolUse hook processes to fire concurrently.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = (STATE_DIR / f"{session_id}.lock").resolve()
    if not lock_path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")

    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _is_real_transcript(path: str) -> bool:
    """Return True if the transcript has at least one human or assistant entry.

    Shadow transcripts created by ``gh pr create`` in a worktree contain only
    ``pr-link`` metadata entries and no actual conversation content.  Accepting
    one of these as the authoritative transcript would leave the tracer with
    nothing to extract LLM spans from.
    """
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") in ("user", "assistant"):
                    return True
        return False
    except OSError:
        return False


def _find_transcript_path(data: dict, session_id: str) -> str | None:
    """Locate the session's transcript JSONL file.

    Searches three locations in priority order and returns the first match
    that contains real conversation content (at least one user/assistant entry).
    Callers that need a stable path across the lifetime of a session should
    cache the result in session state via ``_get_cached_transcript_path``
    rather than calling this function repeatedly — the ``transcript_path``
    value in hook ``data`` can change mid-session when Claude Code writes
    entries to a *different* project directory (e.g. after ``gh pr create``
    in a worktree context).

    Duplicates the ``~/.claude/projects`` discovery in
    ``lib/py/transcripts/runner.py`` (``find_session_files``), and the
    assistant/``usage`` parsing below duplicates
    ``lib/py/transcripts/adapters/claude.py``. Reuse is blocked by packaging,
    not by taste: hooks run as ``uv run --project "${CLAUDE_PLUGIN_ROOT}"``
    against the plugin's own dist environment, which has no path to ``lib/py``
    and none of the transcripts pipeline's third-party dependencies (the
    adapter is a wrapper around ``claude_code_log``). The pipeline is reached
    only by shelling out to a source checkout at ``AOPS_SRC_DIR``, which a hook
    on the hot path of every tool call cannot rely on being set. Collapsing
    the two needs a dependency-free discovery helper in ``lib/`` that the build
    injects into plugin hook directories the way it injects ``dispatch.py``.
    Known duplication, 2026-08-12; not yet tracked by an issue.
    """
    candidates: list[str] = []

    # 1. Provided directly in hook data
    tp = data.get("transcript_path", "")
    if tp and Path(tp).exists():
        candidates.append(tp)

    # 2. Construct from CLAUDE_PROJECT_DIR (path with / → -)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        sanitized = project_dir.replace("/", "-")
        path = Path.home() / ".claude" / "projects" / sanitized / f"{session_id}.jsonl"
        if path.exists():
            candidates.append(str(path))

    # 3. Glob fallback across all project dirs (sorted largest-first so the
    #    real transcript wins over tiny shadow files)
    projects_dir = Path.home() / ".claude" / "projects"
    if projects_dir.exists():
        matches = list(projects_dir.glob(f"*/{session_id}.jsonl"))
        matches.sort(key=lambda p: p.stat().st_size, reverse=True)
        candidates.extend(str(m) for m in matches)

    # Return the first candidate that contains actual conversation entries
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_real_transcript(candidate):
            return candidate

    return None


def _get_cached_transcript_path(
    data: dict,
    state: dict,
    session_id: str,
) -> str | None:
    """Return the transcript path for this session, caching it in *state*.

    Once resolved, the path is stored under ``state["transcript_path"]`` so
    that all subsequent hook calls use the same file even if Claude Code later
    writes a new entry to a different project directory (e.g. a worktree dir
    after ``gh pr create``).  The cache is only accepted when the file still
    exists; if it has been deleted the function re-resolves.
    """
    cached = state.get("transcript_path", "")
    if cached and Path(cached).exists():
        return cached

    resolved = _find_transcript_path(data, session_id)
    if resolved:
        state["transcript_path"] = resolved
    return resolved


def _find_tool_use_id(transcript_path: str, tool_name: str, tool_input: dict) -> str | None:
    if not transcript_path:
        return None
    try:
        if not __import__("os").path.exists(transcript_path):
            return None
        lines = open(transcript_path).read().splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entry = __import__("json").loads(line)
            except Exception:
                continue
            if entry.get("type") == "assistant":
                for block in reversed(entry.get("message", {}).get("content", [])):
                    if block.get("type") == "tool_use" and block.get("name") == tool_name:
                        if tool_input:
                            if block.get("input") == tool_input:
                                return block.get("id")
                        else:
                            return block.get("id")
    except Exception as e:
        log.debug("Failed to find tool_use_id: %s", e)
    return None


# Start of string-content user entries that Claude Code writes for local slash
# commands (/model, /usage, /compact, ...) and bash mode (``!cmd``). Those do
# not fire UserPromptSubmit and are not turns. Skill and custom-command prompts
# start with ``<command-message>`` instead and do count.
_LOCAL_COMMAND_PREFIXES = (
    "<command-name>",
    "<local-command-",
    "<bash-input>",
    "<bash-stdout>",
    "<bash-stderr>",
)


def _is_human_message(entry: dict) -> bool:
    """True for a transcript entry that is a prompt opening a turn.

    Counts ``type=user`` entries whose content is a string: typed prompts and
    skill or custom slash-command prompts (``<command-message>...``). Does not
    count tool results (list content), ``isMeta`` entries (e.g. the
    ``<local-command-caveat>``), ``isCompactSummary`` entries, the
    ``<command-name>`` / ``<local-command-stdout>`` entries of local slash
    commands, or the ``<bash-input>`` / ``<bash-stdout>`` entries of bash mode,
    since none of those fire UserPromptSubmit.
    """
    if entry.get("type") != "user":
        return False
    if entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    content = entry.get("message", {}).get("content", "")
    # Tool result messages have content as a list; human messages have a string
    if not isinstance(content, str):
        return False
    return not content.lstrip().startswith(_LOCAL_COMMAND_PREFIXES)


def _count_human_messages(transcript_path: str) -> int:
    """Count human (non-tool-result) user messages to detect turn boundaries."""
    try:
        count = 0
        for line in Path(transcript_path).read_text().splitlines():
            if not line.strip():
                continue
            try:
                if _is_human_message(json.loads(line)):
                    count += 1
            except json.JSONDecodeError:
                pass
        return count
    except Exception:
        return 0


def _next_turn_number(state: dict, prior_human_count: int) -> int:
    """Return the next turn number and store it on *state*.

    Once the session state has numbered a turn, the next turn is that number
    plus one: the transcript is not consulted, so no transcript entry can
    inflate the count. SessionEnd deletes the state file, so a
    ``claude --resume`` of the same session starts from a fresh state; only
    then is numbering seeded from *prior_human_count*, the number of prompts
    in the transcript before this turn's prompt as counted by
    ``_is_human_message``.
    """
    turn_number = (state.get("turn_number") or prior_human_count) + 1
    state["turn_number"] = turn_number
    return turn_number


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _iso_to_ns(ts: str) -> int:
    """Convert ISO 8601 timestamp string to nanoseconds."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
        # Integer arithmetic: dt.timestamp() * 1e9 loses sub-microsecond
        # precision and can floor a millisecond timestamp to the one before.
        delta = dt - _EPOCH
        return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000
    except Exception:
        return time.time_ns()


# ---------------------------------------------------------------------------
# OpenTelemetry imports (lazy)
# ---------------------------------------------------------------------------


def _otel_imports():
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import (
        NonRecordingSpan,
        SpanContext,
        SpanKind,
        StatusCode,
        TraceFlags,
    )

    return (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        None,  # Exporter instantiated dynamically via _create_exporter
        SpanKind,
        TraceFlags,
        NonRecordingSpan,
        StatusCode,
    )


# Span export runs inside the hook, on the hot path of every tool call. The SDK
# default of 10s lets a dead collector retry three times and add ~7s of latency
# per call; this caps one failed export at roughly a second.
_EXPORT_TIMEOUT_S = 2

# CA bundles a proxied export trusts when the OTel certificate variables are
# unset. A TLS-re-terminating egress proxy (e.g. a Claude Code cloud session)
# publishes its CA through these.
_CA_BUNDLE_ENV_VARS = ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE")
_OTEL_CERTIFICATE_ENV_VARS = (
    "OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE",
    "OTEL_EXPORTER_OTLP_CERTIFICATE",
)


def _proxy_http_kwargs(endpoint: str) -> dict[str, Any]:
    """Extra OTLP HTTP exporter kwargs that route *endpoint* through the env proxy.

    The OTLP HTTP exporter's default transport (a bare ``urllib3.PoolManager``
    in recent opentelemetry-exporter-otlp-proto-http releases) ignores
    ``HTTPS_PROXY`` and connects directly, which an egress firewall rejects
    (403 host_not_allowed in a Claude Code cloud session). When the environment
    names a proxy for *endpoint* (honouring ``NO_PROXY``), hand the exporter a
    ``requests.Session``, which reads the proxy variables itself, and point TLS
    at the environment's CA bundle. Returns ``{}`` when no proxy applies, so
    direct export keeps the exporter's default transport.
    """
    try:
        import requests
        from requests.utils import get_environ_proxies, select_proxy
    except ImportError:
        if any(os.environ.get(v) for v in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")):
            log.warning(
                "A proxy is set but 'requests' is not installed; OTel spans will export directly"
            )
        return {}

    if not select_proxy(endpoint, get_environ_proxies(endpoint)):
        return {}

    kwargs: dict[str, Any] = {"session": requests.Session()}
    if not any(os.environ.get(v) for v in _OTEL_CERTIFICATE_ENV_VARS):
        ca_bundle = next((os.environ[v] for v in _CA_BUNDLE_ENV_VARS if os.environ.get(v)), None)
        if ca_bundle:
            kwargs["certificate_file"] = ca_bundle
    log.debug("Routing OTLP HTTP export for %s through the environment proxy", endpoint)
    return kwargs


def _create_exporter(
    endpoint: str,
    headers: dict | None = None,
    protocol: str = "",
) -> Any:
    """Create an OTel span exporter. Raises on initialization failure."""
    prefer_http = protocol in ("http/protobuf", "http/json", "http")

    if prefer_http:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as HTTPSpanExporter,
        )

        log.debug("Initializing OTLP HTTP span exporter for endpoint %s", endpoint)
        return HTTPSpanExporter(
            endpoint=endpoint,
            headers=headers if headers else None,
            timeout=_EXPORT_TIMEOUT_S,
            **_proxy_http_kwargs(endpoint),
        )

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GRPCSpanExporter,
    )

    insecure = not endpoint.startswith("https://")
    log.debug(
        "Initializing OTLP gRPC span exporter for endpoint %s (insecure=%s)",
        endpoint,
        insecure,
    )
    return GRPCSpanExporter(
        endpoint=endpoint,
        headers=headers if headers else None,
        insecure=insecure,
        timeout=_EXPORT_TIMEOUT_S,
    )


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: dict[str, dict] = {
    "Bash": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "description": {"type": "string"},
            "timeout": {"type": "number"},
            "run_in_background": {"type": "boolean"},
        },
        "required": ["command"],
    },
    "Read": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "offset": {"type": "number"},
            "limit": {"type": "number"},
        },
        "required": ["file_path"],
    },
    "Edit": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "replace_all": {"type": "boolean"},
        },
        "required": ["file_path", "old_string", "new_string"],
    },
    "Write": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["file_path", "content"],
    },
    "Glob": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
    },
    "Grep": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "glob": {"type": "string"},
            "type": {"type": "string"},
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
            },
            "context": {"type": "number"},
        },
        "required": ["pattern"],
    },
    "Agent": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "prompt": {"type": "string"},
            "subagent_type": {"type": "string"},
            "run_in_background": {"type": "boolean"},
            "isolation": {"type": "string"},
        },
        "required": ["description", "prompt"],
    },
    "Task": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "prompt": {"type": "string"},
            "subagent_type": {"type": "string"},
            "run_in_background": {"type": "boolean"},
        },
        "required": ["description", "prompt", "subagent_type"],
    },
    "WebFetch": {
        "type": "object",
        "properties": {"url": {"type": "string"}, "prompt": {"type": "string"}},
        "required": ["url", "prompt"],
    },
    "WebSearch": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "allowed_domains": {"type": "array", "items": {"type": "string"}},
            "blocked_domains": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query"],
    },
    "NotebookEdit": {
        "type": "object",
        "properties": {
            "notebook_path": {"type": "string"},
            "new_source": {"type": "string"},
            "cell_id": {"type": "string"},
            "cell_type": {"type": "string"},
            "edit_mode": {"type": "string"},
        },
        "required": ["notebook_path", "new_source"],
    },
    "Skill": {
        "type": "object",
        "properties": {"skill": {"type": "string"}, "args": {"type": "string"}},
        "required": ["skill"],
    },
    "AskUserQuestion": {
        "type": "object",
        "properties": {"questions": {"type": "array"}},
        "required": ["questions"],
    },
    "EnterPlanMode": {"type": "object", "properties": {}, "required": []},
    "ExitPlanMode": {"type": "object", "properties": {}, "required": []},
    "TaskCreate": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "description": {"type": "string"},
            "activeForm": {"type": "string"},
        },
        "required": ["subject", "description"],
    },
    "TaskUpdate": {
        "type": "object",
        "properties": {
            "taskId": {"type": "string"},
            "status": {"type": "string"},
            "subject": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["taskId"],
    },
    "TaskGet": {
        "type": "object",
        "properties": {"taskId": {"type": "string"}},
        "required": ["taskId"],
    },
    "TaskList": {"type": "object", "properties": {}, "required": []},
    "TaskStop": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": [],
    },
    "TaskOutput": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "block": {"type": "boolean"},
            "timeout": {"type": "number"},
        },
        "required": ["task_id"],
    },
}

# Tools that map to RETRIEVER span kind (web retrieval operations)
RETRIEVER_TOOLS = {"WebSearch", "WebFetch"}

# Standard OpenTelemetry environment variable for string attribute length.
# We default to 524288 (512KB) to allow full-text spans to be exported to Phoenix,
# unless explicitly overridden.
_MAX_ATTR_BYTES = int(os.environ.get("OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT", "524288"))


def _redact_secrets(value: Any) -> str:
    s = json.dumps(value) if not isinstance(value, str) else value

    secrets = [
        os.environ.get("GH_TOKEN"),
        os.environ.get("GITHUB_TOKEN"),
        os.environ.get("AOPS_BOT_GH_TOKEN"),
        os.environ.get("DISPATCHER_MCP_TOKEN"),
        os.environ.get("DISPATCHER_MCP_TOKEN_ID"),
        os.environ.get("DISPATCHER_MCP_TOKEN_SECRET"),
        os.environ.get("WORKER_MCP_TOKEN"),
        os.environ.get("WORKER_MCP_TOKEN_ID"),
        os.environ.get("WORKER_MCP_TOKEN_SECRET"),
    ]
    for k, v in os.environ.items():
        if (
            k.endswith("_API_KEY") or k.endswith("_TOKEN_SECRET") or k.startswith("CF_ACCESS_")
        ) and v:
            secrets.append(v)

    for secret in secrets:
        if secret and len(secret) > 4:
            s = s.replace(secret, "<REDACTED_SECRET>")
    return s


def _truncate(value: Any) -> str:
    s = _redact_secrets(value)
    encoded = s.encode("utf-8")
    if len(encoded) > _MAX_ATTR_BYTES:
        s = encoded[:_MAX_ATTR_BYTES].decode("utf-8", errors="ignore") + "...[truncated]"
    return s


def _format_assistant_message(msg: Any) -> str:
    """Format the assistant message payload from Stop/StopFailure hook into text."""
    if not msg:
        return ""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        if "content" in msg:
            return _format_assistant_message(msg["content"])
        if msg.get("type") == "text" and "text" in msg:
            return str(msg["text"])
        if "text" in msg and isinstance(msg["text"], str):
            return msg["text"]
        return json.dumps(msg)
    if isinstance(msg, (list, tuple)):
        parts = []
        for item in msg:
            formatted = _format_assistant_message(item)
            if formatted:
                parts.append(formatted)
        return "".join(parts) if parts else json.dumps(msg)
    return str(msg)


# ---------------------------------------------------------------------------
# FixedSpanIdGenerator — forces the pre-generated root span ID
# ---------------------------------------------------------------------------


_GITHUB_RESOURCE_ENV = (
    ("github.repository", "GITHUB_REPOSITORY"),
    ("github.run_id", "GITHUB_RUN_ID"),
    ("github.run_attempt", "GITHUB_RUN_ATTEMPT"),
    ("github.workflow", "GITHUB_WORKFLOW"),
    ("github.job", "GITHUB_JOB"),
    ("github.event_name", "GITHUB_EVENT_NAME"),
    ("github.ref", "GITHUB_REF"),
    ("github.sha", "GITHUB_SHA"),
)


def _github_resource_attrs() -> dict[str, str]:
    """The GitHub Actions run a session belongs to, so its spans link back to the run.

    Empty outside Actions (``GITHUB_ACTIONS`` is not ``true``), even when a stray
    ``GITHUB_*`` variable is set.
    """
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true":
        return {}
    attrs = {
        key: value
        for key, var in _GITHUB_RESOURCE_ENV
        if (value := os.environ.get(var, "").strip())
    }
    server = os.environ.get("GITHUB_SERVER_URL", "").strip()
    repo = attrs.get("github.repository")
    run_id = attrs.get("github.run_id")
    if server and repo and run_id:
        url = f"{server}/{repo}/actions/runs/{run_id}"
        if attempt := attrs.get("github.run_attempt"):
            url += f"/attempts/{attempt}"
        attrs["github.run_url"] = url
    return attrs


def _make_fixed_id_generator(forced_span_id_hex: str):
    import secrets

    from opentelemetry.sdk.trace.id_generator import IdGenerator

    forced_int = int(forced_span_id_hex, 16)

    class FixedSpanIdGenerator(IdGenerator):
        def __init__(self):
            self._used = False

        def generate_span_id(self) -> int:
            if not self._used:
                self._used = True
                return forced_int
            return int(secrets.token_hex(8), 16)

        def generate_trace_id(self) -> int:
            return int(secrets.token_hex(16), 16)

    return FixedSpanIdGenerator()


# ---------------------------------------------------------------------------
# Parent-cycle guard
# ---------------------------------------------------------------------------


def _closes_parent_cycle(
    span_id_hex: str,
    parent_hex: str,
    known_parents: dict[str, str | None],
) -> bool:
    """True if parenting *span_id_hex* under *parent_hex* would form a loop.

    Phoenix walks a new span's ancestors with a recursive query that has no
    loop guard, so one loop in the stored parent links stalls its writer.
    The walk follows *known_parents* (span id -> parent id) from *parent_hex*;
    it is bounded by the map's size, so a loop already in the map cannot
    trap it.
    """
    cur: str | None = parent_hex
    seen: set[str] = set()
    while cur is not None and cur not in seen:
        if cur == span_id_hex:
            return True
        seen.add(cur)
        cur = known_parents.get(cur)
    return False


def _known_span_parents(current_trace: dict) -> dict[str, str | None]:
    """Parent links of the forced-id spans this turn has emitted, plus the turn root."""
    known: dict[str, str | None] = dict(current_trace.get("span_parents", {}))
    known.setdefault(current_trace["root_span_id"], current_trace.get("parent_span_id"))
    return known


# ---------------------------------------------------------------------------
# OTLP export helper
# ---------------------------------------------------------------------------


def _build_and_export_spans(
    config: dict,
    session_id: str,
    username: str | None,
    span_records: list[dict],
    agent_id: str | None = None,
    parent_session_id: str | None = None,
    agent_name: str | None = None,
    cwd: str | None = None,
    known_parents: dict[str, str | None] | None = None,
    service_name: str | None = None,
    surface: str | None = None,
) -> bool:
    """Create spans from records and export via OTLP gRPC (with fallbacks).

    Returns True only when every record was handed to an exporter and every
    export call returned SUCCESS. SimpleSpanProcessor discards the exporter's
    result and swallows its exceptions, so the outcome is captured here, in
    the wrapping exporter. SUCCESS means the OTLP endpoint acknowledged the
    request; it does not prove the span was stored downstream of it.

    ``known_parents`` maps span ids already emitted to their parent ids. A
    record whose parent is itself, or whose parent chain through
    ``known_parents`` and the records earlier in this batch leads back to it,
    is exported without a parent (see ``_closes_parent_cycle``).
    """
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    export_results: list[bool] = []
    all_records_exported = True

    (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        _,
        SpanKind,
        TraceFlags,
        NonRecordingSpan,
        StatusCode,
    ) = _otel_imports()

    class ErrorReportingExporter(SpanExporter):
        def __init__(self, target: Any) -> None:
            self._target = target

        def export(self, spans: Any) -> SpanExportResult:
            # OTel exporters log exceptions and HTTP errors to their module logger.
            # We capture those logs during export to report them verbatim.
            target_logger_name = self._target.__module__
            target_logger = logging.getLogger(target_logger_name)

            class CaptureHandler(logging.Handler):
                def __init__(self) -> None:
                    super().__init__()
                    self.messages: list[str] = []

                def emit(self, record: logging.LogRecord) -> None:
                    self.messages.append(record.getMessage())

            handler = CaptureHandler()
            target_logger.addHandler(handler)
            try:
                try:
                    res = self._target.export(spans)
                except Exception:
                    export_results.append(False)
                    raise
                export_results.append(res == SpanExportResult.SUCCESS)
                if res != SpanExportResult.SUCCESS and handler.messages:
                    error_text = "\n".join(handler.messages)
                    print(f"ERROR: OTel span export failed: {error_text}")
                    log.error("OTel span export failed: %s", error_text)
                return res
            finally:
                target_logger.removeHandler(handler)

        def shutdown(self) -> None:
            self._target.shutdown()

        def force_flush(self, timeout_millis: int = 30000) -> bool:
            if hasattr(self._target, "force_flush"):
                return bool(self._target.force_flush(timeout_millis))
            return True

    if service_name is None:
        service_name = config.get("service_name")
    if not service_name:
        if env_srv := os.environ.get("OTEL_SERVICE_NAME", "").strip():
            if env_srv.lower() != "default":
                service_name = env_srv
    if not service_name:
        service_name = "aops-claude-hooks"

    if surface is None:
        surface = config.get("surface") or config.get("aops.surface")
    if not surface:
        if os.environ.get("GITHUB_ACTIONS"):
            surface = "github-actions"
        elif service_name == "aops-agy-hooks":
            surface = "agy"
        else:
            surface = "claude-code"

    project_name = config.get("project_name") or resolve_project_name()
    task_id = config.get("task_id", "")
    if task_id and not is_valid_task_id(task_id):
        task_id = ""

    if agent_name is None:
        agent_name = config.get("agent_name") or resolve_agent_name(cwd=cwd)
    if cwd is None:
        cwd = config.get("cwd") or resolve_cwd()

    project_dir = resolve_checkout_root(cwd) if cwd else ""
    repo = ""
    if cwd:
        raw_repo = resolve_project_from_dir(cwd)
        if raw_repo:
            canon_repo = resolve_canonical_project(raw_repo) or raw_repo
            repo = (
                "academicOps"
                if canon_repo.lower() in ("aops", "academicops", "academic_ops")
                else canon_repo
            )

    try:
        host_name = socket.gethostname()
    except Exception:
        host_name = ""

    resource_attrs = {
        "service.name": service_name,
        "aops.surface": surface,
        "openinference.project.name": project_name,
        "project.name": project_name,
        "session.id": session_id,
    }
    if repo:
        resource_attrs["aops.repo"] = repo
    if project_dir:
        resource_attrs["project.dir"] = project_dir
    if agent_id:
        resource_attrs["agent.id"] = agent_id
        resource_attrs["subagent.id"] = agent_id
    if parent_session_id:
        resource_attrs["parent.session_id"] = parent_session_id
    if task_id:
        resource_attrs["task.id"] = task_id
        resource_attrs["tag.task_id"] = task_id
    if host_name:
        resource_attrs["host.name"] = host_name
    if username:
        resource_attrs["user.id"] = username
    if agent_name:
        resource_attrs["agent.name"] = agent_name
    if cwd:
        resource_attrs["cwd"] = cwd
    github_attrs = _github_resource_attrs()
    resource_attrs.update(github_attrs)

    resource = Resource.create(resource_attrs)
    parents: dict[str, str | None] = dict(known_parents or {})

    for rec in span_records:
        parent_hex: str | None = rec.get("parent_span_id_hex")
        # Only a forced span id is known before export; any other span gets a
        # fresh random id, which nothing can already name as its parent.
        if rec.get("force_span_id"):
            span_id_hex = rec["span_id_hex"]
            if parent_hex and _closes_parent_cycle(span_id_hex, parent_hex, parents):
                log.warning(
                    "Dropping parent %s of span %s (%s): the link would close a parent cycle",
                    parent_hex,
                    span_id_hex,
                    rec.get("name"),
                )
                parent_hex = None
            parents[span_id_hex] = parent_hex
        try:
            headers = {}
            if config.get("api_key"):
                api_key_str = config["api_key"]
                if "=" in api_key_str and ":" not in api_key_str and "Bearer" not in api_key_str:
                    for item in api_key_str.split(","):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            headers[k.strip()] = v.strip()
                elif ":" in api_key_str:
                    for item in api_key_str.split(","):
                        if ":" in item:
                            k, v = item.split(":", 1)
                            headers[k.strip()] = v.strip()
                else:
                    headers["authorization"] = f"Bearer {api_key_str}"

            if project_name and "openinference-project-name" not in headers:
                headers["openinference-project-name"] = project_name

            exporter = _create_exporter(
                endpoint=config["endpoint"],
                headers=headers if headers else None,
                protocol=config.get("protocol", ""),
            )
            if not exporter:
                log.warning("Failed to create any OTel span exporter")
                all_records_exported = False
                continue

            # Resolve None kind (used for LLM spans set by caller)
            kind = rec.get("kind") or SpanKind.CLIENT

            id_generator = None
            if rec.get("force_span_id"):
                id_generator = _make_fixed_id_generator(rec["span_id_hex"])

            kwargs: dict[str, Any] = {"resource": resource}
            if id_generator:
                kwargs["id_generator"] = id_generator

            provider = TracerProvider(**kwargs)

            provider.add_span_processor(SimpleSpanProcessor(ErrorReportingExporter(exporter)))
            tracer = provider.get_tracer("claude-code-tracer")

            ctx = None
            if parent_hex:
                parent_sc = SpanContext(
                    trace_id=int(rec["trace_id_hex"], 16),
                    span_id=int(parent_hex, 16),
                    is_remote=True,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                )
                ctx = trace.set_span_in_context(NonRecordingSpan(parent_sc))

            span = tracer.start_span(
                name=rec["name"],
                context=ctx,
                kind=kind,
                start_time=rec["start_ns"],
            )

            # Patch trace_id if provider generated a different one
            try:
                sc = span.get_span_context()
                desired = int(rec["trace_id_hex"], 16)
                if sc.trace_id != desired:
                    span._context = SpanContext(
                        trace_id=desired,
                        span_id=sc.span_id,
                        is_remote=sc.is_remote,
                        trace_flags=sc.trace_flags,
                    )
            except Exception:
                pass

            span.set_attribute("service.name", service_name)
            span.set_attribute("aops.surface", surface)
            span.set_attribute("session.id", session_id)
            if repo:
                span.set_attribute("aops.repo", repo)
            if project_dir:
                span.set_attribute("project.dir", project_dir)
            if agent_name:
                span.set_attribute("agent.name", agent_name)
            if agent_id:
                span.set_attribute("agent.id", agent_id)
                span.set_attribute("subagent.id", agent_id)
            if parent_session_id:
                span.set_attribute("parent.session_id", parent_session_id)
            if username:
                span.set_attribute("user.id", username)
            if cwd:
                span.set_attribute("cwd", cwd)
            span.set_attribute("project.name", project_name)
            span.set_attribute("openinference.project.name", project_name)
            if task_id:
                span.set_attribute("task.id", task_id)
                span.set_attribute("tag.task_id", task_id)
            if host_name:
                span.set_attribute("host.name", host_name)
            for gh_key, gh_value in github_attrs.items():
                span.set_attribute(gh_key, gh_value)
            for k, v in rec.get("attributes", {}).items():
                span.set_attribute(k, v)

            if rec.get("error"):
                span.set_status(StatusCode.ERROR, description=rec.get("error_msg", ""))

            results_before = len(export_results)
            span.end(end_time=rec["end_ns"])
            provider.shutdown()
            if len(export_results) == results_before:
                # The processor never reached the exporter (e.g. unsampled span).
                all_records_exported = False
        except Exception as e:
            log.warning("Exporting OTel span failed: %s", e)
            raise

    return all_records_exported and all(export_results)


# ---------------------------------------------------------------------------
# Turn completion
# ---------------------------------------------------------------------------


def _agent_span_id(tool_use_id: str) -> str:
    """Span id of the Agent/Task tool span that a tool_use id dispatched."""
    import hashlib

    return hashlib.sha256(tool_use_id.encode()).hexdigest()[:16]


def _subagent_record(
    state: dict,
    agent_id: str,
    agent_type: Any = None,
) -> dict | None:
    """Return the tracing record of in-process subagent *agent_id*, creating it on first use."""
    subagents = state.setdefault("subagents", {})
    record = subagents.get(agent_id)
    if record is None:
        current_trace = state.get("current_trace")
        if not current_trace:
            return None
        record = {
            "agent_type": str(agent_type or ""),
            "trace_id": current_trace["trace_id"],
            "agent_span_id": _find_active_agent_span_id(state, "", "")
            or current_trace["root_span_id"],
        }
        subagents[agent_id] = record
    if agent_type and not record.get("agent_type"):
        record["agent_type"] = str(agent_type)
    return record


def _llm_span_id(message_id: str) -> str:
    """Span id for the LLM span of one API response, derived from its message.id."""
    import hashlib

    return hashlib.sha256(f"llm:{message_id}".encode()).hexdigest()[:16]


def _extract_model_usages_from_transcript(
    transcript_path: str | None,
    human_count_at_start: int = 0,
    stop_at_next_prompt: bool = True,
) -> list[dict[str, Any]]:
    """Extract model call token usages and model name from the transcript for the turn.

    In accordance with the Client Hook Emission Contract, this function reads
    ONLY token counts (input_tokens, output_tokens, cache_read_input_tokens,
    cache_creation_input_tokens) and model from each assistant entry. It does
    NOT read message content, role, timestamps, or tool data from the transcript.

    Entries sharing the same message.id are grouped into one model call (taking the
    fullest usage snapshot).
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    usages: list[dict[str, Any]] = []
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
        human_count = 0
        in_turn = human_count_at_start == 0

        current_group_id: str | None = None
        group_model: str = "claude"
        group_usage: dict[str, Any] = {}

        def _flush_group() -> None:
            nonlocal current_group_id, group_model, group_usage
            if current_group_id is None:
                return
            usages.append(
                {
                    "message_id": current_group_id,
                    "model": group_model,
                    "input_tokens": int(group_usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(group_usage.get("output_tokens", 0) or 0),
                    "cache_read_input_tokens": int(
                        group_usage.get("cache_read_input_tokens", 0) or 0
                    ),
                    "cache_creation_input_tokens": int(
                        group_usage.get("cache_creation_input_tokens", 0) or 0
                    ),
                }
            )
            current_group_id = None
            group_model = "claude"
            group_usage = {}

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if _is_human_message(entry):
                human_count += 1
                if human_count > human_count_at_start:
                    if in_turn and stop_at_next_prompt and usages:
                        break
                    in_turn = True
            elif in_turn and entry.get("type") == "assistant":
                msg = entry.get("message")
                if not isinstance(msg, dict):
                    continue
                msg_id = str(msg.get("id") or "")
                model = str(msg.get("model") or "claude")
                usage = msg.get("usage")
                usage_dict = usage if isinstance(usage, dict) else {}

                if msg_id and msg_id == current_group_id:
                    cur_tot = sum(
                        int(group_usage.get(k, 0) or 0)
                        for k in (
                            "input_tokens",
                            "output_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        )
                    )
                    new_tot = sum(
                        int(usage_dict.get(k, 0) or 0)
                        for k in (
                            "input_tokens",
                            "output_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        )
                    )
                    if new_tot >= cur_tot:
                        group_usage = usage_dict
                    if model:
                        group_model = model
                else:
                    _flush_group()
                    current_group_id = msg_id if msg_id else f"entry_{len(usages)}"
                    group_model = model
                    group_usage = usage_dict

        _flush_group()
    except Exception as e:
        log.debug("Failed reading transcript usages from %s: %s", transcript_path, e)
    return usages


def _emit_pending_llm_spans(
    state: dict,
    transcript_path: str | None,
    config: dict,
    *,
    subagent_id: str | None = None,
    retry_delay_s: float = 0.0,
    force_remaining: bool = False,
) -> None:
    """Emit pending hook-derived LLM spans joined with token counts from transcript."""
    current_trace = state.get("current_trace")
    if not current_trace:
        return

    model_calls = current_trace.setdefault("model_calls", [])
    emitted = current_trace.get("emitted_llm_span_count", 0)
    if emitted >= len(model_calls):
        return

    human_count_at_start = current_trace.get("human_count_at_start", 0)
    usages = _extract_model_usages_from_transcript(transcript_path, human_count_at_start)

    if retry_delay_s > 0 and len(usages) < len(model_calls):
        time.sleep(retry_delay_s)
        usages = _extract_model_usages_from_transcript(transcript_path, human_count_at_start)

    unemitted = model_calls[emitted:]
    if not unemitted:
        return

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()
    spans_to_export: list[dict[str, Any]] = []
    by_tool_call = current_trace.setdefault("llm_span_by_tool_call", {})

    for idx, call in enumerate(unemitted, start=emitted):
        usage_info = usages[idx] if idx < len(usages) else None
        if usage_info is None and not force_remaining:
            # Hold open until later hook or flush
            break

        model = usage_info["model"] if usage_info else "claude"
        msg_id = usage_info.get("message_id", "") if usage_info else ""
        input_tokens = usage_info.get("input_tokens", 0) if usage_info else 0
        output_tokens = usage_info.get("output_tokens", 0) if usage_info else 0
        cache_read = usage_info.get("cache_read_input_tokens", 0) if usage_info else 0
        cache_write = usage_info.get("cache_creation_input_tokens", 0) if usage_info else 0

        span_id_hex = (
            _llm_span_id(msg_id) if msg_id and not msg_id.startswith("entry_") else _new_span_id()
        )
        for tc_id in call.get("tool_call_ids", []):
            if tc_id:
                by_tool_call[str(tc_id)] = span_id_hex

        prompt_tokens = input_tokens + cache_read + cache_write
        total_tokens = prompt_tokens + output_tokens

        attrs: dict[str, Any] = {
            "openinference.span.kind": "LLM",
            "llm.system": "anthropic",
            "llm.provider": "anthropic",
            "llm.model_name": model,
            "llm.token_count.prompt": prompt_tokens,
            "llm.token_count.completion": output_tokens,
            "llm.token_count.total": total_tokens,
            "llm.token_count.prompt_details.cache_read": cache_read,
            "llm.token_count.prompt_details.cache_write": cache_write,
            "input.value": call.get("input_value", ""),
            "input.mime_type": call.get("input_mime", "text/plain"),
            "output.value": call.get("output_value", ""),
            "output.mime_type": call.get("output_mime", "text/plain"),
        }
        if usage_info is None:
            attrs["llm.token_count.type"] = "estimated"
        if msg_id and not msg_id.startswith("entry_"):
            attrs["llm.message.id"] = msg_id

        parent_span_id = current_trace["root_span_id"]
        trace_id = current_trace["trace_id"]
        if subagent_id:
            subagent = state.get("subagents", {}).get(subagent_id)
            if subagent:
                trace_id = subagent.get("trace_id", trace_id)
                parent_span_id = subagent.get("agent_span_id", parent_span_id)

        start_ns = call.get("start_ns", current_trace["turn_start_ns"])
        end_ns = call.get("end_ns", time.time_ns())
        if end_ns < start_ns:
            end_ns = start_ns

        spans_to_export.append(
            {
                "trace_id_hex": trace_id,
                "span_id_hex": span_id_hex,
                "parent_span_id_hex": parent_span_id,
                "name": f"claude/{model}",
                "kind": SpanKind.CLIENT,
                "start_ns": start_ns,
                "end_ns": end_ns,
                "attributes": attrs,
                "force_span_id": True,
            }
        )

    if not spans_to_export:
        return

    phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(state)
    known_parents = _known_span_parents(current_trace)
    for sp in spans_to_export:
        current_trace.setdefault("span_parents", {})[sp["span_id_hex"]] = sp["parent_span_id_hex"]

    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=state.get("username"),
        span_records=spans_to_export,
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=state.get("agent_name"),
        cwd=state.get("cwd"),
        known_parents=known_parents,
    )

    current_trace["emitted_llm_span_count"] = emitted + len(spans_to_export)


def _complete_turn(
    state: dict,
    config: dict,
    end_ns: int,
    failure: dict[str, str] | None = None,
) -> None:
    """Send the CHAIN root span for the current turn's trace.

    The root span's output.value is taken from the last LLM output (captured
    atomically from the Stop / StopFailure hook payload or prior tool turn).

    ``failure`` carries ``error.type`` and ``error.message`` for a turn that
    ended in StopFailure; the root span then gets ERROR status.
    """
    current_trace = state.get("current_trace")
    if not current_trace:
        return

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()

    trace_id = current_trace["trace_id"]
    root_span_id = current_trace["root_span_id"]
    turn_start_ns = current_trace["turn_start_ns"]
    turn_number = current_trace.get("turn_number", 1)
    prompt_preview = current_trace.get("prompt_preview", "")
    final_output = current_trace.get("last_llm_output", "")

    # Root CHAIN span. Always a genuine trace root — including for subagent
    # turns, which are NOT nested inside the dispatching session's trace (see
    # the comment on the Agent/Task branch in handle_pre_tool). Subagent and
    # parent are connected instead via the shared "session.id" attribute.
    username = state.get("username")
    phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(state)
    cwd = state.get("cwd") or resolve_cwd(None, state)
    agent_name = state.get("agent_name") or resolve_agent_name()
    root_attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        "session.id": phoenix_session_id,
        "turn_number": turn_number,
    }
    if username:
        root_attrs["user.id"] = username
    if agent_id:
        root_attrs["agent.id"] = agent_id
        root_attrs["subagent.id"] = agent_id
    if parent_session_id:
        root_attrs["parent.session_id"] = parent_session_id
    if agent_name:
        root_attrs["agent.name"] = agent_name
    if cwd:
        root_attrs["cwd"] = cwd
        root_attrs["project.dir"] = cwd
    if prompt_preview:
        root_attrs["input.value"] = prompt_preview
        root_attrs["input.mime_type"] = "text/plain"
    if final_output:
        root_attrs["output.value"] = final_output
        root_attrs["output.mime_type"] = "text/plain"

    root_record: dict[str, Any] = {
        "trace_id_hex": trace_id,
        "span_id_hex": root_span_id,
        "parent_span_id_hex": current_trace.get("parent_span_id"),
        "name": "claude-code-turn",
        "kind": SpanKind.INTERNAL,
        "start_ns": turn_start_ns,
        "end_ns": end_ns,
        "attributes": root_attrs,
        "force_span_id": True,
    }
    if failure:
        root_attrs.update(failure)
        root_attrs["turn.failed"] = True
        root_record["error"] = True
        root_record["error_msg"] = failure.get("error.type", "")

    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[root_record],
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=agent_name,
        cwd=cwd,
        known_parents=current_trace.get("span_parents", {}),
    )


# ---------------------------------------------------------------------------
# Tool span record builder (shared by post_tool and post_tool_failure)
# ---------------------------------------------------------------------------


def _build_tool_span_record(
    tool_name: str,
    tool_input: Any,
    tool_response: Any,
    start_ns: int,
    end_ns: int,
    trace_id: str,
    root_span_id: str,
    is_failure: bool = False,
    error_msg: str = "",
    span_id: str | None = None,
    tool_call_id: str | None = None,
) -> dict:
    """Build a span record dict for a tool call (success or failure).

    Returns a record suitable for passing to _build_and_export_spans.
    The kind field is left as None so _build_and_export_spans defaults to
    SpanKind.CLIENT.
    """
    if tool_name in RETRIEVER_TOOLS:
        span_kind_str = "RETRIEVER"
    elif tool_name in ("Agent", "Task"):
        span_kind_str = "AGENT"
    else:
        span_kind_str = "TOOL"

    input_value = _truncate(tool_input)
    output_str = json.dumps(tool_response) if not isinstance(tool_response, str) else tool_response

    if is_failure and error_msg:
        error_msg = _truncate(error_msg)
        output_value = _truncate(f"ERROR: {error_msg}\n{output_str}")
    else:
        output_value = _truncate(output_str)

    attrs: dict[str, Any] = {
        "openinference.span.kind": span_kind_str,
        "tool.name": tool_name,
        "input.value": input_value,
        "input.mime_type": "application/json",
        "output.value": output_value,
        "output.mime_type": "application/json",
    }

    parsed_input = tool_input
    if isinstance(parsed_input, str):
        try:
            parsed_input = json.loads(parsed_input)
        except Exception:
            parsed_input = None

    if isinstance(parsed_input, dict):
        action_candidates = [parsed_input]
        if isinstance(parsed_input.get("Arguments"), dict):
            action_candidates.append(parsed_input["Arguments"])
        for candidate in action_candidates:
            for key in ("toolSummary", "toolAction", "description", "Description"):
                val = candidate.get(key)
                if isinstance(val, str) and val.strip():
                    attrs["tool.summary"] = val.strip()
                    break
            if "tool.summary" in attrs:
                break

    if not tool_call_id and isinstance(parsed_input, dict):
        tool_call_id = (
            parsed_input.get("tool_use_id")
            or parsed_input.get("id")
            or parsed_input.get("tool_call_id")
        )
    if tool_call_id:
        attrs["tool.call_id"] = str(tool_call_id)

    # agent.name for AGENT spans: prefer subagent_type from input, fall back to tool_name
    if span_kind_str == "AGENT":
        agent_name = ""
        if isinstance(tool_input, dict):
            agent_name = tool_input.get("subagent_type", "")
        attrs["agent.name"] = agent_name or tool_name

    schema = TOOL_SCHEMAS.get(tool_name)
    if schema:
        attrs["tool.json_schema"] = json.dumps(schema)

    # RETRIEVER-specific attributes per OpenInference spec
    if span_kind_str == "RETRIEVER":
        if tool_name == "WebSearch":
            query = tool_input.get("query", "") if isinstance(tool_input, dict) else ""
            attrs["input.value"] = _truncate(query)
            attrs["input.mime_type"] = "text/plain"
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "") if isinstance(tool_input, dict) else ""
            attrs["input.value"] = _truncate(url)
            attrs["input.mime_type"] = "text/plain"

        # First retrieval document content
        if isinstance(tool_response, str):
            doc_content = _truncate(tool_response)
        else:
            doc_content = _truncate(json.dumps(tool_response))
        attrs["retrieval.documents.0.document.content"] = doc_content

    rec: dict[str, Any] = {
        "trace_id_hex": trace_id,
        "span_id_hex": span_id or _new_span_id(),
        "parent_span_id_hex": root_span_id,
        "name": tool_name,
        "kind": None,  # defaults to SpanKind.CLIENT in _build_and_export_spans
        "start_ns": start_ns,
        "end_ns": end_ns,
        "attributes": attrs,
        "force_span_id": span_id is not None,
    }

    if is_failure:
        rec["error"] = True
        rec["error_msg"] = error_msg

    return rec


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_user_prompt_submit(data: dict, config: dict) -> None:
    """Handle UserPromptSubmit hook: complete previous trace and start a new one.

    Fires before Claude processes the prompt, giving an accurate turn_start_ns
    and the exact prompt text without transcript parsing.
    """
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_user_prompt_submit: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    with _session_lock(session_id):
        _start_turn(data, config, session_id)


def _start_turn(data: dict, config: dict, session_id: str) -> None:
    """Complete the previous turn and open a new one. Caller holds the session lock."""
    prompt = data.get("prompt", "")
    now_ns = time.time_ns()

    state = _load_state(session_id)

    # Initialize session on first event
    if not state.get("session_id"):
        state["session_id"] = session_id
        # Grouping id for the "session.id" span attribute — the root session's
        # id when this is a subagent (see resolve_session_id docstring),
        # falling back to this process's own id when there is no root to
        # inherit from (e.g. AOPS_SESSION_ID unset). Cached once at init so
        # every span this session-state-file ever emits agrees.
        state["phoenix_session_id"] = resolve_session_id(
            data,
            "session_id",
            prefer_env=True,
        )
        state["session_start_ns"] = now_ns
        state["username"] = os.environ.get("USER") or os.environ.get("USERNAME") or None
        state["turn_number"] = 0

    resolved_cwd = resolve_cwd(data, state)
    if resolved_cwd:
        state["cwd"] = resolved_cwd
    client_agent = resolve_client_agent_name(data)
    if client_agent:
        state["agent_name"] = client_agent

    # Complete the previous turn's trace if one is in progress (unclosed turn fallback).
    if state.get("current_trace"):
        prev_tp = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(state, prev_tp, config, force_remaining=True)
        _complete_turn(state, config, now_ns)
        state.pop("pending_tools", None)

    transcript_path = _get_cached_transcript_path(data, state, session_id)
    current_human_count = _count_human_messages(transcript_path) if transcript_path else 0
    turn_number = _next_turn_number(state, current_human_count)

    parent_trace_id = None
    parent_span_id = None
    phoenix_session_id = state.get("phoenix_session_id")
    if phoenix_session_id and phoenix_session_id != session_id:
        try:
            pstate = _load_state(phoenix_session_id)
            if pstate and pstate.get("current_trace"):
                parent_trace_id = pstate["current_trace"]["trace_id"]

            import hashlib

            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
            if project_dir:
                sanitized = project_dir.replace("/", "-")
                sidecar = (
                    Path.home()
                    / ".claude"
                    / "projects"
                    / sanitized
                    / phoenix_session_id
                    / "subagents"
                    / f"agent-{session_id}.meta.json"
                )
                if sidecar.exists():
                    sdata = __import__("json").loads(sidecar.read_text())
                    tuid = sdata.get("toolUseId")
                    if tuid:
                        parent_span_id = hashlib.sha256(tuid.encode()).hexdigest()[:16]
        except Exception as e:
            log.debug("Failed to parent subagent: %s", e)

    pending_turn = state.pop("pending_turn_trace", None) or {}
    state["current_trace"] = {
        "trace_id": parent_trace_id or pending_turn.get("trace_id") or _new_trace_id(),
        "root_span_id": pending_turn.get("root_span_id") or _new_span_id(),
        "parent_span_id": parent_span_id,
        "turn_start_ns": now_ns,
        "turn_number": turn_number,
        "prompt_preview": _truncate(prompt) if prompt else "",
        "human_count_at_start": max(0, turn_number - 1),
        "model_calls": [],
        "emitted_llm_span_count": 0,
        "pending_model_call": {
            "input_value": _truncate(prompt) if prompt else "",
            "input_mime": "text/plain",
            "start_ns": now_ns,
            "tool_calls": [],
        },
    }

    _save_state(session_id, state)


def _get_latest_human_message(transcript_path: str) -> str:
    """Return the text of the most recent human message in the transcript."""
    try:
        last = ""
        for line in Path(transcript_path).read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if _is_human_message(entry):
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        last = content
            except json.JSONDecodeError:
                pass
        return last
    except Exception:
        return ""


def _pending_tool_key(data: dict, tool_name: str) -> str:
    """Pending-tools key of a non-Agent tool call.

    A subagent's calls are keyed apart from the main thread's, so a subagent
    Bash and a main-thread Bash pending together do not overwrite each other.
    """
    agent_id = _subagent_id(data)
    return f"{tool_name}@{agent_id}" if agent_id else tool_name


def _find_pending_tool_entry(
    state: dict,
    tool_name: str,
    data_tool_input: Any,
    pending_key: str | None = None,
) -> tuple[dict, str]:
    """Return (pending_entry, pending_key) for the given tool.

    For Agent/Task tools, parallel calls each get a compound key
    ``"{tool_name}#{span_id}"``.  We find the right entry by matching
    ``tool_input``; if no match, fall back to the first entry with the right
    prefix so single-agent sessions and legacy state files still work.

    For all other tools the key is *pending_key* (``_pending_tool_key``),
    defaulting to ``tool_name``.
    """
    pending = state.get("pending_tools", {})
    prefix = f"{tool_name}#"

    if tool_name in ("Agent", "Task"):
        # Pass 1: exact tool_input match
        if data_tool_input is not None:
            for k, v in pending.items():
                if k.startswith(prefix) and v.get("tool_input") == data_tool_input:
                    return v, k
        # Pass 2: any entry with this tool's prefix (single-agent / legacy key)
        for k, v in pending.items():
            if k.startswith(prefix) or k == tool_name:
                return v, k
        return {}, tool_name

    key = pending_key or tool_name
    return pending.get(key, {}), key


def _find_active_agent_span_id(
    state: dict,
    current_pending_key: str,
    tool_name: str,
) -> str | None:
    """Return the pre_allocated_span_id of the innermost pending Agent/Task call.

    When an inline subagent (e.g. Explore) makes tool calls within the parent
    session, those calls appear in pending_tools alongside the Agent entry.
    This detects that situation and returns the Agent's span_id so the sub-tool
    is correctly parented under the Agent span rather than the CHAIN root.
    For nested agents, the most-recently-started one wins (innermost parent).

    An Agent/Task call is never parented under another pending Agent/Task
    call: parallel Agent calls in one session are siblings, and two of them
    finishing together would otherwise name each other as parent.
    """
    if tool_name in ("Agent", "Task"):
        return None
    pending = state.get("pending_tools", {})
    best_start_ns = -1
    best_span_id: str | None = None
    for k, v in pending.items():
        if k == current_pending_key:
            continue  # don't self-reference
        base_tool = k.split("#")[0] if "#" in k else k
        if base_tool in ("Agent", "Task") and v.get("pre_allocated_span_id"):
            if v.get("start_ns", 0) > best_start_ns:
                best_start_ns = v["start_ns"]
                best_span_id = v["pre_allocated_span_id"]
    return best_span_id


def handle_pre_tool(data: dict, config: dict) -> None:
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_pre_tool: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    # Parallel tool calls fire concurrent PreToolUse hooks; without the lock
    # each would save its own copy of pending_tools and drop the others'.
    with _session_lock(session_id):
        _start_tool_call(data, config, session_id)


def _start_tool_call(data: dict, config: dict, session_id: str) -> None:
    """Record a pending tool call. Caller holds the session lock."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    now_ns = time.time_ns()

    state = _load_state(session_id)

    # Initialize session on first call
    if not state.get("session_id"):
        state["session_id"] = session_id
        # See the matching comment in handle_user_prompt_submit: this is the
        # root-session grouping id stamped on "session.id", not the per-process
        # state key.
        state["phoenix_session_id"] = resolve_session_id(
            data,
            "session_id",
            prefer_env=True,
        )
        state["session_start_ns"] = now_ns
        state["username"] = os.environ.get("USER") or os.environ.get("USERNAME") or None
        state["turn_number"] = 0

    resolved_cwd = resolve_cwd(data, state)
    if resolved_cwd and not state.get("cwd"):
        state["cwd"] = resolved_cwd
    client_agent = resolve_client_agent_name(data)
    if client_agent and not state.get("agent_name"):
        state["agent_name"] = client_agent

    # Fallback: create a trace if UserPromptSubmit has not set one yet.
    if not state.get("current_trace"):
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        current_human_count = _count_human_messages(transcript_path) if transcript_path else 0
        prompt_preview = _get_latest_human_message(transcript_path) if transcript_path else ""

        turn_number = _next_turn_number(state, max(0, current_human_count - 1))

        state["current_trace"] = {
            "trace_id": _new_trace_id(),
            "root_span_id": _new_span_id(),
            "turn_start_ns": now_ns,
            "turn_number": turn_number,
            "prompt_preview": _truncate(prompt_preview) if prompt_preview else "",
            "human_count_at_start": max(0, current_human_count - 1),
            "model_calls": [],
            "emitted_llm_span_count": 0,
            "pending_model_call": {
                "input_value": _truncate(prompt_preview) if prompt_preview else "",
                "input_mime": "text/plain",
                "start_ns": now_ns,
                "tool_calls": [],
            },
        }

    current_trace = state.get("current_trace")
    if current_trace:
        pmc = current_trace.setdefault(
            "pending_model_call",
            {
                "input_value": current_trace.get("prompt_preview", ""),
                "input_mime": "text/plain",
                "start_ns": current_trace.get("turn_start_ns", now_ns),
                "tool_calls": [],
            },
        )
        tuid = str(data.get("tool_use_id") or data.get("toolUseId") or data.get("id") or "")
        pmc.setdefault("tool_calls", []).append(
            {
                "name": tool_name,
                "input": tool_input,
                "id": tuid,
            }
        )
        pmc["end_ns"] = now_ns
        inp_str = (
            json.dumps(tool_input)
            if isinstance(tool_input, (dict, list))
            else str(tool_input or "")
        )
        pmc["output_value"] = _truncate(inp_str)
        pmc["output_mime"] = "application/json"
        pmc["tool_call_ids"] = [tc["id"] for tc in pmc["tool_calls"] if tc.get("id")]

    pending_entry: dict[str, Any] = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "start_ns": now_ns,
    }

    if tool_name in ("Agent", "Task") and current_trace:
        agent_span_id = _new_span_id()
        tuid = str(data.get("tool_use_id") or data.get("toolUseId") or "")
        if tuid:
            agent_span_id = _agent_span_id(tuid)

        pending_entry["pre_allocated_span_id"] = agent_span_id
        pending_key = f"{tool_name}#{agent_span_id}"
    else:
        pending_key = _pending_tool_key(data, tool_name)

    state.setdefault("pending_tools", {})[pending_key] = pending_entry
    _save_state(session_id, state)


def handle_post_tool(data: dict, config: dict) -> None:
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_post_tool: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()
    _finish_tool_call(data, config, session_id, end_ns, is_failure=False)


def _tool_error_message(data: dict, tool_response: Any) -> str:
    """Extract the error message a PostToolUseFailure payload carries."""
    error_msg = ""
    if isinstance(tool_response, dict):
        error_msg = tool_response.get("error", tool_response.get("message", ""))
    elif isinstance(tool_response, str):
        error_msg = tool_response
    if not error_msg:
        error_msg = data.get("error", data.get("error_message", "Tool call failed"))
    return error_msg


def _finish_tool_call(
    data: dict,
    config: dict,
    session_id: str,
    end_ns: int,
    *,
    is_failure: bool,
) -> None:
    """Close a pending tool call: resolve, parent and emit its span.

    Claude Code runs parallel tool calls' hooks as concurrent processes, so
    the pending entry is resolved, its parent chosen and the entry removed in
    one read-modify-write under the session lock. A hook that read the state
    before a sibling removed its entry would otherwise still see that sibling
    as pending. The tool span itself is exported after the lock is released;
    the export is network I/O and needs nothing further from the state file.
    """
    event = "post_tool_failure" if is_failure else "post_tool"
    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state:
            log.warning("No state found for session %s in %s", session_id, event)
            return

        current_trace = state.get("current_trace")
        if not current_trace:
            log.debug("No current trace for session %s in %s", session_id, event)
            return

        tool_name = data.get("tool_name", "unknown")
        data_tool_input = data.get("tool_input")
        subagent_id = _subagent_id(data)
        current_tool, pending_key = _find_pending_tool_entry(
            state,
            tool_name,
            data_tool_input,
            _pending_tool_key(data, tool_name),
        )
        tool_input = data_tool_input or current_tool.get("tool_input", {})
        tool_response = data.get("tool_response", {})
        start_ns = current_tool.get("start_ns", end_ns - 1_000_000)
        # For Agent tool calls the span ID was pre-allocated at PreToolUse time so
        # the subagent could reference it as its parent span. A failed call's
        # span keeps a fresh id.
        pre_allocated_span_id = None if is_failure else current_tool.get("pre_allocated_span_id")

        tool_call_id = data.get("tool_use_id") or data.get("tool_call_id") or data.get("id")
        subagent = (
            _subagent_record(state, subagent_id, data.get("agent_type")) if subagent_id else None
        )

        # Move completed pending_model_call to model_calls
        if (
            current_trace.get("pending_model_call")
            and "end_ns" in current_trace["pending_model_call"]
        ):
            pmc = current_trace.pop("pending_model_call")
            current_trace.setdefault("model_calls", []).append(pmc)

        # Stage the next model call receiving this tool's response
        tool_resp_str = (
            json.dumps(tool_response)
            if isinstance(tool_response, (dict, list))
            else str(tool_response or "")
        )
        if "pending_model_call" not in current_trace:
            current_trace["pending_model_call"] = {
                "input_value": _truncate(tool_resp_str),
                "input_mime": "application/json"
                if isinstance(tool_response, (dict, list))
                else "text/plain",
                "start_ns": end_ns,
                "tool_calls": [],
            }
        else:
            prev_in = current_trace["pending_model_call"].get("input_value", "")
            current_trace["pending_model_call"]["input_value"] = _truncate(
                f"{prev_in}\n{tool_resp_str}"
            )

        # Emit any pending LLM spans whose token counts have landed in the transcript
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(state, transcript_path, config, subagent_id=subagent_id)

        trace_id = current_trace["trace_id"]
        if subagent_id and subagent is not None:
            trace_id = subagent["trace_id"]
            parent_span_id = subagent["agent_span_id"]
        else:
            parent_span_id = (
                _find_active_agent_span_id(state, pending_key, tool_name)
                or current_trace.get("llm_span_by_tool_call", {}).get(str(tool_call_id or ""))
                or current_trace["root_span_id"]
            )
        span_record = _build_tool_span_record(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=tool_response,
            start_ns=start_ns,
            end_ns=end_ns,
            trace_id=trace_id,
            root_span_id=parent_span_id,
            is_failure=is_failure,
            error_msg=_tool_error_message(data, tool_response) if is_failure else "",
            span_id=pre_allocated_span_id,
            tool_call_id=tool_call_id,
        )

        dispatched_id = (
            str(tool_response.get("agentId") or "")
            if tool_name in ("Agent", "Task") and isinstance(tool_response, dict)
            else ""
        )
        if dispatched_id:
            span_record["attributes"]["agent.id"] = dispatched_id
            span_record["attributes"]["subagent.id"] = dispatched_id
            _subagent_record(
                state,
                dispatched_id,
                tool_response.get("agentType") or (tool_input or {}).get("subagent_type"),
            )

        known_parents = _known_span_parents(current_trace)
        if span_record["force_span_id"]:
            # Record the link before export so a later span this turn (e.g. the
            # turn root) can be checked against it.
            current_trace.setdefault("span_parents", {})[span_record["span_id_hex"]] = span_record[
                "parent_span_id_hex"
            ]

        phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(
            state,
            data,
        )
        username = state.get("username")
        agent_name = (
            _subagent_name(subagent.get("agent_type"))
            if subagent is not None
            else state.get("agent_name")
        )
        cwd = state.get("cwd")

        pt = state.get("pending_tools", {})
        pt.pop(pending_key, None)
        if not subagent_id:
            # Fall back to tool_name for any entry written with the old plain key.
            pt.pop(tool_name, None)
        _save_state(session_id, state)

    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[span_record],
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=agent_name,
        cwd=cwd,
        known_parents=known_parents,
    )


def handle_post_tool_failure(data: dict, config: dict) -> None:
    """Handle PostToolUseFailure: emit an error TOOL/RETRIEVER/AGENT span."""
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_post_tool_failure: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()
    _finish_tool_call(data, config, session_id, end_ns, is_failure=True)


def handle_stop(data: dict, config: dict) -> None:
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_stop: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        current_trace = state.get("current_trace")
        if not current_trace:
            log.debug("No active trace for session %s at stop", session_id)
            return

        last_message = (
            data.get("last_assistant_message")
            or data.get("lastAssistantMessage")
            or data.get("message")
            or ""
        )
        if last_message:
            current_trace["last_llm_output"] = _truncate(_format_assistant_message(last_message))

        if current_trace.get("pending_model_call"):
            pmc = current_trace.pop("pending_model_call")
            pmc["output_value"] = _truncate(_format_assistant_message(last_message))
            pmc["output_mime"] = "text/plain"
            pmc["end_ns"] = end_ns
            pmc["is_stop"] = True
            current_trace.setdefault("model_calls", []).append(pmc)

        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(
            state, transcript_path, config, retry_delay_s=0.03, force_remaining=True
        )

        _complete_turn(state, config, end_ns)

        _end_turn(session_id, state)

    _cleanup_stale_states()


def handle_subagent_stop(data: dict, config: dict) -> None:
    """Handle SubagentStop."""
    session_id = resolve_session_id(data, "session_id")
    agent_id = _subagent_id(data)
    if session_id is None or agent_id is None:
        log.warning(
            "handle_subagent_stop: payload lacks 'session_id' or 'agent_id' — skipping",
        )
        return
    log.debug("handle_subagent_stop: session %s agent %s finished", session_id, agent_id)


def _end_turn(session_id: str, state: dict) -> None:
    """Drop the finished turn from *state* and keep the session-level fields.

    ``turn_number`` lives on the session state, so the state file must outlive
    the turn for the next UserPromptSubmit to number its turn one higher.
    SessionEnd deletes the file.
    """
    ct = state.pop("current_trace", None)
    if isinstance(ct, dict) and ct.get("trace_id") and ct.get("root_span_id"):
        state["last_trace"] = {
            "trace_id": ct["trace_id"],
            "root_span_id": ct["root_span_id"],
        }
    state.pop("pending_tools", None)
    state.pop("transcript_path", None)
    _save_state(session_id, state)


def handle_stop_failure(data: dict, config: dict) -> None:
    """Handle StopFailure: close the turn with an ERROR root span.

    Claude Code fires StopFailure instead of Stop when the turn ends on an API
    error, so without this the turn's root span is never sent.
    """
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_stop_failure: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        current_trace = state.get("current_trace")
        if not current_trace:
            log.debug("No active trace for session %s at stop failure", session_id)
            return

        error_type = str(data.get("error") or "unknown")
        last_message = (
            data.get("last_assistant_message")
            or data.get("lastAssistantMessage")
            or data.get("message")
            or ""
        )
        if last_message:
            current_trace["last_llm_output"] = _truncate(_format_assistant_message(last_message))
        elif not current_trace.get("last_llm_output"):
            current_trace["last_llm_output"] = f"(Stop failed: {error_type})"

        if current_trace.get("pending_model_call"):
            pmc = current_trace.pop("pending_model_call")
            pmc["output_value"] = current_trace["last_llm_output"]
            pmc["output_mime"] = "text/plain"
            pmc["end_ns"] = end_ns
            pmc["is_stop"] = True
            current_trace.setdefault("model_calls", []).append(pmc)

        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(
            state, transcript_path, config, retry_delay_s=0.03, force_remaining=True
        )

        _complete_turn(
            state,
            config,
            end_ns,
            failure={
                "error.type": error_type,
                "error.message": _truncate(data.get("error_details") or ""),
            },
        )

        _end_turn(session_id, state)


def _emit_event_span(
    data: dict,
    config: dict,
    event: str,
    build: Callable[[dict], tuple[str, dict[str, Any], int] | None],
) -> None:
    """Emit one CHAIN span under the current turn's root for a session event.

    ``build`` receives the current trace and returns ``(name, attributes,
    start_ns)``, or None to emit nothing. Events outside a turn emit nothing:
    a lone span in a trace of its own has no turn to be read against.
    """
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "%s: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
            event,
        )
        return
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        current_trace = state.get("current_trace")
        if not current_trace:
            log.debug("No active trace for session %s at %s", session_id, event)
            return
        built = build(current_trace)
        _save_state(session_id, state)
    if built is None:
        return
    name, attrs, start_ns = built

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()
    phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(state, data)
    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=state.get("username"),
        span_records=[
            {
                "trace_id_hex": current_trace["trace_id"],
                "span_id_hex": _new_span_id(),
                "parent_span_id_hex": current_trace["root_span_id"],
                "name": name,
                "kind": SpanKind.INTERNAL,
                "start_ns": start_ns,
                "end_ns": end_ns,
                "attributes": {"openinference.span.kind": "CHAIN", **attrs},
            },
        ],
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=(
            _subagent_name(data.get("agent_type"))
            if _subagent_id(data)
            else state.get("agent_name")
        ),
        cwd=state.get("cwd"),
        known_parents=_known_span_parents(current_trace),
    )


def _permission_attrs(data: dict) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "permission.mode": str(data.get("permission_mode") or ""),
        "permission.tool": str(data.get("tool_name") or ""),
        "input.value": _truncate(data.get("tool_input", {})),
        "input.mime_type": "application/json",
    }
    # PermissionRequest only: the "always allow" rules Claude Code offers.
    suggestions = data.get("permission_suggestions")
    if suggestions:
        attrs["permission.suggestions"] = _truncate(suggestions)
    tool_call_id = data.get("tool_use_id")
    if tool_call_id:
        attrs["tool.call_id"] = str(tool_call_id)
    return attrs


def handle_permission_request(data: dict, config: dict) -> None:
    """Handle PermissionRequest: a CHAIN span naming the tool awaiting approval."""

    def build(_current_trace: dict) -> tuple[str, dict[str, Any], int]:
        return "Permission Request", _permission_attrs(data), time.time_ns()

    _emit_event_span(data, config, "handle_permission_request", build)


def handle_permission_denied(data: dict, config: dict) -> None:
    """Handle PermissionDenied: a CHAIN span recording the denied tool call."""

    def build(_current_trace: dict) -> tuple[str, dict[str, Any], int]:
        attrs = _permission_attrs(data)
        attrs["permission.denied"] = "true"
        reason = data.get("reason")
        if reason:
            attrs["permission.reason"] = _truncate(reason)
        return "Permission Denied", attrs, time.time_ns()

    _emit_event_span(data, config, "handle_permission_denied", build)


def handle_notification(data: dict, config: dict) -> None:
    """Handle Notification: a CHAIN span carrying the notification text."""

    def build(_current_trace: dict) -> tuple[str, dict[str, Any], int]:
        notification_type = str(data.get("notification_type") or data.get("type") or "info")
        message = _truncate(data.get("message") or "")
        attrs = {
            "notification.type": notification_type,
            "notification.message": message,
            "notification.title": _truncate(data.get("title") or ""),
            "input.value": message,
            "input.mime_type": "text/plain",
        }
        return f"Notification: {notification_type}", attrs, time.time_ns()

    _emit_event_span(data, config, "handle_notification", build)


def handle_pre_compact(data: dict, config: dict) -> None:
    """Handle PreCompact: record when and why compaction started in this turn."""

    def build(current_trace: dict) -> None:
        current_trace["compact_start_ns"] = time.time_ns()
        if data.get("trigger"):
            current_trace["compact_trigger"] = str(data["trigger"])
        return None

    _emit_event_span(data, config, "handle_pre_compact", build)


def handle_post_compact(data: dict, config: dict) -> None:
    """Handle PostCompact: a CHAIN span covering the compaction PreCompact opened."""

    def build(current_trace: dict) -> tuple[str, dict[str, Any], int]:
        start_ns = current_trace.pop("compact_start_ns", None) or time.time_ns()
        trigger = str(
            data.get("trigger") or current_trace.pop("compact_trigger", None) or "unknown"
        )
        current_trace.pop("compact_trigger", None)
        attrs: dict[str, Any] = {"compact.trigger": trigger}
        summary = data.get("compact_summary")
        if summary:
            attrs["output.value"] = _truncate(summary)
            attrs["output.mime_type"] = "text/plain"
        return f"Compact ({trigger})", attrs, start_ns

    _emit_event_span(data, config, "handle_post_compact", build)


def handle_session_end(data: dict, config: dict) -> None:
    """Handle SessionEnd: close a turn still open, then delete the state file.

    A session that exits mid-turn gets no Stop, so its open turn is sent here.
    """
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        return
    end_ns = time.time_ns()
    with _session_lock(session_id):
        state = _load_state(session_id)
        if state.get("current_trace"):
            transcript_path = _get_cached_transcript_path(data, state, session_id)
            _emit_pending_llm_spans(state, transcript_path, config, force_remaining=True)
            _complete_turn(state, config, end_ns)
        _delete_state(session_id)


def emit_debug_hook_span(
    data: dict,
    config: dict,
    *,
    client: str,
    event: str,
    raw_payload: Any,
) -> bool:
    """Emit a full, untruncated debug span for any hook event, threaded into the session's turn trace."""
    payload_key = "conversationId" if client == "agy" else "session_id"
    session_id = resolve_session_id(data, payload_key, prefer_env=False)
    if session_id is None:
        log.warning(
            "emit_debug_hook_span (%s/%s): no session id in payload (%r missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
            client,
            event,
            payload_key,
        )
        return False

    now_ns = time.time_ns()
    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("session_id"):
            state["session_id"] = session_id
            state["phoenix_session_id"] = resolve_session_id(
                data,
                payload_key,
                prefer_env=True,
            )
            state["session_start_ns"] = now_ns
            state["username"] = os.environ.get("USER") or os.environ.get("USERNAME") or None
            state["turn_number"] = 0

        resolved_cwd = resolve_cwd(data, state)
        if resolved_cwd:
            state["cwd"] = resolved_cwd
        client_agent = resolve_client_agent_name(data)
        if client_agent:
            state["agent_name"] = client_agent

        current_trace = state.get("current_trace")
        last_trace = state.get("last_trace")
        known_parents: dict[str, str | None] | None = None

        if isinstance(current_trace, dict) and current_trace.get("trace_id"):
            trace_id = current_trace["trace_id"]
            parent_span_id = current_trace.get("root_span_id")
            sub_id = _subagent_id(data)
            if sub_id:
                sub_rec = (state.get("subagents") or {}).get(sub_id)
                if isinstance(sub_rec, dict) and sub_rec.get("agent_span_id"):
                    parent_span_id = sub_rec["agent_span_id"]
            known_parents = _known_span_parents(current_trace)
        elif (
            isinstance(last_trace, dict)
            and last_trace.get("trace_id")
            and event not in ("SessionStart", "Setup", "UserPromptSubmit", "PreInvocation")
        ):
            trace_id = last_trace["trace_id"]
            parent_span_id = last_trace.get("root_span_id")
        else:
            pending = state.get("pending_turn_trace")
            if (
                not isinstance(pending, dict)
                or not pending.get("trace_id")
                or not pending.get("root_span_id")
            ):
                parent_trace_id = None
                psid = state.get("phoenix_session_id")
                if psid and psid != session_id:
                    try:
                        pstate = _load_state(psid)
                        if pstate and isinstance(pstate.get("current_trace"), dict):
                            parent_trace_id = pstate["current_trace"].get("trace_id")
                    except Exception:
                        pass
                pending = {
                    "trace_id": parent_trace_id or _new_trace_id(),
                    "root_span_id": _new_span_id(),
                }
                state["pending_turn_trace"] = pending
            trace_id = pending["trace_id"]
            parent_span_id = pending["root_span_id"]

        if event != "SessionEnd":
            _save_state(session_id, state)

    phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(
        state,
        data,
        payload_key=payload_key,
    )
    full_payload_json = _redact_secrets(
        json.dumps(raw_payload, ensure_ascii=False, default=str)
        if not isinstance(raw_payload, str)
        else raw_payload
    )
    hook_event_name = str(data.get("hook_event_name") or data.get("hookEventName") or event)
    attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        "hook.plugin": "aops-debug",
        "hook.client": client,
        "hook.event": event,
        "hook.event_name": hook_event_name,
        "input.value": full_payload_json,
        "input.mime_type": "application/json",
        "hook.raw_payload": full_payload_json,
    }
    tool_name = str(data.get("tool_name") or data.get("toolName") or "")
    if tool_name:
        attrs["tool.name"] = tool_name
    tool_call_id = data.get("tool_use_id") or data.get("toolCallId")
    if tool_call_id:
        attrs["tool.call_id"] = str(tool_call_id)

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()
    surface = "agy" if client == "agy" else "claude-code"
    service_name = "aops-agy-hooks" if client == "agy" else "aops-claude-hooks"
    return _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=state.get("username"),
        span_records=[
            {
                "trace_id_hex": trace_id,
                "span_id_hex": _new_span_id(),
                "parent_span_id_hex": parent_span_id,
                "name": f"aops-debug.{event}",
                "kind": SpanKind.INTERNAL,
                "start_ns": now_ns,
                "end_ns": now_ns,
                "attributes": attrs,
            },
        ],
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=(
            _subagent_name(data.get("agent_type"))
            if _subagent_id(data)
            else state.get("agent_name")
        ),
        cwd=state.get("cwd"),
        known_parents=known_parents,
        service_name=service_name,
        surface=surface,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: claude_code_tracer.py <pre_tool|post_tool|post_tool_failure|user_prompt_submit|stop|subagent_stop>",
            file=sys.stderr,
        )
        sys.exit(0)

    event = sys.argv[1]

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        log.warning("Failed to parse stdin JSON: %s", e)
        data = {}

    config = discover_config()
    if config is None:
        log.debug("OTel tracer not configured, skipping tracing.")
        sys.exit(0)

    try:
        if event == "pre_tool":
            handle_pre_tool(data, config)
        elif event == "post_tool":
            handle_post_tool(data, config)
        elif event == "post_tool_failure":
            handle_post_tool_failure(data, config)
        elif event == "user_prompt_submit":
            handle_user_prompt_submit(data, config)
        elif event == "stop":
            handle_stop(data, config)
        elif event == "subagent_stop":
            handle_subagent_stop(data, config)
        else:
            log.warning("Unknown event: %s", event)
    except Exception as e:
        log.warning("Tracer error (%s): %s", event, e, exc_info=True)
        raise

    sys.exit(0)


if __name__ == "__main__":
    main()
