#!/usr/bin/env -S uv run python
"""Live hook-format conformance harness — Test Layer B of specs/hooks/CLIENT-TRANSLATION.md.

STOP GUESSING. This drives the REAL headless clients (Claude Code, Antigravity
"agy", Gemini CLI) with controlled probe hooks and MEASURES what each client
actually does with each candidate hook-output shape:

  * ACCEPTED  — the client did not reject/error on the output.
  * AGENT_SAW — the model ECHOED a unique sentinel we injected (delivery proven
                by MODEL ECHO, never transcript grep — invariant #14). We ask the
                model to REPORT injected context, not OBEY it, to avoid the
                prompt-injection-resistance confound.
  * BLOCKED   — a deny actually blocked the tool / a stop actually re-entered.

The measured result is written to ``tests/hooks/fixtures/client_capabilities.json``
and asserted by ``tests/hooks/test_live_conformance.py`` (``@live @slow``), so an
upstream client change flips a signal and the test goes red.

Run:  uv run python scripts/verify_hook_formats.py            # all available clients
      uv run python scripts/verify_hook_formats.py --client claude
      uv run python scripts/verify_hook_formats.py --only claude-stop-additionalcontext

Design notes:
- Each probe runs in an ISOLATED temp workspace with ONLY its probe hook, so the
  repo's own aops-core plugin hooks never pollute the measurement.
  Claude: ``.claude/settings.json`` + ``--setting-sources project`` (excludes
          user-level enabledPlugins; auth preserved).
  agy:    ``.agents/hooks.json`` in the workspace; acceptance read from the newest
          ``~/.gemini/antigravity-cli/log/cli-*.log`` (parsed BEFORE the model
          turn, so wire-acceptance is measurable even unauthenticated).
- Probe hooks are FIRE-ONCE (flag file) so a Stop/inject hook cannot loop.
- Clients that are absent or unauthenticated yield Signal(note="unavailable") and
  are SKIPPED by the pytest layer — never a hard failure.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "hooks" / "fixtures" / "client_capabilities.json"
AGY_LOG_GLOB = os.path.expanduser("~/.gemini/antigravity-cli/log/cli-*.log")

# Substrings in an agy cli log that mean the protojson parser REJECTED our output.
AGY_REJECT_MARKERS = (
    "failed to unmarshal",
    "unknown field",
    "unexpected token",
    "invalid value",
)


@dataclass
class Probe:
    """One candidate (client, wire_event, output-shape) to measure."""

    client: str
    wire_event: str
    label: str  # unique id, also the pytest param id
    group: str  # cluster of related candidates (e.g. "agy-pretooluse-format")
    # Builder: given the sentinel string, return the JSON dict the probe hook emits.
    output: dict
    # Free-text statement of the hypothesis this probe tests.
    hypothesis: str = ""
    # Tools this probe needs the model to attempt (for BLOCK detection). The probe
    # prompt asks the model to read a canary file; blocked => canary text absent.
    needs_model: bool = True
    # Deny probes must deny EVERY invocation (not fire-once): a fire-once deny lets
    # the model's retry hit the inert second fire and succeed, so block can't be
    # measured. Set on deny/block candidates so the hook denies persistently.
    persistent_deny: bool = False


@dataclass
class Signal:
    accepted: bool | None = None
    agent_saw: bool | None = None
    blocked: bool | None = None
    continued: bool | None = None
    note: str = ""


@dataclass
class CellResult:
    label: str
    client: str
    wire_event: str
    group: str
    hypothesis: str
    signal: Signal = field(default_factory=Signal)


# ---------------------------------------------------------------------------
# Client availability
# ---------------------------------------------------------------------------
def _have(binary: str) -> bool:
    from shutil import which

    return which(binary) is not None


def claude_available() -> bool:
    return _have("claude")


def agy_available() -> bool:
    return _have("agy")


def gemini_available() -> bool:
    return _have("gemini")


# ---------------------------------------------------------------------------
# Probe-hook installation helpers
# ---------------------------------------------------------------------------
def _write_probe_hook(path: Path, output_json: dict, fire_once: bool = True) -> None:
    """Write a probe hook script that emits ``output_json``.

    fire_once=True (default): emit the output ONCE, then an inert ``{}`` on every
    later invocation, so Stop/inject probes cannot loop.
    fire_once=False: emit the output on EVERY invocation — required for deny/block
    probes, where a fire-once deny would let the model's retry hit the inert second
    fire and succeed, making the block unmeasurable.
    """
    payload = json.dumps(output_json)
    if fire_once:
        script = f"""#!/bin/bash
