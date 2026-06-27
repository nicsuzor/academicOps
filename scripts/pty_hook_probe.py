#!/usr/bin/env -S uv run python
"""PTY hook-visibility probe — Test Layer C of specs/hooks/CLIENT-TRANSLATION.md.

WHY THIS EXISTS
---------------
The former headless harness ``scripts/verify_hook_formats.py`` (Test Layer B,
DELETED 2026-06-26) drove the HEADLESS client (``claude -p --output-format
json``) and was STRUCTURALLY BLIND to user visibility: it could only inspect the
JSON *result envelope* (the model's reply text). A hook's TTY-rendered banners —
``Stop hook feedback:`` / ``Stop hook error:`` notices, the top-level
``systemMessage`` banner, a PreToolUse denial toast — are rendered by the
INTERACTIVE TUI and NEVER enter that envelope. So its ``user_saw`` was
``False``/``None`` *by construction* for those channels, not by observation (the
false negative the PR #1970 review uncovered, task aops-4de68b25).

This harness closes that gap. It drives a REAL INTERACTIVE ``claude`` inside a
tmux pane, fires each candidate hook-output shape with unique sentinels, and
captures BOTH surfaces:

  * USER surface  — the rendered tmux pane (``tmux capture-pane``). This is
                    LITERALLY what the human sees. ``user_saw`` = sentinel
                    present in the pane after a NEUTRAL prompt (the model is not
                    asked to echo anything, so a sentinel in the pane can only be
                    the CLIENT rendering the channel).
  * AGENT surface — the session transcript JSONL
                    (``~/.claude/projects/<sanitized-cwd>/<uuid>.jsonl``), located
                    deterministically from the probe's unique workspace cwd.
                    ``agent_saw`` = sentinel present in the transcript (the model
                    received it in context).

PARAMETERIZED / MULTI-CLIENT
----------------------------
Each ``Probe`` carries a ``client`` field. Only ``claude`` probes run today.
``agy`` (Antigravity) has its own interactive TUI driven the same way — its
probes can be added to ``CANDIDATES`` with ``client="agy"`` and a per-client
driver, WITHOUT changing the matrix shape or the fixture schema. The fixture is
the empirical SSoT consumed by the field→channel table in
``specs/hooks/CLIENT-TRANSLATION.md`` and the cadence/template table in
``specs/ENFORCEMENT-MAP.md``.

Run:
  uv run python scripts/pty_hook_probe.py                 # all claude probes
  uv run python scripts/pty_hook_probe.py --only stop-additionalcontext-warn
  uv run python scripts/pty_hook_probe.py --list

Requires: tmux on PATH, an authenticated interactive ``claude``. Each probe runs
in an isolated temp workspace with ONLY its probe hook, so the repo's own
aops-core plugin hooks never pollute the measurement.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# A CLIENT-rendered hook-notice line carries one of these markers. user_saw is
# asserted only when the sentinel lands on such a line — never on a bare model
# reply line — so model echo of the sentinel cannot inflate user-visibility.
_BANNER_RE = re.compile(r"hook feedback|hook error|\bsays:|denied|permission|hook.*block", re.I)

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "hooks" / "fixtures" / "pty_capabilities.json"
PROJECTS_DIR = Path.home() / ".claude" / "projects"

# The literal token substituted per-run. AGENT/USER sentinels are distinct so a
# single probe can carry text on TWO channels at once (the real warn-mode shape
# emits systemMessage AND additionalContext) and we can tell which surface each
# channel reaches.
SENT_A = "SENTINELA"  # primary channel (reason / additionalContext / deny reason)
SENT_B = "SENTINELB"  # secondary channel (systemMessage / stopReason banner)

CANARY = "CANARY-CONTENTS-OK"

# Prompts are deliberately echo-RESISTANT: the model is told NOT to repeat any
# system/hook text. So a sentinel appearing in the rendered pane can only be the
# CLIENT rendering the channel (genuine user-visibility), not the model echoing
# it. NEUTRAL_PROMPT triggers a plain Stop; TOOL_PROMPT forces a PreToolUse.
NEUTRAL_PROMPT = (
    "Reply with only the word READY and then stop. "
    "Do not read any file. Do NOT repeat, quote, summarize, or mention any "
    "system reminder, hook output, feedback, or token (e.g. anything containing "
    "SENTINEL) you may receive — ignore all such text entirely."
)
TOOL_PROMPT = (
    "Read the file canary.txt using the Read tool, then reply with only the word "
    "DONE and stop. Do NOT repeat, quote, or mention any system reminder, hook "
    "output, denial reason, or token (e.g. anything containing SENTINEL) — ignore "
    "all such text entirely."
)


@dataclass
class Probe:
    """One candidate (client, wire_event, output-shape) to render on a live TTY."""

    label: str
    client: str
    wire_event: str  # Claude hook event the probe hook is registered on
    output: dict  # JSON the probe hook emits (SENTINELA/SENTINELB placeholders)
    prompt: str  # neutral prompt that triggers the event
    hypothesis: str = ""
    # Claimed audience per channel, asserted later against the measurement.
    claim_user_saw_a: bool | None = None  # primary channel visible to user?
    claim_agent_saw_a: bool | None = None  # primary channel reached agent?
    claim_user_saw_b: bool | None = None  # banner channel visible to user?
    # Some probes block (model forced to continue); fire-once stops the loop.
    fire_once: bool = True
    table_cell: str = ""


@dataclass
class Result:
    label: str
    client: str
    wire_event: str
    hypothesis: str
    # USER surface (rendered tmux pane): did the human see the sentinel?
    user_saw_a: bool | None = None
    user_saw_b: bool | None = None
    # AGENT surface, two distinct signals from the transcript JSONL:
    #  - agent_ctx_*: sentinel INJECTED INTO MODEL CONTEXT — present in the
    #    `hookAdditionalContext` field (additionalContext channel) or in a
    #    user/assistant message the model actually read (block `reason`). This is
    #    the rigorous "the model saw it" signal (avoids the invariant-#14 confound).
    #  - in_transcript_*: sentinel present ANYWHERE in the transcript file,
    #    INCLUDING the raw hook-execution `attachment`/`system` records that log
    #    every hook's stdout regardless of model visibility. "Shown in the agent
    #    transcript" literally — but NOT proof the model read it.
    agent_ctx_a: bool | None = None
    agent_ctx_b: bool | None = None
    in_transcript_a: bool | None = None
    in_transcript_b: bool | None = None
    transcript_found: bool = False
    # P8: agent_ctx is authoritative only on Stop (see _agent_signals scope note).
    agent_ctx_authoritative: bool = False
    # P8: self-describing measurement gaps (echo-ambiguity, attachment-ambiguity,
    # capture gaps) so a future reader does not trust a bare negative.
    measurement_caveats: list = field(default_factory=list)
    note: str = ""
    pane_excerpt: str = ""
    claim_user_saw_a: bool | None = None
    claim_agent_saw_a: bool | None = None
    claim_user_saw_b: bool | None = None
    table_cell: str = ""


# ---------------------------------------------------------------------------
# Probe matrix — Claude Code field → channel, measured on the live TTY.
# ---------------------------------------------------------------------------
def candidates() -> list[Probe]:
    HSO = "hookSpecificOutput"
    P: list[Probe] = []

    # ===================== Stop event (where the noise lives) =====================
    # 1. ENFORCEMENT: decision=block + reason. Client renders "Stop hook error:
    #    <reason>" to the user AND feeds reason to the agent (it continues).
    P.append(
        Probe(
            "stop-block-reason",
            "claude",
            "Stop",
            {"decision": "block", "reason": "SENTINELA continue then stop"},
            NEUTRAL_PROMPT,
            "Stop decision=block reason: rendered to USER as 'Stop hook error:' AND to agent.",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            table_cell="Stop enforcement · decision=block reason",
        )
    )
    # 2. WARN-DELIVER (contested cell): additionalContext, no block. Docs say it
    #    renders as 'Stop hook feedback:' to the user (user-visible BY DESIGN).
    P.append(
        Probe(
            "stop-additionalcontext-warn",
            "claude",
            "Stop",
            {
                "decision": "approve",
                HSO: {"hookEventName": "Stop", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "Stop additionalContext (no block): does the TUI render 'Stop hook feedback:' to the USER?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            table_cell="Stop advisory WARN · additionalContext",
        )
    )
    # 3. systemMessage banner alone on Stop.
    P.append(
        Probe(
            "stop-systemmessage",
            "claude",
            "Stop",
            {"systemMessage": "SENTINELB"},
            NEUTRAL_PROMPT,
            "Stop top-level systemMessage: USER banner? agent should NOT see it.",
            claim_user_saw_b=True,
            claim_agent_saw_a=False,
            table_cell="Stop banner · systemMessage",
        )
    )
    # 4. REAL WARN-MODE SHAPE: systemMessage (banner) + additionalContext (advisory).
    #    The task's central claim: the user sees BOTH the short line AND the long
    #    advisory. Distinct sentinels prove which surface each reaches.
    P.append(
        Probe(
            "stop-warnmode-real",
            "claude",
            "Stop",
            {
                "decision": "approve",
                "systemMessage": "SENTINELB",
                HSO: {"hookEventName": "Stop", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "REAL warn-mode emission: user sees systemMessage(B) banner AND additionalContext(A) feedback?",
            claim_user_saw_a=True,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            table_cell="Stop warn-mode (real) · systemMessage + additionalContext",
        )
    )
    # 5. REAL BLOCK-MODE SHAPE: decision=block + reason(A) + systemMessage(B).
    #    Confirms router.py's UNCONDITIONAL systemMessage assignment: user sees
    #    BOTH the short banner(B) and the long reason(A).
    P.append(
        Probe(
            "stop-blockmode-real",
            "claude",
            "Stop",
            {
                "decision": "block",
                "reason": "SENTINELA continue then stop",
                "systemMessage": "SENTINELB",
                "stopReason": "SENTINELB",
            },
            NEUTRAL_PROMPT,
            "REAL block-mode emission: user sees reason(A) 'Stop hook error' AND systemMessage(B) banner?",
            claim_user_saw_a=True,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            table_cell="Stop block-mode (real) · decision=block reason + systemMessage",
        )
    )
    # 6. suppressOutput: does it hide the structured Stop notice? (task open Q).
    P.append(
        Probe(
            "stop-block-suppressoutput",
            "claude",
            "Stop",
            {"decision": "block", "reason": "SENTINELA continue then stop", "suppressOutput": True},
            NEUTRAL_PROMPT,
            "suppressOutput=true on a blocking Stop: does it hide the 'Stop hook error:' notice from the user?",
            claim_agent_saw_a=True,
            table_cell="Stop · suppressOutput effect (UNMEASURED until now)",
        )
    )

    # ===================== UserPromptSubmit (contrast) =====================
    # 7. additionalContext on UPS — agent-only, silent to user.
    P.append(
        Probe(
            "ups-additionalcontext",
            "claude",
            "UserPromptSubmit",
            {HSO: {"hookEventName": "UserPromptSubmit", "additionalContext": "SENTINELA"}},
            NEUTRAL_PROMPT,
            "UPS additionalContext: agent-only (contrast with Stop); user should NOT see it.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            table_cell="UPS advisory · additionalContext",
        )
    )
    # 8. systemMessage on UPS — user banner.
    P.append(
        Probe(
            "ups-systemmessage",
            "claude",
            "UserPromptSubmit",
            {"systemMessage": "SENTINELB"},
            NEUTRAL_PROMPT,
            "UPS systemMessage: USER banner; agent should NOT see it.",
            claim_user_saw_b=True,
            claim_agent_saw_a=False,
            table_cell="UPS banner · systemMessage",
        )
    )

    # ===================== PreToolUse =====================
    # 9. deny + permissionDecisionReason — blocks the Read, denial toast to user.
    P.append(
        Probe(
            "pretool-deny-reason",
            "claude",
            "PreToolUse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "SENTINELA blocked",
                }
            },
            TOOL_PROMPT,
            "PreToolUse deny reason: denial surfaced to user AND agent; blocks the tool.",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            fire_once=False,
            table_cell="PreToolUse deny · permissionDecisionReason",
        )
    )
    # 10. allow + additionalContext — agent-only, silent to user.
    P.append(
        Probe(
            "pretool-additionalcontext",
            "claude",
            "PreToolUse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": "SENTINELA",
                }
            },
            TOOL_PROMPT,
            "PreToolUse allow additionalContext: agent-only; user should NOT see it.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            table_cell="PreToolUse advisory · additionalContext",
        )
    )
    return P


# ---------------------------------------------------------------------------
# tmux + workspace plumbing
# ---------------------------------------------------------------------------
def _tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=check)


def _pane(session: str) -> str:
    """Full pane text including scrollback, ANSI stripped (capture-pane -p)."""
    r = _tmux("capture-pane", "-t", session, "-p", "-S", "-500", check=False)
    return (
        r.stdout or ""
    )  # allow-fallback: empty pane capture is a valid "nothing rendered yet" state


def _sanitized_project_dir(workspace: Path) -> Path:
    """Claude stores transcripts under ~/.claude/projects/<cwd with non-alnum→->."""
    import re

    slug = re.sub(r"[^a-zA-Z0-9]", "-", str(workspace))
    return PROJECTS_DIR / slug


def _transcript_text(workspace: Path) -> str:
    """Read the newest session transcript for this workspace.

    Located by the UNIQUE mkdtemp basename (e.g. ``ptyhook-<label>-XXXX``): the
    project-dir slug ALWAYS ends with it regardless of /var → /private/var
    symlink canonicalization, so this is robust where the full-path slug is not.
    """
    import re

    if not PROJECTS_DIR.is_dir():
        return ""
    base = re.sub(r"[^a-zA-Z0-9]", "-", workspace.name)
    cands = [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and d.name.endswith(base)]
    if not cands:  # fallback: exact full-path slug
        sd = _sanitized_project_dir(workspace)
        cands = [sd] if sd.is_dir() else []
    jsonls: list[Path] = []
    for d in cands:
        jsonls.extend(d.glob("*.jsonl"))
    if not jsonls:
        return ""
    newest = max(jsonls, key=lambda p: p.stat().st_mtime)
    return newest.read_text(errors="replace")


def _user_saw(pane: str, sentinel: str) -> tuple[bool, bool, bool]:
    """Return (saw_on_banner, saw_raw, echo_ambiguous) for a sentinel in the pane.

    saw_on_banner — sentinel is on a CLIENT-rendered hook-notice line (the rigorous
    user-visibility signal; immune to the model echoing the sentinel into its own
    reply). saw_raw — sentinel anywhere in the pane. echo_ambiguous — raw but not on
    a banner line (the sentinel is present only inside a model reply → cannot be
    attributed to client rendering).
    """
    raw = sentinel in pane
    banner = any(sentinel in ln and _BANNER_RE.search(ln) for ln in pane.splitlines())
    return banner, raw, (raw and not banner)


def _agent_signals(transcript: str, sentinel: str) -> tuple[bool | None, bool | None]:
    """Classify how a sentinel appears in the transcript.

    Returns (injected_into_context, present_in_transcript):
      * injected_into_context — sentinel is in the ``hookAdditionalContext`` field
        (the additionalContext injection channel) OR inside a ``user``/``assistant``
        message the model actually read (e.g. a blocking Stop ``reason`` is fed
        back as a user turn). This is the rigorous "the MODEL saw it" signal.
      * present_in_transcript — sentinel appears anywhere in the file, INCLUDING
        the raw hook-stdout ``attachment``/``system`` records (logged regardless
        of whether the model reads them).
    A user-only banner (``systemMessage``/``stopReason``) is present_in_transcript
    (logged) but injected_into_context is **None**, not False — this rig cannot
    structurally prove it is NOT injected (a logged banner and an
    attachment-delivered injection share the same record shape); the C✗ truth for
    banners comes from the router code + docs, not this measurement.

    SCOPE / HONEST LIMIT (measured 2026-06-26): this is authoritative for **Stop**
    (where additionalContext lands in the unambiguous ``hookAdditionalContext``
    field and a blocking ``reason`` lands in a model-read user message). On
    **UserPromptSubmit / PreToolUse**, additionalContext is delivered via a
    ``type:"attachment"`` record — the SAME record type that also logs a user-only
    ``systemMessage`` — so ``type:attachment`` cannot structurally distinguish
    "injected to model" from "merely logged", and this returns
    injected=False there even though the channel DOES reach the model (proven
    historically by MODEL ECHO; CLIENT-TRANSLATION.md records UPS/PreToolUse
    additionalContext as C✓). For those events trust ``present_in_transcript`` for
    "logged" and the model-echo C✓ for "reached the model"; a model-echo agent
    lane (REPORT_PROMPT) is the clean way to extend agent-context to all events.
    """
    if not transcript:
        return None, None
    present = sentinel in transcript
    if not present:
        return False, False
    # Present but, by default, in an ambiguous location (a raw hook-stdout
    # `attachment`/`system` record that logs BOTH user-only banners AND
    # attachment-delivered injections) → unmeasurable by this rig → None, NOT
    # False. Returning False here would reproduce the very false-negative this
    # harness exists to kill (a user-only systemMessage and an attachment-injected
    # UPS additionalContext are structurally indistinguishable in the transcript).
    injected: bool | None = None
    for ln in transcript.splitlines():
        if sentinel not in ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if sentinel in str(
            o.get("hookAdditionalContext", "")
        ):  # allow-fallback: absent field = not this channel
            injected = True
            break
        if o.get("type") in ("user", "assistant") and sentinel in json.dumps(
            o.get("message", "")
        ):  # allow-fallback: absent message = nothing to scan
            injected = True
            break
    return injected, present


def _write_probe_hook(path: Path, output: dict, fire_once: bool) -> None:
    payload = json.dumps(output)
    if fire_once:
        body = (
            'FLAG="$(dirname "$0")/.fired"\n'
            "if [ -f \"$FLAG\" ]; then echo '{}'; exit 0; fi\n"
            'touch "$FLAG"\n'
        )
    else:
        body = ""
    path.write_text(f"#!/bin/bash\n{body}cat <<'PROBE_EOF'\n{payload}\nPROBE_EOF\nexit 0\n")
    path.chmod(0o755)


def _wait_for(session: str, needles: list[str], timeout: float, settle: float = 0.0) -> bool:
    """Poll pane until ANY needle appears; returns True if found within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pane = _pane(session)
        if any(n in pane for n in needles):
            if settle:
                time.sleep(settle)
            return True
        time.sleep(1.0)
    return False


