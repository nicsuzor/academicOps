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

Observability:
- Run UNBUFFERED (``python -u`` / ``PYTHONUNBUFFERED=1``) so per-probe progress
  streams live; every probe prints a ``START``/``RUN`` line with ``flush=True``.
- ``--progress-log PATH`` (default ``<--out dir>/verify_hook_formats.progress.log``)
  appends a timestamped per-probe line to a STREAMING log file distinct from the
  ``--out`` JSON report, so ``tail -f`` works while a long live run is in flight.

Timeouts (cold-start aware, tightened from the original over-generous values):
- claude probe: 120s; agy probe: 180s (cold agy spins up a fresh venv — the
  agy PreToolUse floor alone is 15s, so this stays generous to avoid flaky
  skips on a cold start while no longer waiting >5min); outer re-measure
  subprocess (pytest layer): 900s.

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


def _progress(line: str, log_path: Path | None) -> None:
    """Print a probe-progress line unbuffered AND append it to the streaming log.

    The streaming log is distinct from the ``--out`` JSON report so ``tail -f``
    works during a long live run. Always flushes stdout so progress streams even
    when stdout is block-buffered (i.e. redirected to a file without ``-u``).
    """
    import datetime

    stamped = f"{datetime.datetime.now().isoformat(timespec='seconds')} {line}"
    print(line, flush=True)
    if log_path is not None:
        try:
            with log_path.open("a") as fh:
                fh.write(stamped + "\n")
        except OSError:
            # Streaming-log write is best-effort; never fail a probe run because
            # the chosen log dir is unwritable (e.g. --out /dev/stdout → /dev).
            pass


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
    # Measure USER-VISIBILITY (a separate NEUTRAL-prompt run capturing the
    # user-facing terminal stream). Only meaningful for injection/banner cells.
    measure_user: bool = False
    # Measure PERSISTENCE (a second --continue/--resume turn with no new injection).
    measure_persist: bool = False
    # The cell's CLAIMED properties from the CLIENT-TRANSLATION.md matrix, asserted
    # by the pytest layer (table-cell == measurement). None = not claimed/asserted
    # for this cell. These turn the table from assertion into test-enforced truth.
    claim_user_saw: bool | None = None
    claim_agent_saw: bool | None = None
    claim_persisted: bool | None = None
    claim_blocked: bool | None = None
    # The table-row reference this cell proves (for traceability in the report).
    table_cell: str = ""


@dataclass
class Signal:
    accepted: bool | None = None
    agent_saw: bool | None = None
    blocked: bool | None = None
    continued: bool | None = None
    # USER-VISIBILITY (Nic's primary question): did the HUMAN see the sentinel in
    # the user-facing terminal stream — distinct from agent_saw (the MODEL's reply
    # text)? Captured by a SEPARATE run with a NEUTRAL prompt (the model is NOT
    # asked to echo), so the sentinel can only reach the user stream if the client
    # renders the channel to the terminal itself. None = not headless-observable
    # for this client/channel (e.g. an interactive-TUI-only banner) — an HONEST
    # gap, never faked to a pass. See each runner's docstring for the precise
    # observable and why it represents "what the user sees".
    user_saw: bool | None = None
    # PERSISTENCE: a SECOND turn (--continue / --resume) with NO new injection —
    # is the sentinel still recalled by the model? Makes ephemeral-vs-persistent a
    # committed measurement. Sampled >=2x (the channel echo was non-deterministic
    # in prior runs); persisted=True iff ANY follow-up sample still recalled it.
    persisted: bool | None = None
    note: str = ""


