"""An additional emission path for the same per-rule evaluation records
``evaluator_trace.py`` already writes as JSON Lines — this module turns each
one into a real OpenTelemetry span, encoded in OTLP JSON and appended to its
own destination. It changes nothing about ``evaluator_trace.py``: that JSON
Lines trace is already tested and in production use as tuning data, and
nothing here replaces it. Both sinks are wired side by side in
``handlers.evaluate``.

**Why a span exists at all.** ``handlers.evaluate`` asks the evaluator once
per rule, per tool call, and the ``on_outcome`` callback ``evaluator.check()``
calls once per rule is the only place this plugin sees a completed
evaluation. One span here is one rule evaluation there: same content, same
verdict, same latency — the two channels stay legible against each other even
though nothing links them by id (see "Field mapping" below for what each side
carries).

**Why OTLP JSON and not a network exporter.** The framework's only existing
OTel machinery (``lib/polecat/env_contract.py`` ``TELEMETRY_ENV``,
specs/ARCHITECTURE.md "Observability & OTEL Tracing") is Claude Code's own
native session export — token counts, tool invocations — forwarded to a
Tailnet OTLP collector. It carries no knowledge of a rule evaluation, and
nothing in this repository built a span of its own before this module.
``opentelemetry-exporter-otlp-proto-http`` is the wire format that collector
already speaks, but it is protobuf, not JSON, and it exists to reach a
network endpoint — shipping one into this plugin would need exactly the
URL/host configuration the framework's no-defaults rule keeps out of a
shipped artifact.  ``opentelemetry-exporter-otlp-json-file``'s
``FileSpanExporter`` writes the same OTLP wire schema (``resourceSpans`` ->
``scopeSpans`` -> ``spans``) straight to a plain file path, in real OTLP
JSON — genuinely OpenTelemetry, genuinely JSON, with the same "path from the
environment, no default" shape ``COPE_EVALUATOR_TRACE_PATH`` already uses. A
collector that ingests OTLP JSON files, or a batch job that replays them as
OTLP/HTTP later, reads this directly; nothing here forecloses that.

**One span per rule, ``SimpleSpanProcessor``, never batched.** A hook
invocation is one short-lived process that exits once ``dispatch.py``
finishes (``handlers.py``'s own module docstring). A ``BatchSpanProcessor``
exports off a background thread and can lose spans to that exit before it
flushes; ``SimpleSpanProcessor`` exports synchronously, inside ``span.end()``,
so nothing outlives the process that created it.

**Enablement mirrors ``evaluator_trace.py`` exactly**: one variable,
``COPE_EVALUATOR_OTEL_TRACE_PATH``, read through the same
``CLAUDE_PLUGIN_OPTION_<NAME>``-then-plain-variable lookup
(``evaluator._setting``). Nothing set means nothing attempted — the same
silent-when-unconfigured contract every setting in this plugin already draws.
Setting the path is the whole enablement; there is no separate toggle.

**Fail-open, always, like the rest of this plugin and like
``evaluator_trace.py``.** An SDK that cannot be imported, or a destination
that cannot be opened or written to, is reported once per sweep on stderr and
then left alone; the tool call this sweep is judging is never affected by
whether its own span could be recorded.

**Field mapping**, one rule evaluation to one span:

- ``rule_slug`` -> the span name (``rbg.rule_evaluation.<slug>``) and a
  ``rule_slug`` attribute.
- ``label``, ``confidence``, ``reason``, ``error`` -> attributes; ``error``
  also sets the span status to ``ERROR`` (``OK`` when there is none).
- ``latency_ms`` -> an attribute, and the span's own start/end delta —
  ``start_time`` is derived backward from ``latency_ms`` so the exported
  span's duration means the same thing the field does.
- ``rule_layer``, ``rule_text`` -> attributes. A rule the loaded set does not
  carry (``rule is None``) omits both rather than sending a placeholder —
  span attributes cannot carry ``None``.
- ``model``, ``protocol``, ``concurrency`` -> attributes, unchanged.
- ``sweep_id``, ``sweep_temperature`` -> attributes. ``sweep_id`` here is its
  own value, generated independently of ``evaluator_trace.py``'s — the two
  channels are not correlated by id, only by carrying the same fields for the
  same sweep. ``sweep_temperature`` reuses
  ``evaluator_trace.sweep_temperature`` rather than recomputing the same
  cold/warm marker twice.
- ``session_id``, ``client``, ``event``, ``tool``, ``content`` -> attributes,
  unchanged.
- resource ``service.name`` -> fixed to ``rbg-evaluator``, identifying every
  span this module emits regardless of whatever ``OTEL_RESOURCE_ATTRIBUTES``
  or ``OTEL_SERVICE_NAME`` an operator has set for Claude Code's own native
  export.

**Never write a credential.** Same contract as ``evaluator_trace.py``: the
evaluator's API key never enters a span attribute, a span name, or a log line
anywhere in this file.
"""