def _wait_quiescent(session: str, timeout: float, stable_polls: int = 3) -> None:
    """Poll until the pane stops changing for `stable_polls` consecutive reads."""
    deadline = time.time() + timeout
    last = None
    stable = 0
    while time.time() < deadline:
        pane = _pane(session)
        if pane == last:
            stable += 1
            if stable >= stable_polls:
                return
        else:
            stable = 0
            last = pane
        time.sleep(1.5)


def _submit_prompt(session: str, prompt: str) -> bool:
    """Type the prompt and CONFIRM the turn actually started.

    The startup splash can still be repainting when the input box first accepts
    focus, so a single ``send-keys "text" Enter`` may leave the prompt sitting
    UNSENT (the model never runs, no transcript is written). We type the text
    literally (``-l``), send Enter separately, and verify the turn began by
    watching for ``esc to interrupt`` (model working). Retry the Enter a few
    times if the first did not take. Returns True once the turn is running.
    """
    for attempt in range(4):
        _tmux("send-keys", "-t", session, "-l", prompt)
        time.sleep(0.6)
        _tmux("send-keys", "-t", session, "Enter")
        # Turn started ⇒ "esc to interrupt" appears (model is generating).
        if _wait_for(session, ["esc to interrupt", "Choreographing", "tokens · "], timeout=12):
            return True
        # Prompt likely didn't submit; clear and retry.
        time.sleep(1.0 + attempt)
    return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def _drive_once(workspace: Path, session: str, probe: Probe) -> tuple[str, str]:
    """Drive ONE fresh interactive claude session; return (status, pane).

    status ∈ {ok, not_ready, not_started}. The caller resets the fire-once flag
    before each call so the probe hook re-fires on a retry.
    """
    _tmux("kill-session", "-t", session, check=False)
    _tmux("new-session", "-d", "-s", session, "-x", "220", "-y", "50")
    try:
        launch = (
            f"cd {workspace} && claude --setting-sources project "
            f"--permission-mode acceptEdits --allowedTools Read"
        )
        _tmux("send-keys", "-t", session, launch, "Enter")
        # Trust dialog → accept (Enter selects "Yes, I trust this folder").
        if _wait_for(session, ["trust this folder", "Is this a project"], timeout=20):
            _tmux("send-keys", "-t", session, "Enter")
        # Wait for the input box, then let the splash finish repainting so the
        # first prompt is not eaten by the splash.
        if not _wait_for(session, ["accept edits on", "for shortcuts"], timeout=30):
            return "not_ready", ""
        time.sleep(3.0)
        if not _submit_prompt(session, probe.prompt):
            return "not_started", _pane(session)
        # Let the turn run and the Stop/Pre hook fire; wait for quiescence.
        _wait_quiescent(session, timeout=90, stable_polls=3)
        return "ok", _pane(session)
    finally:
        _tmux("kill-session", "-t", session, check=False)


