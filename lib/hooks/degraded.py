"""The hook framework's own failures, given a reader.

A hook that degrades has always said so on stderr. Nothing renders a hook's
stderr to the person running the session: the client captures it into the
transcript and shows them only what the response JSON puts in
``systemMessage``. So a check that stopped working stopped working invisibly —
true of the process, false of the human. This module is the missing reader.

One call here replaces one ``print(..., file=sys.stderr)``. ``report`` still
writes the same line to stderr, because that is the log and the log is right;
it additionally records the fault so ``attach`` can put it on the wire — the
precise reason into the agent's context, one short sentence to the person
watching.

**What counts.** A degradation is a mechanism that was supposed to run and did
not. It is not the absence of a mechanism nobody configured: cope with no
evaluator set is a legitimate state and stays silent, exactly as
``evaluator.resolve()`` already draws that line. Report a fault only where the
alternative is a silent loss of something the session was relying on.

**Rate.** These hooks fire on ``PreToolUse``, so a line per tool call is a line
the user learns to skip past, and a notice nobody reads is worse than none. A
fault is therefore announced at most once per session per ``kind`` — the
identity of the mechanism that broke, not the identity of the occurrence. A
dead evaluator says so once, not once per rule per call; the second unreadable
rule file adds nothing the first did not already send the person to look at.
Kinds are a small fixed vocabulary, so a whole session can produce at most that
many lines however badly it is broken.

One hook invocation is one process, so that gate cannot live in memory. It is a
zero-length marker file per (session, kind), claimed with ``O_CREAT | O_EXCL``,
under the directory the OS names for temporary files — no path is compiled in,
and the file name is a digest so a session id read from the payload can never
name a path of its own. Claiming is the announcement: whoever creates the
marker speaks, everyone else stays quiet. A payload carrying no session id
cannot be rate-limited at all, and then nothing goes on the wire — an unbounded
notice is worse than the stderr line by itself.

**Fail-open, without exception.** Nothing here raises into dispatch, and
nothing here can block: ``attach`` only ever adds an advisory, or a user line
beside a refusal that was already going to be made. A degradation notice is
never a gate.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import messages
from result import Result, warn

#: A registered handler raised, or a plugin's ``handlers.py`` would not load —
#: either way a check the session was relying on did not run.
HANDLER = "hook-handler"

#: The session env file could not be written (credentials.py).
CREDENTIALS = "session-credentials"

#: The message pair carrying both readers' wording, in this hook's own
#: ``messages/`` directory (shipped from ``lib/hooks/messages/``).
_MESSAGE = "degraded"

#: Filled by the loaded message text; one fault block per line for the agent,
#: one sentence per kind for the person watching.
_PLACEHOLDER = "{faults}"

#: Where the once-per-session markers live, under ``tempfile.gettempdir()``.
_MARKER_DIR = "aops-hook-faults"


@dataclass(frozen=True)
class Fault:
    kind: str  # the rate-limit key: which mechanism broke, not which occurrence
    message: str  # one sentence, written for a person; both readers see it
    detail: str  # the precise reason — stderr and the agent only


_faults: list[Fault] = []


def report(kind: str, message: str, detail: str = "") -> None:
    """Record one degradation, and log it exactly as before.

    ``message`` is one sentence a person can act on — what stopped working and
    what that costs them. ``detail`` is the machine-precise reason (an
    exception repr, the failures a remote call came back with); it reaches the
    log and the agent, and is kept out of the user's line, which has room for
    one fact only.
    """
    print(f"{message}: {detail}" if detail else message, file=sys.stderr)
    _faults.append(Fault(kind, message, detail))


def reset() -> None:
    """Drop everything recorded so far. For tests, which share one process."""
    _faults.clear()


def attach(result: Result | None, hooks_dir: Path, session_id: str) -> Result | None:
    """Fold this process's un-announced faults into the response.

    Returns ``result`` untouched when there is nothing new to say, when the
    payload carries no session id to rate-limit against, or when composing the
    notice fails for any reason — a fault report that breaks the hook it was
    reporting on would be the worst outcome available here.
    """
    try:
        return _attach(result, hooks_dir, session_id)
    except Exception as exc:  # noqa: BLE001 - a notice may never break the hook
        print(f"aops hooks: could not render a degradation notice: {exc!r}", file=sys.stderr)
        return result


def _attach(result: Result | None, hooks_dir: Path, session_id: str) -> Result | None:
    if not _faults or not session_id:
        return result

    announced = [
        kind for kind in dict.fromkeys(f.kind for f in _faults) if _claim(session_id, kind)
    ]
    if not announced:
        return result
    faults = [fault for fault in _faults if fault.kind in announced]

    agent_text, user_text = messages.load_pair(hooks_dir, _MESSAGE)
    agent = agent_text.replace(_PLACEHOLDER, _for_agent(faults))
    user = user_text.replace(_PLACEHOLDER, _for_user(faults)) if user_text else None

    if result is None:
        return warn(agent, user)
    combined = " ".join(line for line in (result.user_text, user) if line) or None
    if result.is_refusal:
        # The denial reason is the whole contract of a refusal; the notice rides
        # on the user's line instead of diluting it.
        return Result(result.inject_text, combined, is_refusal=True)
    return Result(f"{result.inject_text}\n\n{agent}", combined)


def _for_agent(faults: list[Fault]) -> str:
    """Every fault, with its reason. The agent is the reader who can use it."""
    return "\n".join(
        f"- {fault.message}: {fault.detail}" if fault.detail else f"- {fault.message}"
        for fault in faults
    )


def _for_user(faults: list[Fault]) -> str:
    """One sentence per broken mechanism — the first occurrence's, which is the
    one that names where to look. Repeats of the same kind add length, not
    information."""
    first: dict[str, str] = {}
    for fault in faults:
        first.setdefault(fault.kind, fault.message)
    return "; ".join(first.values())


def _claim(session_id: str, kind: str) -> bool:
    """True for exactly one hook process in this session, for this kind.

    A failure to claim and an already-claimed marker are the same answer on
    purpose: both mean this process does not speak. Silence is the only bounded
    response to a rate limiter that cannot do its job, and the stderr line has
    already been written either way.
    """
    try:
        root = Path(tempfile.gettempdir()) / _MARKER_DIR
        root.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(f"{session_id}\0{kind}".encode()).hexdigest()[:32]
        os.close(os.open(root / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except OSError:
        return False
