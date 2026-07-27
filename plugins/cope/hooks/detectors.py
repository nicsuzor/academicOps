"""Built-in PreToolUse detectors.

A hook sees a tool name and its input, not intent. Six of the sixteen
axioms have a shape that is actually visible at that surface — a literal
pattern in a Bash command string or a tool's file path. The other ten
(``honest-epistemics``, ``cite-sources``, ``do-one-thing``, ``closure``,
``categorical-imperative``, ``exercise-authority``, ``judgment-non-delegable``,
``full-observability``'s reasoning half, ``single-source-of-truth``,
``pull-over-push``, ``synthesize-not-accrete``) require reading and
understanding what the agent is claiming or intends, which a tool call does
not carry — cope does not pretend to check them here. See
plugins/cope/README.md.

Each detector takes the hook's ``HookContext`` and returns the matched
snippet as a string (something to echo back to the agent as evidence — see
``honest-epistemics``/``cite-sources``: show, don't tell) or ``None`` if
nothing matched. A match is a signal that triggers a human-legible advisory,
never a verdict — the detectors are syntactic pattern checks, not a stand-in
for the qualitative judgment call about whether the axiom was actually
violated (judgment-non-delegable's carve-out: deterministic syntactic
checks are not the judgment they flag for review).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from context import HookContext

Detector = Callable[["HookContext"], "str | None"]


def _bash_command(ctx: "HookContext") -> str:
    return ctx.command if ctx.tool == "Bash" else ""


def _first_match(patterns: list[str], text: str, *, flags: int = 0) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(0)
    return None


_BOUNDED_EXECUTION_PATTERNS = [
    r"\btail\s+-[a-zA-Z]*f\b",
    r"--follow\b",
    r"--watch\b",
    r"\bwatch\s+-?n?\d*\s",
    r"\bwhile\s+true\b",
    r"\byes\s*\|",
]


def detect_bounded_execution(ctx: "HookContext") -> str | None:
    """No visible terminating bound: follow/watch/tail-f/while-true shapes."""
    command = _bash_command(ctx)
    if not command:
        return None
    return _first_match(_BOUNDED_EXECUTION_PATTERNS, command)


_COSTLY_OPS_PATTERNS = [
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b",
    r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r\b",
    r"\bgit\s+push\b[^\n]*(--force\b|(?<!-)-f\b)",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-zA-Z]*f",
    r"\bgit\s+branch\s+-D\b",
    r"\bDROP\s+(TABLE|DATABASE)\b",
    r"\bTRUNCATE\s+TABLE\b",
    r"\bfind\b[^\n]*-delete\b",
    r"\bxargs\s+rm\b",
]


def detect_costly_ops_approval(ctx: "HookContext") -> str | None:
    """High-blast-radius or destructive shapes: force-push, hard reset,
    recursive delete, drop/truncate, mass find -delete."""
    command = _bash_command(ctx)
    if not command:
        return None
    return _first_match(_COSTLY_OPS_PATTERNS, command, flags=re.IGNORECASE)


_HALT_ON_FAILURE_PATTERNS = [
    r"--no-verify\b",
    r"--no-gpg-sign\b",
    r"-c\s+commit\.gpgsign=false",
    r"core\.hooksPath=/dev/null",
]


def detect_halt_on_failure(ctx: "HookContext") -> str | None:
    """Bypassing a validation gate instead of fixing the failure."""
    command = _bash_command(ctx)
    if not command:
        return None
    return _first_match(_HALT_ON_FAILURE_PATTERNS, command)


_DATA_BOUNDARY_PATH_KEYS = ("file_path", "path", "pattern", "notebook_path")

_DATA_BOUNDARY_PATTERNS = [
    r"\.env\b",
    r"credentials\.json",
    r"\bid_rsa\b",
    r"\.pem\b",
    r"\.netrc\b",
    r"\.aws/credentials",
    r"\.ssh/",
    r"secrets?\.ya?ml\b",
]


def detect_data_boundaries(ctx: "HookContext") -> str | None:
    """A call touching a path that looks like a credential or secret file."""
    parts: list[str] = []
    command = _bash_command(ctx)
    if command:
        parts.append(command)
    tool_input = ctx.raw.get("tool_input")
    if isinstance(tool_input, dict):
        for key in _DATA_BOUNDARY_PATH_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str):
                parts.append(value)
    haystack = " ".join(parts)
    if not haystack:
        return None
    return _first_match(_DATA_BOUNDARY_PATTERNS, haystack)


_EVIDENCE_PATH_PATTERNS = [
    r"/fixtures?/",
    r"/golden/",
    r"/evidence/",
    r"/testdata/",
    r"\.golden\.",
]


def detect_evidence_immutable(ctx: "HookContext") -> str | None:
    """An Edit/Write targeting a path that looks like fixture/golden/evidence data."""
    if ctx.tool not in ("Edit", "Write"):
        return None
    tool_input = ctx.raw.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return None
    match = _first_match(_EVIDENCE_PATH_PATTERNS, path)
    return path if match else None


_SUPPRESSED_OUTPUT_PATTERN = (
    r">\s*/dev/null\s*2>&1|2>&1\s*>\s*/dev/null|2>\s*/dev/null\s+1?>&?\s*/dev/null"
)
_MUTATING_VERB_PATTERN = r"\bgit\s+(commit|push)\b|\brm\s+-|\bmv\s+"


def detect_full_observability(ctx: "HookContext") -> str | None:
    """A mutating action (commit, push, rm, mv) whose output is discarded,
    leaving no trace to audit."""
    command = _bash_command(ctx)
    if not command:
        return None
    if not re.search(_SUPPRESSED_OUTPUT_PATTERN, command):
        return None
    if not re.search(_MUTATING_VERB_PATTERN, command):
        return None
    return command


# Registration order is the tiebreak when a single call matches more than
# one detector (evaluate() in handlers.py returns the first hit).
DETECTORS: dict[str, Detector] = {
    "bounded-execution": detect_bounded_execution,
    "costly-ops-approval": detect_costly_ops_approval,
    "halt-on-failure": detect_halt_on_failure,
    "data-boundaries": detect_data_boundaries,
    "evidence-immutable": detect_evidence_immutable,
    "full-observability": detect_full_observability,
}
