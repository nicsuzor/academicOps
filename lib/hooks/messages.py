"""Message loading: all injected wording lives in markdown, never a Python literal.

A handler names a message; the runtime loads ``hooks/messages/<name>.md`` from
the plugin's own hooks directory (the directory ``dispatch.py`` runs from). A
missing or empty message file is a hard error — logged loudly, never a silent
empty injection.
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