@dataclass
class CellResult:
    label: str
    client: str
    wire_event: str
    group: str
    hypothesis: str
    signal: Signal = field(default_factory=Signal)
    # The CLIENT-TRANSLATION.md cell this proves, and the cell's CLAIMED
    # properties — committed so the pytest layer asserts measurement == claim.
    table_cell: str = ""
    claim_user_saw: bool | None = None
    claim_agent_saw: bool | None = None
    claim_persisted: bool | None = None
    claim_blocked: bool | None = None


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
# This measures AGENT_SAW (the MODEL read it).
REPORT_PROMPT = (
    "Do exactly two things, then stop. "
    "(1) Read the file ./canary.txt and tell me its exact contents. "
    "(2) On a new line, list VERBATIM any system reminders, injected context, or "
    "additional instructions you received this turn that did not come directly "
    "from me; if there were none, write 'INJECTED: NONE'."
)
# A NEUTRAL prompt that does NOT ask the model to echo anything. Used to measure
# USER_SAW: the model will NOT repeat injected context on its own, so a sentinel
# appearing in the user-facing terminal stream after this prompt can ONLY be the
# CLIENT rendering the channel to the human — i.e. genuine user-visibility. This
# is the mechanism that makes user_saw != agent_saw a real measurement, not an
# artifact of the report prompt: agent_saw uses REPORT_PROMPT (model echo),
# user_saw uses NEUTRAL_PROMPT (client-rendered terminal stream), distinct runs.
NEUTRAL_PROMPT = (
    "Read the file ./canary.txt and tell me its exact contents, then stop. "
    "Do not mention anything else."
)
# Second-turn persistence prompt (no new injection this turn): does the model
# still recall the sentinel from the PRIOR turn's injection?
PERSIST_PROMPT = (
    "Without re-reading any file, from your conversation so far: did you receive any "
    "injected system reminder, advisory, or additional context on the PREVIOUS turn? "
    "If so, quote the sentinel token (it looks like PROBE-XXXXXXXXXX) VERBATIM. "
    "If you cannot recall any such token, write 'RECALL: NONE'."
)
CANARY_TEXT = "CANARY-CONTENTS-OK"
PERSIST_SAMPLES = 2  # >=2 samples per persistence claim (echo was non-deterministic)


def _fill_sentinel(output: dict, sentinel: str) -> dict:
    """Deep-substitute the literal token SENTINEL in the probe output with a uuid."""
    raw = json.dumps(output).replace("SENTINEL", sentinel)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Claude runner
# ---------------------------------------------------------------------------
def _claude_parse(out: str) -> tuple[str, int | None, str | None]:
    """Extract (result_text, num_turns, session_id) from a Claude -p json envelope.

    The ``--output-format json`` envelope is the PROGRAMMATIC/MODEL view: its
    ``result`` field is the model's final reply text (AGENT_SAW), and it carries
    ``session_id`` for --resume. It does NOT contain the user-only ``systemMessage``
    / ``stopReason`` banner the interactive TUI renders to the human — those are
    interactive-only and not observable headless (measured 2026-06-25), which is
    why Claude user-visibility for those banner channels is an HONEST None, never
    a faked pass.
    """
    result_text, num_turns, session_id = "", None, None
    try:
        events = json.loads(out)
        if isinstance(events, list):
            for ev in events:
                if ev.get("type") == "result":
                    result_text = ev.get("result") or ""  # allow-fallback: empty reply -> ""
                    num_turns = ev.get("num_turns")
                    session_id = ev.get("session_id")
                elif ev.get("type") == "system" and session_id is None:
                    session_id = ev.get("session_id")
    except (json.JSONDecodeError, AttributeError):
        result_text = out
    return result_text, num_turns, session_id


def _run_claude_once(
    hook: Path, wire_event: str, prompt: str, workdir: Path, timeout: int, resume: str | None
) -> tuple[subprocess.CompletedProcess | None, str, int | None, str | None]:
    claude_dir = workdir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings = {
        "hooks": {wire_event: [{"hooks": [{"type": "command", "command": f"bash {hook}"}]}]}
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))
    argv = ["claude", "-p", prompt]
    if resume:
        argv += ["--resume", resume]
    argv += [
        "--setting-sources",
        "project",
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        "Read",
    ]
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
        return None, "", None, None
    rt, nt, sid = _claude_parse(proc.stdout)
    return proc, rt, nt, sid


