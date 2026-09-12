"""Ida scratchpad write gate and tool permission enforcement."""

from __future__ import annotations

import os
from pathlib import Path

from dispatch import HookContext, Result, refuse

# PKB write operations that must be blocked for Ida. The Claude Code plugin
# wrapper (`mcp__plugin_pkb_services__`) is stable -- it comes from this repo's
# own plugin name and MCP config key. What is NOT stable is the segment the
# backend behind $PKB_MCP_URL adds on top of that (a gateway's per-catalog-key
# tool-name prefix, a different gateway's own convention, or nothing at all on
# a direct connection). Matching on the operation name's suffix, rather than
# enumerating every prefix combination, survives any such endpoint move.
# Over-matching is the safe failure here: the only cost of a false positive is
# Ida being told to delegate a write it may not even have attempted, while a
# false negative lets a write through the gate exists to stop.
PKB_PLUGIN_PREFIX = "mcp__plugin_pkb_services__"

PKB_WRITE_OPS = frozenset(
    {
        "create",
        "create_task",
        "update_task",
        "update_body",
        "edit_body",
        "append",
        "delete",
        "decompose_task",
        "claim_task",
        "batch_update",
        "batch_merge",
        "batch_create_epics",
        "apply_consolidation_batch",
    }
)

# Operation-name prefixes that cover writes not individually enumerated above
# (e.g. `batch_reparent`, `merge_duplicates`).
PKB_WRITE_OP_PREFIXES = ("batch_", "merge_")

_NAME_SEPARATORS = ("__", "_", "-")


def _matches_pkb_write_op(remainder: str) -> bool:
    """True if remainder is a PKB write op, with zero or more prefix segments."""
    if remainder in PKB_WRITE_OPS:
        return True
    if any(remainder.endswith(f"{sep}{op}") for op in PKB_WRITE_OPS for sep in _NAME_SEPARATORS):
        return True
    for prefix in PKB_WRITE_OP_PREFIXES:
        if remainder.startswith(prefix):
            return True
        if any(f"{sep}{prefix}" in remainder for sep in _NAME_SEPARATORS):
            return True
    return False


def _is_pkb_write_tool(tool_name: str) -> bool:
    """True if tool_name resolves to a PKB write op under any transport prefix."""
    if not tool_name:
        return False
    if tool_name.startswith(PKB_PLUGIN_PREFIX):
        return _matches_pkb_write_op(tool_name[len(PKB_PLUGIN_PREFIX) :])
    # No Claude Code plugin wrapper in front: a raw JSON-RPC client, or a
    # client whose tool-naming shape differs from Claude Code's.
    return _matches_pkb_write_op(tool_name)


FORBIDDEN_OPERATIONAL_TOOLS = frozenset(
    {
        "Bash",
        "Edit",
        "NotebookEdit",
        "run_command",
        "replace_file_content",
        "notebook_edit",
    }
)

# Canonical scratchpad path prefix: /opt/nic/tmp/claude-1000/<project>/<session>/scratchpad
SCRATCHPAD_CANONICAL_PREFIX = "/opt/nic/tmp/claude-1000/"


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


def is_allowed_scratchpad_path(target_path: str) -> bool:
    """Check if target_path is strictly confined to the session scratchpad directory."""
    if not target_path or not str(target_path).strip():
        return False

    try:
        resolved = str(Path(target_path).resolve())
    except Exception:
        resolved = str(target_path)

    # 1. Canonical pattern: /opt/nic/tmp/claude-1000/<project>/<session>/scratchpad/...
    if resolved.startswith(SCRATCHPAD_CANONICAL_PREFIX):
        rel = resolved[len(SCRATCHPAD_CANONICAL_PREFIX) :].strip("/")
        parts = rel.split("/")
        # Expected: [<project>, <session>, "scratchpad", ...]
        if len(parts) >= 3 and parts[2] == "scratchpad":
            return True

    # 2. Container scratch mount /scratch/...
    if resolved == "/scratch" or resolved.startswith("/scratch/"):
        return True

    # 3. Explicit scratch dir environment variable
    env_scratch = os.environ.get("POLECAT_SCRATCH_DIR") or os.environ.get("AOPS_SCRATCH_DIR")
    if env_scratch:
        try:
            resolved_scratch = str(Path(env_scratch).resolve())
            if resolved == resolved_scratch or resolved.startswith(
                resolved_scratch.rstrip("/") + "/"
            ):
                return True
        except Exception:
            pass

    # 4. Any path explicitly inside a directory named 'scratchpad'
    parts = Path(resolved).parts
    if "scratchpad" in parts:
        # ensure it's not just a file named scratchpad at root
        idx = parts.index("scratchpad")
        if idx < len(parts):
            return True

    return False


def scratchpad_write_gate(ctx: HookContext) -> Result | None:
    """Constrain Ida's permissions: deny operational/write tools, confine Write to scratchpad."""
    if not is_ida(ctx):
        return None

    tool_name = ctx.tool or ctx.raw.get("tool_name") or ctx.raw.get("toolName") or ""

    # 1. Deny forbidden operational tools
    if tool_name in FORBIDDEN_OPERATIONAL_TOOLS:
        return refuse(
            f"Tool '{tool_name}' is prohibited for Ida. Commission execution or editing to James or Sara."
        )

    # 2. Deny PKB write tools
    if _is_pkb_write_tool(tool_name):
        return refuse(
            f"PKB write tool '{tool_name}' is prohibited for Ida. Delegate graph writes to Pauli."
        )

    # 3. Confine Write to scratchpad directory
    if tool_name in ("Write", "write_to_file"):
        tool_input = ctx.raw.get("tool_input") or {}
        target_path = (
            tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("TargetFile")
            or ""
        )
        if not target_path or not is_allowed_scratchpad_path(target_path):
            return refuse(
                f"Writing outside session scratchpad directory (/opt/nic/tmp/claude-1000/<project>/<session>/scratchpad) is prohibited for Ida: '{target_path}'."
            )

    return None
