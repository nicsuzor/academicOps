"""Pre-push / pre-PR task-body mandatory gate (epic-50b5ade9.3).

Blocks `git push` and `gh pr create` when a worker session's task body declares
mandatory gate markers (e.g. "MUST", "mandatory", "before PR", "before push",
"James re-review", "QA verdict", "marsha verdict") that have not yet recorded
satisfaction evidence (e.g. an APPROVE verdict) for the session.

Gating mode is controlled via $TASK_BODY_GATE_MODE:
- "off"   : gate is disabled (default).
- "warn"  : emits an advisory warning without denying the tool call.
- "block" : refuses/denies the push/PR tool call until the gate is satisfied.

Overrides:
- $TASK_BODY_GATE_OVERRIDE=1 (or true/yes)
- $AOP_FORCE=1 or $AOP_OVERRIDE=1
- Command containing --override-gate
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, refuse, warn

# Markers indicating a push or PR creation command
_PUSH_PR_PATTERNS = [
    re.compile(r"\bgit\s+push\b", re.IGNORECASE),
    re.compile(r"\bgh\s+pr\s+create\b", re.IGNORECASE),
]

# Mandatory requirement indicators in task body
_MANDATORY_WORDS = re.compile(r"\b(MUST|mandatory|required)\b", re.IGNORECASE)
_TIMING_WORDS = re.compile(r"\b(before\s+(?:PR|push|pull\s+request))\b", re.IGNORECASE)

# Known gate types and their matchers
_GATE_DETECTORS: dict[str, re.Pattern] = {
    "james": re.compile(r"(?:James(?:\s+re-review)?(?:\s+APPROVE)?|code\s+review)", re.IGNORECASE),
    "marsha": re.compile(r"(?:marsha(?:\s+verdict|\s+APPROVE)?|QA\s+verdict)", re.IGNORECASE),
    "adversary": re.compile(
        r"(?:adversary(?:\s+verdict|\s+APPROVE)?|red-team\s+verdict)", re.IGNORECASE
    ),
}


def _verdict_dir() -> Path:
    """Directory used to store session gate verdicts."""
    override = os.environ.get("AOPS_VERDICTS_DIR")
    if override:
        path = Path(override)
    else:
        path = Path(tempfile.gettempdir()) / "aops_gate_verdicts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _verdict_file(session_id: str) -> Path:
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    return _verdict_dir() / f"{safe_session}.json"


def record_gate_verdict(
    session_id: str,
    gate: str,
    verdict: str = "APPROVE",
    detail: str = "",
) -> None:
    """Record satisfaction evidence (verdict) for a gate in a session."""
    target = _verdict_file(session_id)
    records: dict[str, Any] = {}
    if target.exists():
        try:
            records = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            records = {}
    gate_key = gate.lower().strip()
    records[gate_key] = {
        "verdict": verdict.upper().strip(),
        "detail": detail,
    }
    target.write_text(json.dumps(records, indent=2), encoding="utf-8")


def get_recorded_verdicts(session_id: str) -> dict[str, dict[str, str]]:
    """Retrieve all recorded verdicts for a given session."""
    verdicts: dict[str, dict[str, str]] = {}
    target = _verdict_file(session_id)
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        verdicts[k.lower()] = {
                            "verdict": str(v.get("verdict", "")).upper(),
                            "detail": str(v.get("detail", "")),
                        }
                    elif isinstance(v, str):
                        verdicts[k.lower()] = {"verdict": v.upper(), "detail": ""}
        except Exception:
            pass

    # Also inspect environment variable AOPS_GATE_VERDICTS
    env_verdicts = os.environ.get("AOPS_GATE_VERDICTS", "")
    if env_verdicts:
        for item in env_verdicts.split(","):
            if ":" in item:
                g, v = item.split(":", 1)
                verdicts[g.strip().lower()] = {"verdict": v.strip().upper(), "detail": "env"}

    # Also inspect individual AOPS_GATE_SATISFIED_<GATE>
    for k, v in os.environ.items():
        if k.startswith("AOPS_GATE_SATISFIED_") and v in ("1", "true", "TRUE", "yes", "YES"):
            gate_name = k[len("AOPS_GATE_SATISFIED_") :].lower()
            verdicts[gate_name] = {"verdict": "APPROVE", "detail": "env"}

    return verdicts


def clear_recorded_verdicts(session_id: str) -> None:
    """Clear verdicts for a session (useful in tests)."""
    target = _verdict_file(session_id)
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass


def is_push_or_pr_command(command: str) -> bool:
    """Detect whether a command string attempts a git push or gh pr create."""
    if not command:
        return False
    return any(p.search(command) is not None for p in _PUSH_PR_PATTERNS)


def parse_mandatory_gates(task_body: str) -> list[str]:
    """Parse a task body string and extract all declared mandatory gates.

    Returns a list of detected gate names (e.g. ['james', 'marsha']).
    """
    if not task_body:
        return []

    gates: list[str] = []
    # Search for mandatory phrases line by line or section by section
    for line in task_body.splitlines():
        has_mandatory = _MANDATORY_WORDS.search(line) is not None
        has_timing = _TIMING_WORDS.search(line) is not None

        if has_mandatory or has_timing:
            for gate_name, detector in _GATE_DETECTORS.items():
                if detector.search(line):
                    if gate_name not in gates:
                        gates.append(gate_name)

            # Generic fallback if mandatory + timing present without specific detector
            if (has_mandatory and has_timing) and not gates:
                gates.append("review")

    # If no line-by-line match, search whole text for combined mandatory patterns
    if not gates:
        for gate_name, detector in _GATE_DETECTORS.items():
            if (
                _MANDATORY_WORDS.search(task_body)
                and detector.search(task_body)
                and _TIMING_WORDS.search(task_body)
            ):
                if gate_name not in gates:
                    gates.append(gate_name)

    return gates


def _is_override_active(command: str) -> bool:
    """Check if human/maintainer override is requested."""
    for var in ("TASK_BODY_GATE_OVERRIDE", "AOP_FORCE", "AOP_OVERRIDE"):
        val = os.environ.get(var, "").strip().lower()
        if val in ("1", "true", "yes"):
            return True
    if "--override-gate" in command:
        return True
    return False


def _get_task_body(ctx: HookContext) -> str:
    """Retrieve task body from context, environment, or file."""
    # 1. Check explicit raw payload
    if ctx.raw.get("task_body"):
        return str(ctx.raw["task_body"])
    if isinstance(ctx.raw.get("task"), dict) and ctx.raw["task"].get("body"):
        return str(ctx.raw["task"]["body"])

    # 2. Check environment variable
    env_body = os.environ.get("AOPS_TASK_BODY") or os.environ.get("TASK_BODY")
    if env_body:
        return env_body

    # 3. Check prompt if it contains task body
    prompt = str(ctx.raw.get("prompt") or "")
    if "MUST" in prompt or "mandatory" in prompt or "before PR" in prompt:
        return prompt

    # 4. Check session task file if exists
    if ctx.session_id:
        sessions_root = os.environ.get("AOPS_SESSIONS")
        if sessions_root:
            task_file = Path(sessions_root) / ctx.session_id / "task.md"
            if task_file.exists():
                try:
                    return task_file.read_text(encoding="utf-8")
                except Exception:
                    pass

    return ""


def task_body_gate_handler(ctx: HookContext) -> Result | None:
    """PreToolUse handler checking for unsatisfied task-body mandatory gates."""
    command = ctx.command or (
        ctx.raw.get("tool_input", {}).get("command", "")
        if isinstance(ctx.raw.get("tool_input"), dict)
        else ""
    )
    if not is_push_or_pr_command(command):
        return None

    mode = os.environ.get("TASK_BODY_GATE_MODE", "off").strip().lower()
    if mode == "off":
        return None

    if _is_override_active(command):
        return None

    task_body = _get_task_body(ctx)
    if not task_body:
        return None

    mandatory_gates = parse_mandatory_gates(task_body)
    if not mandatory_gates:
        return None

    verdicts = get_recorded_verdicts(ctx.session_id)
    unsatisfied: list[str] = []

    for gate in mandatory_gates:
        record = verdicts.get(gate.lower())
        if not record or record.get("verdict") not in ("APPROVE", "PASS", "APPROVED"):
            unsatisfied.append(gate)

    if not unsatisfied:
        return None

    gate_list_str = ", ".join(f"'{g}'" for g in unsatisfied)
    reason = (
        f"Task body specifies mandatory gate(s) [{gate_list_str}] before push/PR, "
        f"but no satisfaction verdict (APPROVE) has been recorded for session '{ctx.session_id or 'current'}'. "
        f"Obtain the required gate verdict before pushing or creating a PR."
    )
    user_msg = f"Task-body mandatory gate blocked push/PR: missing verdict for {gate_list_str}."

    if mode == "warn":
        return warn(reason, user_msg)
    elif mode == "block":
        return refuse(reason, user_msg)

    return None