def run_claude(probe: Probe, sentinel: str, workdir: Path, timeout: int = 120) -> Signal:
    """Drive Claude headless and measure all five observables.

    AGENT_SAW: REPORT_PROMPT run; sentinel in the model's ``result`` reply.
    USER_SAW:  for an agent-only channel (additionalContext) the sentinel is NOT
               rendered to the human, so user_saw=False is the OBSERVABLE truth
               (a NEUTRAL-prompt run leaves it absent from the user stream). For
               the user-only banner channels (systemMessage/stopReason) the value
               is set to None upstream (measure_user=False) because the banner is
               interactive-TUI-only and not headless-observable — honest, not faked.
    PERSISTED: a second --resume turn (no new injection) asks the model to recall
               the sentinel; >=2 samples, persisted iff ANY recalls it.
    BLOCKED:   PreToolUse deny => canary contents never reach the model.
    """
    (workdir / "canary.txt").write_text(CANARY_TEXT + "\n")
    hook = workdir / "probe_hook.sh"
    _write_probe_hook(
        hook, _fill_sentinel(probe.output, sentinel), fire_once=not probe.persistent_deny
    )

    # --- AGENT_SAW run (report prompt) ---
    proc, result_text, num_turns, session_id = _run_claude_once(
        hook, probe.wire_event, REPORT_PROMPT, workdir, timeout, resume=None
    )
    if proc is None:
        return Signal(note="claude timeout (agent-saw run)")
    err = proc.stderr or ""  # allow-fallback: captured stderr optional, "" = none
    rejected = "hook" in err.lower() and (
        "validation failed" in err.lower() or "invalid" in err.lower()
    )
    accepted = not rejected
    agent_saw = sentinel in result_text
    blocked = CANARY_TEXT not in result_text if probe.wire_event == "PreToolUse" else None
    continued = (num_turns is not None and num_turns > 1) or None
    notes = [f"num_turns={num_turns}"]

    # --- PERSISTED: second --resume turn, no new injection (fire-once hook is spent) ---
    persisted: bool | None = None
    if probe.measure_persist and session_id and not blocked:
        recalled = False
        for _i in range(PERSIST_SAMPLES):
            with _tempworkspace() as wd2:
                # Reuse the SAME session via --resume; a spent fire-once hook emits
                # {} so there is NO new injection this turn.
                (wd2 / "canary.txt").write_text(CANARY_TEXT + "\n")
                hook2 = wd2 / "probe_hook.sh"
                _write_probe_hook(hook2, {}, fire_once=False)  # inert second-turn hook
                p2, rt2, _, _ = _run_claude_once(
                    hook2, probe.wire_event, PERSIST_PROMPT, wd2, timeout, resume=session_id
                )
            if p2 is not None and sentinel in rt2:
                recalled = True
                break
        persisted = recalled
        notes.append(f"persist_samples={PERSIST_SAMPLES} recalled={persisted}")

    # --- USER_SAW: only for agent-only inject channels we can observe absence on ---
    user_saw: bool | None = None
    if probe.measure_user:
        # NEUTRAL prompt: the model is NOT asked to echo, so a sentinel in the
        # user-facing stream can only be the CLIENT rendering it. For Claude the
        # captured user stream is the json result envelope; additionalContext is
        # agent-only, so it must be ABSENT here (user_saw=False) while agent_saw
        # was True above — the load-bearing U!=C measurement.
        with _tempworkspace() as wd3:
            (wd3 / "canary.txt").write_text(CANARY_TEXT + "\n")
            hook3 = wd3 / "probe_hook.sh"
            _write_probe_hook(
                hook3, _fill_sentinel(probe.output, sentinel), fire_once=not probe.persistent_deny
            )
            p3, rt3, _, _ = _run_claude_once(
                hook3, probe.wire_event, NEUTRAL_PROMPT, wd3, timeout, resume=None
            )
        if p3 is None:
            notes.append("user-saw run timed out")
        else:
            user_saw = sentinel in rt3
            notes.append(f"user_saw(neutral)={user_saw}")

    return Signal(
        accepted=accepted,
        agent_saw=agent_saw,
        blocked=blocked,
        continued=continued,
        user_saw=user_saw,
        persisted=persisted,
        note="; ".join(notes),
    )


