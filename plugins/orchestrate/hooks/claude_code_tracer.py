#!/usr/bin/env python3
"""
claude_code_tracer.py — OpenInference tracer for Claude Code hooks.

Ships Claude Code activities as OpenInference traces to Arthur Engine.

Trace model:
  - Each user prompt → one trace (CHAIN root + TOOL/RETRIEVER/AGENT children + LLM children)
  - Exiting the session completes the current in-progress trace
  - Traces are linked by arthur.session attribute

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
import socket
import sys
import time
from datetime import datetime
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
    cfg_path = os.environ.get("AOPS_POLECAT_CONFIG")
    if not cfg_path:
        sessions = os.environ.get("AOPS_SESSIONS")
        if sessions:
            cfg_path = os.path.join(sessions, "polecat.yaml")
    if cfg_path and os.path.exists(cfg_path):
        try:
            import yaml

            with open(cfg_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log.debug("Failed to read polecat config %s: %s", cfg_path, e)
    return {}


def resolve_canonical_project(project: str | None, config: dict | None = None) -> str | None:
    """Resolve a project name or alias to its canonical project slug.

    Reads aliases configured in polecat.yaml:
    - `projects.<slug>.aliases`: list of alias strings or single alias string
    - top-level `aliases:` dict: mapping from alias to canonical slug (e.g. `academicOps: aops`),
      or canonical slug to alias list (e.g. `aops: [academicOps, academicops]`).

    If `project` matches a canonical slug or an alias (checked case-insensitively if exact
    case does not hit), returns the canonical slug.
    Also handles `<alias>-<task_id>` prefixes by canonicalizing the prefix.
    If no alias matches, returns `project`.
    """
    if not project:
        return project

    if config is None:
        config = _load_polecat_config()

    project_str = str(project).strip()
    if not project_str:
        return project

    projects = config.get("projects", {})
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

    top_aliases = config.get("aliases", {})
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

    return project_str


def resolve_project_name(
    data: dict | None = None,
    task_id: str = "",
    config: dict | None = None,
) -> str:
    """Resolve project name from environment, config, hook payload cwd, or starting dirname.

    Priority:
    1. Explicit task_id / GENAI_ENGINE_TASK_ID if non-empty
    2. PHOENIX_PROJECT_NAME env var
    3. OTEL_SERVICE_NAME env var
    4. Hook payload cwd or CLAUDE_PROJECT_DIR or current working directory basename
    5. Fallback to 'default'

    Any resolved project name is automatically mapped to its canonical slug if defined
    in polecat.yaml aliases.
    """
    raw_name = ""
    if task_id:
        raw_name = task_id
    elif env_task := os.environ.get("GENAI_ENGINE_TASK_ID", "").strip():
        raw_name = env_task
    elif env_phoenix := os.environ.get("PHOENIX_PROJECT_NAME", "").strip():
        raw_name = env_phoenix
    elif env_service := os.environ.get("OTEL_SERVICE_NAME", "").strip():
        raw_name = env_service
    else:
        # Directory resolution
        cwd = ""
        if data and isinstance(data, dict):
            cwd = str(data.get("cwd") or "")
        if not cwd:
            cwd = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
        if not cwd:
            try:
                cwd = os.getcwd()
            except Exception:
                cwd = ""

        if cwd:
            name = Path(cwd).resolve().name
            if name and name not in ("/", "\\", "."):
                raw_name = name

    if not raw_name:
        raw_name = "default"

    canonical = resolve_canonical_project(raw_name, config=config)
    return canonical or raw_name


def discover_config(data: dict | None = None) -> dict | None:
    """Returns config dict with keys: api_key, task_id, endpoint, protocol (optional), project_name.
    Returns None if not configured (silent no-op)."""
    api_key = (
        os.environ.get("GENAI_ENGINE_API_KEY")
        or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS", "")
    )
    task_id = (
        os.environ.get("GENAI_ENGINE_TASK_ID")
        or os.environ.get("OTEL_SERVICE_NAME")
        or os.environ.get("PHOENIX_PROJECT_NAME", "")
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

    project_name = resolve_project_name(data, task_id)
    if not task_id:
        task_id = project_name

    cfg = {
        "api_key": api_key,
        "task_id": task_id,
        "endpoint": endpoint,
        "project_name": project_name,
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
      session. ``$AOPS_SESSION_ID`` is written once, at the root session's
      SessionStart, into ``CLAUDE_ENV_FILE`` (handlers.py:_isolate_credentials)
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
    payload_value = data.get(payload_key)
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

    Serialises concurrent handle_post_tool / handle_post_tool_failure
    processes so that _emit_pending_llm_spans reads a consistent
    emitted_llm_span_count and never emits the same LLM span twice.
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


# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------


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
                for block in entry.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use" and block.get("name") == tool_name:
                        return block.get("id")
    except Exception as e:
        log.debug("Failed to find tool_use_id: %s", e)
    return None


def _is_human_message(entry: dict) -> bool:
    """True for user-initiated messages (not tool results)."""
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content", "")
    # Tool result messages have content as a list; human messages have a string
    return isinstance(content, str)


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


def _iso_to_ns(ts: str) -> int:
    """Convert ISO 8601 timestamp string to nanoseconds."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return time.time_ns()


