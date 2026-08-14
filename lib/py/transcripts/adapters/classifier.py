"""Classification logic for user events in transcript adapters.

Classifies user event content into human-typed prompts vs injected context
(system reminders, hook context envelopes, skill preambles, tool results,
command outputs, stop hook feedback).
"""

from __future__ import annotations

import re
from typing import Any

USER_REQUEST_RE = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL)


def classify_user_prompt(content: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify a user prompt event's content.

    Returns a metadata dictionary containing:
        - prompt_kind: str ("human_prompt", "system_reminder", "hook_injected_context",
                       "stop_hook_feedback", "skill_preamble", "command_output",
                       "tool_result", "mixed")
        - is_human: bool
        - human_content: str
        - injected_content: str
    """
    if not content:
        return {
            "prompt_kind": "human_prompt",
            "is_human": True,
            "human_content": "",
            "injected_content": "",
        }

    raw = content.strip()

    # Check user_type if provided (e.g. Claude Code userType)
    user_type = (meta or {}).get("user_type")
    if user_type and user_type not in ("external", "user"):
        return {
            "prompt_kind": "hook_injected_context",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for Stop hook feedback
    if raw.startswith("Stop hook feedback:") or "Stop hook feedback:" in raw:
        parts = raw.split("Stop hook feedback:", 1)
        human_part = parts[0].strip()
        injected_part = "Stop hook feedback:" + parts[1]
        if human_part:
            return {
                "prompt_kind": "mixed",
                "is_human": True,
                "human_content": human_part,
                "injected_content": injected_part,
            }
        return {
            "prompt_kind": "stop_hook_feedback",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for <USER_REQUEST> wrapper
    user_req_match = USER_REQUEST_RE.search(raw)
    if user_req_match:
        human_text = user_req_match.group(1).strip()
        injected_text = USER_REQUEST_RE.sub("", raw).strip()
        if injected_text:
            return {
                "prompt_kind": "mixed",
                "is_human": bool(human_text),
                "human_content": human_text,
                "injected_content": injected_text,
            }
        return {
            "prompt_kind": "human_prompt",
            "is_human": True,
            "human_content": human_text,
            "injected_content": "",
        }

    # Check for pure system-reminder / honesty reminder
    if (
        raw.startswith("<system-reminder>")
        or raw.startswith("<system_reminder>")
        or raw.startswith("<system-instruction>")
        or raw.startswith("<system-reminders>")
        or raw.startswith("<academicOps honesty reminder>")
        or raw.startswith("<system-context>")
    ):
        return {
            "prompt_kind": "system_reminder",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for pure hook-injected envelopes
    if (
        raw.startswith("<ADDITIONAL_METADATA>")
        or raw.startswith("<USER_SETTINGS_CHANGE>")
        or raw.startswith("<context>")
        or raw.startswith("<SYSTEM_MESSAGE>")
        or raw.startswith("<hooks>")
    ):
        return {
            "prompt_kind": "hook_injected_context",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for skill preamble
    if (
        raw.startswith("<skill_instructions>")
        or raw.startswith("Skill routing:")
        or raw.startswith("Skill preamble:")
    ):
        return {
            "prompt_kind": "skill_preamble",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for command output
    if raw.startswith("Command output:") or raw.startswith("!"):
        return {
            "prompt_kind": "command_output",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check for tool result
    if raw.startswith("Tool result:") or raw.startswith("[Tool output"):
        return {
            "prompt_kind": "tool_result",
            "is_human": False,
            "human_content": "",
            "injected_content": raw,
        }

    # Check if there are embedded injected tags within the prompt
    tag_pattern = re.compile(
        r"<(system-reminder|system_reminder|system-instruction|system-reminders|academicOps honesty reminder|ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|context|SYSTEM_MESSAGE|skill_instructions)[^>]*>.*",
        re.DOTALL,
    )
    tag_match = tag_pattern.search(raw)
    if tag_match:
        start_idx = tag_match.start()
        human_part = raw[:start_idx].strip()
        injected_part = raw[start_idx:].strip()
        if human_part:
            return {
                "prompt_kind": "mixed",
                "is_human": True,
                "human_content": human_part,
                "injected_content": injected_part,
            }
        else:
            tag_name = tag_match.group(1)
            kind = (
                "system_reminder"
                if "reminder" in tag_name or "instruction" in tag_name
                else "hook_injected_context"
            )
            return {
                "prompt_kind": kind,
                "is_human": False,
                "human_content": "",
                "injected_content": injected_part,
            }

    # Otherwise, it is human content
    return {
        "prompt_kind": "human_prompt",
        "is_human": True,
        "human_content": raw,
        "injected_content": "",
    }
