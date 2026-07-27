"""Message loading: all injected wording lives in markdown, never a Python literal.

A handler names a message; the runtime loads ``hooks/messages/<name>.md`` from
the plugin's own hooks directory (the directory ``dispatch.py`` runs from). A
missing or empty message file is a hard error — logged loudly, never a silent
empty injection.

A message has two readers, and they need different things. The agent gets the
full text, injected into its context, where length buys precision. The person
watching gets one line in their terminal telling them what just fired, where
length buys nothing and costs attention. So a message may ship a second file,
``<name>.user.md``, holding that line.

A sibling file rather than frontmatter in ``<name>.md``, for two reasons. This
module runs inside a hook subprocess with nothing importable beyond the
standard library, so frontmatter would mean hand-rolling a parser here and
every malformed delimiter would leak markup into the agent's context. And the
two texts are edited for different readers — keeping them in separate files
means revising the user's line cannot disturb the agent's.
"""

from __future__ import annotations

from pathlib import Path


class MessageNotFoundError(RuntimeError):
    """Raised when a hook message file is missing or empty."""


def load(hooks_dir: Path, name: str) -> str:
    """Load ``<hooks_dir>/messages/<name>.md``, stripped of surrounding whitespace.

    Raises:
        MessageNotFoundError: the file does not exist, or exists but is empty.
    """
    path = Path(hooks_dir) / "messages" / f"{name}.md"
    if not path.exists():
        raise MessageNotFoundError(f"hook message file missing: {path}")
    text = path.read_text().strip()
    if not text:
        raise MessageNotFoundError(f"hook message file is empty: {path}")
    return text


def load_user(hooks_dir: Path, name: str) -> str | None:
    """The one-line user-facing version of ``<name>``, or ``None``.

    Absent is the ordinary case, not an error: a hook with nothing worth
    saying in a status line says nothing there. An empty file reads as absent
    for the same reason — the alternative is a blank line in the user's
    terminal, which is strictly worse than silence.
    """
    path = Path(hooks_dir) / "messages" / f"{name}.user.md"
    if not path.exists():
        return None
    return path.read_text().strip() or None


def load_pair(hooks_dir: Path, name: str) -> tuple[str, str | None]:
    """``(agent text, user line or None)`` — what ``result.warn`` takes.

    Raises:
        MessageNotFoundError: the agent's message is missing or empty.
    """
    return load(hooks_dir, name), load_user(hooks_dir, name)