def _tool_result_text(content: list) -> str:
    """Extract readable text from a tool_result content list."""
    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_result":
            inner = item.get("content", "")
            if isinstance(inner, str):
                parts.append(inner)
            elif isinstance(inner, list):
                for rc in inner:
                    if isinstance(rc, dict) and rc.get("type") == "text":
                        parts.append(rc.get("text", ""))
    return "\n".join(parts)


def _extract_llm_spans_for_turn(
    transcript_path: str,
    human_count_at_start: int,
    trace_id_hex: str,
    root_span_id_hex: str,
) -> list[dict]:
    """
    Extract LLM spans from transcript entries that belong to this turn.

    A turn starts after the `human_count_at_start`-th human message and ends
    at the next human message (or end of transcript).  Scanning stops as soon
    as a second human message is seen while in_turn is True — those subsequent
    turns belong to their own traces.
    Uses actual timestamps from the transcript.

    For each LLM call we use the immediately-preceding message as the input:
      - First call in turn  → the human prompt (text/plain)
      - Subsequent calls    → the tool result(s) that preceded them (application/json)

    Output is the assistant's text response when present; otherwise the
    tool_use blocks serialised as JSON so the span always has an output value.

    **Grouping by message.id**

    Claude Code (with extended thinking enabled) splits a single API response
    across multiple consecutive transcript entries that share the same
    ``message.id`` — one entry per block type (thinking / text / tool_use).
    Each entry duplicates the input-side token counts.  We MUST group these
    entries and emit exactly one LLM span per API response, otherwise:

      * Prompt tokens are reported N× too high (once per entry).
      * "Thinking-only" entries produce empty, noisy spans.
      * Intermediate text (the entry with ``type=text`` that precedes a tool
        call) becomes its own orphaned 8-token span instead of being part of
        the single span for that API call.

    Grouping strategy:
      - Input tokens  → first entry in the group (avoids duplication).
      - Output tokens → sum across all entries (each entry captures the tokens
                        for its own block).
      - Text output   → concatenate all ``text`` blocks from any entry.
      - Tool output   → JSON of tool_use blocks from the last entry (fall-back
                        when no text is present).
      - Timestamp     → first entry.
    """
    spans = []
    try:
        lines = Path(transcript_path).read_text().splitlines()
        human_count = 0
        in_turn = False

        # Tracks the input for the *next* LLM call we encounter
        last_input_value = ""
        last_input_mime = "text/plain"
        last_input_role = "user"
        last_input_content = ""
        last_input_tool_call_id = ""

        # Accumulator for the current message.id group
        current_group_id: str | None = None
        group_first_usage: dict = {}
        group_total_output_tokens: int = 0
        group_text_parts: list = []
        group_tool_use_parts: list = []
        group_model: str = "claude"
        group_ts: str = ""
        group_stop_reason: str = ""
        group_input_snapshot: dict = {}  # last_input* captured at group start

        def _flush_group() -> None:
            """Emit one LLM span for the accumulated group, if non-empty."""
            nonlocal current_group_id, group_first_usage, group_total_output_tokens
            nonlocal group_text_parts, group_tool_use_parts, group_model, group_ts
            nonlocal group_input_snapshot, group_stop_reason

            if not current_group_id:
                return

            usage = group_first_usage
            input_tokens = usage.get("input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            output_tokens = group_total_output_tokens

            if group_text_parts:
                output_value = _truncate("".join(group_text_parts))
                output_mime = "text/plain"
            elif group_tool_use_parts:
                output_value = _truncate(json.dumps(group_tool_use_parts))
                output_mime = "application/json"
            else:
                output_value = ""
                output_mime = "text/plain"

            # Per OpenInference spec, message.content carries text only; tool calls
            # go in structured tool_calls attributes (not serialised into content).
            output_message_content = (
                _truncate("".join(group_text_parts)) if group_text_parts else None
            )

            start_ns = _iso_to_ns(group_ts)
            end_ns = start_ns + max(output_tokens * 10_000_000, 1_000_000)

            snap = group_input_snapshot
            attrs: dict[str, Any] = {
                "openinference.span.kind": "LLM",
                "llm.system": "anthropic",
                "llm.model_name": group_model,
                "llm.token_count.prompt": input_tokens + cache_read + cache_create,
                "llm.token_count.completion": output_tokens,
                "llm.token_count.total": input_tokens + cache_read + cache_create + output_tokens,
                "llm.token_count.prompt_details.cache_read": cache_read,
                "llm.token_count.prompt_details.cache_write": cache_create,
                "llm.input_messages.0.message.role": snap.get("role", "user"),
                "llm.input_messages.0.message.content": snap.get("content", ""),
                "input.value": snap.get("value", ""),
                "input.mime_type": snap.get("mime", "text/plain"),
                "llm.output_messages.0.message.role": "assistant",
                "output.value": output_value,
                "output.mime_type": output_mime,
            }
            if output_message_content:
                attrs["llm.output_messages.0.message.content"] = output_message_content

            # Structured tool_calls attributes (OpenInference spec)
            for i, tc in enumerate(group_tool_use_parts):
                attrs[f"llm.output_messages.0.message.tool_calls.{i}.tool_call.id"] = tc.get(
                    "id", ""
                )
                attrs[f"llm.output_messages.0.message.tool_calls.{i}.tool_call.function.name"] = (
                    tc.get("name", "")
                )
                attrs[
                    f"llm.output_messages.0.message.tool_calls.{i}.tool_call.function.arguments"
                ] = _truncate(json.dumps(tc.get("input", {})))

            # tool_call_id on input message when input is a tool result
            if snap.get("tool_call_id"):
                attrs["llm.input_messages.0.message.tool_call_id"] = snap["tool_call_id"]

            # Map stop_reason to OpenInference llm.finish_reason
            _FINISH_REASON_MAP = {"end_turn": "stop", "max_tokens": "length"}
            finish_reason = _FINISH_REASON_MAP.get(group_stop_reason, group_stop_reason)
            if finish_reason:
                attrs["llm.finish_reason"] = finish_reason

            spans.append(
                {
                    "trace_id_hex": trace_id_hex,
                    "span_id_hex": _new_span_id(),
                    "parent_span_id_hex": root_span_id_hex,
                    "name": f"claude/{group_model}",
                    "kind": None,
                    "start_ns": start_ns,
                    "end_ns": end_ns,
                    "attributes": attrs,
                    "force_span_id": False,
                },
            )

            # Reset accumulator
            current_group_id = None
            group_first_usage = {}
            group_total_output_tokens = 0
            group_text_parts = []
            group_tool_use_parts = []
            group_model = "claude"
            group_ts = ""
            group_stop_reason = ""
            group_input_snapshot = {}

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")

            # ── Human message: marks the start of this turn ──────────────────
            if _is_human_message(entry):
                _flush_group()
                human_count += 1
                if in_turn:
                    # Next user turn has started — stop here.  Its spans belong
                    # to a different trace.
                    break
                if human_count > human_count_at_start:
                    in_turn = True
                    human_text = entry.get("message", {}).get("content", "")
                    last_input_value = json.dumps(
                        {"role": "user", "content": human_text[:500]},
                    )
                    last_input_mime = "application/json"
                    last_input_role = "user"
                    last_input_content = _truncate(human_text)
                    last_input_tool_call_id = ""
                continue

            if not in_turn:
                continue

            # ── Tool result (user message with list content) ──────────────────
            if entry_type == "user":
                _flush_group()
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    text = _tool_result_text(content)
                    payload = text if text else json.dumps(content)
                    # Extract tool_use_id from first tool_result for message.tool_call_id
                    tool_use_id = ""
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tool_use_id = item.get("tool_use_id", "")
                            break
                    last_input_value = json.dumps(
                        {"role": "tool", "content": payload[:500]},
                    )
                    last_input_mime = "application/json"
                    last_input_role = "tool"
                    last_input_content = _truncate(payload)
                    last_input_tool_call_id = tool_use_id
                continue

            # ── Non-assistant entries (progress, system, …) ───────────────────
            if entry_type != "assistant":
                continue

            msg = entry.get("message", {})
            usage = msg.get("usage", {})
            if not usage:
                continue

            # Falls back to the entry's object id, as a string: this is only ever a
            # grouping key compared against `current_group_id`, which is `str | None`.
            msg_id = msg.get("id", "") or str(id(entry))
            model = msg.get("model", "claude")
            content_blocks = msg.get("content", [])
            ts = entry.get("timestamp", "")
            stop_reason = msg.get("stop_reason", "")

            # ── Start a new group or extend the current one ───────────────────
            if msg_id != current_group_id:
                _flush_group()
                current_group_id = msg_id
                group_first_usage = usage
                group_total_output_tokens = 0
                group_text_parts = []
                group_tool_use_parts = []
                group_model = model
                group_ts = ts
                group_stop_reason = stop_reason
                # Snapshot the input context at the start of this API call
                group_input_snapshot = {
                    "role": last_input_role,
                    "content": last_input_content,
                    "value": last_input_value,
                    "mime": last_input_mime,
                    "tool_call_id": last_input_tool_call_id,
                }
            else:
                # Extending the group: last non-empty stop_reason wins
                if stop_reason:
                    group_stop_reason = stop_reason

            # Accumulate output tokens and content blocks for this group
            group_total_output_tokens += usage.get("output_tokens", 0)
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    group_text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    group_tool_use_parts.append(
                        {
                            "id": block.get("id", ""),
                            "name": block.get("name", ""),
                            "input": block.get("input", {}),
                        },
                    )

        _flush_group()

    except Exception as e:
        log.warning("Failed to extract LLM spans: %s", e)
        raise

    return spans


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


def _create_exporter(
    endpoint: str,
    headers: dict | None = None,
    protocol: str = "",
) -> Any:
    """Create an OTel span exporter. Fails safe if modules are missing or initialization fails."""
    prefer_http = protocol in ("http/protobuf", "http/json", "http")

    if not prefer_http:
        try:
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
        except Exception as e:
            log.debug("gRPC exporter unavailable (%s), trying HTTP fallback", e)

    # HTTP Exporter
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as HTTPSpanExporter,
        )

        log.debug("Initializing OTLP HTTP span exporter for endpoint %s", endpoint)
        return HTTPSpanExporter(
            endpoint=endpoint,
            headers=headers if headers else None,
            timeout=_EXPORT_TIMEOUT_S,
        )
    except Exception as e:
        log.debug("HTTP exporter unavailable (%s), trying Console fallback", e)

    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        return ConsoleSpanExporter()
    except Exception as e:
        log.debug("Console exporter unavailable (%s)", e)
        return None


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

