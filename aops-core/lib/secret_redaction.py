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

Apply :func:`redact_secrets` to rendered text and :func:`redact_obj` to a
JSON-serialisable object (redacts string *values*, never keys or structure).
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

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

_ASSIGN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Shell:  export FOO_TOKEN=value   /   FOO_TOKEN='value'
    (
        re.compile(
            rf"((?:export\s+)?{_SENSITIVE_NAME})(\s*=\s*)(['\"]?)([^\s'\"]+)(['\"]?)",
            re.IGNORECASE,
        ),
        rf"\1\2\3{REDACTED}\5",
    ),
    # JSON / YAML:  "FOO_TOKEN": "value"   /   FOO_TOKEN: value
    (
        re.compile(
            rf"(\"?{_SENSITIVE_NAME}\"?\s*:\s*)(['\"]?)([^\s'\",}}]+)(['\"]?)",
            re.IGNORECASE,
        ),
        rf"\1\2{REDACTED}\4",
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
    for pattern, repl in _ASSIGN_PATTERNS:
        text = pattern.sub(repl, text)
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def redact_obj(obj: Any) -> Any:
    """Recursively redact string *values* in a JSON-serialisable object.

    Walks dicts and lists, applying :func:`redact_secrets` to every string
    value. Dict keys, numbers, booleans, and ``None`` pass through untouched so
    the structure (and any consumer's schema) is preserved.
    """
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj
