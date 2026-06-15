"""Regression: agy `toolCall` lives at the ROOT of the stdin payload (#1800).

DEFECT (#1800, GitHub): ``router.normalize_input`` looked for the agy tool
descriptor at ``raw_input["raw_input"]["toolCall"]`` (double-nested). The REAL
agy 1.0.7 Pre/PostToolUse payload — captured from the live hook log of session
``6d3d5783`` — places ``toolCall`` at the ROOT of the stdin object::

    {"stepIdx": 5,
     "toolCall": {"name": "grep_search", "args": {...}},
     "workspacePaths": [...]}

With the lookup pointed at the wrong nesting, ``ctx.tool_name`` was ``None`` on
every agy tool event, silently defeating sentinel / enforcer / handover
tool-name matching (the gates believed no tool was being called).

These tests drive the REAL router (``HookRouter.normalize_input``) with the
exact logged payload shape and assert the extracted ``tool_name`` /
``tool_input``. They FAIL the instant the root-level lookup regresses back to
the dead double-nested form.

These tests are agy-specific by design — they pin the exact agy 1.0.7 payload
shape; analogous claude/gemini extraction behaviour is covered in gate_helpers
tests.
"""

from __future__ import annotations

import pytest
from hooks.router import HookRouter  # type: ignore  # noqa: E402

from tests.hooks.gate_helpers import AOPS_CORE  # noqa: F401  (ensures sys.path insert)

# Verbatim from the live hook log:
# /home/nic/.gemini/antigravity-cli/brain/6d3d5783-.../20260612-1538-...-hooks.jsonl
_REAL_AGY_PRETOOL = {
    "stepIdx": 5,
    "toolCall": {
        "args": {
            "CaseInsensitive": True,
            "IsRegex": False,
            "MatchPerLine": True,
            "Query": "session_type",
            "SearchPath": "/home/nic/src/overwhelm-dashboard",
        },
        "name": "grep_search",
    },
    "workspacePaths": ["/home/nic/src/overwhelm-dashboard"],
}

# Real agy PostToolUse: toolCall + root-level `error` (empty on success).
_REAL_AGY_POSTTOOL = {
    "error": "",
    "stepIdx": 5,
    "toolCall": {
        "args": {
            "Query": "session_type",
            "SearchPath": "/home/nic/src/overwhelm-dashboard",
        },
        "name": "grep_search",
    },
    "workspacePaths": ["/home/nic/src/overwhelm-dashboard"],
}


@pytest.mark.parametrize(
    ("payload", "event"),
    [
        (_REAL_AGY_PRETOOL, "PreToolUse"),
        (_REAL_AGY_POSTTOOL, "PostToolUse"),
    ],
    ids=["pretool", "posttool"],
)
def test_agy_root_level_toolcall_populates_tool_name(payload, event):
    """The #1800 GATE: real agy payload (toolCall at ROOT) yields tool_name."""
    ctx = HookRouter().normalize_input(dict(payload), event, client_type="agy")
    assert ctx.tool_name == "grep_search", (
        f"#1800: agy {event} with root-level toolCall must populate tool_name; "
        f"got {ctx.tool_name!r}. (Lookup regressed to double-nested raw_input.)"
    )


def test_agy_pretool_args_become_tool_input():
    """The toolCall.args object must surface as ctx.tool_input."""
    ctx = HookRouter().normalize_input(dict(_REAL_AGY_PRETOOL), "PreToolUse", client_type="agy")
    assert ctx.tool_input.get("Query") == "session_type"
    assert ctx.tool_input.get("SearchPath") == "/home/nic/src/overwhelm-dashboard"


def test_agy_legacy_double_nested_toolcall_still_resolves():
    """Backward-compat: a wrapper that re-nests under raw_input still resolves.

    The fix prefers the root-level object but keeps the nested form as a
    defensive fallback, so neither shape silently drops the tool name.
    """
    legacy = {"raw_input": {"toolCall": {"name": "grep_search", "args": {"q": "x"}}}}
    ctx = HookRouter().normalize_input(legacy, "PreToolUse", client_type="agy")
    assert ctx.tool_name == "grep_search"