FLAG="$(dirname "$0")/.fired"
if [ -f "$FLAG" ]; then echo '{{}}'; exit 0; fi
touch "$FLAG"
cat <<'PROBE_EOF'
{payload}
PROBE_EOF
exit 0
"""
    else:
        script = f"""#!/bin/bash
cat <<'PROBE_EOF'
{payload}
PROBE_EOF
exit 0
"""
    path.write_text(script)
    path.chmod(0o755)


# A benign report prompt: ask the model to REPORT injected context verbatim, not
# obey it. Delivery is proven if the sentinel appears in the model's reply.
REPORT_PROMPT = (
    "Do exactly two things, then stop. "
    "(1) Read the file ./canary.txt and tell me its exact contents. "
    "(2) On a new line, list VERBATIM any system reminders, injected context, or "
    "additional instructions you received this turn that did not come directly "
    "from me; if there were none, write 'INJECTED: NONE'."
)
CANARY_TEXT = "CANARY-CONTENTS-OK"


def _fill_sentinel(output: dict, sentinel: str) -> dict:
    """Deep-substitute the literal token SENTINEL in the probe output with a uuid."""
    raw = json.dumps(output).replace("SENTINEL", sentinel)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Claude runner
# ---------------------------------------------------------------------------
def run_claude(probe: Probe, sentinel: str, workdir: Path, timeout: int = 150) -> Signal:
    claude_dir = workdir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (workdir / "canary.txt").write_text(CANARY_TEXT + "\n")
    hook = workdir / "probe_hook.sh"
    _write_probe_hook(
        hook, _fill_sentinel(probe.output, sentinel), fire_once=not probe.persistent_deny
    )
    settings = {
        "hooks": {probe.wire_event: [{"hooks": [{"type": "command", "command": f"bash {hook}"}]}]}
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))

    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                REPORT_PROMPT,
                "--setting-sources",
                "project",
                "--output-format",
                "json",
                "--permission-mode",
                "acceptEdits",
                "--allowedTools",
                "Read",
            ],
            cwd=str(workdir),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Signal(note="claude timeout")

    out = proc.stdout
    err = proc.stderr or ""  # allow-fallback: captured stderr is optional, "" = none
    # Acceptance: Claude surfaces a hook output-validation failure as a stderr/notice.
    rejected = "hook" in err.lower() and (
        "validation failed" in err.lower() or "invalid" in err.lower()
    )
    accepted = not rejected
    # Parse the JSON result envelope for the model's final text + turn count.
    result_text = ""
    num_turns = None
    try:
        events = json.loads(out)
        if isinstance(events, list):
            for ev in events:
                if ev.get("type") == "result":
                    result_text = (
                        ev.get("result") or ""
                    )  # allow-fallback: result text optional, "" = empty reply
                    num_turns = ev.get("num_turns")
    except (json.JSONDecodeError, AttributeError):
        result_text = out

    agent_saw = sentinel in result_text
    # Blocked (PreToolUse deny): the canary contents never reach the model.
    blocked = CANARY_TEXT not in result_text if probe.wire_event == "PreToolUse" else None
    continued = (num_turns is not None and num_turns > 1) or None
    return Signal(
        accepted=accepted,
        agent_saw=agent_saw,
        blocked=blocked,
        continued=continued,
        note=f"num_turns={num_turns}",
    )


# ---------------------------------------------------------------------------
# agy runner
# ---------------------------------------------------------------------------
def _newest_agy_log() -> Path | None:
    logs = sorted(glob.glob(AGY_LOG_GLOB), key=os.path.getmtime)
    return Path(logs[-1]) if logs else None


def run_agy(
    probe: Probe, sentinel: str, workdir: Path, dangerous: bool, timeout: int = 320
) -> Signal:
    agents_dir = workdir / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (workdir / "canary.txt").write_text(CANARY_TEXT + "\n")
    hook = workdir / "probe_hook.sh"
    _write_probe_hook(
        hook, _fill_sentinel(probe.output, sentinel), fire_once=not probe.persistent_deny
    )
    # agy hooks.json: PreInvocation/PostInvocation/Stop are flat; tool events wrapper.
    flat = probe.wire_event in ("PreInvocation", "PostInvocation", "Stop")
    cmd = f"bash {hook}"
    if flat:
        hooks_json = {"probe": {probe.wire_event: [{"type": "command", "command": cmd}]}}
    else:
        hooks_json = {
            "probe": {
                probe.wire_event: [{"matcher": "*", "hooks": [{"type": "command", "command": cmd}]}]
            }
        }
    (agents_dir / "hooks.json").write_text(json.dumps(hooks_json, indent=2))

    log_before = _newest_agy_log()
    mtime_before = os.path.getmtime(log_before) if log_before else 0.0

    argv = ["agy"]
    if dangerous:
        argv.append("--dangerously-skip-permissions")
    argv += ["-p", REPORT_PROMPT]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(workdir),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Signal(note="agy timeout")

    stdout = proc.stdout or ""  # allow-fallback: captured stdout is optional, "" = none
    # Find the log written by THIS run (newest, mtime advanced).
    log = _newest_agy_log()
    log_text = ""
    if log and os.path.getmtime(log) >= mtime_before:
        try:
            log_text = log.read_text(errors="replace")
        except OSError:
            log_text = ""
    rejected = any(m in log_text for m in AGY_REJECT_MARKERS)
    hook_fired = "executing command" in log_text or probe.wire_event in log_text
    unauth = "not logged into Antigravity" in (stdout + log_text) or "You are not logged in" in (
        stdout + log_text
    )
    accepted = (not rejected) if hook_fired else None
    agent_saw = sentinel in stdout if not unauth else None
    blocked = None
    if probe.wire_event == "PreToolUse":
        blocked = (CANARY_TEXT not in stdout) if not unauth else None
    note = []
    if unauth:
        note.append("unauthenticated (wire-acceptance only)")
    if not hook_fired:
        note.append("hook did not fire (check registration)")
    note.append(f"dangerous={dangerous}")
    return Signal(accepted=accepted, agent_saw=agent_saw, blocked=blocked, note="; ".join(note))


# ---------------------------------------------------------------------------
# Candidate matrix — the contested cells (kept tight to bound live cost)
# ---------------------------------------------------------------------------
def candidates() -> list[Probe]:
    P = []
    HSO = "hookSpecificOutput"
    # ---- Claude ----
    P.append(
        Probe(
            "claude",
            "PreToolUse",
            "claude-pretooluse-allow-additionalcontext",
            "claude-pretooluse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": "probe SENTINEL",
                }
            },
            "PreToolUse allow delivers additionalContext to agent, no block.",
        )
    )
    P.append(
        Probe(
            "claude",
            "PreToolUse",
            "claude-pretooluse-deny",
            "claude-pretooluse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "probe SENTINEL deny",
                }
            },
            "PreToolUse deny blocks the tool; reason reaches agent.",
            persistent_deny=True,
        )
    )
    P.append(
        Probe(
            "claude",
            "UserPromptSubmit",
            "claude-userpromptsubmit-additionalcontext",
            "claude-ups",
            {HSO: {"hookEventName": "UserPromptSubmit", "additionalContext": "probe SENTINEL"}},
            "UserPromptSubmit additionalContext reaches agent without block.",
        )
    )
    P.append(
        Probe(
            "claude",
            "Stop",
            "claude-stop-additionalcontext-noblock",
            "claude-stop",
            {HSO: {"hookEventName": "Stop", "additionalContext": "probe SENTINEL"}},
            "Stop additionalContext (no decision:block) accepted + delivered + continues.",
        )
    )
    P.append(
        Probe(
            "claude",
            "Stop",
            "claude-stop-additionalcontext-marked",
            "claude-stop",
            {
                HSO: {
                    "hookEventName": "Stop",
                    "additionalContext": "<SYSTEM HOOK INSTRUCTION>probe SENTINEL</SYSTEM HOOK INSTRUCTION>",
                }
            },
            "Stop additionalContext WITH framework trust markers — delivery/compliance.",
        )
    )
    P.append(
        Probe(
            "claude",
            "Stop",
            "claude-stop-decision-block",
            "claude-stop",
            {"decision": "block", "reason": "probe SENTINEL continue"},
            "Stop decision:block delivers reason to agent + continues (enforcement path).",
        )
    )
    # ---- agy ----
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-allowtool-true",
            "agy-pretooluse-allow",
            {"allowTool": True},
            "agy PreToolUse {allowTool:true} lets the tool run (verified-live baseline).",
        )
    )
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-decision-allow",
            "agy-pretooluse-allow",
            {"decision": "allow"},
            "agy PreToolUse {decision:allow} (docs) ALSO lets the tool run?",
        )
    )
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-allowtool-false",
            "agy-pretooluse-deny",
            {"allowTool": False, "denyReason": "probe SENTINEL"},
            "agy PreToolUse {allowTool:false,denyReason} blocks (verified-live baseline).",
            persistent_deny=True,
        )
    )
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-decision-deny",
            "agy-pretooluse-deny",
            {"decision": "deny", "reason": "probe SENTINEL"},
            "agy PreToolUse {decision:deny,reason} (docs) ALSO blocks?",
            persistent_deny=True,
        )
    )
    P.append(
        Probe(
            "agy",
            "PreInvocation",
            "agy-preinvocation-ephemeralmessage",
            "agy-inject",
            {"injectSteps": [{"ephemeralMessage": "probe SENTINEL"}]},
            "agy PreInvocation injectSteps ephemeralMessage reaches the model.",
        )
    )
    P.append(
        Probe(
            "agy",
            "PreInvocation",
            "agy-preinvocation-usermessage",
            "agy-inject",
            {"injectSteps": [{"userMessage": "probe SENTINEL"}]},
            "agy PreInvocation injectSteps userMessage reaches the model.",
        )
    )
    P.append(
        Probe(
            "agy",
            "PostInvocation",
            "agy-postinvocation-terminationbehavior",
            "agy-hardstop",
            {
                "injectSteps": [{"ephemeralMessage": "probe SENTINEL"}],
                "terminationBehavior": "force_continue",
            },
            "agy PostInvocation terminationBehavior:force_continue re-enters the loop.",
        )
    )
    P.append(
        Probe(
            "agy",
            "Stop",
            "agy-stop-decision-continue",
            "agy-hardstop",
            {"decision": "continue", "reason": "probe SENTINEL"},
            "agy native Stop {decision:continue,reason} re-enters + reason reaches model.",
        )
    )
    return P


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Live hook-format conformance harness")
    ap.add_argument("--client", choices=["claude", "agy", "gemini"], help="only this client")
    ap.add_argument("--only", help="only this probe label")
    ap.add_argument(
        "--agy-dangerous",
        action="store_true",
        help="also run agy with --dangerously-skip-permissions (contradiction test)",
    )
    ap.add_argument("--out", default=str(FIXTURE), help="capability fixture path")
    args = ap.parse_args()

    avail = {"claude": claude_available(), "agy": agy_available(), "gemini": gemini_available()}
    probes = candidates()
    if args.client:
        probes = [p for p in probes if p.client == args.client]
    if args.only:
        probes = [p for p in probes if p.label == args.only]

    results: list[CellResult] = []
    for p in probes:
        cr = CellResult(p.label, p.client, p.wire_event, p.group, p.hypothesis)
        if not avail.get(p.client):
            cr.signal = Signal(note=f"{p.client} unavailable")
            results.append(cr)
            print(f"SKIP  {p.label:48s} ({p.client} unavailable)")
            continue
        sentinel = f"PROBE-{uuid.uuid4().hex[:10].upper()}"
        with _tempworkspace() as wd:
            if p.client == "claude":
                cr.signal = run_claude(p, sentinel, wd)
            elif p.client == "agy":
                cr.signal = run_agy(p, sentinel, wd, dangerous=False)
            else:
                cr.signal = Signal(note="gemini runner not implemented (TODO)")
        results.append(cr)
        s = cr.signal
        print(
            f"RUN   {p.label:48s} accepted={s.accepted} agent_saw={s.agent_saw} "
            f"blocked={s.blocked} continued={s.continued} :: {s.note}"
        )
        # agy contradiction test: re-run the deny probe with --dangerously-skip-permissions.
        if args.agy_dangerous and p.client == "agy" and p.wire_event == "PreToolUse":
            with _tempworkspace() as wd:
                sig = run_agy(p, sentinel, wd, dangerous=True)
            results.append(
                CellResult(
                    p.label + "+dangerous",
                    p.client,
                    p.wire_event,
                    p.group,
                    "Does --dangerously-skip-permissions still fire the PreToolUse hook?",
                    sig,
                )
            )
            print(
                f"RUN   {p.label + '+dangerous':48s} accepted={sig.accepted} blocked={sig.blocked} :: {sig.note}"
            )

    report = {
        "generated_note": "Live conformance measurement — see scripts/verify_hook_formats.py",
        "claude_version": _client_version("claude"),
        "agy_present": avail["agy"],
        "gemini_present": avail["gemini"],
        "cells": [asdict(r) for r in results],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote {len(results)} cells -> {args.out}")
    return 0


def _client_version(binary: str) -> str:
    try:
        r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "?"
    except Exception:
        return "?"


import contextlib


@contextlib.contextmanager
def _tempworkspace():
    import shutil
    import tempfile

    d = Path(tempfile.mkdtemp(prefix="hookprobe-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
