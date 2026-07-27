"""Write-time secret redaction for session artifacts (aops-9f290e36).

Session transcripts (``transcripts/*.md``) and insight summaries
(``summaries/*.json``) are committed to the GitHub-backed sessions repo. A
``bash`` tool that runs ``export``/``env``, or any command that echoes a
credential, would otherwise land verbatim in those files. On 2026-06-01 a full
environment dump (GH PAT, Anthropic OAuth, Tailscale authkey, etc.) leaked into
``summaries/user-prompts-2026-06.txt`` exactly this way.

This module scrubs known credential shapes at write time. It is deliberately
pattern-based — known token prefixes plus sensitively-named ``KEY=VALUE``
assignments — rather than entropy-based, to avoid mangling ordinary prose. It
is the producer-side facet of the structural secret-leakage epic
(``aops-00c0fa10``); a pre-commit secret linter is the complementary backstop.

Apply :func:`redact_obj` to anything with structure — a JSON sidecar, a tool
call's arguments — *before* it is serialised, and :func:`redact_secrets` only to
text that is already its final form (Markdown, HTML, the prompt ledger).
Running the regexes over serialised JSON is wrong twice over: a match that abuts
an escaped quote eats the backslash and re-emits a bare ``"``, terminating the
string and producing a file that will not parse; and a value whose quotes are
escaped (``"KEY=\\"secret\\""``) puts the credential outside the match, so it
survives. Redacting the parsed values cannot damage the structure, because the
serialiser escapes whatever redaction leaves behind.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

REDACTED = "[REDACTED]"

# A bare integer or float is never a credential. Used to spare usage-metric
# keys like ``input_tokens: 12345`` from over-matching ``_SENSITIVE_NAME``
# components like ``TOKEN`` (matched as the plural ``_tokens`` suffix).
_NUMERIC_VALUE = re.compile(r"-?\d+(?:\.\d+)?")

# Standalone token shapes — the whole match is replaced with the marker.
_TOKEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub PAT / OAuth / user-server / refresh
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),  # GitHub fine-grained PAT
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),  # Anthropic API key
    re.compile(r"\bsk-[A-Za-z0-9]{32,}"),  # OpenAI-style key
    re.compile(r"\btskey-[A-Za-z0-9-]{10,}"),  # Tailscale auth key
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack token
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),  # Google API key
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
]

# Component matching a sensitively-named identifier (GH_TOKEN, ANTHROPIC_API_KEY,
# ZOTERO_API_KEY, *_SECRET, etc.). Used to redact the VALUE while keeping the
# name visible, so the artifact still records that a secret was present.
_SENSITIVE_NAME = (
    r"[A-Za-z0-9_]*"
    r"(?:TOKEN|API[_-]?KEY|SECRET|PASSWORD|PASSWD|AUTHKEY|AUTH[_-]?TOKEN|"
    r"CREDENTIAL|PRIVATE[_-]?KEY|ACCESS[_-]?KEY|CLIENT[_-]?SECRET|OAUTH|BEARER)"
    r"[A-Za-z0-9_]*"
)

# The same identifier standing alone as a mapping key, so a structural walk can
# recognise the name that the text pass would have read across the `":"`.
_SENSITIVE_KEY = re.compile(_SENSITIVE_NAME, re.IGNORECASE)


def _redact_shell_assign(m: re.Match[str]) -> str:
    # Spare numeric values: ``input_tokens=12345`` is a usage metric, not a
    # credential. Real tokens are never bare integers/floats.
    if _NUMERIC_VALUE.fullmatch(m.group(4)):
        return m.group(0)
    return f"{m.group(1)}{m.group(2)}{m.group(3)}{REDACTED}{m.group(5)}"


def _redact_yaml_json_assign(m: re.Match[str]) -> str:
    if _NUMERIC_VALUE.fullmatch(m.group(3)):
        return m.group(0)
    return f"{m.group(1)}{m.group(2)}{REDACTED}{m.group(4)}"


_ASSIGN_PATTERNS: list[tuple[re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    # Shell:  export FOO_TOKEN=value   /   FOO_TOKEN='value'
    (
        re.compile(
            rf"((?:export\s+)?{_SENSITIVE_NAME})(\s*=\s*)(['\"]?)([^\s'\"]+)(['\"]?)",
            re.IGNORECASE,
        ),
        _redact_shell_assign,
    ),
    # JSON / YAML:  "FOO_TOKEN": "value"   /   FOO_TOKEN: value
    (
        re.compile(
            rf"(\"?{_SENSITIVE_NAME}\"?\s*:\s*)(['\"]?)([^\s'\",}}]+)(['\"]?)",
            re.IGNORECASE,
        ),
        _redact_yaml_json_assign,
    ),
]


def redact_secrets(text: str) -> str:
    """Return ``text`` with known credential shapes replaced by ``[REDACTED]``.

    Redacts (a) sensitively-named assignments (``GH_TOKEN=...``, ``"api_key":
    "..."``) keeping the name but scrubbing the value, and (b) standalone token
    shapes (``ghp_...``, ``sk-ant-...``, JWTs, etc.) anywhere in the text.
    Non-secret text is returned unchanged.
    """
    if not text or not isinstance(text, str):
        return text
    for pattern, replacer in _ASSIGN_PATTERNS:
        text = pattern.sub(replacer, text)
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def _is_sensitive_key(key: Any) -> bool:
    """True when a mapping key is itself a credential-shaped identifier."""
    return isinstance(key, str) and _SENSITIVE_KEY.fullmatch(key) is not None


def redact_obj(obj: Any, *, under_sensitive_key: bool = False) -> Any:
    """Recursively redact a JSON-serialisable object, structure preserved.

    Three things are scrubbed, and together they cover everything the text pass
    catches when the same object is serialised first:

    - Every string, through :func:`redact_secrets` — the assignments and token
      shapes that live *inside* one value.
    - Any string reached under a sensitively-named key (``{"ZOTERO_API_KEY":
      "aB3x..."}``). Serialised, that is the text ``"ZOTERO_API_KEY": "aB3x..."``
      and the assignment regex spans the key/value boundary; walking values one
      at a time never sees the name, so the name has to be carried down. Numeric
      strings are spared for the same reason ``input_tokens: 12345`` is.
    - Keys, through :func:`redact_secrets`, so a credential used *as* a key is
      not left standing by a walk that only looks at values.

    Numbers, booleans, and ``None`` pass through untouched: no credential shape
    is a bare scalar, and rewriting them would break every consumer's schema.
    """
    if isinstance(obj, str):
        if under_sensitive_key and not _NUMERIC_VALUE.fullmatch(obj):
            return REDACTED
        return redact_secrets(obj)
    if isinstance(obj, dict):
        return {
            (redact_secrets(k) if isinstance(k, str) else k): redact_obj(
                v, under_sensitive_key=under_sensitive_key or _is_sensitive_key(k)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_obj(v, under_sensitive_key=under_sensitive_key) for v in obj]
    return obj
