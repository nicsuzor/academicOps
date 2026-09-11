"""Ida citation enforcement hook on Stop event."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from dispatch import HookContext, Result, block

log = logging.getLogger("ida.citation_enforcement")

# PKB identifier regex: kb_, mem_, task_, aops_, note_, spec_ and hyphenated variants
PKB_ID_RE = re.compile(
    r"\b((?:kb|mem|task|aops|note|spec)[_-][a-zA-Z0-9_-]+)\b",
    re.IGNORECASE,
)

# Common generic terms or variable names to exclude from citation enforcement
EXCLUDED_IDS = frozenset(
    {
        "task_id",
        "task_ids",
        "task-id",
        "task-ids",
        "task_search",
        "task_summary",
        "task_create",
        "task_update",
        "task_list",
        "task_get",
        "task_stop",
        "task-tracking",
        "task-level",
        "task-based",
        "task-specific",
        "task-management",
        "note_id",
        "note-id",
        "kb_id",
        "kb-id",
        "mem_id",
        "mem-id",
        "spec_id",
        "spec-id",
        "aops_version",
        "aops-version",
        "aops_build",
        "aops-build",
        "aops_image",
        "aops-image",
        "aops_dist",
        "aops-dist",
    }
)

# path:line regex (e.g. file.py:42, /path/to/file.py:123, lib/polecat/cli.py:123:45)
# Requires either a slash '/' or a dot-extension before ':' followed by line number
PATH_LINE_RE = re.compile(
    r"(?<![a-zA-Z0-9_/.-])((?:[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)+|\b[a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+):[0-9]+(?::[0-9]+)?)\b"
)


def is_ida(ctx: HookContext) -> bool:
    if ctx.agent_type:
        agent_type = ctx.agent_type.lower()
        if agent_type in ("ida", "ida:ida", "aops:ida", "pkb:ida") or agent_type.endswith(":ida"):
            return True
    raw_agent = ctx.raw.get("agent_type") or ctx.raw.get("subagentType") or ctx.raw.get("agent")
    if raw_agent:
        raw_agent = str(raw_agent).lower()
        if raw_agent in ("ida", "ida:ida", "aops:ida", "pkb:ida") or raw_agent.endswith(":ida"):
            return True
    return False


def get_turn_retrievals(transcript_path: str) -> tuple[set[str], set[str]]:
    """Scan transcript for tool calls in the CURRENT turn and return (retrieved_ids, retrieved_paths)."""
    retrieved_ids: set[str] = set()
    retrieved_paths: set[str] = set()

    if not transcript_path or not Path(transcript_path).exists():
        return retrieved_ids, retrieved_paths

    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        log.warning("Failed to read transcript %s: %s", transcript_path, exc)
        return retrieved_ids, retrieved_paths

    # Collect entries from the current turn: after the last human message
    turn_entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue

        if entry.get("type") == "user":
            msg = entry.get("message", {})
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            if isinstance(content, str):
                # Found the user prompt opening this turn
                break

        turn_entries.append(entry)

    # Process entries in chronological order
    for entry in reversed(turn_entries):
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue

        content = msg.get("content", [])
        if isinstance(content, list):
            for block_item in content:
                if not isinstance(block_item, dict):
                    continue

                btype = block_item.get("type")
                if btype == "tool_use":
                    tool_name = block_item.get("name", "")
                    inp = block_item.get("input", {})
                    if not isinstance(inp, dict):
                        inp = {}

                    # File read tools
                    if tool_name in ("Read", "view_file"):
                        fpath = (
                            inp.get("file_path") or inp.get("path") or inp.get("AbsolutePath") or ""
                        )
                        if fpath:
                            retrieved_paths.add(fpath)
                            retrieved_paths.add(Path(fpath).name)

                    # PKB get_document
                    elif tool_name.endswith("get_document"):
                        did = inp.get("id") or inp.get("document_id") or ""
                        if did:
                            retrieved_ids.add(str(did).lower())

                    # PKB get_task
                    elif tool_name.endswith("get_task"):
                        tid = inp.get("id") or inp.get("task_id") or ""
                        if tid:
                            retrieved_ids.add(str(tid).lower())

                    # Context / trace
                    elif any(k in tool_name for k in ("pkb_trace", "context", "dependency_tree")):
                        for v in inp.values():
                            if isinstance(v, str):
                                retrieved_ids.add(v.lower())

                elif btype == "tool_result":
                    # If tool was a subagent delegate, its report is in tool_result
                    res_content = block_item.get("content", "")
                    text = ""
                    if isinstance(res_content, str):
                        text = res_content
                    elif isinstance(res_content, list):
                        text = " ".join(
                            item.get("text", "") for item in res_content if isinstance(item, dict)
                        )

                    if text:
                        # Extract citations reported back by delegate
                        for match in PKB_ID_RE.finditer(text):
                            retrieved_ids.add(match.group(1).lower())
                        for match in PATH_LINE_RE.finditer(text):
                            p = match.group(1).split(":")[0]
                            retrieved_paths.add(p)
                            retrieved_paths.add(Path(p).name)

    return retrieved_ids, retrieved_paths


def citation_enforcement_gate(ctx: HookContext) -> Result | None:
    """Enforce citations on Ida's outgoing messages."""
    if not is_ida(ctx):
        return None

    # Get outgoing message text
    msg = ctx.raw.get("last_assistant_message", "")
    if not msg and ctx.transcript_path and Path(ctx.transcript_path).exists():
        try:
            for line in reversed(
                Path(ctx.transcript_path).read_text(encoding="utf-8").splitlines()
            ):
                entry = json.loads(line)
                if entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        msg = content
                        break
                    elif isinstance(content, list):
                        text_parts = [
                            b.get("text", "")
                            for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        if text_parts:
                            msg = "".join(text_parts)
                            break
        except Exception:
            pass

    if not msg:
        return None

    # Scan for identifiers
    found_ids = set()
    for m in PKB_ID_RE.finditer(msg):
        ident = m.group(1)
        if ident.lower() not in EXCLUDED_IDS:
            found_ids.add(ident)

    # Scan for path:line references
    found_paths = set()
    for m in PATH_LINE_RE.finditer(msg):
        ref = m.group(1)
        if not ref.startswith(("http://", "https://", "ftp://")):
            found_paths.add(ref)

    if not found_ids and not found_paths:
        return None

    retrieved_ids, retrieved_paths = get_turn_retrievals(ctx.transcript_path)

    unverified = []

    for ident in sorted(found_ids):
        if ident.lower() not in retrieved_ids:
            unverified.append(f"identifier '{ident}'")

    for path_ref in sorted(found_paths):
        path_str = path_ref.split(":")[0]
        base_name = Path(path_str).name
        if (
            path_str not in retrieved_paths
            and base_name not in retrieved_paths
            and not any(rp.endswith(path_str) for rp in retrieved_paths)
        ):
            unverified.append(f"citation '{path_ref}'")

    if unverified:
        items_str = ", ".join(unverified)
        reason = (
            f"Citation enforcement violation: Ida cited unretrieved source(s) in outgoing message: {items_str}. "
            f"Every cited PKB identifier or path:line reference must be retrieved by an actual tool call "
            f"(get_document, get_task, or Read) in the same turn before citing. "
            f"Retrieve the object or remove the unverified citation."
        )
        log.warning("Citation enforcement blocked Ida: %s", items_str)
        return block(
            reason,
            user_text=f"[Citation Enforcement] Blocked outgoing message citing unretrieved source(s): {items_str}",
        )

    return None
