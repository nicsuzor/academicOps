"""Where the agent CLIs write transcripts, and what a container can see of them.

Two callers need this, for opposite reasons:

- `transcripts.runner` collects finished top-level sessions for the batch render
  pipeline and drops subagent sidechains.
- A supervisor asking what the workers it spawned actually did wants the
  sidechains — they *are* the workers — and has no host session store to read.

Both resolve the same client state roots, defined here once. Every root follows
the home the process is actually running under, so the same call answers on a
host and inside a container. Beyond that the two clients differ, and the
difference is not cosmetic: Claude Code honours `$CLAUDE_CONFIG_DIR` and this
module honours it too, while agy exposes no equivalent lever, so its roots are
its own fixed on-disk layout under home and nothing in the environment moves
them.

`find_container_transcripts` is the container-local view. It reads only the
client state roots, never `$AOPS_SESSIONS`, which is a host-side value polecat
does not forward into a container (`lib/polecat/env_contract.py`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from transcripts.adapters.claude import SUBAGENT_DIR_NAME, SUBAGENT_FILE_PREFIX

#: Claude Code names each conversation `<session-uuid>.jsonl`. Matched by shape
#: so a session directory's other `.jsonl` files — polecat's hook log above all —
#: cannot be mistaken for a conversation. This is the only thing keeping the hook
#: log out of the result: it sits at the project root, which the subagent glob
#: below never reaches.
CLAUDE_TRANSCRIPT_NAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$"
)

#: agy keeps one directory per conversation under its brain, and writes both a
#: pruned `transcript.jsonl` and a `transcript_full.jsonl` into it.
AGY_TRANSCRIPT_GLOB = "*/.system_generated/logs/transcript*.jsonl"


def _home(home: Path | str | None = None) -> Path:
    return Path(home) if home is not None else Path.home()


def claude_projects_root(env: dict[str, str] | None = None, home: Path | str | None = None) -> Path:
    """The directory holding one subdirectory per project Claude Code has run in.

    `$CLAUDE_CONFIG_DIR` relocates Claude Code's whole state directory and is
    honoured here for the same reason the client honours it; otherwise the
    client's own convention under the current home applies.
    """
    env = env if env is not None else {}
    configured = env.get("CLAUDE_CONFIG_DIR")
    base = Path(configured) if configured else _home(home) / ".claude"
    return base / "projects"


def agy_brain_roots(home: Path | str | None = None) -> list[Path]:
    """Every directory agy keeps conversation state under.

    Both are agy's own layout under home; it reads no variable that relocates
    them, which is why this takes no `env`. The second is where the brain lands
    when agy runs under polecat: `lib/polecat/cli.py` gives the agy branch
    `AGY_SESSION_PATH` (`~/.gemini/tmp/workspace`) as the container path it
    mounts the session directory at, so `agy-brain` appears beneath it as well as
    at the brain mount proper.
    """
    base = _home(home) / ".gemini"
    return [base / "antigravity-cli" / "brain", base / "tmp" / "workspace" / "agy-brain"]


@dataclass(frozen=True)
class TranscriptRef:
    """One transcript file, and what the filesystem says about who wrote it."""

    path: Path
    #: `claude` or `agy`.
    client: str
    #: `session` for a top-level conversation, `subagent` for a Claude sidechain.
    kind: str
    #: Claude session uuid, subagent file stem, or agy conversation id.
    session_id: str
    #: The trunk a sidechain belongs to; `None` for a top-level conversation.
    parent_id: str | None = None
    #: The agent a sidechain ran as, read from its `.meta.json` when present.
    agent: str | None = None


def _subagent_meta(path: Path) -> str | None:
    meta = path.with_suffix(".meta.json")
    try:
        obj = json.loads(meta.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    for key in ("name", "agentType", "subagent_type"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _claude_refs(root: Path) -> list[TranscriptRef]:
    refs: list[TranscriptRef] = []
    if not root.is_dir():
        return refs
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(project_dir.glob("*.jsonl")):
            if CLAUDE_TRANSCRIPT_NAME.match(path.name):
                refs.append(
                    TranscriptRef(path=path, client="claude", kind="session", session_id=path.stem)
                )
        for path in sorted(project_dir.glob(f"*/{SUBAGENT_DIR_NAME}/**/*.jsonl")):
            if not path.name.startswith(SUBAGENT_FILE_PREFIX):
                continue
            parts = path.relative_to(project_dir).parts
            refs.append(
                TranscriptRef(
                    path=path,
                    client="claude",
                    kind="subagent",
                    session_id=path.stem,
                    parent_id=parts[0],
                    agent=_subagent_meta(path),
                )
            )
    return refs


def _agy_refs(roots: list[Path]) -> list[TranscriptRef]:
    refs: list[TranscriptRef] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob(AGY_TRANSCRIPT_GLOB)):
            # `<conversation-id>/.system_generated/logs/transcript*.jsonl`
            conversation_id = path.relative_to(root).parts[0]
            refs.append(
                TranscriptRef(path=path, client="agy", kind="session", session_id=conversation_id)
            )
    return refs


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def find_container_transcripts(
    env: dict[str, str] | None = None, home: Path | str | None = None
) -> list[TranscriptRef]:
    """Every transcript reachable from the client state roots, newest first.

    Inside a container these roots hold what this container's run wrote — but
    not only that. `lib/polecat/cli.py` derives the session directory it mounts
    as `<sessions>/logs/<YYYYMMDD>/<session-id>/<project>`, so a second run
    given the same `-s` on the same day mounts the same directory and sees the
    earlier run's transcripts too. Read the result as "the conversations under
    this session directory", and use the mtime ordering to tell runs apart.

    On a host the same call returns the local client state, which is the correct
    answer to the same question asked there.
    """
    refs = _claude_refs(claude_projects_root(env, home))
    refs.extend(_agy_refs(agy_brain_roots(home)))
    return sorted(refs, key=lambda ref: _mtime(ref.path), reverse=True)


def _format(ref: TranscriptRef) -> str:
    fields = [ref.client, ref.kind, ref.session_id]
    if ref.agent:
        fields.append(f"agent={ref.agent}")
    if ref.parent_id:
        fields.append(f"parent={ref.parent_id}")
    return "\t".join([*fields, str(ref.path)])


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(
        description="List the transcripts reachable from this machine's client state roots."
    )
    parser.add_argument(
        "--client", choices=("claude", "agy"), help="Restrict output to one client."
    )
    parser.add_argument(
        "--kind", choices=("session", "subagent"), help="Restrict output to one kind."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON objects instead of columns.")
    args = parser.parse_args(argv)

    refs = find_container_transcripts(dict(os.environ))
    if args.client:
        refs = [ref for ref in refs if ref.client == args.client]
    if args.kind:
        refs = [ref for ref in refs if ref.kind == args.kind]

    if args.json:
        print(
            json.dumps(
                [{**vars(ref), "path": str(ref.path)} for ref in refs],
                indent=2,
            )
        )
    else:
        for ref in refs:
            print(_format(ref))
    if not refs:
        print("no transcripts under the client state roots", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
