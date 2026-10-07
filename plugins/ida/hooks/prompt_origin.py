"""Who wrote a UserPromptSubmit prompt: Nic, another agent, or both.

Nic's text is hydrated from the PKB. A message from an agent gets the hearsay
reminder and arms the premise-check gate. The harness batches queued messages
into one prompt, so a prompt can carry both, and then it gets both treatments.

The rules are deliberately loose so they survive changes to the harness's
wrapper formats on Claude Code and agy:

- An agent message is any ``<...-message>`` or ``<...-notification>`` block
  (``cross-session-message``, ``teammate-message`` and ``task-notification``
  today), up to its close tag or the end of the prompt.
- Nic's text is what is left once agent blocks, ``<system-reminder>`` blocks
  and Claude Code's peer preamble and trailer are removed, with tag markup
  stripped. A Telegram ``<channel>`` or an agy ``<USER_REQUEST>`` therefore
  contributes its body. If the boilerplate wording changes, the cost is one
  wasted search.

Nothing here is authenticated. A message that imitates a wrapper is taken at
its word.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_AGENT_BLOCK = re.compile(
    r"<((?!command-)[\w-]+-(?:message|notification))\b[^>]*>.*?(?:</\1>|\Z)", re.DOTALL
)
_SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?(?:</system-reminder>|\Z)", re.DOTALL)
_PEER_BOILERPLATE = re.compile(
    r"^Another Claude session sent a message:\s*$|^This came from another Claude session\b.*$",
    re.MULTILINE,
)
_USER_REQUEST = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL)
_TAG = re.compile(r"</?[A-Za-z][\w:-]*(?:\s[^<>]*)?/?>")


@dataclass(frozen=True)
class PromptOrigin:
    nic_text: str
    from_agent: bool


def classify_prompt(prompt: str) -> PromptOrigin:
    text = _SYSTEM_REMINDER.sub(" ", prompt or "")
    text, agent_blocks = _AGENT_BLOCK.subn(" ", text)
    text = _TAG.sub(" ", _PEER_BOILERPLATE.sub(" ", text))
    return PromptOrigin(nic_text=" ".join(text.split()), from_agent=agent_blocks > 0)


def prompt_from_payload(raw: dict) -> str:
    """The prompt text of a UserPromptSubmit payload, on Claude Code or agy.

    agy's PreInvocation payload carries no prompt, only ``transcriptPath``,
    whose latest ``USER_INPUT`` step holds it inside ``<USER_REQUEST>``,
    followed by harness metadata. PreInvocation also fires once per model
    invocation within a turn; only the first (``invocationNum`` 0) is the
    prompt arriving, so the later ones read as empty.
    """
    value = raw.get("prompt")
    if isinstance(value, dict):
        value = value.get("text") or value.get("content")
    if value:
        return str(value)
    if str(raw.get("invocationNum", "0")) != "0":
        return ""
    return _last_user_input(raw.get("transcriptPath"))


def _last_user_input(path: object) -> str:
    if not path:
        return ""
    try:
        lines = Path(str(path)).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            step = json.loads(line)
        except ValueError:
            continue
        if isinstance(step, dict) and step.get("type") == "USER_INPUT":
            content = str(step.get("content") or "")
            request = _USER_REQUEST.search(content)
            return request.group(1) if request else content
    return ""