# ---------------------------------------------------------------------------
# agy runner
# ---------------------------------------------------------------------------
def _newest_agy_log() -> Path | None:
    logs = sorted(glob.glob(AGY_LOG_GLOB), key=os.path.getmtime)
    return Path(logs[-1]) if logs else None


def _write_agy_hooks(workdir: Path, wire_event: str, hook: Path) -> None:
    agents_dir = workdir / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    # agy hooks.json: PreInvocation/PostInvocation/Stop are flat; tool events wrapper.
    flat = wire_event in ("PreInvocation", "PostInvocation", "Stop")
    cmd = f"bash {hook}"
    if flat:
        hooks_json = {"probe": {wire_event: [{"type": "command", "command": cmd}]}}
    else:
        hooks_json = {
            "probe": {
                wire_event: [{"matcher": "*", "hooks": [{"type": "command", "command": cmd}]}]
            }
        }
    (agents_dir / "hooks.json").write_text(json.dumps(hooks_json, indent=2))


def _run_agy_once(
    argv_extra: list[str], prompt: str, workdir: Path, dangerous: bool, timeout: int
) -> tuple[str, str]:
    """Run one agy -p invocation; return (stdout, cli-log-text-for-this-run).

    agy ``-p`` STDOUT is the MODEL'S REPLY (the user-facing terminal stream in
    headless print mode) — measured 2026-06-25: with a clean stdin (</dev/null)
    and a positional prompt, stdout carries exactly the model's answer. The
    injected ``injectSteps``/``ephemeralMessage`` are delivered as MODEL CONTEXT
    (rendered as an EPHEMERAL_MESSAGE / source:SYSTEM step in the conversation
    transcript) and are NOT independently printed to the terminal — so a NEUTRAL
    prompt that does not ask the model to echo leaves the sentinel ABSENT from
    stdout, which is precisely how user-visibility is distinguished from the
    model-echo agent_saw run.
    """
    log_before = _newest_agy_log()
    mtime_before = os.path.getmtime(log_before) if log_before else 0.0
    argv = ["agy"]
    if dangerous:
        argv.append("--dangerously-skip-permissions")
    argv += argv_extra + ["-p", prompt]
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
        return "", "__TIMEOUT__"
    stdout = proc.stdout or ""  # allow-fallback: captured stdout optional, "" = none
    log = _newest_agy_log()
    log_text = ""
    if log and os.path.getmtime(log) >= mtime_before:
        try:
            log_text = log.read_text(errors="replace")
        except OSError:
            log_text = ""
    return stdout, log_text


def _agy_unauth(stdout: str, log_text: str) -> bool:
    """True only when a FATAL auth failure left the model turn un-run.

    The "not logged into Antigravity" markers also appear on a FULLY
    AUTHENTICATED run (benign secondary-token poll failures), so unauth is keyed
    on the model turn NOT having run (no conversation stream + empty stdout).
    """
    auth_marker = "not logged into Antigravity" in log_text or "You are not logged in" in log_text
    model_turn_ran = (
        "Stopping conversation stream" in log_text
        or "Streaming conversation" in log_text
        or bool(stdout.strip())
    )
    return auth_marker and not model_turn_ran


