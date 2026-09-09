"""Ida scratchpad write gate and tool permission enforcement."""

from __future__ import annotations

import os
from pathlib import Path

from dispatch import HookContext, Result, refuse

# PKB write tools that must be blocked for Ida
PKB_WRITE_TOOLS = frozenset(
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
        "pkb__create",
        "pkb__create_task",
        "pkb__update_task",
        "pkb__update_body",
        "pkb__edit_body",
        "pkb__append",
        "pkb__delete",
        "pkb__decompose_task",
        "pkb__claim_task",
        "pkb__batch_update",
        "pkb__batch_merge",
        "pkb__batch_create_epics",
        "pkb__apply_consolidation_batch",
        "mcp__services__pkb__create",
        "mcp__services__pkb__create_task",
        "mcp__services__pkb__update_task",
        "mcp__services__pkb__update_body",
        "mcp__services__pkb__edit_body",
        "mcp__services__pkb__append",
        "mcp__services__pkb__delete",
        "mcp__services__pkb__decompose_task",
        "mcp__services__pkb__claim_task",
        "mcp__services__pkb__batch_update",
        "mcp__services__pkb__batch_merge",
        "mcp__services__pkb__batch_create_epics",
        "mcp__services__pkb__apply_consolidation_batch",
    }
)

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
    if tool_name in PKB_WRITE_TOOLS or any(
        tool_name.startswith(pfx)
        for pfx in (
            "pkb__batch_",
            "mcp__services__pkb__batch_",
            "pkb__merge_",
            "mcp__services__pkb__merge_",
        )
    ):
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
