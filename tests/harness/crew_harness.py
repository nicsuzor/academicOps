#!/usr/bin/env python3
"""Minimal tmux harness for driving an interactive `polecat crew` session.

The agent invokes this on direction from the user. It is NOT a test suite —
no scenarios, no analyzer, no semantic judgment. The agent drives the
interaction and reads the pane to decide whether the session went up in smoke.

Mechanical checks only: did tmux start, did the pane capture, did artifacts
land in $AOPS_SESSIONS.

Subcommands:
  start [-g] [--name N] [--target aops]   spawn a tmux session running polecat crew
  send  <tmux_session> <text>             type text + Enter into the pane
  pane  <tmux_session>                    print pane contents to stdout
  end   <tmux_session> <since_iso>        send /exit, collect artifacts, kill tmux

Typical agent flow:
  out=$(crew_harness.py start)            # prints: TMUX=... SINCE=...
  crew_harness.py send "$TMUX" 'hello'
  crew_harness.py pane "$TMUX"
  crew_harness.py end  "$TMUX" "$SINCE" --out artifacts/run1
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _aops_sessions() -> Path:
    p = os.environ.get("AOPS_SESSIONS")
    if not p:
        sys.exit("AOPS_SESSIONS not set")
    return Path(p)


def _polecat_cmd() -> list[str]:
    # `polecat` is a zsh alias; tmux launches via /bin/sh, so we resolve the
    # real entry point. Honour AOPS env, fall back to repo-root sibling.
    aops = os.environ.get("AOPS") or str(Path(__file__).resolve().parents[2])
    return ["uv", "run", "--project", aops, f"{aops}/polecat/cli.py"]


def cmd_start(args: argparse.Namespace) -> int:
    tmux = f"crew-{secrets.token_hex(3)}"
    polecat_args = _polecat_cmd() + ["crew"]
    if args.gemini:
        polecat_args.append("-g")
    if args.name:
        polecat_args += ["-n", args.name]
    polecat_args.append(args.target)

    since = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Mark the start so `find -newer` can locate artifacts deterministically.
    marker = Path(f"/tmp/crew_harness_{tmux}.marker")
    marker.touch()

    # Pass argv as one shell-quoted string so tmux's /bin/sh launcher gets
    # the right tokens even when paths contain spaces.
    import shlex

    r = _run(
        ["tmux", "new-session", "-d", "-s", tmux, "-x", "220", "-y", "50", shlex.join(polecat_args)]
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return r.returncode

    print(f"TMUX={tmux}")
    print(f"SINCE={since}")
    print(f"MARKER={marker}")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    # send-keys with -l sends literal text (no key translation), then Enter.
    r1 = _run(["tmux", "send-keys", "-t", args.tmux, "-l", args.text])
    r2 = _run(["tmux", "send-keys", "-t", args.tmux, "Enter"])
    if r1.returncode or r2.returncode:
        print((r1.stderr + r2.stderr), file=sys.stderr)
        return r1.returncode or r2.returncode
    if args.wait:
        time.sleep(args.wait)
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    # Raw tmux key names (Enter, Up, Down, Escape, etc) — for navigating menus.
    r = _run(["tmux", "send-keys", "-t", args.tmux, *args.keys])
    if r.returncode:
        print(r.stderr, file=sys.stderr)
    if args.wait:
        time.sleep(args.wait)
    return r.returncode


def cmd_pane(args: argparse.Namespace) -> int:
    # -p prints to stdout; -S -<n> grabs n lines of scrollback.
    r = _run(["tmux", "capture-pane", "-t", args.tmux, "-p", "-S", f"-{args.scrollback}"])
    if r.returncode:
        print(r.stderr, file=sys.stderr)
        return r.returncode
    sys.stdout.write(r.stdout)
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # 1. Capture the pane before anything else (in case /exit clears it).
    pane = _run(["tmux", "capture-pane", "-t", args.tmux, "-p", "-S", "-5000"])
    (out / "pane.log").write_text(pane.stdout)

    # 2. Ask the worker to exit cleanly so SessionEnd hook fires.
    _run(["tmux", "send-keys", "-t", args.tmux, "-l", "/exit"])
    _run(["tmux", "send-keys", "-t", args.tmux, "Enter"])

    # 3. Wait for the SessionEnd hook to flush before tearing down tmux.
    deadline = time.time() + args.timeout
    sessions = _aops_sessions()
    marker = Path(args.marker) if args.marker else None
    found_session_end = False
    while time.time() < deadline:
        if _has_session_end(sessions, args.since, marker):
            found_session_end = True
            break
        time.sleep(1)

    # 4. Before killing tmux, snapshot the container's hooks/transcripts —
    #    polecat's `_extract_gemini_sessions` only runs on clean exit, so a
    #    forced teardown would lose them.
    container_extracts = _extract_from_containers(out)

    # 5. Kill tmux regardless — we captured what we could.
    _run(["tmux", "kill-session", "-t", args.tmux])

    # 6. Bundle every artifact newer than SINCE into out/.
    bundled = _bundle_artifacts(sessions, args.since, marker, out)
    bundled.extend(container_extracts)

    # 6. Mechanical summary on stdout — the agent reads this and decides.
    print(f"OUT={out}")
    print(f"SESSION_END_SEEN={found_session_end}")
    print(f"ARTIFACT_COUNT={len(bundled)}")
    for p in bundled:
        print(f"  {p.relative_to(out)}")
    if marker and marker.exists():
        marker.unlink()
    return 0 if bundled else 2


def _has_session_end(sessions: Path, since: str, marker: Path | None) -> bool:
    for hooks in _iter_recent(sessions / "hooks", since, marker, suffix=".jsonl"):
        try:
            for line in hooks.read_text().splitlines():
                if '"SessionEnd"' in line or '"hook_event_name":"SessionEnd"' in line.replace(
                    " ", ""
                ):
                    return True
        except OSError:
            continue
    return False


def _iter_recent(root: Path, since: str, marker: Path | None, suffix: str = ""):
    if not root.exists():
        return
    cutoff = _parse_iso(since)
    marker_mtime = marker.stat().st_mtime if marker and marker.exists() else None
    for p in root.rglob(f"*{suffix}"):
        if not p.is_file():
            continue
        mt = p.stat().st_mtime
        if marker_mtime is not None and mt < marker_mtime:
            continue
        if marker_mtime is None and mt < cutoff:
            continue
        yield p


def _extract_from_containers(out: Path) -> list[Path]:
    """Pull hooks/state files out of any running aops-crew container.

    Polecat normally syncs these on clean exit. The harness defends against the
    case where the worker is wedged (auth wall, prompt loop) and we can't get a
    clean exit — in that scenario the artifacts only exist inside the container.
    """
    bundled: list[Path] = []
    r = _run(["docker", "ps", "--filter", "ancestor=aops-crew", "--format", "{{.Names}}"])
    if r.returncode != 0:
        return bundled
    for name in [n for n in r.stdout.splitlines() if n.strip()]:
        dst = out / "container" / name
        dst.mkdir(parents=True, exist_ok=True)
        for src in ("/home/worker/.gemini/tmp", "/home/worker/.claude"):
            cp = _run(["docker", "cp", f"{name}:{src}/.", str(dst / Path(src).name)])
            if cp.returncode == 0:
                for p in (dst / Path(src).name).rglob("*"):
                    if p.is_file():
                        bundled.append(p)
    return bundled


def _bundle_artifacts(sessions: Path, since: str, marker: Path | None, out: Path) -> list[Path]:
    bundled: list[Path] = []
    for sub in ("hooks", "summaries", "transcripts"):
        src_root = sessions / sub
        for src in _iter_recent(src_root, since, marker):
            dst = out / sub / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            bundled.append(dst)
    return bundled


def _parse_iso(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def main() -> int:
    ap = argparse.ArgumentParser(prog="crew_harness", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="spawn tmux + polecat crew")
    s.add_argument("-g", "--gemini", action="store_true")
    s.add_argument("-n", "--name")
    s.add_argument("--target", default="aops")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("send", help="type text + Enter into the pane")
    s.add_argument("tmux")
    s.add_argument("text")
    s.add_argument("--wait", type=float, default=0.0, help="sleep after sending")
    s.set_defaults(func=cmd_send)

    s = sub.add_parser("keys", help="send raw tmux keys (Enter, Up, Down, ...)")
    s.add_argument("tmux")
    s.add_argument("keys", nargs="+", help="e.g. 'Down' 'Down' 'Enter'")
    s.add_argument("--wait", type=float, default=0.0)
    s.set_defaults(func=cmd_keys)

    s = sub.add_parser("pane", help="print pane contents")
    s.add_argument("tmux")
    s.add_argument("--scrollback", type=int, default=2000)
    s.set_defaults(func=cmd_pane)

    s = sub.add_parser("end", help="exit cleanly, bundle artifacts, kill tmux")
    s.add_argument("tmux")
    s.add_argument("since", help="ISO Z timestamp from `start`")
    s.add_argument("--out", default="tests/harness/artifacts/last")
    s.add_argument("--marker", help="path to marker file from `start`")
    s.add_argument(
        "--timeout", type=float, default=15.0, help="seconds to wait for SessionEnd hook"
    )
    s.set_defaults(func=cmd_end)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