def run_agy(
    probe: Probe, sentinel: str, workdir: Path, dangerous: bool, timeout: int = 360
) -> Signal:
    """Drive agy headless and measure all five observables.

    ISOLATION NOTE: the global aops-core agy plugin (symlinked to Nic's live
    build) co-fires its own PreInvocation/Stop hooks on these runs. That is
    tolerated WITHOUT touching Nic's config because every probe injects a UNIQUE
    ``PROBE-<uuid>`` sentinel: the aops advisory cannot contain our sentinel, so
    a sentinel hit proves OUR cell's delivery independent of the co-firing plugin.
    Disabling the plugin would mutate ``~/.gemini/config/import_manifest.json``
    (a live file) for no measurement gain.

    AGENT_SAW: REPORT_PROMPT run; sentinel in stdout (the model echoed it).
    USER_SAW:  NEUTRAL_PROMPT run; sentinel in stdout means agy RENDERED the
               channel to the human (the model was not asked to echo). For
               injectSteps this is expected ABSENT (model-context only) — the
               empirical answer to "does ephemeralMessage leak to the user?".
    PERSISTED: a second turn via ``--continue`` (no new injection: the fire-once
               hook is spent) asks the model to recall the sentinel; >=2 samples.
    BLOCKED:   PreToolUse deny => canary contents never reach the model.
    """
    hook = workdir / "probe_hook.sh"
    _write_probe_hook(
        hook, _fill_sentinel(probe.output, sentinel), fire_once=not probe.persistent_deny
    )
    (workdir / "canary.txt").write_text(CANARY_TEXT + "\n")
    _write_agy_hooks(workdir, probe.wire_event, hook)

    # --- AGENT_SAW run (report prompt) ---
    stdout, log_text = _run_agy_once([], REPORT_PROMPT, workdir, dangerous, timeout)
    if log_text == "__TIMEOUT__":
        return Signal(note="agy timeout (agent-saw run)")
    rejected = any(m in log_text for m in AGY_REJECT_MARKERS)
    hook_fired = "executing command" in log_text or probe.wire_event in log_text
    unauth = _agy_unauth(stdout, log_text)
    accepted = (not rejected) if hook_fired else None
    agent_saw = (sentinel in stdout) if not unauth else None
    blocked: bool | None = None
    if probe.wire_event == "PreToolUse":
        blocked = (CANARY_TEXT not in stdout) if not unauth else None
    notes = [f"dangerous={dangerous}"]
    if unauth:
        notes.append("unauthenticated (wire-acceptance only)")
    if not hook_fired:
        notes.append("hook did not fire (check registration)")

    # --- USER_SAW: NEUTRAL prompt; sentinel in user-facing stdout only if agy
    #     renders the channel to the human (model not asked to echo). ---
    user_saw: bool | None = None
    if probe.measure_user and not unauth:
        with _tempworkspace() as wd2:
            hook2 = wd2 / "probe_hook.sh"
            _write_probe_hook(
                hook2,
                _fill_sentinel(probe.output, sentinel),
                fire_once=not probe.persistent_deny,
            )
            (wd2 / "canary.txt").write_text(CANARY_TEXT + "\n")
            _write_agy_hooks(wd2, probe.wire_event, hook2)
            so2, lt2 = _run_agy_once([], NEUTRAL_PROMPT, wd2, dangerous, timeout)
        if lt2 == "__TIMEOUT__" or _agy_unauth(so2, lt2):
            notes.append("user-saw run unmeasurable")
        else:
            user_saw = sentinel in so2
            notes.append(f"user_saw(neutral)={user_saw}")

    # --- PERSISTED: second turn via --continue, no new injection ---
    # The agent_saw run above already fired the fire-once hook (its flag file
    # ``<workdir>/.fired`` now exists), so a ``--continue`` turn from the SAME
    # workspace re-enters the SAME conversation and the spent hook emits ``{}``
    # (no new injection). If the model still quotes the sentinel, the channel
    # PERSISTED into conversation history; if not, it was ephemeral/transient.
    persisted: bool | None = None
    if probe.measure_persist and not unauth and agent_saw:
        recalled = False
        for _ in range(PERSIST_SAMPLES):
            so3, lt3 = _run_agy_once(["--continue"], PERSIST_PROMPT, workdir, dangerous, timeout)
            if lt3 != "__TIMEOUT__" and sentinel in so3:
                recalled = True
                break
        persisted = recalled
        notes.append(f"persist_samples={PERSIST_SAMPLES} persisted={persisted}")

    return Signal(
        accepted=accepted,
        agent_saw=agent_saw,
        blocked=blocked,
        continued=None,
        user_saw=user_saw,
        persisted=persisted,
        note="; ".join(notes),
    )