from __future__ import annotations

import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import evaluator
import evaluator_trace
import rules
from dispatch import HookContext

#: The one setting this module reads. Same lookup order as every other
#: setting in this plugin (``evaluator._setting``) and the same shape as
#: ``evaluator_trace.py``'s ``COPE_EVALUATOR_TRACE_PATH`` — a sibling
#: destination, not an alternative toggle for the same one.
_ENV_PATH = "COPE_EVALUATOR_OTEL_TRACE_PATH"

_TRACER_NAME = "academicops.rbg.evaluator"
_RESOURCE_SERVICE_NAME = "rbg-evaluator"


@dataclass(frozen=True)
class Config:
    path: Path


def resolve() -> Config | None:
    """Read the OTel trace destination from the environment.

    ``None`` means this emission path is off — the same
    silent-when-unconfigured contract ``evaluator_trace.resolve()`` and
    ``evaluator.resolve()`` both draw.
    """
    raw = evaluator._setting(_ENV_PATH)  # same plugin, same lookup rule as every other setting
    if not raw:
        return None
    return Config(path=Path(raw))


def _attributes(record: dict[str, Any]) -> dict[str, Any]:
    """Span attributes cannot carry ``None`` — an absent field is omitted
    rather than sent as a sentinel that would misread as a real answer."""
    return {key: value for key, value in record.items() if value is not None}


def sink_for(
    config: Config | None,
    ctx: HookContext,
    eval_config: evaluator.Config,
    loaded: dict[str, rules.Rule],
    temperature: str | None = None,
) -> Callable[[evaluator.EvalOutcome], None] | None:
    """Build the ``on_outcome`` callback ``evaluator.check()`` calls once per
    rule, or ``None`` when this emission path is off.

    Same shape as ``evaluator_trace.sink_for`` — a sibling, not a
    replacement. Every failure mode here — an unimportable SDK, an
    destination that cannot be opened, a write that raises — is caught and
    reported at most once per sweep; none of them ever reaches the caller.

    ``sweep_temperature`` is a one-shot cold/warm marker keyed on session id:
    the first caller to ask for a given session claims "cold" and every one
    after reads "warm", so computing it independently in each sink would make
    the two channels disagree about the very same sweep — whichever sink runs
    second would always read "warm" even on a session's first tool call. Pass
    the one reading ``handlers.evaluate`` already took for this sweep in as
    ``temperature`` so both sinks report the same value; omitted, this
    computes its own (only relevant for a caller that runs this sink alone).
    """
    if config is None:
        return None

    try:
        from opentelemetry.exporter.otlp.json.file import FileSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.trace import Status, StatusCode
    except ImportError as exc:
        print(f"rbg otel trace: opentelemetry not importable: {exc!r}", file=sys.stderr)
        return None

    try:
        config.path.parent.mkdir(parents=True, exist_ok=True)
        resource = Resource.create({"service.name": _RESOURCE_SERVICE_NAME})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(str(config.path))))
        tracer = provider.get_tracer(_TRACER_NAME)
    except OSError as exc:
        print(f"rbg otel trace: could not open {config.path}: {exc!r}", file=sys.stderr)
        return None

    sweep_id = uuid.uuid4().hex[:12]
    if temperature is None:
        temperature = evaluator_trace.sweep_temperature(ctx.session_id)
    content = evaluator.render_content(ctx.tool, ctx.raw.get("tool_input"))
    reported_failure = False

    def _on_outcome(outcome: evaluator.EvalOutcome) -> None:
        nonlocal reported_failure
        rule = loaded.get(outcome.slug)
        attrs = _attributes(
            {
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
        )
        end_ns = time.time_ns()
        start_ns = end_ns - max(int(outcome.latency_s * 1_000_000_000), 0)
        try:
            span = tracer.start_span(
                f"rbg.rule_evaluation.{outcome.slug}",
                start_time=start_ns,
                attributes=attrs,
            )
            if outcome.error:
                span.set_status(Status(StatusCode.ERROR, description=outcome.error))
            else:
                span.set_status(Status(StatusCode.OK))
            span.end(end_time=end_ns)
        except Exception as exc:  # fail-open: a span failure never fails the tool call
            if not reported_failure:
                print(
                    f"rbg otel trace: could not emit span to {config.path}: {exc!r}",
                    file=sys.stderr,
                )
                reported_failure = True

    return _on_outcome
