#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for hearsay checking.

Enforces that an agent evaluates incoming subagent reports and peer messages
against logic-check doctrine before dispatching further subagents, contacting the
user, or finishing tasks:

- ``hearsay_arm``: a ``UserPromptSubmit`` / ``PostToolUse`` handler that arms
  the check when a report or direction arrives: a peer or worker message, or a
  foreground subagent's returned result. A spawn acknowledgement, any other of the
  agent's own tool results, a notice with no report in it, and the user's own
  messages never arm it.
- ``hearsay_handler``: a ``PreToolUse`` / ``Stop`` handler that refuses the
  agent's next subagent dispatch, communication, channel reply, or stop while armed.
- ``arm()`` / ``disarm()``: state management primitives. Calling ``disarm()``
  clears the check once a verdict is recorded.

Verdict recording and OpenTelemetry trace emission live in ``premise_check_verdict.py``.
"""

from __future__ import annotations

import fcntl
import hashlib
import html
import json
import logging
import os
import re
import shlex
import tempfile
import textwrap
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from dispatch import HookContext, Result, block, load_message_pair, refuse, warn

try:
    import claude_code_tracer
except ImportError:
    claude_code_tracer = None

log = logging.getLogger("aops.hearsay_gate")


def _now() -> str:
    """Current time as an ISO-8601 string carrying the local system UTC offset."""
    return datetime.now().astimezone().isoformat()


# Envelopes the harness wraps around a report or direction from another agent. Anything
# else arriving on UserPromptSubmit -- a channel message or a typed prompt -- is
# the user's own message, which is an ask, not a claim to check.
_PEER_ENVELOPES = (
    "<cross-session-message",
    "<teammate-message",
    "<task-notification",
    "<subagent-handback",
    "<agent-message",
)


# Tools that dispatch subagents
_DISPATCH_TOOLS = ["Agent", "Task", "invoke_subagent"]

# Tools that reach the user directly. Matched on the full name or the last
# ``__`` segment, case-insensitively.
_CHANNEL_REPLY_TOOLS = frozenset(
    name.lower()
    for name in (
        "AskUserQuestion",
        "AskQuestion",
        "ask_user_question",
        "ask_question",
        "ask_user",
        "reply",
        "telegram_reply",
        "telegram_send_message",
        "discord_reply",
        "discord_send_message",
    )
)

# Non-channel tools blocked while the check is armed
_GATED_TOOLS = frozenset(
    [
        *_DISPATCH_TOOLS,
        "SendMessage",
        "SubagentHandback",
        "Dump",
        "send_message",
        "subagent_handback",
        "dump",
    ]
)


def is_channel_reply_tool(tool_name: str) -> bool:
    """True when a tool sends a message to the user over a channel or prompt."""
    if not tool_name:
        return False
    tool_lower = tool_name.lower()
    if tool_lower in _CHANNEL_REPLY_TOOLS or tool_lower.split("__")[-1] in _CHANNEL_REPLY_TOOLS:
        return True
    return ("telegram" in tool_lower or "discord" in tool_lower) and (
        "reply" in tool_lower or "send" in tool_lower or "ask_user" in tool_lower
    )


def _is_blocked_tool(tool_name: str) -> bool:
    if not tool_name:
        return False
    tool_lower = tool_name.lower()
    last_seg_lower = tool_lower.split("__")[-1]
    gated_lower = {t.lower() for t in _GATED_TOOLS}
    if tool_lower in gated_lower or last_seg_lower in gated_lower:
        return True
    return is_channel_reply_tool(tool_name)


ID_PATTERN = re.compile(
    r"^(?P<kind>claim|verdict|report)-(?P<hash>[0-9a-f]{8})(?:-(?P<title>[a-z0-9]+(?:-[a-z0-9]+)*))?$"
)


def slugify_title(title: str | None) -> str:
    """Convert an arbitrary title string into a lowercase kebab-case slug."""
    if not title:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:40]


def build_id(kind: str, content: str, title: str | None = None) -> str:
    """Build a short id in the shared format: <kind>-<hash>[-<title>]."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
    slug = slugify_title(title)
    if slug:
        return f"{kind}-{digest}-{slug}"
    return f"{kind}-{digest}"


def is_valid_id(identifier: str) -> bool:
    """Return True if identifier conforms to the shared id format."""
    return bool(ID_PATTERN.match(identifier.strip()))


def parse_id(identifier: str) -> dict[str, str | None] | None:
    """Parse an id into its components: kind, hash, and optional title slug."""
    match = ID_PATTERN.match(identifier.strip())
    if not match:
        return None
    return match.groupdict()


def mint_verification_id(
    claim_id: str,
    verdict: str,
    reason: str,
    title: str | None = None,
) -> str:
    """Mint a verification id in the shared format referencing the verified content."""
    content = f"{claim_id}:{verdict}:{reason}"
    return build_id("verdict", content, title=title)


# ---------------------------------------------------------------------------
# State: is the hearsay check armed (awaiting verdict) or disarmed?
# ---------------------------------------------------------------------------


def _canonical_agent_id(session_id: str, agent_id: str | None = None) -> str:
    """Normalize recipient agent_id; empty, 'main', or matching session_id maps to root slot ''."""
    aid = str(agent_id or "").strip()
    if not aid or aid.lower() == "main" or (session_id and aid == session_id.strip()):
        return ""
    return aid


def _safe_token(value: str, fallback: str = "default") -> str:
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", value or fallback)


def _scope_suffix(session_id: str, agent_id: str | None = None) -> str:
    canon = _canonical_agent_id(session_id, agent_id)
    if not canon:
        return ""
    return f".agent-{_safe_token(canon, 'agent')}"


def _state_dir() -> Path:
    override = os.environ.get("AOPS_PREMISE_CHECK_DIR") or os.environ.get("AOPS_PREMISE_GATE_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_premise_check"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(session_id: str, agent_id: str | None = None) -> Path:
    safe_session = _safe_token(session_id, "default")
    suffix = _scope_suffix(session_id, agent_id)
    return _state_dir() / f"{safe_session}{suffix}.json"


def _parents_path(session_id: str) -> Path:
    safe_session = _safe_token(session_id, "default")
    return _state_dir() / f"{safe_session}.parents.json"


def _lock_path(session_id: str) -> Path:
    safe_session = _safe_token(session_id, "default")
    return _state_dir() / f"{safe_session}.lock"


@contextmanager
def _session_file_lock(session_id: str) -> Generator[None, None, None]:
    """Serialize read-modify-write state mutations for one session across concurrent hooks."""
    lock_file = _lock_path(session_id)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(data, indent=2))


def _load_state(session_id: str, agent_id: str | None = None) -> dict[str, Any]:
    target = _state_path(session_id, agent_id=agent_id)
    if target.exists():
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"corrupt gate state in {target}: expected JSON object")
        return data
    return {}


def _save_state(session_id: str, state: dict[str, Any], agent_id: str | None = None) -> None:
    canon_agent = _canonical_agent_id(session_id, agent_id)
    state["session_id"] = session_id
    state["agent_id"] = canon_agent
    _write_json_atomic(_state_path(session_id, agent_id=canon_agent), state)


def _load_parents(session_id: str) -> dict[str, Any]:
    path = _parents_path(session_id)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"corrupt parents metadata in {path}: expected JSON object")
        return data
    return {
        "session_id": session_id,
        "subagent_parents": {},
        "known_subagents": [],
        "known_subagent_names": {},
        "pending_spawns": {},
        "pending_spawn_names": {},
        "handbacks": {},
    }


def _save_parents(session_id: str, data: dict[str, Any]) -> None:
    data["session_id"] = session_id
    _write_json_atomic(_parents_path(session_id), data)


def clear_state(session_id: str, agent_id: str | None = None) -> None:
    """Reset hearsay check state for a session (or specific agent slot). Used by tests."""
    target = _state_path(session_id, agent_id=agent_id)
    target.unlink(missing_ok=True)


def get_state(session_id: str, agent_id: str | None = None) -> dict[str, Any]:
    return _load_state(session_id, agent_id=agent_id)


def _judged_path(session_id: str, claim_id: str, agent_id: str | None = None) -> Path:
    safe_session = _safe_token(session_id, "default")
    suffix = _scope_suffix(session_id, agent_id)
    safe_claim = _safe_token(claim_id, "claim")[:60]
    digest = hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:8]
    return _state_dir() / f"{safe_session}{suffix}.{safe_claim}-{digest}.judged.txt"


_DISARMED_HISTORY_LIMIT = 200
_HANDBACK_PREAMBLE = re.compile(r"^[ \t]*\[Subagent\s+hand-back\][^\n]*(?:\n|$)", re.IGNORECASE)
_HANDBACK_FOLLOWS_RE = re.compile(r"^[ \t]*The report follows:[ \t]*(?:\n|$)", re.IGNORECASE)
_HARNESS_PATTERN_BANNER_RE = re.compile(
    r"^[ \t]*\[harness:\s*subagent output matched[^\n]*(?:\n|$)", re.IGNORECASE
)


_OUTER_PEER_ENVELOPE_RE = re.compile(
    r"^\s*<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)\b[^>]*>(.*?)(?:</\1>\s*$|$)",
    re.DOTALL,
)

_HANDBACK_POINTER = re.compile(
    r"^(?:"
    r"(?:this|the)\s+(?:agent(?:'s)?\s+)?report was delivered to you as a message from\s+\S[^\n]*?\(its SubagentHandback call\)[^\n]*"
    r"|this agent has not reported yet:[^\n]*?\bSubagentHandback\b[^\n]*"
    r")$",
    re.IGNORECASE,
)


def _is_handback_pointer_text(text: str | None) -> bool:
    """True when text is a single-line SubagentHandback delivered/waiting pointer stub."""
    s = (text or "").strip()
    if not s or "\n" in s:
        return False
    return bool(_HANDBACK_POINTER.match(s))


def _unpack_teammate_idle_json(inner: str) -> tuple[bool, str]:
    """Return (is_idle_notification, extracted_result) for a teammate JSON payload."""
    stripped = inner.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return False, ""
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False, ""
    if not isinstance(parsed, dict) or parsed.get("type") != "idle_notification":
        return False, ""
    res = parsed.get("result")
    return True, res.strip() if isinstance(res, str) else ""


_NULL_CLAIM_BLOCK_RE = re.compile(
    r"(?:`{3,}|~{3,})\s*argdown[ \t]*\n"
    r"(?:\s*===[ \t]*\n\s*asks:\s*none[ \t]*\n\s*===[ \t]*\n+)?"
    r"\s*\[no\s+claim\][ \t]*\n+"
    r"\s*(?:`{3,}|~{3,})",
    re.IGNORECASE,
)
_NULL_CLAIM_LINE_RE = re.compile(r"^\s*\[no\s+claim\]\s*$", re.IGNORECASE)


def _normalize_peer_body(text: str | None) -> str:
    """Unwrap peer/handback transport framing before dedenting, un-neutralizing <\\, and trimming."""
    raw = html.unescape(text or "").replace("\r\n", "\n").replace("\r", "\n")
    channel_m = re.match(r"^\s*<channel\b[^>]*>(.*)</channel>\s*$", raw, re.DOTALL)
    unwrapped = channel_m.group(1).strip("\r\n") if channel_m else raw
    stripped_outer = _strip_peer_wrapper(raw)
    env_m = _OUTER_PEER_ENVELOPE_RE.match(stripped_outer)
    if env_m:
        tag = env_m.group(1)
        inner = env_m.group(2).strip("\r\n")
        if tag == "task-notification":
            res = extract_notification_result(inner)
            if res is not None:
                inner = res.strip("\r\n")
        elif tag == "teammate-message":
            is_idle, idle_res = _unpack_teammate_idle_json(inner)
            if is_idle:
                inner = idle_res
        norm = inner
    else:
        norm = unwrapped.strip("\r\n")

    norm, sub_count = _HANDBACK_PREAMBLE.subn("", norm, count=1)
    had_preamble = sub_count > 0
    if had_preamble:
        norm = _HANDBACK_FOLLOWS_RE.sub("", norm, count=1)
        norm = _HARNESS_PATTERN_BANNER_RE.sub("", norm, count=1)
        norm = re.sub(r"^(?:[ \t]*\n)+", "", norm)
    norm = textwrap.dedent(norm)
    if had_preamble:
        norm = norm.replace("<\\", "<")
    return norm.strip()


def _is_null_claim(text: str | None) -> bool:
    """True only when the entire unwrapped message body is the canonical [no claim] null form."""
    if not text or not text.strip():
        return False
    norm = _normalize_peer_body(text)
    if _NULL_CLAIM_BLOCK_RE.fullmatch(norm):
        return True
    return bool(_NULL_CLAIM_LINE_RE.fullmatch(norm))


