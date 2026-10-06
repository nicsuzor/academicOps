"""Who is speaking in a UserPromptSubmit prompt: Nic, another agent, or both.

Nic's messages (console prompts, Telegram channel messages) get PKB hydration.
Messages flowing the other way (peer sessions, teammates, background task
results) get the hearsay reminder and arm the premise-check verdict gate.

Wrapper formats come from real ``claude-code-turn`` spans in Phoenix (samples
and span ids in tests/test_prompt_origin.py):

- Telegram: ``<channel source="plugin:telegram:telegram" ...>body</channel>``
- Peer:     ``<cross-session-message from=... from-name=...>...</cross-session-message>``,
            sometimes preceded by "Another Claude session sent a message:" and
            followed by a harness trailer paragraph.
- Teammate: ``<teammate-message teammate_id=...>...</teammate-message>``, same
            preamble/trailer.
- Task:     ``<task-notification>...</task-notification>``

Rules, applied to top-level wrappers only (a wrapper opening at the start of
a line, scanned left to right; anything inside a wrapper is that wrapper's
content and is never re-classified, so a peer report quoting a Telegram line
stays a peer report and vice versa):

- ``<system-reminder>`` blocks are harness text: dropped.
- A Telegram ``<channel>`` contributes its body to ``nic_text``.
- A ``<channel>`` from any other source counts as agent: Nic named only
  Telegram and the console, so unknown channels fail closed onto the gate.
- An agent wrapper sets ``from_agent``. An unterminated one runs to the end.
- Text outside every wrapper is Nic's console text, unless an agent wrapper
  is present -- then it is the harness preamble/trailer and is dropped.

``kind`` is ``nic``, ``agent``, ``mixed`` (both), or ``none`` (empty or
harness-only, e.g. a lone system-reminder: not Nic speaking, not a claim).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_AGENT_TAGS = frozenset({"cross-session-message", "teammate-message", "task-notification"})

_OPEN_RE = re.compile(
    r"^[ \t]*<(cross-session-message|teammate-message|task-notification|channel|system-reminder)"
    r"\b([^>]*)>",
    re.MULTILINE,
)
_SOURCE_RE = re.compile(r'\bsource="([^"]*)"')


@dataclass(frozen=True)
class PromptOrigin:
    nic_text: str
    from_agent: bool

    @property
    def kind(self) -> str:
        if self.nic_text and self.from_agent:
            return "mixed"
        if self.from_agent:
            return "agent"
        if self.nic_text:
            return "nic"
        return "none"


def classify_prompt(prompt: str) -> PromptOrigin:
    text = prompt or ""
    nic_parts: list[str] = []
    outside: list[str] = []
    from_agent = False
    pos = 0

    while (m := _OPEN_RE.search(text, pos)) is not None:
        outside.append(text[pos : m.start()])
        tag = m.group(1)
        close_tag = f"</{tag}>"
        close = text.find(close_tag, m.end())
        body_end = len(text) if close < 0 else close
        pos = len(text) if close < 0 else close + len(close_tag)

        if tag == "system-reminder":
            continue
        if tag == "channel":
            source = _SOURCE_RE.search(m.group(2))
            if source and "telegram" in source.group(1):
                body = text[m.end() : body_end].strip()
                if body:
                    nic_parts.append(body)
            else:
                from_agent = True
            continue
        if tag in _AGENT_TAGS:
            from_agent = True

    outside.append(text[pos:])
    loose = "".join(outside).strip()
    if loose and not from_agent:
        nic_parts.insert(0, loose)

    return PromptOrigin(nic_text="\n\n".join(nic_parts), from_agent=from_agent)


def prompt_from_payload(raw: dict) -> str:
    """The prompt string from a UserPromptSubmit payload, whatever its shape."""
    value = raw.get("prompt")
    if isinstance(value, dict):
        value = value.get("text") or value.get("content") or ""
    return str(value or "")