# ---------------------------------------------------------------------------
# Candidate matrix — the contested cells (kept tight to bound live cost)
# ---------------------------------------------------------------------------
def candidates() -> list[Probe]:
    """One Probe per CLIENT-TRANSLATION.md "Message audience / persistence" cell.

    Each Probe carries the table-cell's CLAIMED (user_saw, agent_saw, persisted,
    blocked) so the pytest layer asserts measurement == claim — turning the table
    from prose assertion into test-enforced truth. ``measure_user`` /
    ``measure_persist`` gate the extra (expensive) runs to the cells where those
    columns are load-bearing.
    """
    P = []
    HSO = "hookSpecificOutput"

    # ======================= Claude Code (2.1.191) =======================
    # additionalContext = agent-only (C✓), persists (P✓), NOT user-visible (U✗).
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
            "PreToolUse allow additionalContext: agent-only (C✓), user✗.",
            measure_user=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_blocked=False,
            table_cell="PreToolUse advisory · Claude additionalContext U✗ C✓ P✓",
        )
    )
    # deny permissionDecisionReason = user✓ AND agent✓, blocks.
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
            "PreToolUse deny permissionDecisionReason: blocks; reason to agent.",
            persistent_deny=True,
            claim_agent_saw=True,
            claim_blocked=True,
            table_cell="PreToolUse deny-reason · Claude permissionDecisionReason U✓ C✓ P✓",
        )
    )
    # UPS additionalContext = agent-only (C✓), persists (P✓), user✗.
    P.append(
        Probe(
            "claude",
            "UserPromptSubmit",
            "claude-userpromptsubmit-additionalcontext",
            "claude-ups",
            {HSO: {"hookEventName": "UserPromptSubmit", "additionalContext": "probe SENTINEL"}},
            "UPS additionalContext: agent-only (C✓ P✓), user✗.",
            measure_user=True,
            measure_persist=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_persisted=True,
            table_cell="UPS advisory · Claude additionalContext U✗ C✓ P✓",
        )
    )
    # Stop additionalContext (no block) = agent-only (C✓ P✓), user✗, continues.
    P.append(
        Probe(
            "claude",
            "Stop",
            "claude-stop-additionalcontext-noblock",
            "claude-stop",
            {HSO: {"hookEventName": "Stop", "additionalContext": "probe SENTINEL"}},
            "Stop additionalContext (no block): agent-only (C✓ P✓), user✗, continues.",
            measure_user=True,
            measure_persist=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_persisted=True,
            table_cell="Stop advisory WARN · Claude additionalContext U✗ C✓ P✓",
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
            "Stop additionalContext WITH trust markers: still agent-only, user✗.",
            measure_user=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            table_cell="Stop advisory (marked) · Claude additionalContext U✗ C✓ P✓",
        )
    )
    # Stop decision:block reason = user✓ AND agent✓ (the only Claude channel both see).
    P.append(
        Probe(
            "claude",
            "Stop",
            "claude-stop-decision-block",
            "claude-stop",
            {"decision": "block", "reason": "probe SENTINEL continue"},
            "Stop decision:block reason: agent✓ (enforcement); reaches user as notice.",
            claim_agent_saw=True,
            table_cell="Stop enforcement · Claude decision=block reason U✓ C✓ P✓",
        )
    )
    # Claude top-level systemMessage = USER-only banner. HONEST GAP: the banner is
    # interactive-TUI-only and NOT observable in headless -p (measured 2026-06-25):
    # it appears in NEITHER the json envelope NOR stdout/stderr. So user_saw is
    # NOT headless-measurable (measure_user stays False -> user_saw=None) and the
    # pytest layer xfails the user-visibility assertion with that reason rather
    # than faking a pass. We DO assert agent_saw=False (the model must NOT echo a
    # user-only banner it never received), which IS observable via the report run.
    P.append(
        Probe(
            "claude",
            "UserPromptSubmit",
            "claude-ups-systemmessage",
            "claude-systemmessage",
            {"systemMessage": "probe SENTINEL banner"},
            "Claude top-level systemMessage: USER-only banner; agent does NOT see it.",
            claim_agent_saw=False,
            table_cell="UPS short-reason · Claude systemMessage U✓ C✗ P✗ (U not headless-observable)",
        )
    )

    # ======================= Antigravity (agy 1.0.12) =======================
    # PreToolUse allow (verified-live baseline + docs variant).
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-allowtool-true",
            "agy-pretooluse-allow",
            {"allowTool": True},
            "agy PreToolUse {allowTool:true} lets the tool run.",
            claim_blocked=False,
            table_cell="PreToolUse allow · agy allowTool=true",
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
            table_cell="PreToolUse allow (docs variant) · agy decision=allow",
        )
    )
    # PreToolUse deny: blocks; denyReason fed to model (C✓), user✗.
    P.append(
        Probe(
            "agy",
            "PreToolUse",
            "agy-pretooluse-allowtool-false",
            "agy-pretooluse-deny",
            {"allowTool": False, "denyReason": "probe SENTINEL"},
            "agy PreToolUse {allowTool:false,denyReason} blocks; reason to model.",
            persistent_deny=True,
            claim_blocked=True,
            table_cell="PreToolUse deny-reason · agy denyReason U✗ C✓ P✓",
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
            table_cell="PreToolUse deny (docs variant) · agy decision=deny",
        )
    )
    # ===== THE CONTESTED INJECT CELLS — Nic's primary questions =====
    # ephemeralMessage: claimed U✗ C✓ P✗ (model-context, transient). Measure ALL.
    P.append(
        Probe(
            "agy",
            "PreInvocation",
            "agy-preinvocation-ephemeralmessage",
            "agy-inject",
            {"injectSteps": [{"ephemeralMessage": "probe SENTINEL"}]},
            "agy ephemeralMessage: model-context (C✓), USER-visible? (Nic q), PERSISTS?",
            measure_user=True,
            measure_persist=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_persisted=False,
            table_cell="UPS advisory · agy ephemeralMessage U✗ C✓ P✗ (Nic: does it LEAK to user?)",
        )
    )
    # userMessage: claimed U✗ C✓ P✓ (model-context, PERSISTS as a user turn).
    P.append(
        Probe(
            "agy",
            "PreInvocation",
            "agy-preinvocation-usermessage",
            "agy-inject",
            {"injectSteps": [{"userMessage": "probe SENTINEL"}]},
            "agy userMessage: model-context (C✓); PERSISTS (P✓)? USER-visible?",
            measure_user=True,
            measure_persist=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_persisted=True,
            table_cell="UPS advisory · agy userMessage U✗ C✓ P✓",
        )
    )
    # systemMessage MEMBER #3 — the ‹being measured› cell. Nested structured step.
    # mem-83cedbdd (1.0.7) says agy DROPS systemMessage; a 1.0.12 ad-hoc run claimed
    # it delivers. This probe RESOLVES it. No claim_* asserted (it is the open
    # question being filled) — the measurement WRITES the truth into the table.
    P.append(
        Probe(
            "agy",
            "PreInvocation",
            "agy-preinvocation-systemmessage-member",
            "agy-inject",
            {"injectSteps": [{"systemMessage": {"systemMessage": "probe SENTINEL"}}]},
            "agy injectSteps systemMessage MEMBER (nested): DELIVERS on 1.0.12? user-visible? "
            "(resolves mem-83cedbdd 'drops' vs ad-hoc 'delivers').",
            measure_user=True,
            measure_persist=True,
            table_cell="UPS advisory · agy injectSteps.systemMessage member ‹BEING MEASURED›",
        )
    )
    # PostInvocation ephemeralMessage (Stop-equivalent advisory channel).
    P.append(
        Probe(
            "agy",
            "PostInvocation",
            "agy-postinvocation-ephemeralmessage",
            "agy-inject",
            {"injectSteps": [{"ephemeralMessage": "probe SENTINEL"}]},
            "agy PostInvocation ephemeralMessage: model-context (C✓), user-visible? persists?",
            measure_user=True,
            measure_persist=True,
            claim_user_saw=False,
            claim_agent_saw=True,
            claim_persisted=False,
            table_cell="Stop advisory · agy PostInvocation ephemeralMessage U✗ C✓ P✗",
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
            table_cell="Stop hard-block · agy PostInvocation terminationBehavior (PROVISIONAL)",
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
            measure_user=True,
            claim_user_saw=False,
            table_cell="Stop short-reason · agy native Stop reason U✗ C✓ P✓ (PROVISIONAL)",
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
    ap.add_argument(
        "--progress-log",
        default=None,
        help="streaming per-probe progress log (default: <out dir>/verify_hook_formats.progress.log); "
        "distinct from --out so tail -f works during a long live run",
    )
    args = ap.parse_args()

    out_path = Path(args.out)
    if args.progress_log:
        progress_log: Path | None = Path(args.progress_log)
    else:
        # Default beside --out, EXCEPT when --out is a device/non-dir target
        # (e.g. the pytest layer's --out /dev/stdout), where /dev is unwritable.
        out_dir = out_path.parent
        progress_log = (
            out_dir / "verify_hook_formats.progress.log"
            if out_dir.is_dir() and os.access(out_dir, os.W_OK) and str(out_dir) != "/dev"
            else None
        )
    if progress_log is not None:
        try:
            progress_log.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            progress_log = None

    avail = {"claude": claude_available(), "agy": agy_available(), "gemini": gemini_available()}
    probes = candidates()
    if args.client:
        probes = [p for p in probes if p.client == args.client]
    if args.only:
        probes = [p for p in probes if p.label == args.only]

    _progress(f"START run: {len(probes)} probe(s); progress -> {progress_log}", progress_log)

    results: list[CellResult] = []
    for idx, p in enumerate(probes, 1):
        cr = CellResult(
            p.label,
            p.client,
            p.wire_event,
            p.group,
            p.hypothesis,
            table_cell=p.table_cell,
            claim_user_saw=p.claim_user_saw,
            claim_agent_saw=p.claim_agent_saw,
            claim_persisted=p.claim_persisted,
            claim_blocked=p.claim_blocked,
        )
        if not avail.get(p.client):
            cr.signal = Signal(note=f"{p.client} unavailable")
            results.append(cr)
            _progress(
                f"SKIP  [{idx}/{len(probes)}] {p.label:48s} ({p.client} unavailable)", progress_log
            )
            continue
        _progress(
            f"START [{idx}/{len(probes)}] {p.label:48s} ({p.client}/{p.wire_event})", progress_log
        )
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
        _progress(
            f"RUN   [{idx}/{len(probes)}] {p.label:48s} accepted={s.accepted} agent_saw={s.agent_saw} "
            f"user_saw={s.user_saw} persisted={s.persisted} blocked={s.blocked} "
            f"continued={s.continued} :: {s.note}",
            progress_log,
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
            _progress(
                f"RUN   [{idx}/{len(probes)}] {p.label + '+dangerous':48s} accepted={sig.accepted} blocked={sig.blocked} :: {sig.note}",
                progress_log,
            )

    report = {
        "generated_note": "Live conformance measurement — see scripts/verify_hook_formats.py",
        "claude_version": _client_version("claude"),
        "agy_present": avail["agy"],
        "gemini_present": avail["gemini"],
        "cells": [asdict(r) for r in results],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    _progress(f"DONE  Wrote {len(results)} cells -> {args.out}", progress_log)
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