def _normalized_body_hash(text: str) -> str:
    norm = _normalize_peer_body(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _arm_locked(
    session_id: str,
    claim_id: str | None = None,
    judged_text: str | None = None,
    judged_ref: str | None = None,
    agent_id: str | None = None,
    source_agent_id: str = "",
    caller_notified: bool | None = None,
    armed_via: str = "",
    seen_channel: str = "",
) -> None:
    """Locked core of arm(); caller must hold _session_file_lock(session_id)."""
    canon_agent = _canonical_agent_id(session_id, agent_id)
    state = _load_state(session_id, agent_id=canon_agent)
    cid = claim_id or state.get("claim_id") or "unnamed-claim"
    state["armed"] = True
    state["pending"] = True  # backward compat
    state["claim_id"] = cid
    claim_ids = state.get("claim_ids") or []
    if cid not in claim_ids:
        claim_ids.append(cid)
    state["claim_ids"] = claim_ids
    state["armed_at"] = _now()
    disarmed_map = state.get("disarmed_claims")
    if isinstance(disarmed_map, dict) and cid in disarmed_map:
        disarmed_map.pop(cid, None)
        state["disarmed_claims"] = disarmed_map
    if (
        judged_text is not None
        or judged_ref
        or source_agent_id
        or caller_notified is not None
        or armed_via
        or seen_channel
    ):
        judged = state.get("judged") or {}
        raw_prev = judged.get(cid)
        prev: dict[str, Any] = raw_prev if isinstance(raw_prev, dict) else {}
        entry: dict[str, Any] = {**prev, "ref": judged_ref or prev.get("ref") or cid}
        if source_agent_id:
            entry["source_agent_id"] = source_agent_id
        if caller_notified is not None:
            entry["caller_notified"] = caller_notified
        if armed_via:
            entry["armed_via"] = armed_via
        seen_channels = dict(prev.get("seen_channels") or {})
        if seen_channel:
            seen_channels[seen_channel] = True
        if seen_channels:
            entry["seen_channels"] = seen_channels
        seen_refs = list(prev.get("seen_refs") or [])
        if judged_ref and judged_ref != cid and judged_ref not in seen_refs:
            seen_refs.append(judged_ref)
        if seen_refs:
            entry["seen_refs"] = seen_refs
        if judged_text is not None:
            path = _judged_path(session_id, cid, agent_id=canon_agent)
            _write_text_atomic(path, judged_text)
            entry["file"] = path.name
            entry["body_sha256"] = _normalized_body_hash(judged_text)
        judged[cid] = entry
        state["judged"] = judged
    _save_state(session_id, state, agent_id=canon_agent)


def arm(
    session_id: str,
    claim_id: str | None = None,
    judged_text: str | None = None,
    judged_ref: str | None = None,
    agent_id: str | None = None,
    source_agent_id: str = "",
    caller_notified: bool | None = None,
    armed_via: str = "",
) -> None:
    """Arm the hearsay check for a session recipient slot until a verdict disarms it.

    ``judged_text`` is the report the verdict will judge; it is stored beside
    the state file so the recorder can verify integrity and hash it into telemetry.
    ``judged_ref`` names where that text came from: the tool-use id of a subagent
    result, the id of a peer envelope, or a task id.
    """
    with _session_file_lock(session_id):
        _arm_locked(
            session_id,
            claim_id=claim_id,
            judged_text=judged_text,
            judged_ref=judged_ref,
            agent_id=agent_id,
            source_agent_id=source_agent_id,
            caller_notified=caller_notified,
            armed_via=armed_via,
        )


def get_judged(
    session_id: str, claim_id: str, agent_id: str | None = None
) -> tuple[str | None, str | None]:
    """The judged text and its reference stored when ``claim_id`` armed the gate.

    (None, None) when the arm stored nothing; an entry naming a file that is
    gone raises FileNotFoundError.
    """
    entry = (_load_state(session_id, agent_id=agent_id).get("judged") or {}).get(claim_id)
    if not entry:
        return None, None
    text = None
    if entry.get("file"):
        text = (_state_dir() / entry["file"]).read_text(encoding="utf-8")
    return text, entry.get("ref")


def _disarm_locked(
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
    machine: bool = False,
    no_claim: bool = False,
    agent_id: str | None = None,
) -> None:
    """Locked core of disarm(); caller must hold _session_file_lock(session_id)."""
    canon_agent = _canonical_agent_id(session_id, agent_id)
    state = _load_state(session_id, agent_id=canon_agent)
    claim_ids = state.get("claim_ids") or []
    was_pending = claim_id in claim_ids
    if claim_id in claim_ids:
        claim_ids.remove(claim_id)
    state["claim_id"] = claim_id  # overwritten below if claims remain
    state["claim_ids"] = claim_ids
    judged = state.get("judged") or {}
    entry = judged.pop(claim_id, None)
    if entry and entry.get("file"):
        (_state_dir() / entry["file"]).unlink()
    state["judged"] = judged

    # Track gate-armed claims that have been disarmed (excludes unarmed out-of-band labels)
    if entry is not None or was_pending:
        disarmed = state.get("disarmed_claims") or {}
        rec: dict[str, Any] = {
            "verdict": verdict,
            "verification_id": verification_id,
            "disarmed_at": _now(),
        }
        if isinstance(entry, dict):
            if entry.get("body_sha256"):
                rec["body_sha256"] = entry["body_sha256"]
            if entry.get("source_agent_id"):
                rec["source_agent_id"] = entry["source_agent_id"]
            if entry.get("ref"):
                rec["ref"] = entry["ref"]
            if entry.get("seen_refs"):
                rec["seen_refs"] = list(entry["seen_refs"])
            if entry.get("seen_channels"):
                rec["seen_channels"] = dict(entry["seen_channels"])
        disarmed[claim_id] = rec
        while len(disarmed) > _DISARMED_HISTORY_LIMIT:
            oldest_key = next(iter(disarmed))
            disarmed.pop(oldest_key, None)
        state["disarmed_claims"] = disarmed

    if claim_ids:
        state["armed"] = True
        state["pending"] = True
        state["claim_id"] = claim_ids[-1]
    else:
        state["armed"] = False
        state["pending"] = False
        state["claim_id"] = claim_id

    last_verdict: dict[str, Any] = {
        "claim_id": claim_id,
        "verdict": verdict,
        "reason": reason,
        "recorded_at": _now(),
    }
    if verification_id:
        last_verdict["verification_id"] = verification_id
    if title:
        last_verdict["title"] = title
    if machine:
        last_verdict["machine"] = True
    if verdict == "no-claim" or no_claim:
        last_verdict["no_claim"] = True
    state["last_verdict"] = last_verdict
    _save_state(session_id, state, agent_id=canon_agent)


def disarm(
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
    machine: bool = False,
    no_claim: bool = False,
    agent_id: str | None = None,
) -> None:
    """Disarm the hearsay check after a verdict is recorded."""
    with _session_file_lock(session_id):
        _disarm_locked(
            session_id,
            claim_id=claim_id,
            verdict=verdict,
            reason=reason,
            verification_id=verification_id,
            title=title,
            machine=machine,
            no_claim=no_claim,
            agent_id=agent_id,
        )


def is_armed(session_id: str, agent_id: str | None = None) -> bool:
    """Return True if the hearsay check is armed (awaiting verdict)."""
    state = _load_state(session_id, agent_id=agent_id)
    return bool(state.get("armed") or state.get("pending"))


def is_disarmed(session_id: str, agent_id: str | None = None) -> bool:
    """Return True if the hearsay check is disarmed (cleared to proceed)."""
    return not is_armed(session_id, agent_id=agent_id)


def find_armed_owner(
    session_id: str, claim_id: str, exclude_agent: str | None = None
) -> str | None:
    """Return owner agent label ('main' or agent_id) if claim_id is armed in another slot of session_id."""
    if not session_id or not claim_id:
        return None
    canon_excluded = _canonical_agent_id(session_id, exclude_agent)
    safe_session = _safe_token(session_id, "default")
    state_dir = _state_dir()
    if not state_dir.is_dir():
        return None
    with _session_file_lock(session_id):
        candidates = [
            state_dir / f"{safe_session}.json",
            *state_dir.glob(f"{safe_session}.agent-*.json"),
        ]
        for sfile in candidates:
            if not sfile.is_file():
                continue
            data = json.loads(sfile.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"corrupt gate state in {sfile}: expected JSON object")
            if not (data.get("armed") or data.get("pending")):
                continue
            owner_agent = _canonical_agent_id(session_id, data.get("agent_id", ""))
            if owner_agent == canon_excluded:
                continue
            cids = data.get("claim_ids") or ([data["claim_id"]] if data.get("claim_id") else [])
            judged = data.get("judged") or {}
            if claim_id in cids or claim_id in judged:
                return owner_agent or "main"
    return None


# Aliases for terminology clarity:
# "open" = disarmed (free to proceed), "closed" = armed (blocking dispatch)
close_gate = arm
open_gate = disarm
is_gate_open = is_disarmed


_AGY_USER_REQUEST = re.compile(r"<USER_REQUEST>\s*(.*)\s*</USER_REQUEST>", re.DOTALL)


def _is_session_start_or_harness_injection(content: str) -> bool:
    """True if a SYSTEM_MESSAGE is a SessionStart hook message or harness banner, not an incoming turn message."""
    s = content.lower()
    return "injected by a sessionstart hook" in s or (
        "session:" in s and "host:" in s and "cwd:" in s
    )


def _agy_candidate_transcripts(ctx: HookContext) -> list[Path]:
    raw_path = ctx.transcript_path or ctx.raw.get("transcriptPath")
    candidates: list[Path] = []
    if raw_path:
        p = Path(raw_path)
        if p.is_file():
            candidates.append(p)
        parent = p.parent
        for alt_name in ("transcript.jsonl", "transcript_full.jsonl"):
            alt_path = parent / alt_name
            if alt_path.is_file() and alt_path not in candidates:
                candidates.append(alt_path)
    return candidates


def _read_all_agy_entries(ctx: HookContext) -> list[dict[str, Any]]:
    candidates = _agy_candidate_transcripts(ctx)
    if not candidates:
        return []
    entries_by_index: dict[int, dict[str, Any]] = {}
    fallback_entries: list[dict[str, Any]] = []

    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(entry, dict):
                        continue
                    step_idx = entry.get("step_index")
                    if isinstance(step_idx, int):
                        existing = entries_by_index.get(step_idx)
                        if existing is None:
                            entries_by_index[step_idx] = entry
                        else:
                            # Prefer entry with complete content if existing has truncated content
                            if "content" in existing.get("truncated_fields", []):
                                if "content" not in entry.get("truncated_fields", []):
                                    entries_by_index[step_idx] = entry
                    else:
                        fallback_entries.append(entry)
        except OSError:
            continue

    if entries_by_index:
        return [entries_by_index[idx] for idx in sorted(entries_by_index.keys())]
    return fallback_entries


def _agy_turn_start(ctx: HookContext) -> dict[str, Any] | None:
    inv = (ctx.raw or {}).get("invocationNum", 0)
    if inv is not None and inv != 0:
        return None
    entries = _read_all_agy_entries(ctx)
    if not entries:
        return None
    for entry in reversed(entries):
        entry_type = entry.get("type")
        if entry_type == "USER_INPUT":
            return entry
        if entry_type == "SYSTEM_MESSAGE":
            content = str(entry.get("content") or "")
            if _is_session_start_or_harness_injection(content):
                continue
            return entry
    return None


_AGY_MESSAGE = re.compile(
    r"\[Message\][^\n]*?\bsender=(\S+)[^\n]*?\bcontent=(.*?)\s*(?:</SYSTEM_MESSAGE>\s*)?$",
    re.DOTALL,
)


def agy_arrival(content: str) -> str:
    """The report or direction an agy SYSTEM_MESSAGE delivers, or "" when it delivers none.

    agy starts a SYSTEM_MESSAGE turn for every wake: the session's own command
    tasks and timers finishing (sender ``<conversation>/task-N``), system
    notices, stop-hook refusals, and messages from other agents. Only a message
    whose sender is another agent's conversation carries a report or direction.
    Automated harness notices (including sender=system idle notices) are
    non-claim lifecycle events and deliver none.
    """
    m = _AGY_MESSAGE.search(content)
    if not m:
        return ""
    sender, body = m.group(1), m.group(2).strip()
    if sender == "system" or "/" in sender:
        return ""
    return body


def _agy_user_prompt(ctx: HookContext) -> str:
    """The user's text for an agy turn, read from the turn's transcript."""
    turn_start = _agy_turn_start(ctx)
    if not turn_start:
        return ""
    if turn_start.get("type") == "USER_INPUT":
        content = str(turn_start.get("content") or "").strip()
        m = _AGY_USER_REQUEST.search(content)
        return (m.group(1) if m else content).strip()
    if turn_start.get("type") == "SYSTEM_MESSAGE":
        content = str(turn_start.get("content") or "").strip()
        arrival = agy_arrival(content)
        if arrival:
            return arrival
    return ""


def prompt_text(ctx: HookContext) -> str:
    """Extract prompt text canonically across Claude Code and agy."""
    prompt = ctx.raw.get("prompt")
    if prompt is None and hasattr(ctx, "prompt"):
        prompt = ctx.prompt
    if isinstance(prompt, dict):
        prompt = prompt.get("text") or prompt.get("content") or ""
    text = str(prompt or "").strip()
    if not text and ctx.client == "agy":
        text = _agy_user_prompt(ctx)
    return text


_prompt_text = prompt_text


def _strip_channel_wrapper(text: str) -> str:
    """Unwrap outer or leading <channel> envelope if present."""
    s = text.strip()
    m = re.match(r"^<channel\b[^>]*>(.*)</channel>$", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    m = re.match(r"^<channel\b[^>]*>.*?</channel>\s*(.*)$", s, re.DOTALL)
    if m and m.group(1):
        s = m.group(1).strip()
    return s


_PEER_PREAMBLE = re.compile(
    r"^(?:Another Claude session sent a message:\s*)+",
    re.IGNORECASE,
)


def _strip_peer_wrapper(text: str) -> str:
    """Unwrap channel envelopes and Claude Code teammate/peer preambles."""
    s = _strip_channel_wrapper(text).strip()
    m = _PEER_PREAMBLE.match(s)
    if m:
        s = s[m.end() :].strip()
    s = _strip_channel_wrapper(s).strip()
    return s


# A Claude projects coordinator receives a thread session's report as a harness wake:
# ``<wake reason="thread-activity">`` wrapping the triggering ``<message from="agent">``.
# Human, system and quiet wakes carry no agent message and never match.
_THREAD_WAKE_RE = re.compile(r"^<wake\b[^>]*\breason=[\"']thread-activity[\"']")
_WAKE_MESSAGE_RE = re.compile(r"<message\b([^>]*)>(.*?)</message>", re.DOTALL)


def thread_reports(text: str) -> list[tuple[str, str]]:
    """Return (attrs, body) for each triggering agent message in a thread-activity wake."""
    s = _strip_peer_wrapper(text or "").lstrip()
    if not _THREAD_WAKE_RE.match(s):
        return []
    items: list[tuple[str, str]] = []
    for m in _WAKE_MESSAGE_RE.finditer(s):
        attrs = m.group(1)
        if re.search(r'\bfrom=["\']agent["\']', attrs) and re.search(
            r'\btrigger=["\']true["\']', attrs
        ):
            body = html.unescape(m.group(2)).strip()
            if body:
                items.append((attrs, body))
    return items


def is_peer_report(ctx: HookContext) -> bool:
    """True when an incoming prompt is another agent's report or direction, not the user's message."""
    if ctx.client == "agy":
        turn_start = _agy_turn_start(ctx)
        if turn_start and turn_start.get("type") == "SYSTEM_MESSAGE":
            return bool(agy_arrival(str(turn_start.get("content") or "")))
    raw = _prompt_text(ctx)
    text = _strip_peer_wrapper(raw).lstrip()
    if not text:
        return False
    return text.startswith(_PEER_ENVELOPES) or bool(thread_reports(text))


def is_foreground_dispatch(ctx: HookContext) -> bool:
    """True when a PostToolUse event returns a foreground subagent's result."""
    if ctx.event != "PostToolUse" or ctx.tool not in _DISPATCH_TOOLS:
        return False
    if ctx.client == "agy":
        return False
    response = _tool_response(ctx)
    return isinstance(response, dict) and response.get("status") == "completed"


def _hooks_base(hooks_dir: Path | None = None) -> Path:
    if hooks_dir:
        resolved_hooks = hooks_dir.resolve()
        if (
            resolved_hooks.parent / "skills" / "premise-check" / "scripts" / "verdict.py"
        ).is_file() or (resolved_hooks / "premise_check_verdict.py").is_file():
            return resolved_hooks
        if resolved_hooks.is_dir() and resolved_hooks.name == "hooks":
            return resolved_hooks
        if hooks_dir.is_absolute():
            return resolved_hooks
        cand = (Path.cwd() / hooks_dir).resolve()
        if (cand.parent / "skills" / "premise-check" / "scripts" / "verdict.py").is_file() or (
            cand / "premise_check_verdict.py"
        ).is_file():
            return cand
        if cand.is_dir() and cand.name == "hooks":
            return cand
    cwd = Path.cwd().resolve()
    if (cwd / "skills" / "premise-check" / "scripts" / "verdict.py").is_file():
        return cwd / "hooks"
    if (cwd / "premise_check_verdict.py").is_file():
        return cwd
    return Path(__file__).resolve().parent


def resolve_verdict_script(hooks_dir: Path | None = None) -> Path:
    base = _hooks_base(hooks_dir)
    plugin_dir = base.parent if base.name == "hooks" else base
    skill_script = (plugin_dir / "skills" / "premise-check" / "scripts" / "verdict.py").resolve()
    if skill_script.is_file():
        return skill_script
    hook_script = (base / "premise_check_verdict.py").resolve()
    if hook_script.is_file():
        return hook_script
    direct_skill = (base / "scripts" / "verdict.py").resolve()
    if direct_skill.is_file():
        return direct_skill
    return skill_script


def resolve_plugin_project_dir(script_path: Path) -> Path:
    """Resolve the real plugin project root directory (with pyproject.toml) for script_path."""
    resolved = script_path.resolve()
    for parent in resolved.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    if resolved.parent.name == "hooks":
        return resolved.parent.parent
    if len(resolved.parents) >= 3 and resolved.parents[1].name == "skills":
        return resolved.parents[2]
    return resolved.parent


def format_verdict_command(
    claim_id: str,
    hooks_dir: Path | None = None,
    session_id: str = "",
    verdict: str = "<PASS|REVISE|FAIL>",
    reason: str | None = None,
    agent_id: str | None = None,
) -> str:
    script_path = resolve_verdict_script(hooks_dir).resolve()
    plugin_dir = resolve_plugin_project_dir(script_path).resolve()
    quoted_project = shlex.quote(str(plugin_dir))
    quoted_script = shlex.quote(str(script_path))
    quoted_claim = shlex.quote(claim_id)
    cmd = (
        f"uv run --project {quoted_project} python {quoted_script}"
        f" --claim {quoted_claim} --verdict {verdict}"
    )
    if reason is not None:
        cmd += f" --reason {shlex.quote(reason)}"
    else:
        cmd += " --reason-file <path>"
    eff_session = session_id or os.environ.get("AOPS_SESSION_ID") or ""
    if eff_session:
        cmd += f" --session {shlex.quote(eff_session)}"
    canon_agent = _canonical_agent_id(eff_session, agent_id)
    if canon_agent:
        cmd += f" --agent {shlex.quote(canon_agent)}"
    return cmd


def _claim_id_from_envelope(envelope_text: str, attrs: str) -> str:
    id_match = re.search(
        r'\b(?:id|report_id|claim_id|verification_id|task_id)=["\']([^"\']+)["\']',
        attrs,
    )
    if id_match:
        cid = id_match.group(1).strip()
        if cid and re.match(r"^[a-zA-Z0-9_\-\.:@]+$", cid):
            return cid

    title_match = re.search(
        r'\b(?:title|short_title|slug)=["\']([^"\']+)["\']',
        attrs,
    )
    title = title_match.group(1).strip() if title_match else None
    return build_id("claim", envelope_text, title=title)


def _derive_claim_id(ctx: HookContext) -> str:
    if ctx.event == "PostToolUse":
        for call in ctx.tool_calls:
            if call.get("tool_name") in _DISPATCH_TOOLS:
                tool_input = call.get("tool_input") or {}
                desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
                if desc:
                    return desc[:80]
                call_id = call.get("tool_use_id") or ""
                if call_id:
                    return str(call_id)

        if ctx.tool in _DISPATCH_TOOLS:
            tool_input = ctx.raw.get("tool_input") or ctx.raw.get("toolInput") or {}
            if isinstance(tool_input, dict):
                desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
                if desc:
                    return desc[:80]
            call_id = (
                ctx.raw.get("tool_call_id") or ctx.raw.get("id") or ctx.raw.get("tool_use_id") or ""
            )
            if call_id:
                return str(call_id)
        raise RuntimeError("Dispatch tool call lacks identifier and description metadata")

    if ctx.event == "UserPromptSubmit":
        prompt = _strip_peer_wrapper(_prompt_text(ctx)).strip()
        if not prompt and ctx.client == "agy":
            turn_start = _agy_turn_start(ctx)
            if turn_start:
                prompt = str(turn_start.get("content") or "").strip()
        envelopes = _split_peer_envelopes(prompt)
        if envelopes:
            raw_env, _tag, attrs, _inner = envelopes[0]
            return _claim_id_from_envelope(raw_env, attrs)
        match = re.match(
            r"<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)([^>]*)>(.*?)(?:</\1>|$)",
            prompt,
            re.DOTALL,
        )
        if match:
            return _claim_id_from_envelope(prompt, match.group(2))

        if prompt:
            return build_id("claim", prompt)
        return build_id("claim", uuid.uuid4().hex)

    raise RuntimeError(f"Cannot derive claim_id for event {ctx.event}")


_OVERRIDE_VARS = (
    "PREMISE_CHECK_OVERRIDE",
    "PREMISE_CHECK_GATE_OVERRIDE",
    "AOP_FORCE",
    "AOP_OVERRIDE",
)


def _active_override() -> str | None:
    """The first override variable set truthy, or None."""
    for var in _OVERRIDE_VARS:
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return var
    return None


def _is_override_active() -> bool:
    return _active_override() is not None


def _count_override(ctx: HookContext, variable: str) -> None:
    """Count an override that let an armed gate pass a blocked action."""
    import premise_check_verdict as pcv

    canon_agent = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    with _session_file_lock(ctx.session_id):
        state = _load_state(ctx.session_id, agent_id=canon_agent)
        count = int(state.get("override_count") or 0) + 1
        pcv.emit_override_span(
            pcv._import_claude_code_tracer(),
            ctx.session_id,
            str(state.get("claim_id") or ""),
            ctx.tool or "",
            ctx.event,
            variable,
            count,
        )
        state["override_count"] = count
        _save_state(ctx.session_id, state, agent_id=canon_agent)


# ---------------------------------------------------------------------------
# What arrived: the judged text and its reference
# ---------------------------------------------------------------------------

_TASK_READ_TOOL = "get_task"
_REPORT_HEADING = re.compile(r"^##\s+Report\s*$", re.MULTILINE)
_VERDICT_HEADING = re.compile(r"^##\s+Premise-Check Verdict\s*$", re.MULTILINE)


def is_task_read_tool(tool_name: str) -> bool:
    """True for the PKB task-read tool under any MCP server prefix."""
    if not tool_name:
        return False
    if tool_name.split("__")[-1] == _TASK_READ_TOOL:
        return True
    return tool_name == _TASK_READ_TOOL or tool_name.endswith(
        (f"_{_TASK_READ_TOOL}", f".{_TASK_READ_TOOL}")
    )


def _tool_input(ctx: HookContext) -> dict[str, Any]:
    tool_input = ctx.raw.get("tool_input") or ctx.raw.get("toolInput") or {}
    return tool_input if isinstance(tool_input, dict) else {}


def _tool_response(ctx: HookContext) -> Any:
    return ctx.raw.get("tool_response", ctx.raw.get("toolResponse"))


def _response_text(value: Any) -> str:
    """Plain text of a tool response: a string, content blocks, or a result mapping.

    Completion metadata dicts lacking report body keys (content, text, result,
    output) return '' rather than serializing metadata JSON as a prose report.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(t for t in (_response_text(v) for v in value) if t)
    if isinstance(value, dict):
        for key in ("content", "text", "result", "output"):
            if key in value:
                return _response_text(value[key])
        return ""
    return ""


def _task_record(value: Any) -> dict[str, Any] | None:
    """The task mapping (one with a ``body``) inside a task-read response."""
    if isinstance(value, dict):
        if isinstance(value.get("body"), str):
            return value
        for key in ("structuredContent", "result", "task", "content", "text"):
            if key in value:
                found = _task_record(value[key])
                if found:
                    return found
        return None
    if isinstance(value, list):
        for item in value:
            found = _task_record(item)
            if found:
                return found
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {"body": value}
        return _task_record(parsed) if isinstance(parsed, (dict, list)) else None
    return None


def unverdicted_task_report(ctx: HookContext) -> tuple[str, str] | None:
    """(task id, body) when a PKB task read returned a report with no verdict section."""
    if ctx.event != "PostToolUse" or not is_task_read_tool(ctx.tool):
        return None
    record = _task_record(_tool_response(ctx))
    if not record:
        return None
    body = record["body"]
    if not _REPORT_HEADING.search(body) or _VERDICT_HEADING.search(body):
        return None
    tool_input = _tool_input(ctx)
    task_id = str(record.get("id") or tool_input.get("id") or tool_input.get("task_id") or "")
    if not task_id:
        return None
    return task_id, body


def _tool_use_id(ctx: HookContext) -> str:
    return str(ctx.raw.get("tool_use_id") or ctx.raw.get("tool_call_id") or ctx.raw.get("id") or "")


def _envelope_id(prompt: str) -> str | None:
    stripped = _strip_peer_wrapper(prompt)
    match = re.search(r"<([a-zA-Z0-9_\-]+)([^>]*)>", stripped)
    if not match:
        return None
    id_match = re.search(
        r'\b(?:id|report_id|claim_id|verification_id|task_id)=["\']([^"\']+)["\']',
        match.group(2),
    )
    if id_match:
        cid = id_match.group(1).strip()
        if cid and re.match(r"^[a-zA-Z0-9_\-\.:@]+$", cid):
            return cid
    return None


def _find_code_fence_intervals(text: str) -> list[tuple[int, int]]:
    """Return [start, end) character offsets of code fences in text."""
    intervals = []
    fence_pattern = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$", re.MULTILINE)
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_start = 0
    for match in fence_pattern.finditer(text):
        char = match.group(2)[0]
        length = len(match.group(2))
        if not in_fence:
            in_fence = True
            fence_char = char
            fence_len = length
            fence_start = match.start()
        else:
            if char == fence_char and length >= fence_len:
                in_fence = False
                fence_end = match.start() + len(match.group(1)) + length
                intervals.append((fence_start, fence_end))
    if in_fence:
        intervals.append((fence_start, len(text)))
    return intervals


def extract_notification_result(text: str) -> str | None:
    """Extract content from <result>...</result> ignoring tags inside code fences."""
    intervals = _find_code_fence_intervals(text)

    def is_inside(pos: int) -> bool:
        return any(start <= pos < end for start, end in intervals)

    open_match = None
    for m in re.finditer(r"<result\b[^>]*>", text):
        if not is_inside(m.start()):
            open_match = m
            break
    if not open_match:
        return None

    for m in re.finditer(r"</result>", text):
        if m.start() >= open_match.end() and not is_inside(m.start()):
            return text[open_match.end() : m.start()]
    return None


_NOTIFICATION_RESULT = re.compile(r"<result>(.*?)</result>", re.DOTALL)


def _is_dispatch_pointer_only(resp: Any) -> bool:
    """True when an Agent/Task completion response points to an out-of-band SubagentHandback message."""
    if not isinstance(resp, dict):
        return False
    text = _response_text(resp)
    if _is_handback_pointer_text(text):
        return True
    return resp.get("handback") == "send" and not text.strip()


def _should_bridge_foreground_dispatch(caller_id: str, resp: Any) -> bool:
    """True when foreground PostToolUse/PostToolBatch should bridge a silent/handback child report."""
    if not (isinstance(resp, dict) and resp.get("status") == "completed"):
        return False
    if _is_dispatch_pointer_only(resp):
        return bool(caller_id)
    return not _response_text(resp).strip()


def carries_report(text: str) -> bool:
    """False when an arrival only announces, idles, or points at a report.

    A task notification carries a report in its ``<result>``; one without (a
    background command finishing) carries none. Hand-back delivered/waiting pointer
    notices and resultless teammate ``idle_notification`` JSON payloads arm nothing.
    """
    body = _strip_peer_wrapper(text).lstrip()
    if not body or _is_handback_pointer_text(body):
        return False
    if body.startswith("<task-notification"):
        result = extract_notification_result(body)
        if not result or not result.strip():
            return False
        if _is_handback_pointer_text(result):
            return False
    elif body.startswith("<teammate-message"):
        env_m = _OUTER_PEER_ENVELOPE_RE.match(body)
        if env_m:
            is_idle, idle_res = _unpack_teammate_idle_json(env_m.group(2))
            if is_idle and (not idle_res or _is_handback_pointer_text(idle_res)):
                return False
    return True


_PEER_TAG_NAMES = (
    "cross-session-message",
    "teammate-message",
    "task-notification",
    "subagent-handback",
    "agent-message",
)
_PEER_OPEN_RE = re.compile(
    r"<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)\b([^>]*)>"
)


def _split_peer_envelopes(stripped: str) -> list[tuple[str, str, str, str]]:
    """Return sequential top-level (envelope_text, tag, attrs, inner) items skipping fenced code."""
    text = stripped.strip()
    if not text:
        return []
    intervals = _find_code_fence_intervals(text)

    def _in_fence(pos: int) -> bool:
        return any(start <= pos < end for start, end in intervals)

    envelopes: list[tuple[str, str, str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        open_m = _PEER_OPEN_RE.search(text, pos)
        while open_m and _in_fence(open_m.start()):
            open_m = _PEER_OPEN_RE.search(text, open_m.end())
        if not open_m:
            break
        tag = open_m.group(1)
        attrs = open_m.group(2)
        inner_start = open_m.end()
        tag_token_re = re.compile(rf"<(/?){re.escape(tag)}\b([^>]*)>")
        depth = 1
        close_start: int | None = None
        close_end: int | None = None
        for tok in tag_token_re.finditer(text, inner_start):
            if _in_fence(tok.start()):
                continue
            if tok.group(1) == "/":
                depth -= 1
                if depth == 0:
                    close_start = tok.start()
                    close_end = tok.end()
                    break
            else:
                depth += 1
        if close_end is not None and close_start is not None:
            env_text = text[open_m.start() : close_end]
            inner = text[inner_start:close_start]
            pos = close_end
        else:
            env_text = text[open_m.start() :]
            inner = text[inner_start:]
            pos = n
        envelopes.append((env_text, tag, attrs, inner))
    return envelopes


def _unpack_envelope(env_text: str, tag: str, attrs: str, inner: str) -> tuple[str, str]:
    """Return (judged_text, sender_id) for one parsed peer envelope."""
    sender_m = re.search(r'\b(?:from|teammate_id|sender)=["\']([^"\']+)["\']', attrs)
    sender_id = sender_m.group(1).strip() if sender_m else ""
    if tag == "teammate-message":
        is_idle, idle_res = _unpack_teammate_idle_json(inner)
        if is_idle:
            return idle_res, sender_id
    elif tag == "task-notification":
        if not sender_id:
            tid_m = re.search(r"<task-id>([^<]+)</task-id>", inner)
            if tid_m:
                sender_id = tid_m.group(1).strip()
        result_match = extract_notification_result(inner)
        if result_match is not None:
            return result_match.strip(), sender_id
    return inner.strip("\r\n") if len(inner.strip()) and tag in (
        "agent-message",
        "subagent-handback",
    ) else env_text, sender_id


def _extract_judged_text(prompt: str) -> str:
    """Extract report content from an incoming peer prompt.

    For an idle_notification JSON inside a <teammate-message> envelope,
    the teammate's final report is the JSON `result` string; returning that
    unpacks the unescaped markdown (including any fenced argdown blocks).
    For other peer messages, returns the prompt text.
    """
    stripped = _strip_peer_wrapper(prompt)
    match = re.search(
        r"<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)([^>]*)>(.*?)(?:</\1>|$)",
        stripped,
        re.DOTALL,
    )
    if match:
        tag = match.group(1)
        if tag == "teammate-message":
            is_idle, idle_res = _unpack_teammate_idle_json(match.group(3))
            if is_idle:
                return idle_res
        elif tag == "task-notification":
            inner = match.group(3)
            result_match = extract_notification_result(inner)
            if result_match is not None:
                return result_match.strip()
    return prompt


def _allocate_non_colliding_claim_id(
    base_id: str,
    judged_ref: str,
    body_sha256: str,
    active_judged: dict[str, Any],
    disarmed_claims: dict[str, Any],
    batch_used: set[str],
) -> tuple[str, bool]:
    """Return (claim_id, already_armed_same_item) avoiding overwrites on distinct active or disarmed items."""
    for existing_cid, entry in active_judged.items():
        if not isinstance(entry, dict):
            continue
        if (
            judged_ref
            and entry.get("ref") == judged_ref
            and entry.get("body_sha256") == body_sha256
        ):
            return existing_cid, True
    reserved = set(active_judged) | set(disarmed_claims) | batch_used
    cand = base_id
    if (
        (cand in active_judged and active_judged[cand].get("ref") != judged_ref)
        or cand in disarmed_claims
        or cand in batch_used
    ):
        short_tag = hashlib.sha256(f"{judged_ref}:{body_sha256}".encode()).hexdigest()[:6]
        cand = f"{base_id[:68]} [{short_tag}]"
        idx = 2
        while cand in reserved:
            cand = f"{base_id[:62]} [{short_tag}-{idx}]"
            idx += 1
    batch_used.add(cand)
    return cand, False


def _call_description_id(tool_input: Any, call_id: str) -> str:
    if isinstance(tool_input, dict):
        desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
        if desc:
            return desc[:80]
    return str(call_id or "")[:80]


class IncomingItem(NamedTuple):
    """One delivered report candidate awaiting arming or dedup against a recipient slot."""

    judged_text: str
    judged_ref: str
    base_cid: str
    sender: str
    channel: str


def _extract_judged_items_with_channel(ctx: HookContext) -> list[IncomingItem]:
    """Extract (judged_text, judged_ref, base_claim_id, sender_id, channel) candidates."""
    if ctx.event == "UserPromptSubmit":
        if not is_peer_report(ctx):
            return []
        text = _prompt_text(ctx)
        if not text and ctx.client == "agy":
            turn_start = _agy_turn_start(ctx)
            if turn_start:
                text = agy_arrival(str(turn_start.get("content") or ""))
        threads = thread_reports(text)
        if threads:
            items: list[IncomingItem] = []
            for attrs, body in threads:
                if not carries_report(body):
                    continue
                sender_m = re.search(r'\bauthor-id=["\']([^"\']+)["\']', attrs)
                id_m = re.search(r'(?<![\w-])id=["\']([A-Za-z0-9_\-.:@]+)["\']', attrs)
                cid = id_m.group(1) if id_m else build_id("claim", body)
                items.append(
                    IncomingItem(
                        body, cid, cid, sender_m.group(1) if sender_m else "", "user_prompt"
                    )
                )
            return items
        stripped = _strip_peer_wrapper(text).strip()
        envelopes = _split_peer_envelopes(stripped)
        if not envelopes:
            judged_text = _extract_judged_text(text)
            if not carries_report(judged_text):
                return []
            cid = _derive_claim_id(ctx)
            ref = _envelope_id(text.strip()) or cid
            return [IncomingItem(judged_text, ref, cid, "", "user_prompt")]

        items = []
        for env_text, tag, attrs, inner in envelopes:
            judged_text, sender_id = _unpack_envelope(env_text, tag, attrs, inner)
            if (
                not carries_report(env_text)
                if tag in ("task-notification", "teammate-message")
                else not carries_report(judged_text)
            ):
                continue
            # Keep single-envelope legacy text identical when unpacked inner text lacked argdown/wrapper cues
            if len(envelopes) == 1 and tag in (
                "cross-session-message",
                "agent-message",
                "subagent-handback",
            ):
                judged_text = _extract_judged_text(text)
            cid = _claim_id_from_envelope(env_text, attrs)
            ref = _envelope_id(env_text) or cid
            channel = "task_notification" if tag == "task-notification" else "user_prompt"
            items.append(IncomingItem(judged_text, ref, cid, sender_id, channel))
        return items

    if ctx.event == "PostToolUse":
        if not is_foreground_dispatch(ctx):
            return []
        resp = _tool_response(ctx)
        if _is_dispatch_pointer_only(resp):
            return []
        judged_text = _response_text(resp)
        if not judged_text.strip() or not carries_report(judged_text):
            return []
        call_id = _tool_use_id(ctx)
        ti_dict = _tool_input(ctx)
        sender_id = (
            str(resp.get("agentId") or resp.get("agent_id") or ti_dict.get("name") or "").strip()
            if isinstance(resp, dict)
            else str(ti_dict.get("name") or "").strip()
        )
        base_cid = _call_description_id(ti_dict, call_id) or _derive_claim_id(ctx)
        ref = call_id or base_cid
        return [IncomingItem(judged_text, ref, base_cid, sender_id, "agent_result")]

    if ctx.event == "PostToolBatch":
        if ctx.client == "agy":
            return []
        batch_items: list[IncomingItem] = []
        for call in ctx.tool_calls:
            if call.get("tool_name") not in _DISPATCH_TOOLS:
                continue
            resp = call.get("tool_response") or call.get("toolResponse")
            if not (isinstance(resp, dict) and resp.get("status") == "completed"):
                continue
            if _is_dispatch_pointer_only(resp):
                continue
            judged_text = _response_text(resp)
            if not judged_text.strip() or not carries_report(judged_text):
                continue
            call_id = str(call.get("tool_use_id") or call.get("id") or "")
            raw_ti = call.get("tool_input") or call.get("toolInput") or {}
            ti_dict = raw_ti if isinstance(raw_ti, dict) else {}
            base_cid = _call_description_id(ti_dict, call_id)
            ref = call_id or base_cid
            sender_id = str(
                resp.get("agentId") or resp.get("agent_id") or ti_dict.get("name") or ""
            ).strip()
            batch_items.append(IncomingItem(judged_text, ref, base_cid, sender_id, "agent_result"))
        return batch_items

    return []


def extract_judged_contents(ctx: HookContext) -> list[tuple[str, str, str, str]]:
    """Extract all (judged_text, judged_ref, base_claim_id, sender_id) hearsay candidates."""
    return [item[:4] for item in _extract_judged_items_with_channel(ctx)]


def extract_judged_content(ctx: HookContext) -> tuple[str, str] | None:
    """Extract first non-null (or first null fallback) (judged_text, judged_ref) candidate."""
    items = extract_judged_contents(ctx)
    if not items:
        return None
    fallback: tuple[str, str] | None = None
    for judged_text, judged_ref, _cid, _sender in items:
        if _is_null_claim(judged_text):
            if fallback is None:
                fallback = (judged_text, judged_ref)
            continue
        return judged_text, judged_ref
    return fallback


def _resolve_sender_id(parents: dict[str, Any], raw_sender: str) -> str:
    """Resolve raw sender name or id through subagent name mappings when available."""
    sender = str(raw_sender or "").strip()
    if not sender:
        return ""
    names_map = parents.get("known_subagent_names") or {}
    mapped = names_map.get(sender)
    if mapped:
        return str(mapped).strip()
    if "@" in sender:
        bare = sender.split("@", 1)[0].strip()
        if bare and bare in names_map:
            return str(names_map[bare]).strip()
    return sender


def _is_failed_tool_response(ctx: HookContext | None, resp: Any) -> bool:
    """True when a tool_response (or raw hook event) signals failed execution."""
    if ctx is not None and bool(ctx.raw.get("is_error") or ctx.raw.get("isError")):
        return True
    if isinstance(resp, dict):
        if resp.get("success") is False or bool(resp.get("is_error")) or bool(resp.get("isError")):
            return True
    return False


def _find_channel_match(
    entries: dict[str, Any],
    *,
    body_sha256: str,
    canon_sender: str,
    judged_ref: str,
    base_cid: str,
    channel: str,
    parents: dict[str, Any],
    require_active: bool = False,
) -> tuple[str, dict[str, Any]] | None:
    """Match an active or un-superseded disarmed claim for a delivery channel pair.

    A delivery pairs with an entry carrying the same normalized digest when any holds:
    the delivery reference was already seen on that entry; the canonical senders agree;
    or a senderless foreground ``agent_result`` and a named envelope/handback copy meet
    symmetrically (at most once per channel pair).
    """
    has_unique_ref = bool(judged_ref and judged_ref != base_cid)
    for cid, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        if not require_active and entry.get("superseded"):
            continue
        if entry.get("body_sha256") != body_sha256:
            continue
        esender = _resolve_sender_id(parents, str(entry.get("source_agent_id") or ""))
        seen_refs = entry.get("seen_refs") or (
            [entry["ref"]] if entry.get("ref") and entry.get("ref") != cid else []
        )
        seen_channels = entry.get("seen_channels") or {}
        unique_ref_match = bool(has_unique_ref and judged_ref in seen_refs)
        sender_match = bool(esender and canon_sender and esender == canon_sender)
        senderless_to_named_match = bool(
            channel in ("user_prompt", "task_notification", "post_tool_use")
            and canon_sender
            and not esender
            and seen_channels.get("agent_result")
            and not seen_channels.get(channel)
        )
        named_to_senderless_match = bool(
            channel == "agent_result"
            and not canon_sender
            and esender
            and not seen_channels.get("agent_result")
        )
        if (
            unique_ref_match
            or sender_match
            or senderless_to_named_match
            or named_to_senderless_match
        ):
            return cid, entry
    return None


def _iter_dispatch_calls(ctx: HookContext) -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    """Collect (tool_input, tool_response, tool_use_id) for non-failed dispatch tool events."""
    raw_calls: list[tuple[Any, Any, str, HookContext | None]] = []
    if ctx.event == "PostToolUse" and ctx.tool in _DISPATCH_TOOLS:
        raw_calls.append((_tool_input(ctx), _tool_response(ctx), _tool_use_id(ctx), ctx))
    elif ctx.event == "PostToolBatch" and ctx.client != "agy":
        for c in ctx.tool_calls:
            if isinstance(c, dict) and c.get("tool_name") in _DISPATCH_TOOLS:
                raw_calls.append(
                    (
                        c.get("tool_input") or c.get("toolInput") or {},
                        c.get("tool_response") or c.get("toolResponse") or {},
                        str(c.get("tool_use_id") or c.get("id") or ""),
                        None,
                    )
                )
    out: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for ti, tr, tuid, call_ctx in raw_calls:
        if _is_failed_tool_response(call_ctx, tr):
            continue
        out.append((ti if isinstance(ti, dict) else {}, tr if isinstance(tr, dict) else {}, tuid))
    return out


def _in_flight_resume_ids(ctx: HookContext) -> set[str]:
    """Collect resumed subagent IDs from non-failed dispatch calls in PostToolUse/PostToolBatch."""
    resumed: set[str] = set()
    for ti_dict, tr_dict, _tuid in _iter_dispatch_calls(ctx):
        rid = str(
            ti_dict.get("resume")
            or tr_dict.get("resumedAgentId")
            or tr_dict.get("revivedAgentId")
            or ""
        ).strip()
        if rid:
            resumed.add(rid)
    return resumed


def _with_inflight_aliases(ctx: HookContext, parents: dict[str, Any]) -> dict[str, Any]:
    """Return parents with in-flight dispatch name/teammate_id aliases overlaid in memory."""
    dispatch_calls = _iter_dispatch_calls(ctx)
    if not dispatch_calls:
        return parents
    names_map = dict(parents.get("known_subagent_names") or {})
    pending_names = parents.get("pending_spawn_names") or {}
    changed = False
    for ti_dict, tr_dict, tuid in dispatch_calls:
        child_id = str(tr_dict.get("agentId") or tr_dict.get("agent_id") or "").strip()
        if not child_id:
            continue
        aliases = (
            pending_names.get(tuid, ""),
            ti_dict.get("name", ""),
            tr_dict.get("name", ""),
            tr_dict.get("teammate_id", ""),
        )
        for raw_alias in aliases:
            alias = str(raw_alias or "").strip()
            if not alias:
                continue
            names_map[alias] = child_id
            changed = True
            if "@" in alias:
                bare = alias.split("@", 1)[0].strip()
                if bare and bare not in names_map:
                    names_map[bare] = child_id
    if not changed:
        return parents
    return {**parents, "known_subagent_names": names_map}


def should_arm_hearsay(ctx: HookContext) -> bool:
    """Shared trigger predicate: True when an incoming event should fire hearsay notice/arming."""
    items = _extract_judged_items_with_channel(ctx)
    parents: dict[str, Any] = {}
    slot_judged: dict[str, Any] = {}
    slot_disarmed: dict[str, Any] = {}
    if ctx.session_id and (items or (ctx.event == "PostToolBatch" and ctx.client != "agy")):
        canon_agent = _canonical_agent_id(ctx.session_id, ctx.agent_id)
        parents = _with_inflight_aliases(ctx, _load_parents(ctx.session_id))
        slot_state = _load_state(ctx.session_id, agent_id=canon_agent)
        slot_judged = slot_state.get("judged") or {}
        slot_disarmed = slot_state.get("disarmed_claims") or {}
    in_flight_resumes = _in_flight_resume_ids(ctx)

    for judged_text, judged_ref, base_cid, raw_sender, channel in items:
        if _is_null_claim(judged_text):
            continue
        if not ctx.session_id:
            return True
        body_sha = _normalized_body_hash(judged_text)
        canon_sender = _resolve_sender_id(parents, raw_sender)
        active = _find_channel_match(
            slot_judged,
            body_sha256=body_sha,
            canon_sender=canon_sender,
            judged_ref=judged_ref,
            base_cid=base_cid,
            channel=channel,
            parents=parents,
            require_active=True,
        )
        if active is not None:
            _existing_cid, entry = active
            if (
                ctx.event == "PostToolBatch"
                and entry.get("armed_via") == "PostToolUse"
                and entry.get("ref") == judged_ref
            ):
                continue
            if not entry.get("caller_notified"):
                return True
            continue
        if canon_sender not in in_flight_resumes:
            if (
                _find_channel_match(
                    slot_disarmed,
                    body_sha256=body_sha,
                    canon_sender=canon_sender,
                    judged_ref=judged_ref,
                    base_cid=base_cid,
                    channel=channel,
                    parents=parents,
                    require_active=False,
                )
                is not None
            ):
                continue
        return True
    if ctx.event == "PostToolBatch" and ctx.client != "agy":
        return bool(_batch_handback_candidates(ctx))
    return False


is_hearsay_trigger = should_arm_hearsay


def emit_hearsay_span(*args: Any, **kwargs: Any) -> bool:
    """Forward hearsay span emission to premise_check_verdict."""
    import premise_check_verdict as pcv

    return pcv.emit_hearsay_span(*args, **kwargs)


def _emit_hearsay_trace(
    ctx: HookContext, claim_id: str, judged_ref: str | None, target_agent_id: str | None = None
) -> None:
    """Emit an OTel span for a hearsay check if tracing is configured."""
    tracer = claude_code_tracer
    if tracer is None:
        return
    try:
        config = tracer.discover_config()
        if config is not None:
            emit_hearsay_span(
                tracer,
                session_id=ctx.session_id,
                claim_id=claim_id,
                event=ctx.event,
                judged_ref=judged_ref,
                config=config,
                agent_id=target_agent_id,
            )
    except Exception as exc:
        log.debug("Hearsay span export skipped: %s", exc)


# ---------------------------------------------------------------------------
# Parent-child tracking, SendMessage routing, and SubagentHandback helpers
# ---------------------------------------------------------------------------


def _is_ancestor(subagent_parents: dict[str, str], node: str, candidate_ancestor: str) -> bool:
    """True when candidate_ancestor lies above node in subagent_parents."""
    if not node or not candidate_ancestor:
        return False
    cur: str | None = subagent_parents.get(node)
    seen: set[str] = {node}
    while cur and cur not in seen:
        if cur == candidate_ancestor:
            return True
        seen.add(cur)
        cur = subagent_parents.get(cur)
    return False


def _register_parent_locked(
    parents: dict[str, Any],
    child_id: str,
    caller_id: str,
    *,
    name: str = "",
    names: tuple[str, ...] | list[str] = (),
    overwrite: bool = False,
) -> None:
    if not child_id:
        return
    sub_parents = parents.setdefault("subagent_parents", {})
    known = parents.setdefault("known_subagents", [])
    if child_id not in known:
        known.append(child_id)
    names_map = parents.setdefault("known_subagent_names", {})
    for raw_alias in (name, *names):
        alias = str(raw_alias or "").strip()
        if not alias:
            continue
        names_map[alias] = child_id
        if "@" in alias:
            bare = alias.split("@", 1)[0].strip()
            if bare and bare not in names_map:
                names_map[bare] = child_id
    if child_id == caller_id:
        return
    if _is_ancestor(sub_parents, caller_id, child_id):
        return
    if overwrite or child_id not in sub_parents:
        sub_parents[child_id] = caller_id


def _tool_base_lower(tool_name: str | None) -> str:
    return (tool_name or "").strip().split("__")[-1].lower()


def record_pre_dispatch(ctx: HookContext) -> None:
    """Record caller agent for an in-flight dispatch tool_use_id under session lock."""
    if ctx.event != "PreToolUse" or ctx.tool not in _DISPATCH_TOOLS or not ctx.session_id:
        return
    tuid = _tool_use_id(ctx)
    if not tuid:
        return
    caller_id = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    sub_name = str(_tool_input(ctx).get("name") or "").strip()
    with _session_file_lock(ctx.session_id):
        parents = _load_parents(ctx.session_id)
        if caller_id:
            known = parents.setdefault("known_subagents", [])
            if caller_id not in known:
                known.append(caller_id)
        pending = parents.setdefault("pending_spawns", {})
        pending_names = parents.setdefault("pending_spawn_names", {})
        pending[tuid] = caller_id
        if sub_name:
            pending_names[tuid] = sub_name
        while len(pending) > 100:
            oldest = next(iter(pending))
            pending.pop(oldest, None)
            pending_names.pop(oldest, None)
        _save_parents(ctx.session_id, parents)


def _supersede_disarmed_claims_locked(session_id: str, caller_id: str, child_id: str) -> None:
    """Mark prior disarmed claims from child_id as superseded so resumed deliveries re-arm cleanly."""
    if not session_id or not child_id:
        return
    canon_caller = _canonical_agent_id(session_id, caller_id)
    state = _load_state(session_id, agent_id=canon_caller)
    disarmed = state.get("disarmed_claims")
    if not isinstance(disarmed, dict) or not disarmed:
        return
    parents = _load_parents(session_id)
    canon_child = _resolve_sender_id(parents, child_id)
    changed = False
    for entry in disarmed.values():
        if not isinstance(entry, dict) or entry.get("superseded"):
            continue
        esender = _resolve_sender_id(parents, str(entry.get("source_agent_id") or ""))
        if esender and esender == canon_child:
            entry["superseded"] = True
            changed = True
    if changed:
        _save_state(session_id, state, agent_id=canon_caller)


def _record_single_post_dispatch_locked(
    parents: dict[str, Any],
    session_id: str,
    caller_id: str,
    tool_name: str,
    tool_input: Any,
    tool_response: Any,
    tool_use_id: str,
    *,
    ctx: HookContext | None = None,
) -> None:
    if _is_failed_tool_response(ctx, tool_response):
        return
    ti = tool_input if isinstance(tool_input, dict) else {}
    tr = tool_response if isinstance(tool_response, dict) else {}
    if tool_name in _DISPATCH_TOOLS:
        pre_name = ""
        if tool_use_id:
            parents.get("pending_spawns", {}).pop(tool_use_id, None)
            pre_name = str(
                parents.get("pending_spawn_names", {}).pop(tool_use_id, "") or ""
            ).strip()
        resumed = str(
            ti.get("resume") or tr.get("resumedAgentId") or tr.get("revivedAgentId") or ""
        ).strip()
        child_id = str(tr.get("agentId") or tr.get("agent_id") or "").strip()
        if child_id:
            aliases = [
                pre_name,
                str(ti.get("name") or "").strip(),
                str(tr.get("name") or "").strip(),
                str(tr.get("teammate_id") or "").strip(),
            ]
            _register_parent_locked(parents, child_id, caller_id, names=aliases, overwrite=True)
        target_resume = resumed or (child_id if ti.get("resume") else "")
        if target_resume:
            canon_resumed = _resolve_sender_id(parents, target_resume) or target_resume
            (parents.get("handbacks") or {}).pop(canon_resumed, None)
            _supersede_disarmed_claims_locked(session_id, caller_id, target_resume)
    elif _tool_base_lower(tool_name) in ("sendmessage", "send_message"):
        resumed = str(
            tr.get("resumedAgentId")
            or tr.get("revivedAgentId")
            or ti.get("to")
            or ti.get("recipient")
            or ""
        ).strip()
        if tr.get("resumedAgentId") or tr.get("revivedAgentId"):
            revived = str(tr.get("resumedAgentId") or tr.get("revivedAgentId") or "").strip()
            if revived:
                _register_parent_locked(parents, revived, caller_id, overwrite=False)
        if resumed:
            canon_resumed = _resolve_sender_id(parents, resumed) or resumed
            if (parents.get("subagent_parents") or {}).get(canon_resumed) == caller_id:
                (parents.get("handbacks") or {}).pop(canon_resumed, None)
            _supersede_disarmed_claims_locked(session_id, caller_id, resumed)


def record_post_dispatch(ctx: HookContext) -> None:
    """Record authoritative parent-child and subagent registry metadata on PostToolUse/PostToolBatch."""
    if not ctx.session_id:
        return
    caller_id = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    if ctx.event == "PostToolUse" and (
        ctx.tool in _DISPATCH_TOOLS or _tool_base_lower(ctx.tool) in ("sendmessage", "send_message")
    ):
        with _session_file_lock(ctx.session_id):
            parents = _load_parents(ctx.session_id)
            _record_single_post_dispatch_locked(
                parents,
                ctx.session_id,
                caller_id,
                ctx.tool or "",
                _tool_input(ctx),
                _tool_response(ctx),
                _tool_use_id(ctx),
                ctx=ctx,
            )
            _save_parents(ctx.session_id, parents)
    elif ctx.event == "PostToolBatch" and ctx.tool_calls:
        relevant = [
            c
            for c in ctx.tool_calls
            if isinstance(c, dict)
            and c.get("tool_name") in (*_DISPATCH_TOOLS, "SendMessage", "send_message")
        ]
        if not relevant:
            return
        with _session_file_lock(ctx.session_id):
            parents = _load_parents(ctx.session_id)
            for call in relevant:
                _record_single_post_dispatch_locked(
                    parents,
                    ctx.session_id,
                    caller_id,
                    str(call.get("tool_name") or ""),
                    call.get("tool_input") or call.get("toolInput") or {},
                    call.get("tool_response") or call.get("toolResponse") or {},
                    str(call.get("tool_use_id") or call.get("id") or ""),
                )
            _save_parents(ctx.session_id, parents)


def _lookup_sidecar_tool_use_id(ctx: HookContext, child_id: str) -> str:
    """Inspect Claude Code agent-<child_id>.meta.json sidecar for deterministic toolUseId."""
    candidates: list[Path] = []
    tp_raw = ctx.transcript_path or ctx.raw.get("transcript_path")
    if tp_raw:
        tp = Path(str(tp_raw))
        candidates.append(tp.parent / f"agent-{child_id}.meta.json")
        candidates.append(tp.parent / ctx.session_id / "subagents" / f"agent-{child_id}.meta.json")
    proj_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if proj_dir and ctx.session_id:
        sanitized = proj_dir.replace("/", "-")
        candidates.append(
            Path.home()
            / ".claude"
            / "projects"
            / sanitized
            / ctx.session_id
            / "subagents"
            / f"agent-{child_id}.meta.json"
        )
    for cand in candidates:
        if cand.is_file():
            data = json.loads(cand.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"corrupt sidecar metadata in {cand}: expected JSON object")
            tuid = str(data.get("toolUseId") or "").strip()
            if tuid:
                return tuid
    return ""


def _resolve_handback_caller(ctx: HookContext, child_id: str) -> str | None:
    """Resolve child subagent's caller agent_id ('': main, non-empty: subagent), or None if unknown."""
    with _session_file_lock(ctx.session_id):
        parents = _load_parents(ctx.session_id)
        sub_parents = parents.get("subagent_parents") or {}
        if child_id in sub_parents:
            return str(sub_parents[child_id])
        tuid = _lookup_sidecar_tool_use_id(ctx, child_id)
        if tuid and tuid in (parents.get("pending_spawns") or {}):
            caller = str(parents["pending_spawns"][tuid])
            pre_name = str((parents.get("pending_spawn_names") or {}).get(tuid, "") or "").strip()
            _register_parent_locked(parents, child_id, caller, name=pre_name, overwrite=True)
            _save_parents(ctx.session_id, parents)
            return caller
    return None


def _buffer_unresolved_handback(
    session_id: str,
    child_id: str,
    message: str,
    judged_ref: str,
    *,
    resolved_caller: str | None = None,
) -> None:
    """Buffer a root-bound or caller-unresolved SubagentHandback until arrival on the caller."""
    with _session_file_lock(session_id):
        parents = _load_parents(session_id)
        ref = judged_ref or child_id
        if resolved_caller == "":
            canon_child = _resolve_sender_id(parents, child_id) or child_id
            body_sha = _normalized_body_hash(message)
            base_cid = build_id("claim", message)
            root_state = _load_state(session_id, agent_id="")
            root_judged = root_state.get("judged") or {}
            active_match = _find_channel_match(
                root_judged,
                body_sha256=body_sha,
                canon_sender=canon_child,
                judged_ref=ref,
                base_cid=base_cid,
                channel="post_tool_use",
                parents=parents,
                require_active=True,
            )
            if active_match is not None:
                ecid, entry = active_match
                _record_channel_hit(entry, "post_tool_use", ref, ecid)
                root_judged[ecid] = entry
                root_state["judged"] = root_judged
                _save_state(session_id, root_state, agent_id="")
                return
            root_disarmed = root_state.get("disarmed_claims") or {}
            disarmed_match = _find_channel_match(
                root_disarmed,
                body_sha256=body_sha,
                canon_sender=canon_child,
                judged_ref=ref,
                base_cid=base_cid,
                channel="post_tool_use",
                parents=parents,
                require_active=False,
            )
            if disarmed_match is not None:
                dcid, dentry = disarmed_match
                _record_channel_hit(dentry, "post_tool_use", ref, dcid)
                root_disarmed[dcid] = dentry
                root_state["disarmed_claims"] = root_disarmed
                _save_state(session_id, root_state, agent_id="")
                return
        handbacks = parents.setdefault("handbacks", {})
        handbacks.pop(child_id, None)
        handbacks[child_id] = {
            "message": message,
            "ref": ref,
            "recorded_at": _now(),
        }
        while len(handbacks) > 100:
            oldest = next(iter(handbacks))
            handbacks.pop(oldest, None)
        _save_parents(session_id, parents)


def _reconcile_buffered_root_handback(session_id: str, child_id: str) -> None:
    """Drop a buffered root handback if it already matches an active or disarmed root claim."""
    if not session_id or not child_id:
        return
    with _session_file_lock(session_id):
        parents = _load_parents(session_id)
        handbacks = parents.get("handbacks")
        if not isinstance(handbacks, dict) or child_id not in handbacks:
            return
        hb = handbacks.get(child_id)
        if not isinstance(hb, dict):
            return
        msg = str(hb.get("message") or "")
        if not msg.strip():
            return
        ref = str(hb.get("ref") or child_id)
        body_sha = _normalized_body_hash(msg)
        base_cid = build_id("claim", msg)
        root_state = _load_state(session_id, agent_id="")
        root_judged = root_state.get("judged") or {}
        active_match = _find_channel_match(
            root_judged,
            body_sha256=body_sha,
            canon_sender=child_id,
            judged_ref=ref,
            base_cid=base_cid,
            channel="post_tool_use",
            parents=parents,
            require_active=True,
        )
        if active_match is not None:
            ecid, entry = active_match
            handbacks.pop(child_id, None)
            _record_channel_hit(entry, "post_tool_use", ref, ecid)
            root_judged[ecid] = entry
            root_state["judged"] = root_judged
            _save_parents(session_id, parents)
            _save_state(session_id, root_state, agent_id="")
            return
        root_disarmed = root_state.get("disarmed_claims") or {}
        disarmed_match = _find_channel_match(
            root_disarmed,
            body_sha256=body_sha,
            canon_sender=child_id,
            judged_ref=ref,
            base_cid=base_cid,
            channel="post_tool_use",
            parents=parents,
            require_active=False,
        )
        if disarmed_match is not None:
            dcid, dentry = disarmed_match
            handbacks.pop(child_id, None)
            _record_channel_hit(dentry, "post_tool_use", ref, dcid)
            root_disarmed[dcid] = dentry
            root_state["disarmed_claims"] = root_disarmed
            _save_parents(session_id, parents)
            _save_state(session_id, root_state, agent_id="")


def _resolve_sendmessage_target(
    session_id: str, sender_id: str, tool_input: dict[str, Any], tool_response: dict[str, Any]
) -> str:
    """Resolve non-main target agent_id on SendMessage, prioritizing resumedAgentId/revivedAgentId."""
    raw_resumed = str(
        tool_response.get("resumedAgentId") or tool_response.get("revivedAgentId") or ""
    ).strip()
    parents = _load_parents(session_id)
    known = set(parents.get("known_subagents") or [])
    names_map = parents.get("known_subagent_names") or {}
    sub_parents = parents.get("subagent_parents") or {}

    candidates = [
        raw_resumed,
        str(tool_input.get("to") or "").strip(),
        str(tool_input.get("recipient") or "").strip(),
    ]
    target = ""
    for cand in candidates:
        if not cand or cand.lower() == "main" or cand == session_id:
            continue
        if cand in known:
            target = cand
            break
        if cand in names_map and str(names_map[cand]) in known:
            target = str(names_map[cand])
            break
    if not target or target == sender_id:
        return ""
    if sub_parents.get(target) == sender_id:
        return ""
    return target


def _batch_handback_candidates(ctx: HookContext) -> list[tuple[str, str]]:
    """Return [(child_id, description_or_call_id)] for foreground calls with bridged handbacks."""
    if not ctx.session_id:
        return []
    caller_id = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    parents = _load_parents(ctx.session_id)
    handbacks = parents.get("handbacks") or {}
    slot_state = _load_state(ctx.session_id, agent_id=caller_id)
    slot_judged = slot_state.get("judged") or {}
    slot_disarmed = slot_state.get("disarmed_claims") or {}
    found: list[tuple[str, str]] = []
    for call in ctx.tool_calls:
        if not isinstance(call, dict) or call.get("tool_name") not in _DISPATCH_TOOLS:
            continue
        resp = call.get("tool_response") or call.get("toolResponse")
        if not isinstance(resp, dict) or not _should_bridge_foreground_dispatch(caller_id, resp):
            continue
        child_id = str(resp.get("agentId") or resp.get("agent_id") or "").strip()
        if not child_id:
            continue
        buffered = handbacks.get(child_id)
        has_buffered = False
        if isinstance(buffered, dict):
            msg = str(buffered.get("message") or "")
            if msg.strip() and not _is_null_claim(msg):
                bsha = _normalized_body_hash(msg)
                bref = str(buffered.get("ref") or child_id)
                bcid = build_id("claim", msg)
                already_active = _find_channel_match(
                    slot_judged,
                    body_sha256=bsha,
                    canon_sender=child_id,
                    judged_ref=bref,
                    base_cid=bcid,
                    channel="post_tool_use",
                    parents=parents,
                    require_active=True,
                )
                already_disarmed = _find_channel_match(
                    slot_disarmed,
                    body_sha256=bsha,
                    canon_sender=child_id,
                    judged_ref=bref,
                    base_cid=bcid,
                    channel="post_tool_use",
                    parents=parents,
                    require_active=False,
                )
                if already_active is not None:
                    has_buffered = not already_active[1].get("caller_notified")
                elif already_disarmed is None:
                    has_buffered = True
        has_existing = any(
            isinstance(e, dict)
            and _resolve_sender_id(parents, str(e.get("source_agent_id") or "")) == child_id
            and not e.get("caller_notified")
            for e in slot_judged.values()
        )
        has_hr = False
        if not has_buffered and not has_existing and caller_id and _is_dispatch_pointer_only(resp):
            hr = resp.get("handbackReport")
            if isinstance(hr, dict):
                hr_msg = str(hr.get("text") or "")
                if hr_msg.strip() and not _is_null_claim(hr_msg):
                    hsha = _normalized_body_hash(hr_msg)
                    href = str(hr.get("toolUseId") or call.get("tool_use_id") or child_id)
                    hcid = build_id("claim", hr_msg)
                    already_active = _find_channel_match(
                        slot_judged,
                        body_sha256=hsha,
                        canon_sender=child_id,
                        judged_ref=href,
                        base_cid=hcid,
                        channel="agent_result",
                        parents=parents,
                        require_active=True,
                    )
                    already_disarmed = _find_channel_match(
                        slot_disarmed,
                        body_sha256=hsha,
                        canon_sender=child_id,
                        judged_ref=href,
                        base_cid=hcid,
                        channel="agent_result",
                        parents=parents,
                        require_active=False,
                    )
                    if already_active is not None:
                        has_hr = not already_active[1].get("caller_notified")
                    elif already_disarmed is None:
                        has_hr = True
        if has_buffered or has_existing or has_hr:
            found.append(
                (
                    child_id,
                    _call_description_id(
                        call.get("tool_input"), str(call.get("tool_use_id") or "")
                    ),
                )
            )
    return found


def _format_notice_pair(
    items: list[tuple[str, str]],
    hooks_dir: Path | None,
) -> Result:
    """Format agent-only arming notice preserving <=2 line single-claim contract and multi-claim list."""
    eff_dir = _hooks_base(hooks_dir)
    agent_tmpl, _ = load_message_pair(eff_dir, "hearsay_armed")
    if len(items) == 1:
        claim_id, cmd = items[0]
        if not agent_tmpl:
            agent_tmpl = (
                "Premise-check gate armed by {claim_id}. Brief: check Turn-1 inputs, `## Ask`, "
                "satisfiability; disarm via `verdict.py --no-claim` (`PASS` before frozen "
                "acceptance checklist; `REVISE` if clarifying). Report: load `ida:premise-check`, "
                "run judicial review on the message alone (zero substantive checks; proportionate "
                "depth, material remands only), record reasons.\n{command}"
            )
        inject = agent_tmpl.format(claim_id=claim_id, command=cmd)
        return warn(inject)

    claim_label = f"{len(items)} claims ({', '.join(cid for cid, _cmd in items)})"
    first_line = (
        agent_tmpl.splitlines()[0]
        if agent_tmpl
        else "Premise-check gate armed by {claim_id}; run judicial review on the message alone (zero substantive checks; effort proportionate to stakes) and record appealable reasons per `ida:premise-check`."
    ).format(claim_id=claim_label, command="")
    cmd_block = "\n".join(cmd for _cid, cmd in items)
    inject = f"{first_line}\n{cmd_block}"
    return warn(inject)


def _record_channel_hit(
    entry: dict[str, Any], channel: str, judged_ref: str, claim_or_base_id: str
) -> None:
    """Record delivery channel and unique ref onto an active or disarmed entry."""
    if channel:
        seen_channels = dict(entry.get("seen_channels") or {})
        seen_channels[channel] = True
        entry["seen_channels"] = seen_channels
    if judged_ref and judged_ref != claim_or_base_id:
        seen_refs = list(entry.get("seen_refs") or [])
        if judged_ref not in seen_refs:
            seen_refs.append(judged_ref)
            entry["seen_refs"] = seen_refs


def _apply_incoming_items(
    ctx: HookContext,
    items: list[IncomingItem],
    target_agent: str,
    *,
    allow_dedup_notice: bool = False,
    emit_notice: bool = True,
) -> list[tuple[str, str]]:
    """Process extracted reports against target_agent's slot; return notice tuples [(cid, cmd)]."""
    if not items:
        return []
    canon_target = _canonical_agent_id(ctx.session_id, target_agent)
    notice_items: list[tuple[str, str]] = []
    batch_used: set[str] = set()
    traces_to_emit: list[tuple[str, str]] = []

    with _session_file_lock(ctx.session_id):
        parents = _load_parents(ctx.session_id)
        for judged_text, judged_ref, base_cid, raw_sender, channel in items:
            body_sha = _normalized_body_hash(judged_text)
            canon_sender = _resolve_sender_id(parents, raw_sender)
            matched_hb_ref = ""
            handbacks = parents.get("handbacks")
            if canon_sender and isinstance(handbacks, dict) and canon_sender in handbacks:
                hb_owner = (parents.get("subagent_parents") or {}).get(canon_sender)
                hb_entry = handbacks.get(canon_sender)
                if (
                    (hb_owner is None or hb_owner == canon_target)
                    and isinstance(hb_entry, dict)
                    and (
                        _normalized_body_hash(str(hb_entry.get("message") or "")) == body_sha
                        or (judged_ref and hb_entry.get("ref") == judged_ref)
                    )
                ):
                    popped = handbacks.pop(canon_sender, None)
                    if isinstance(popped, dict):
                        matched_hb_ref = str(popped.get("ref") or "")
                    _save_parents(ctx.session_id, parents)

            # 1. Null form clears without blocking
            if _is_null_claim(judged_text):
                _disarm_locked(
                    ctx.session_id,
                    claim_id=base_cid,
                    verdict="no-claim",
                    reason="null form",
                    machine=True,
                    agent_id=canon_target,
                )
                continue

            slot_state = _load_state(ctx.session_id, agent_id=canon_target)
            slot_judged = slot_state.get("judged") or {}
            slot_disarmed = slot_state.get("disarmed_claims") or {}

            # 2. Symmetric dedup against already-active claim in target slot
            active_match = _find_channel_match(
                slot_judged,
                body_sha256=body_sha,
                canon_sender=canon_sender,
                judged_ref=judged_ref,
                base_cid=base_cid,
                channel=channel,
                parents=parents,
                require_active=True,
            )
            if active_match is not None:
                existing_cid, entry = active_match
                if canon_sender and not entry.get("source_agent_id"):
                    entry["source_agent_id"] = canon_sender
                _record_channel_hit(entry, channel, judged_ref, existing_cid)
                if matched_hb_ref and channel != "post_tool_use":
                    _record_channel_hit(entry, "post_tool_use", matched_hb_ref, existing_cid)
                should_notify = (emit_notice or allow_dedup_notice) and not bool(
                    entry.get("caller_notified")
                )
                if should_notify:
                    entry["caller_notified"] = True
                slot_judged[existing_cid] = entry
                slot_state["judged"] = slot_judged
                _save_state(ctx.session_id, slot_state, agent_id=canon_target)
                if should_notify:
                    cmd = format_verdict_command(
                        existing_cid,
                        ctx.hooks_dir,
                        ctx.session_id,
                        agent_id=canon_target,
                    )
                    notice_items.append((existing_cid, cmd))
                continue

            # 3. Suppress delayed twin or repeated same-sender delivery if already disarmed (until resume)
            disarmed_match = _find_channel_match(
                slot_disarmed,
                body_sha256=body_sha,
                canon_sender=canon_sender,
                judged_ref=judged_ref,
                base_cid=base_cid,
                channel=channel,
                parents=parents,
                require_active=False,
            )
            if disarmed_match is not None:
                disarmed_cid, dentry = disarmed_match
                if canon_sender and not dentry.get("source_agent_id"):
                    dentry["source_agent_id"] = canon_sender
                _record_channel_hit(dentry, channel, judged_ref, disarmed_cid)
                if matched_hb_ref and channel != "post_tool_use":
                    _record_channel_hit(dentry, "post_tool_use", matched_hb_ref, disarmed_cid)
                slot_disarmed[disarmed_cid] = dentry
                slot_state["disarmed_claims"] = slot_disarmed
                _save_state(ctx.session_id, slot_state, agent_id=canon_target)
                continue

            # 4. Allocate non-colliding claim_id across active + disarmed claims
            cid, already_same_ref = _allocate_non_colliding_claim_id(
                base_cid, judged_ref, body_sha, slot_judged, slot_disarmed, batch_used
            )
            if ctx.event == "PostToolBatch" and already_same_ref:
                raw_existing = slot_judged.get(cid)
                if (
                    isinstance(raw_existing, dict)
                    and raw_existing.get("armed_via") == "PostToolUse"
                ):
                    continue

            _arm_locked(
                ctx.session_id,
                claim_id=cid,
                judged_text=judged_text,
                judged_ref=judged_ref,
                agent_id=canon_target,
                source_agent_id=canon_sender,
                caller_notified=emit_notice,
                armed_via=ctx.event,
                seen_channel=channel,
            )
            if matched_hb_ref and channel != "post_tool_use":
                armed_state = _load_state(ctx.session_id, agent_id=canon_target)
                armed_judged = armed_state.get("judged") or {}
                armed_entry = armed_judged.get(cid)
                if isinstance(armed_entry, dict):
                    _record_channel_hit(armed_entry, "post_tool_use", matched_hb_ref, cid)
                    armed_judged[cid] = armed_entry
                    armed_state["judged"] = armed_judged
                    _save_state(ctx.session_id, armed_state, agent_id=canon_target)
            traces_to_emit.append((cid, judged_ref))

            if emit_notice:
                cmd = format_verdict_command(
                    cid,
                    ctx.hooks_dir,
                    ctx.session_id,
                    agent_id=canon_target,
                )
                notice_items.append((cid, cmd))

    for cid, judged_ref in traces_to_emit:
        _emit_hearsay_trace(ctx, cid, judged_ref, target_agent_id=canon_target or None)

    return notice_items


def _bridge_foreground_child(
    ctx: HookContext,
    caller_id: str,
    child_id: str,
    description_id: str,
    call_ref: str,
    resp: Any = None,
) -> list[tuple[str, str]]:
    """Bridge silent SubagentHandback into foreground caller notice without double-arming."""
    if not child_id:
        return []
    buffered: dict[str, Any] | None = None
    with _session_file_lock(ctx.session_id):
        parents = _load_parents(ctx.session_id)
        handbacks = parents.get("handbacks") or {}
        if child_id in handbacks:
            buffered = handbacks.pop(child_id)
            _register_parent_locked(parents, child_id, caller_id, overwrite=True)
            _save_parents(ctx.session_id, parents)

    if buffered is not None:
        msg = str(buffered.get("message") or "")
        if not msg.strip():
            return []
        ref = str(buffered.get("ref") or call_ref or child_id)
        base_cid = description_id or build_id("claim", msg)
        return _apply_incoming_items(
            ctx,
            [IncomingItem(msg, ref, base_cid, child_id, "post_tool_use")],
            caller_id,
            emit_notice=True,
        )

    # Check if child_id already armed caller_id earlier (e.g. via meta.json sidecar) and hasn't notified yet
    bridged: list[tuple[str, str]] = []
    with _session_file_lock(ctx.session_id):
        parents = _load_parents(ctx.session_id)
        slot_state = _load_state(ctx.session_id, agent_id=caller_id)
        slot_judged = slot_state.get("judged") or {}
        for cid, entry in list(slot_judged.items()):
            if not isinstance(entry, dict):
                continue
            esender = _resolve_sender_id(parents, str(entry.get("source_agent_id") or ""))
            if esender != child_id:
                continue
            if entry.get("caller_notified"):
                continue
            _arm_locked(
                ctx.session_id,
                claim_id=cid,
                agent_id=caller_id,
                caller_notified=True,
                seen_channel="agent_result",
            )
            cmd = format_verdict_command(
                cid,
                ctx.hooks_dir,
                ctx.session_id,
                agent_id=caller_id,
            )
            bridged.append((cid, cmd))
    if bridged:
        return bridged

    # Non-root subagent coordinators without UserPromptSubmit fall back to handbackReport if no claim exists yet
    if caller_id and _is_dispatch_pointer_only(resp) and isinstance(resp, dict):
        hr = resp.get("handbackReport")
        if isinstance(hr, dict):
            hr_text = str(hr.get("text") or "")
            if hr_text.strip():
                hr_ref = str(hr.get("toolUseId") or call_ref or child_id)
                base_cid = description_id or build_id("claim", hr_text)
                return _apply_incoming_items(
                    ctx,
                    [IncomingItem(hr_text, hr_ref, base_cid, child_id, "agent_result")],
                    caller_id,
                    emit_notice=True,
                )
    return []


def subagent_start_gate_notice(ctx: HookContext) -> Result | None:
    """SubagentStart advisory hint with --agent <id> plus any pending armed claims for waking agent."""
    if ctx.event != "SubagentStart" or not ctx.session_id:
        return None
    canon_agent = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    if not canon_agent:
        return None

    slot = _load_state(ctx.session_id, agent_id=canon_agent)
    if bool(slot.get("armed") or slot.get("pending")):
        pending_cids = slot.get("claim_ids") or ([slot["claim_id"]] if slot.get("claim_id") else [])
        items: list[tuple[str, str]] = []
        for cid in pending_cids:
            cmd = format_verdict_command(
                cid,
                ctx.hooks_dir,
                ctx.session_id,
                agent_id=canon_agent,
            )
            items.append((cid, cmd))
        if items:
            res = _format_notice_pair(items, ctx.hooks_dir)
            hint = f"Subagent agent_id for verdict commands: --agent {canon_agent}"
            return warn(f"{hint}\n{res.inject_text}")

    hint = f"Subagent agent_id for verdict commands: --agent {canon_agent}"
    return warn(hint)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def hearsay_arm(ctx: HookContext) -> Result | None:
    """Arm recipient-scoped hearsay gates on incoming reports, handbacks, and completed batches."""
    if ctx.event not in ("UserPromptSubmit", "PostToolUse", "PostToolBatch"):
        return None

    if ctx.event in ("PostToolUse", "PostToolBatch"):
        record_post_dispatch(ctx)

    caller_id = _canonical_agent_id(ctx.session_id, ctx.agent_id)

    tool_base = _tool_base_lower(ctx.tool)

    # 1. SubagentHandback PostToolUse: subagent callers arm silently; Root/unresolved callers buffer until delivery
    if ctx.event == "PostToolUse" and tool_base in ("subagenthandback", "subagent_handback"):
        if _is_failed_tool_response(ctx, _tool_response(ctx)):
            return None
        child_id = caller_id
        msg = str(_tool_input(ctx).get("message") or "").strip()
        if not msg or not child_id:
            return None
        resolved_caller = _resolve_handback_caller(ctx, child_id)
        tuid = _tool_use_id(ctx) or child_id
        if not resolved_caller:
            _buffer_unresolved_handback(
                ctx.session_id, child_id, msg, tuid, resolved_caller=resolved_caller
            )
            return None
        base_cid = build_id("claim", msg)
        _apply_incoming_items(
            ctx,
            [IncomingItem(msg, tuid, base_cid, child_id, "post_tool_use")],
            resolved_caller,
            emit_notice=False,
        )
        return None

    # 2. Subagent-to-subagent SendMessage PostToolUse: silently arm target (excluding parent->child briefs)
    if ctx.event == "PostToolUse" and tool_base in (
        "sendmessage",
        "send_message",
    ):
        if not caller_id:
            return None
        ti = _tool_input(ctx)
        tr = _tool_response(ctx)
        if _is_failed_tool_response(ctx, tr):
            return None
        tr_dict = tr if isinstance(tr, dict) else {}
        target = _resolve_sendmessage_target(ctx.session_id, caller_id, ti, tr_dict)
        if not target:
            return None
        msg = str(ti.get("message") or ti.get("content") or "").strip()
        if not msg:
            return None
        tuid = _tool_use_id(ctx) or f"sm-{caller_id}"
        base_cid = build_id("claim", msg)
        _apply_incoming_items(
            ctx,
            [IncomingItem(msg, tuid, base_cid, caller_id, "post_tool_use")],
            target,
            emit_notice=False,
        )
        return None

    # 3. Normal extraction (UserPromptSubmit envelopes, completed Agent PostToolUse, PostToolBatch)
    items = _extract_judged_items_with_channel(ctx)
    notice_items = _apply_incoming_items(
        ctx,
        items,
        caller_id,
        allow_dedup_notice=True,
        emit_notice=True,
    )

    # 4. Foreground bridge when PostToolUse(Agent) / PostToolBatch omits or pointer-stubs report body
    if ctx.event == "PostToolUse" and ctx.tool in _DISPATCH_TOOLS:
        resp = _tool_response(ctx)
        child_id = (
            str(resp.get("agentId") or resp.get("agent_id") or "").strip()
            if isinstance(resp, dict)
            else ""
        )
        if _should_bridge_foreground_dispatch(caller_id, resp):
            desc_id = _call_description_id(_tool_input(ctx), _tool_use_id(ctx))
            notice_items.extend(
                _bridge_foreground_child(
                    ctx, caller_id, child_id, desc_id, _tool_use_id(ctx), resp=resp
                )
            )
        elif not caller_id and _is_dispatch_pointer_only(resp) and child_id:
            _reconcile_buffered_root_handback(ctx.session_id, child_id)
    elif ctx.event == "PostToolBatch" and ctx.client != "agy":
        for call in ctx.tool_calls:
            if not isinstance(call, dict) or call.get("tool_name") not in _DISPATCH_TOOLS:
                continue
            resp = call.get("tool_response") or call.get("toolResponse")
            child_id = (
                str(resp.get("agentId") or resp.get("agent_id") or "").strip()
                if isinstance(resp, dict)
                else ""
            )
            if _should_bridge_foreground_dispatch(caller_id, resp):
                call_id = str(call.get("tool_use_id") or call.get("id") or "")
                desc_id = _call_description_id(
                    call.get("tool_input") or call.get("toolInput"), call_id
                )
                notice_items.extend(
                    _bridge_foreground_child(ctx, caller_id, child_id, desc_id, call_id, resp=resp)
                )
            elif not caller_id and _is_dispatch_pointer_only(resp) and child_id:
                _reconcile_buffered_root_handback(ctx.session_id, child_id)

    if not notice_items:
        return None
    return _format_notice_pair(notice_items, ctx.hooks_dir)


_USER_QUESTION_TOOLS = frozenset(
    {
        "askuserquestion",
        "askquestion",
        "ask_user_question",
        "ask_question",
        "ask_user",
    }
)

_BLOCKED_TOOL_ACTION_DESCS: dict[str, str] = {
    **{name.lower(): "dispatching a subagent" for name in _DISPATCH_TOOLS},
    "sendmessage": "sending an agent message",
    "send_message": "sending an agent message",
    "subagenthandback": "delivering a subagent handback",
    "subagent_handback": "delivering a subagent handback",
    "dump": "handing over the session",
}


def _blocked_action_desc(ctx: HookContext) -> str:
    """Return a plain-language action phrase for the blocked event or tool."""
    if ctx.event == "Stop":
        return "finishing the task or contacting the user/teammates"
    base = _tool_base_lower(ctx.tool)
    if base in _USER_QUESTION_TOOLS:
        return "asking the user a question"
    if is_channel_reply_tool(ctx.tool):
        return "sending a channel reply"
    return _BLOCKED_TOOL_ACTION_DESCS.get(base, "performing this action")


def hearsay_handler(ctx: HookContext) -> Result | None:
    """PreToolUse/Stop handler: refuse the next restricted action while recipient slot is armed."""
    if ctx.event == "PreToolUse" and not _is_blocked_tool(ctx.tool):
        return None

    mode = (
        os.environ.get("PREMISE_CHECK_GATE_MODE", os.environ.get("PREMISE_CHECK_MODE", "block"))
        .strip()
        .lower()
    )
    if mode == "off":
        return None
    canon_agent = _canonical_agent_id(ctx.session_id, ctx.agent_id)
    if not is_armed(ctx.session_id, agent_id=canon_agent):
        return None
    if _active_override():
        return None

    state = get_state(ctx.session_id, agent_id=canon_agent)
    pending_cids = state.get("claim_ids") or (
        [state["claim_id"]] if state.get("claim_id") else ["the pending report"]
    )
    action_desc = _blocked_action_desc(ctx)

    agent_tmpl, _ = load_message_pair(ctx.hooks_dir, "hearsay_blocked")
    if not agent_tmpl:
        agent_tmpl = (
            "Premise-check gate armed by {claim_id} blocks {action_desc}; load "
            "`ida:premise-check`, run judicial review on the message alone (zero substantive "
            "checks; proportionate depth, material remands only; never bypass) and record "
            "reasons, or for a brief add `--no-claim` below (`PASS`/`REVISE`).\n{command}"
        )

    if len(pending_cids) == 1:
        claim_id = pending_cids[0]
        cmd = format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id, agent_id=canon_agent)
        reason = agent_tmpl.format(claim_id=claim_id, action_desc=action_desc, command=cmd)
    else:
        cids_str = ", ".join(pending_cids)
        cmds: list[str] = [
            format_verdict_command(cid, ctx.hooks_dir, ctx.session_id, agent_id=canon_agent)
            for cid in pending_cids
        ]
        claim_label = f"{len(pending_cids)} claims ({cids_str})"
        reason = agent_tmpl.format(
            claim_id=claim_label, action_desc=action_desc, command="\n".join(cmds)
        )

    if mode == "warn":
        return warn(reason)

    if ctx.event == "Stop":
        return block(reason)

    return refuse(reason)


def _tracer_state_dir() -> Path:
    env_dir = (
        os.environ.get("AOPS_TRACER_STATE_DIR")
        or os.environ.get("TRACER_STATE_DIR")
        or os.environ.get("AOPS_TRACER_DIR")
    )
    if env_dir:
        return Path(env_dir)
    if claude_code_tracer is not None and hasattr(claude_code_tracer, "_tracer_state_dir"):
        return claude_code_tracer._tracer_state_dir()
    if claude_code_tracer is not None and hasattr(claude_code_tracer, "STATE_DIR"):
        return Path(claude_code_tracer.STATE_DIR)
    return Path.home() / ".claude" / "tracer"


def _has_subagent_marker(text: str) -> bool:
    return "<subagent_reminder>" in text or "invoked by a caller agent" in text


def _initial_agy_turn_content(ctx: HookContext) -> str:
    """Content of the first non-harness turn-start entry in an agy transcript."""
    for entry in _read_all_agy_entries(ctx):
        entry_type = entry.get("type")
        if entry_type == "USER_INPUT":
            return str(entry.get("content") or "")
        if entry_type == "SYSTEM_MESSAGE":
            content = str(entry.get("content") or "")
            if _is_session_start_or_harness_injection(content):
                continue
            return content
    return ""


def _is_subagent_conversation(ctx: HookContext) -> bool:
    """True if ctx is an agy subagent conversation invoked by a caller agent."""
    raw = ctx.raw or {}
    if (
        raw.get("caller_id")
        or raw.get("parent_conversation_id")
        or raw.get("is_subagent")
        or raw.get("caller_session")
    ):
        return True
    if ctx.session_id:
        try:
            tracer_file = _tracer_state_dir() / f"{ctx.session_id}.json"
            if tracer_file.is_file():
                tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
                phx_sid = tdata.get("phoenix_session_id")
                if phx_sid:
                    phx_root = str(phx_sid).split("/", 1)[0]
                    if phx_root and phx_root != ctx.session_id:
                        return True
                if tdata.get("parent_session_id") or tdata.get("caller_session_id"):
                    return True
        except Exception:
            pass
    if ctx.client == "agy" and ctx.event == "PreToolUse":
        direct_prompt = raw.get("prompt")
        if direct_prompt is None and hasattr(ctx, "prompt"):
            direct_prompt = ctx.prompt
        if isinstance(direct_prompt, dict):
            direct_prompt = direct_prompt.get("text") or direct_prompt.get("content") or ""
        if _has_subagent_marker(str(direct_prompt or "")):
            return True
        return _has_subagent_marker(_initial_agy_turn_content(ctx))
    prompt = prompt_text(ctx) or ""
    if _has_subagent_marker(prompt):
        return True
    return False


# Backward compatibility aliases
premise_check_arm = hearsay_arm
premise_check_handler = hearsay_handler