def run_probe(probe: Probe, workspace: Path) -> Result:
    session = f"pty_{probe.label.replace('-', '_')}"
    out = json.loads(
        json.dumps(probe.output).replace("SENTINELA", SENT_A).replace("SENTINELB", SENT_B)
    )

    (workspace / ".claude").mkdir(parents=True, exist_ok=True)
    (workspace / "canary.txt").write_text(CANARY + "\n")
    hook = workspace / "probe_hook.sh"
    _write_probe_hook(hook, out, probe.fire_once)
    settings = {
        "hooks": {probe.wire_event: [{"hooks": [{"type": "command", "command": f"bash {hook}"}]}]}
    }
    (workspace / ".claude" / "settings.json").write_text(json.dumps(settings))

    res = Result(
        probe.label,
        probe.client,
        probe.wire_event,
        probe.hypothesis,
        claim_user_saw_a=probe.claim_user_saw_a,
        claim_agent_saw_a=probe.claim_agent_saw_a,
        claim_user_saw_b=probe.claim_user_saw_b,
        table_cell=probe.table_cell,
    )

    # Drive up to MAX_ATTEMPTS fresh sessions, retrying ONLY on a HARD failure
    # (TUI never ready / turn never started / transcript missing) — the
    # non-determinism marsha measured (1/3 clean reproductions). The fire-once
    # flag is reset before each attempt so the probe hook re-fires. A clean run
    # whose user channel reads False is NOT retried — that is a real,
    # self-caveated measurement, not a failure.
    MAX_ATTEMPTS = 3
    pane = transcript = ""
    attempts: list[str] = []
    for n in range(1, MAX_ATTEMPTS + 1):
        (workspace / ".fired").unlink(missing_ok=True)  # re-arm the fire-once hook
        status, pane = _drive_once(workspace, session, probe)
        transcript = _transcript_text(workspace)
        attempts.append(f"a{n}:{status}{'+tx' if transcript else '+notx'}")
        if status == "ok" and transcript:
            break
        time.sleep(2.0)

    res.transcript_found = bool(transcript)

    # USER surface (P9 echo positive-control): user_saw is TRUE only when the
    # sentinel lands on a CLIENT-rendered hook-notice line (`Stop hook feedback:`
    # / `Stop hook error:` / `… says:` / denial), NOT merely anywhere in the pane.
    # This excludes the case where the model echoes the sentinel into its own
    # reply. If raw is True but banner is False the cell is echo-ambiguous.
    res.user_saw_a, raw_a, amb_a = _user_saw(pane, SENT_A)
    res.user_saw_b, raw_b, amb_b = _user_saw(pane, SENT_B)
    # AGENT surface: structural classification (context-injection vs logged).
    res.agent_ctx_a, res.in_transcript_a = _agent_signals(transcript, SENT_A)
    res.agent_ctx_b, res.in_transcript_b = _agent_signals(transcript, SENT_B)

    # P8: make measurement gaps self-describing in the fixture, not bare
    # negatives a future reader would trust over the prose caveats.
    #  - agent_ctx is authoritative ONLY on Stop (hookAdditionalContext /
    #    model-read reason); on UPS/PreToolUse it is attachment-ambiguous.
    res.agent_ctx_authoritative = probe.wire_event in ("Stop", "SessionEnd")
    caveats: list[str] = []
    if amb_a or amb_b:
        caveats.append("echo-ambiguous: sentinel in pane but not on a client banner line")
    if not res.agent_ctx_authoritative:
        caveats.append(
            "agent_ctx NOT authoritative on this event (additionalContext rides an "
            "attachment record, structurally indistinguishable from a logged banner); "
            "C truth is the model-echo finding in CLIENT-TRANSLATION.md"
        )
    # A claimed-but-not-captured user channel = a capture gap (e.g. the PreToolUse
    # denial toast is transient and scrolls before snapshot).
    if probe.claim_user_saw_a is True and res.user_saw_a is False:
        caveats.append(
            "user_saw_a=False despite claim=True — likely a CAPTURE GAP (transient "
            "notice scrolled before the post-quiescence snapshot), NOT proof of U✗"
        )
    if not transcript:
        caveats.append("no transcript after retries — run did not complete; signals unreliable")
    res.measurement_caveats = caveats

    # Capture a compact excerpt of the rendered hook region for the report.
    lines = [
        ln
        for ln in pane.splitlines()
        if SENT_A in ln
        or SENT_B in ln
        or "Stop hook" in ln
        or "hook error" in ln
        or "hook feedback" in ln
        or "Stop says" in ln
    ]
    res.pane_excerpt = "\n".join(lines[-6:])
    res.note = (
        f"USER pane A={res.user_saw_a} B={res.user_saw_b}; "
        f"AGENT ctx A={res.agent_ctx_a} B={res.agent_ctx_b}; "
        f"in_transcript A={res.in_transcript_a} B={res.in_transcript_b}; "
        f"transcript={'found' if transcript else 'MISSING'}; attempts={','.join(attempts)}"
    )
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="PTY hook-visibility probe (Layer C)")
    ap.add_argument("--only", help="run only this probe label")
    ap.add_argument("--client", default="claude", help="only this client (default claude)")
    ap.add_argument("--out", default=str(FIXTURE), help="fixture path")
    ap.add_argument("--list", action="store_true", help="list probe labels and exit")
    args = ap.parse_args()

    probes = [p for p in candidates() if p.client == args.client]
    if args.only:
        probes = [p for p in probes if p.label == args.only]
    if args.list:
        for p in probes:
            print(f"{p.label:32s} {p.wire_event:16s} {p.hypothesis}")
        return 0

    if not shutil.which("tmux"):
        print("CRITICAL: tmux not on PATH", file=sys.stderr)
        return 1
    if not shutil.which("claude"):
        print("CRITICAL: claude not on PATH", file=sys.stderr)
        return 1

    results: list[Result] = []
    for idx, p in enumerate(probes, 1):
        print(f"[{idx}/{len(probes)}] RUN {p.label} ({p.wire_event}) ...", flush=True)
        d = Path(tempfile.mkdtemp(prefix=f"ptyhook-{p.label}-"))
        try:
            r = run_probe(p, d)
        except Exception as e:  # noqa: BLE001 — record the failure, keep going
            r = Result(p.label, p.client, p.wire_event, p.hypothesis, note=f"ERROR: {e}")
        finally:
            shutil.rmtree(d, ignore_errors=True)
        results.append(r)
        print(f"      {r.note}", flush=True)
        if r.pane_excerpt:
            print("      pane: " + r.pane_excerpt.replace("\n", " | "), flush=True)

    report = {
        "generated_note": "PTY user-visibility measurement — scripts/pty_hook_probe.py (Layer C)",
        "claude_version": _client_version(),
        "cells": [asdict(r) for r in results],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(f"DONE wrote {len(results)} cells -> {args.out}", flush=True)
    return 0


def _client_version() -> str:
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=15)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "?"


if __name__ == "__main__":
    sys.exit(main())