_MAX_ATTR_BYTES = 8192


def _truncate(value: Any) -> str:
    s = json.dumps(value) if not isinstance(value, str) else value
    encoded = s.encode("utf-8")
    if len(encoded) > _MAX_ATTR_BYTES:
        s = encoded[:_MAX_ATTR_BYTES].decode("utf-8", errors="ignore") + "...[truncated]"
    return s


# ---------------------------------------------------------------------------
# FixedSpanIdGenerator — forces the pre-generated root span ID
# ---------------------------------------------------------------------------


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
# OTLP export helper
# ---------------------------------------------------------------------------


def _build_and_export_spans(
    config: dict,
    session_id: str,
    username: str,
    span_records: list[dict],
) -> None:
    """Create spans from records and export via OTLP gRPC (with fallbacks)."""
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

    service_name = config.get("service_name") or config.get("task_id") or "claude-code"
    project_name = config.get("project_name") or config.get("task_id") or "default"
    try:
        host_name = socket.gethostname()
    except Exception:
        host_name = ""

    resource_attrs = {
        "service.name": service_name,
        "openinference.project.name": project_name,
        "project.name": project_name,
        "arthur.task": config.get("task_id", project_name),
        "arthur.session": session_id,
        "arthur.user": username,
    }
    if host_name:
        resource_attrs["host.name"] = host_name
    if username:
        resource_attrs["user.id"] = username

    resource = Resource.create(resource_attrs)

    for rec in span_records:
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

            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("claude-code-tracer")

            ctx = None
            if rec.get("parent_span_id_hex"):
                parent_sc = SpanContext(
                    trace_id=int(rec["trace_id_hex"], 16),
                    span_id=int(rec["parent_span_id_hex"], 16),
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

            span.set_attribute("arthur_span_version", "arthur_span_v1")
            span.set_attribute("session.id", session_id)
            span.set_attribute("user.id", username)
            span.set_attribute("project.name", project_name)
            span.set_attribute("openinference.project.name", project_name)
            if host_name:
                span.set_attribute("host.name", host_name)
            for k, v in rec.get("attributes", {}).items():
                span.set_attribute(k, v)

            if rec.get("error"):
                span.set_status(StatusCode.ERROR, description=rec.get("error_msg", ""))

            span.end(end_time=rec["end_ns"])
            provider.shutdown()
        except Exception as e:
            log.warning("Exporting OTel span failed: %s", e)
            raise


# ---------------------------------------------------------------------------
# Turn completion
# ---------------------------------------------------------------------------


def _emit_pending_llm_spans(
    state: dict,
    transcript_path: str | None,
    config: dict,
) -> None:
    """Emit any new LLM spans from the transcript that haven't been sent yet.

    Called from handle_post_tool (real-time, after each tool response) and
    handle_stop (catches the final LLM response after the last tool call).
    Updates state.current_trace in-place so the caller must save state afterwards.
    """
    current_trace = state.get("current_trace")
    if not current_trace or not transcript_path:
        return

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()

    all_llm_spans = _extract_llm_spans_for_turn(
        transcript_path,
        current_trace.get("human_count_at_start", 0),
        current_trace["trace_id"],
        current_trace["root_span_id"],
    )

    emitted = current_trace.get("emitted_llm_span_count", 0)
    new_spans = all_llm_spans[emitted:]

    # Always keep last_llm_output in sync with the last known assistant message,
    # even if there are no new spans to emit (e.g. all were emitted by post_tool
    # and the final text response was already the last one processed).
    if all_llm_spans:
        current_trace["last_llm_output"] = all_llm_spans[-1]["attributes"].get(
            "output.value",
            "",
        )

    if not new_spans:
        return

    for sp in new_spans:
        sp["kind"] = SpanKind.CLIENT

    _build_and_export_spans(
        config=config,
        session_id=_phoenix_session_id(state),
        username=state.get("username", "unknown"),
        span_records=new_spans,
    )

    current_trace["emitted_llm_span_count"] = emitted + len(new_spans)


def _complete_turn(
    state: dict,
    config: dict,
    transcript_path: str | None,
    end_ns: int,
) -> None:
    """Send the CHAIN root span for the current turn's trace.

    LLM spans are emitted in real-time from _emit_pending_llm_spans (called
    from handle_post_tool and handle_stop), so they do not need to be re-sent
    here.  The root span's output.value is taken from the last LLM output
    already tracked in state.
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
    username = state.get("username", "unknown")
    phoenix_session_id = _phoenix_session_id(state)
    root_attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        "session.id": phoenix_session_id,
        "user.id": username,
        "arthur.turn_number": turn_number,
    }
    if prompt_preview:
        root_attrs["input.value"] = prompt_preview
        root_attrs["input.mime_type"] = "text/plain"
    if final_output:
        root_attrs["output.value"] = final_output
        root_attrs["output.mime_type"] = "text/plain"

    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[
            {
                "trace_id_hex": trace_id,
                "span_id_hex": root_span_id,
                "parent_span_id_hex": current_trace.get("parent_span_id"),
                "name": "claude-code-turn",
                "kind": SpanKind.INTERNAL,
                "start_ns": turn_start_ns,
                "end_ns": end_ns,
                "attributes": root_attrs,
                "force_span_id": True,
            },
        ],
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

    input_value = json.dumps(tool_input) if not isinstance(tool_input, str) else tool_input
    output_str = json.dumps(tool_response) if not isinstance(tool_response, str) else tool_response

    if is_failure and error_msg:
        output_value = f"ERROR: {error_msg}\n{output_str}"
    else:
        output_value = output_str

    attrs: dict[str, Any] = {
        "openinference.span.kind": span_kind_str,
        "tool.name": tool_name,
        "input.value": input_value,
        "input.mime_type": "application/json",
        "output.value": output_value,
        "output.mime_type": "application/json",
    }

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
            attrs["input.value"] = query
            attrs["input.mime_type"] = "text/plain"
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "") if isinstance(tool_input, dict) else ""
            attrs["input.value"] = url
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
        state["username"] = os.environ.get(
            "USER",
            os.environ.get("USERNAME", "unknown"),
        )
        state["human_msg_count"] = 0
        state["turn_number"] = 0

    # Complete the previous turn's trace if one is in progress.
    # Use the cached transcript path from state so that any mid-session
    # project-dir changes (e.g. gh pr create writing to a worktree dir) do
    # not silently redirect us to a shadow transcript file.
    if state.get("current_trace"):
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(state, transcript_path, config)
        _complete_turn(state, config, transcript_path, now_ns)
        # Clear the cached path and any lingering pending tools so the new turn starts clean
        state.pop("transcript_path", None)
        state.pop("pending_tools", None)

    # Count human messages for LLM span extraction.
    # UserPromptSubmit fires before Claude processes the prompt, so the new
    # message is not yet in the transcript — human_count_at_start equals the
    # current count (the new prompt will become count+1 in the transcript).
    # Resolve and immediately cache the transcript path for this new turn.
    transcript_path = _get_cached_transcript_path(data, state, session_id)
    current_human_count = _count_human_messages(transcript_path) if transcript_path else 0

    turn_number = state.get("turn_number", 0) + 1
    state["turn_number"] = turn_number
    state["human_msg_count"] = current_human_count

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

    state["current_trace"] = {
        "trace_id": parent_trace_id if parent_trace_id else _new_trace_id(),
        "root_span_id": _new_span_id(),
        "parent_span_id": parent_span_id,
        "turn_start_ns": now_ns,
        "turn_number": turn_number,
        "human_count_at_start": current_human_count,
        "prompt_preview": _truncate(prompt) if prompt else "",
    }

    _save_state(session_id, state)


def handle_pre_tool(data: dict, config: dict) -> None:
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_pre_tool: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
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
        state["username"] = os.environ.get(
            "USER",
            os.environ.get("USERNAME", "unknown"),
        )
        state["human_msg_count"] = 0
        state["turn_number"] = 0

    # Detect context continuation: Claude Code compresses context and continues
    # without firing UserPromptSubmit for the resumption message. The symptom is
    # current_trace still set from the previous turn, but the transcript has grown
    # by more than one human message since that trace started.
    if state.get("current_trace"):
        ct = state["current_trace"]
        _tp = _get_cached_transcript_path(data, state, session_id)
        if _tp:
            _cur_human = _count_human_messages(_tp)
            _start = ct.get("human_count_at_start", 0)
            if _cur_human > _start + 1:
                # A new turn started without UserPromptSubmit. Complete the old
                # trace and fall through to the fallback that creates a new one.
                _emit_pending_llm_spans(state, _tp, config)
                _complete_turn(state, config, _tp, now_ns)
                state.pop("current_trace", None)
                state.pop("pending_tools", None)

    # Fallback: create a trace if UserPromptSubmit has not set one yet.
    # This handles cases where the hook isn't registered or fires before the
    # UserPromptSubmit event is available.
    if not state.get("current_trace"):
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        current_human_count = _count_human_messages(transcript_path) if transcript_path else 0
        prompt_preview = _get_latest_human_message(transcript_path) if transcript_path else ""

        turn_number = state.get("turn_number", 0) + 1
        state["turn_number"] = turn_number
        state["human_msg_count"] = current_human_count

        state["current_trace"] = {
            "trace_id": _new_trace_id(),
            "root_span_id": _new_span_id(),
            "turn_start_ns": now_ns,
            "turn_number": turn_number,
            # human_count_at_start is one less than the current count so that
            # _extract_llm_spans_for_turn finds entries where count > this value,
            # i.e. entries belonging to the NEW turn whose prompt is the
            # current_human_count-th human message.
            "human_count_at_start": max(0, current_human_count - 1),
            "prompt_preview": _truncate(prompt_preview) if prompt_preview else "",
        }

    pending_entry: dict[str, Any] = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "start_ns": now_ns,
    }

    # For Agent/Task tool calls, pre-allocate the span ID so any INLINE
    # subagent activity (tool calls that land in this same session's
    # pending_tools while the Agent/Task call is still open — see
    # _find_active_agent_span_id) is parented under the Agent span rather
    # than the CHAIN root. Genuinely out-of-process subagents (dispatched via
    # the Agent/Task tool as a separate Claude process) get their own,
    # distinct session id and state file — confirmed empirically: 25 distinct
    # per-subagent state files observed in ~/.claude/tracer/, none sharing
    # the dispatching session's id — so they cannot be nested by trace here.
    # They are grouped instead via the shared "session.id" span attribute
    # (resolve_session_id(..., prefer_env=True), sourced from
    # $AOPS_SESSION_ID). A prior side-channel mechanism attempted trace-level
    # nesting for this case (a pending_agent JSON file written here, claimed
    # by the subagent's first hook) but never once succeeded across 29
    # historical state files, leaving 21 orphaned side-channel files; removed.
    current_trace = state.get("current_trace")
    if tool_name in ("Agent", "Task") and current_trace:
        agent_span_id = _new_span_id()
        transcript_path = state.get("transcript_path")
        if transcript_path:
            tuid = _find_tool_use_id(transcript_path, tool_name, tool_input)
            if tuid:
                import hashlib

                agent_span_id = hashlib.sha256(tuid.encode()).hexdigest()[:16]

        pending_entry["pre_allocated_span_id"] = agent_span_id
        pending_key = f"{tool_name}#{agent_span_id}"
    else:
        pending_key = tool_name

    state.setdefault("pending_tools", {})[pending_key] = pending_entry
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


def _find_pending_tool_entry(
    state: dict,
    tool_name: str,
    data_tool_input: Any,
) -> tuple[dict, str]:
    """Return (pending_entry, pending_key) for the given tool.

    For Agent/Task tools, parallel calls each get a compound key
    ``"{tool_name}#{span_id}"``.  We find the right entry by matching
    ``tool_input``; if no match, fall back to the first entry with the right
    prefix so single-agent sessions and legacy state files still work.

    For all other tools the key is just ``tool_name``.
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

    entry = pending.get(tool_name, {})
    return entry, tool_name


def _find_active_agent_span_id(
    state: dict,
    current_pending_key: str,
) -> str | None:
    """Return the pre_allocated_span_id of the innermost pending Agent/Task call.

    When an inline subagent (e.g. Explore) makes tool calls within the parent
    session, those calls appear in pending_tools alongside the Agent entry.
    This detects that situation and returns the Agent's span_id so the sub-tool
    is correctly parented under the Agent span rather than the CHAIN root.
    For nested agents, the most-recently-started one wins (innermost parent).
    """
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


def handle_post_tool(data: dict, config: dict) -> None:
    session_id = resolve_session_id(data, "session_id")
    if session_id is None:
        log.warning(
            "handle_post_tool: no session id in payload ('session_id' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()

    # Read state once to build the tool span (no mutation needed).
    state = _load_state(session_id)
    if not state:
        log.warning("No state found for session %s in post_tool", session_id)
        return

    current_trace = state.get("current_trace")
    if not current_trace:
        log.debug("No current trace for session %s in post_tool", session_id)
        return

    tool_name = data.get("tool_name", "unknown")
    data_tool_input = data.get("tool_input")
    current_tool, pending_key = _find_pending_tool_entry(
        state,
        tool_name,
        data_tool_input,
    )
    tool_input = data_tool_input or current_tool.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    start_ns = current_tool.get("start_ns", end_ns - 1_000_000)
    # For Agent tool calls the span ID was pre-allocated at PreToolUse time so
    # the subagent could reference it as its parent span.
    pre_allocated_span_id = current_tool.get("pre_allocated_span_id")

    # If an Agent/Task tool is still pending, this tool ran inside that agent
    # (inline subagent pattern). Parent it to the agent span, not the CHAIN root.
    active_agent_span_id = _find_active_agent_span_id(state, pending_key)
    span_record = _build_tool_span_record(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=start_ns,
        end_ns=end_ns,
        trace_id=current_trace["trace_id"],
        root_span_id=active_agent_span_id or current_trace["root_span_id"],
        span_id=pre_allocated_span_id,
    )

    # Export the tool span before acquiring the lock — this is the slow network
    # I/O and does not mutate state, so it is safe to run outside the lock.
    _build_and_export_spans(
        config=config,
        session_id=_phoenix_session_id(state),
        username=state.get("username", "unknown"),
        span_records=[span_record],
    )

    # Acquire an exclusive per-session lock before emitting LLM spans.
    # Parallel PostToolUse processes race on emitted_llm_span_count; the lock
    # ensures each process re-reads the latest count and never double-emits.
    # Resolve the transcript path *inside* the lock so we always use the path
    # that was cached in state at UserPromptSubmit time — not the (potentially
    # stale or redirected) path carried in the current hook payload.
    with _session_lock(session_id):
        state = _load_state(session_id)
        # Use the compound key resolved above; fall back to tool_name for
        # any other entry that might have been written with the old plain key.
        pt = state.get("pending_tools", {})
        pt.pop(pending_key, None)
        pt.pop(tool_name, None)
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(state, transcript_path, config)
        _save_state(session_id, state)


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

    state = _load_state(session_id)
    if not state:
        log.warning("No state found for session %s in post_tool_failure", session_id)
        return

    current_trace = state.get("current_trace")
    if not current_trace:
        log.debug("No current trace for session %s in post_tool_failure", session_id)
        return

    tool_name = data.get("tool_name", "unknown")
    data_tool_input = data.get("tool_input")
    current_tool, pending_key = _find_pending_tool_entry(
        state,
        tool_name,
        data_tool_input,
    )
    tool_input = data_tool_input or current_tool.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    start_ns = current_tool.get("start_ns", end_ns - 1_000_000)

    # Extract error message from various possible fields
    error_msg = ""
    if isinstance(tool_response, dict):
        error_msg = tool_response.get("error", tool_response.get("message", ""))
    elif isinstance(tool_response, str):
        error_msg = tool_response
    if not error_msg:
        error_msg = data.get("error", data.get("error_message", "Tool call failed"))

    active_agent_span_id = _find_active_agent_span_id(state, pending_key)
    span_record = _build_tool_span_record(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=start_ns,
        end_ns=end_ns,
        trace_id=current_trace["trace_id"],
        root_span_id=active_agent_span_id or current_trace["root_span_id"],
        is_failure=True,
        error_msg=error_msg,
    )

    _build_and_export_spans(
        config=config,
        session_id=_phoenix_session_id(state),
        username=state.get("username", "unknown"),
        span_records=[span_record],
    )

    with _session_lock(session_id):
        state = _load_state(session_id)
        pt = state.get("pending_tools", {})
        pt.pop(pending_key, None)
        pt.pop(tool_name, None)
        transcript_path = _get_cached_transcript_path(data, state, session_id)
        _emit_pending_llm_spans(state, transcript_path, config)
        _save_state(session_id, state)


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
        if not state.get("current_trace"):
            log.debug("No active trace for session %s at stop", session_id)
            return

        transcript_path = _get_cached_transcript_path(data, state, session_id)

        # Detect context continuation: same check as handle_pre_tool.
        # When no tool calls happen during a continuation turn, handle_pre_tool
        # never fires, so the stale trace would otherwise be completed with the
        # wrong LLM spans.  Complete the old trace here and start a new one so
        # the normal stop logic below runs against the correct turn.
        if transcript_path:
            ct = state["current_trace"]
            _cur_human = _count_human_messages(transcript_path)
            _start = ct.get("human_count_at_start", 0)
            if _cur_human > _start + 1:
                _emit_pending_llm_spans(state, transcript_path, config)
                _complete_turn(state, config, transcript_path, end_ns)
                state.pop("current_trace", None)
                state.pop("pending_tools", None)

                current_human_count = _cur_human
                prompt_preview = _get_latest_human_message(transcript_path)
                turn_number = state.get("turn_number", 0) + 1
                state["turn_number"] = turn_number
                state["human_msg_count"] = current_human_count
                state["current_trace"] = {
                    "trace_id": _new_trace_id(),
                    "root_span_id": _new_span_id(),
                    "turn_start_ns": end_ns,
                    "turn_number": turn_number,
                    "human_count_at_start": max(0, current_human_count - 1),
                    "prompt_preview": (_truncate(prompt_preview) if prompt_preview else ""),
                }

        # Emit the final LLM span(s) — the last response has no tool call after it,
        # so handle_post_tool never got the chance to emit it.
        _emit_pending_llm_spans(state, transcript_path, config)

        _complete_turn(state, config, transcript_path, end_ns)

        _delete_state(session_id)

    _cleanup_stale_states()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: claude_code_tracer.py <pre_tool|post_tool|post_tool_failure|user_prompt_submit|stop>",
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
        log.debug("Arthur Engine not configured, skipping tracing.")
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
        else:
            log.warning("Unknown event: %s", event)
    except Exception as e:
        log.warning("Tracer error (%s): %s", event, e, exc_info=True)
        raise

    sys.exit(0)


if __name__ == "__main__":
    main()
