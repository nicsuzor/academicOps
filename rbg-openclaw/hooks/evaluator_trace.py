"""Durable per-rule evaluation trace — the input/rule/verdict tuples the
evaluator's known instability (README.md, "Concurrency changes the verdicts,
not just the latency") needs as tuning data.

``evaluate`` (handlers.py) asks the evaluator once per tool call, once per
live rule, in parallel. Nothing before this module recorded what any single
one of those requests actually saw or answered — only the fire-level summary
(``lib/hooks/dispatch.py``'s ``AOPS_HOOK_LOG_PATH``: timestamp, client, event,
session, tool) and the human-facing advisory that only ever named the flagged
rules. Both true negatives and the exact rule text sent are the point: a
tuning set built from the flags alone could never show what an unflagged rule
was asked and answered, and this evaluator's known failure mode is producing
a *different* set of flags for the same input under different concurrency,
which no summary log distinguishes.

Enablement is one variable, ``COPE_EVALUATOR_TRACE_PATH`` — read through the
same ``CLAUDE_PLUGIN_OPTION_<NAME>``-then-plain-variable lookup every other
setting in this plugin uses (``evaluator._setting``), so a declared
``userConfig`` option would reach this exactly like it reaches the URL or the
model. No path is compiled in, per the framework's no-defaults rule; with
nothing set, ``resolve()`` returns ``None`` and nothing is written or
attempted — the same silent-when-unconfigured contract ``evaluator.resolve()``
already draws for the evaluator endpoint itself. Setting the path is the whole
enablement: there is no separate on/off flag, because a variable an operator
has to set twice to get one capability is friction the capability does not
need. This mirrors ``AOPS_HOOK_LOG_PATH``'s existing convention in
``lib/hooks/dispatch.py`` (same file, same idea, one layer up).

**Never write a credential.** Nothing here reads ``config.api_key`` — the
evaluator's ``Config`` is passed around this module only for the fields that
are safe to record (``model``, ``protocol``); the api key never enters a
record, a variable name, or a log line anywhere in this file.

**Fail-open, always, like the rest of this plugin.** A destination that
cannot be created or written to is reported once per sweep on stderr and then
left alone; the tool call this sweep is judging is never affected by whether
its own trace could be recorded.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import evaluator
import rules
from dispatch import HookContext

#: The one setting this module reads. Same lookup order as every other
#: setting in this plugin (``evaluator._setting``): the plugin option first,
#: then the plain variable — see that function's docstring for why the first
#: route can only ever be reached via a declared ``userConfig`` option.
_ENV_PATH = "COPE_EVALUATOR_TRACE_PATH"

#: Where the once-per-session "have we swept this session before" marker
#: lives, under ``tempfile.gettempdir()`` — the same idiom
#: ``evaluator.claim_once`` uses, and for the same reason: one hook
#: invocation is one process, so the fact "this session has swept before"
#: cannot live in memory between calls.
_WARM_MARKER_DIR = "aops-rbg-trace-warm"


@dataclass(frozen=True)
class Config:
    path: Path


def resolve() -> Config | None:
    """Read the trace destination from the environment.

    ``None`` means tracing is off — nothing set is a legitimate, silent state,
    exactly as ``evaluator.resolve()`` treats an unconfigured endpoint.
    """
    raw = evaluator._setting(_ENV_PATH)  # same plugin, same lookup rule as every other setting
    if not raw:
        return None
    return Config(path=Path(raw))


def sweep_temperature(session_id: str) -> str:
    """ "cold" for the first sweep this session has run, "warm" after,
    "unknown" when the session id cannot be used to tell.

    A proxy for the evaluator server's own KV-cache state, not a direct read of
    it: this process cannot see llama-server's slots, and neither could the
    measurements this proxy is modelled on (README.md, "What a CPU build
    costs") — those distinguished a `--warmup` sweep from a session's later
    `PreToolUse` calls the same way, by which one came first. A session id
    that is empty can never be marked, so it is "unknown" rather than
    defaulting to "cold" — reporting a temperature with no way to earn it would
    be worse than admitting the trace cannot tell.
    """
    if not session_id:
        return "unknown"
    try:
        root = Path(tempfile.gettempdir()) / _WARM_MARKER_DIR
        root.mkdir(parents=True, exist_ok=True)
        marker = root / hashlib.sha256(session_id.encode()).hexdigest()[:32]
    except OSError:
        return "unknown"
    try:
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return "cold"
    except FileExistsError:
        return "warm"
    except OSError:
        return "unknown"


def _append(path: Path, record: dict) -> None:
    """One JSON line, appended. Never rewritten, never reformatted in place —
    this is research data (see the module docstring's fail-open note for what
    happens when this raises)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def sink_for(
    config: Config | None,
    ctx: HookContext,
    eval_config: evaluator.Config,
    loaded: dict[str, rules.Rule],
    temperature: str | None = None,
    sweep_id: str | None = None,
) -> Callable[[evaluator.EvalOutcome], None] | None:
    """Build the ``on_outcome`` callback ``evaluator.check()`` calls once per
    rule, or ``None`` when tracing is off.

    One sweep (one ``check()`` call, i.e. one tool call's worth of rule
    evaluation) shares a ``sweep_id`` and one ``sweep_temperature`` reading
    across every rule in it — the temperature is a property of the sweep, not
    of any single rule inside it, and grouping by ``sweep_id`` is what lets a
    later reader reassemble "everything this one tool call was asked."

    ``sweep_temperature`` is a one-shot marker: the first call for a session
    id claims "cold" and every later one reads "warm". Where a caller (like
    ``handlers.evaluate``, wiring this sink alongside ``evaluator_otel_trace``'s)
    already has a reading for this exact sweep, it passes it in as
    ``temperature`` so both sinks agree; omitted, this computes its own —
    every existing caller's behaviour, unchanged.

    ``sweep_id`` works the same way: ``handlers.evaluate`` generates one id per
    sweep and hands it to both this sink and ``evaluator_otel_trace``'s, so a
    reader can join the JSON Lines trace and the OTel spans for the same tool
    call on ``sweep_id`` directly rather than a fuzzy match on timestamp and
    content. Omitted, this generates its own — every existing caller's
    behaviour, unchanged.
    """
    if config is None:
        return None
    if sweep_id is None:
        sweep_id = uuid.uuid4().hex[:12]
    if temperature is None:
        temperature = sweep_temperature(ctx.session_id)
    content = evaluator.render_content(ctx.tool, ctx.raw.get("tool_input"))
    reported_failure = False

    def _on_outcome(outcome: evaluator.EvalOutcome) -> None:
        nonlocal reported_failure
        rule = loaded.get(outcome.slug)
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "sweep_id": sweep_id,
            "session_id": ctx.session_id,
            "client": ctx.client,
            "event": ctx.event,
            "tool": ctx.tool,
            "content": content,
            "rule_slug": outcome.slug,
            "rule_layer": rule.layer if rule is not None else None,
            "rule_text": rule.body if rule is not None else None,
            "label": outcome.label,
            "confidence": outcome.confidence,
            "reason": outcome.reason,
            "error": outcome.error,
            "latency_ms": round(outcome.latency_s * 1000, 1),
            "model": eval_config.model,
            "protocol": eval_config.protocol,
            "concurrency": evaluator.MAX_CONCURRENCY,
            "sweep_temperature": temperature,
        }
        try:
            _append(config.path, record)
        except OSError as exc:
            if not reported_failure:
                print(f"rbg trace: could not write to {config.path}: {exc!r}", file=sys.stderr)
                reported_failure = True

    return _on_outcome
