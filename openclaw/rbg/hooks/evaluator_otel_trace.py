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
- ``sweep_id``, ``sweep_temperature`` -> attributes. ``handlers.evaluate``
  generates one ``sweep_id`` per sweep and hands it to both this sink and
  ``evaluator_trace.py``'s, so the two channels are directly joinable on it —
  the same tool call's JSON Lines record and OTel span carry the identical id.
  ``sweep_temperature`` likewise reuses ``evaluator_trace.sweep_temperature``
  rather than recomputing the same cold/warm marker twice.
- ``session_id``, ``client``, ``event``, ``tool``, ``content`` -> attributes,
  unchanged.
- resource ``service.name`` -> fixed to ``rbg-evaluator``, identifying every
  span this module emits regardless of whatever ``OTEL_RESOURCE_ATTRIBUTES``
  or ``OTEL_SERVICE_NAME`` an operator has set for Claude Code's own native
  export.

**Parenting** (``_extract_parent_context``). Every span this module starts is
given the W3C trace context Claude Code exports as ``TRACEPARENT`` (and
``TRACESTATE``, when present) in this hook subprocess's own environment, so a
rule-evaluation span lands in the same trace as the Claude Code session that
triggered it rather than as an orphaned root — real linkage where both sides
export to the same collector. That context is one id pair *per Claude Code
process*, confirmed unchanged across two sequential tool calls in one session,
so it nests every span in a session under the same parent rather than under a
distinct span per tool call; ``sweep_id`` is what still groups one tool call's
spans together. Absent (no ``TRACEPARENT`` — the native-export contract is not
fully populated) or unparseable, spans start as fresh roots exactly as before;
nothing here is required for this module to keep working.

**Never write a credential.** Same contract as ``evaluator_trace.py``: the
evaluator's API key never enters a span attribute, a span name, or a log line
anywhere in this file.
"""

from __future__ import annotations

import os
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


def _extract_parent_context() -> Any | None:
    """Pick up the W3C trace context Claude Code exports to a hook subprocess
    for the tool call it is currently dispatching, or ``None`` when no such
    context is present.

    Claude Code sets ``TRACEPARENT`` (and, when present, ``TRACESTATE``) in a
    hook subprocess's environment whenever the full native-export contract is
    populated — ``CLAUDE_CODE_ENABLE_TELEMETRY``, ``CLAUDE_CODE_ENHANCED_TELEMETRY_BETA``,
    and ``OTEL_TRACES_EXPORTER=otlp`` together (verified empirically against a
    real headless ``claude`` session with a diagnostic hook: absent with any one
    of the three missing, present with all three). The framework's own
    ``lib/polecat/env_contract.py`` ``TELEMETRY_ENV`` already forwards this
    whole contract, so any session with telemetry enabled the way the
    framework sets it up carries this context into every hook subprocess,
    this one included.

    That context is one W3C trace/span id **per Claude Code process**, not one
    per tool call — confirmed by comparing ``TRACEPARENT`` across two
    sequential tool calls in one session: identical trace id and identical
    span id both times. So extracting it and using it as the parent nests
    every rule-evaluation span under the session's own trace — real,
    verifiable linkage to Claude Code's native export when both reach the same
    collector — but it does not, and cannot on this harness, distinguish one
    tool call's spans from another's: that distinction is what ``sweep_id``
    carries instead (see ``sink_for``'s docstring).

    Returns ``None`` — meaning "no parent, start a fresh root" — exactly when
    ``TRACEPARENT`` is absent or unparseable, so a session without the full
    contract populated degrades to today's behavior with no error.
    """
    traceparent = os.environ.get("TRACEPARENT")
    if not traceparent:
        return None
    try:
        from opentelemetry.trace import get_current_span
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )
    except ImportError:
        return None
    carrier = {"traceparent": traceparent}
    tracestate = os.environ.get("TRACESTATE")
    if tracestate:
        carrier["tracestate"] = tracestate
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
    # An unparseable traceparent extracts to a context with no span in it
    # rather than raising — the propagator degrades silently by design. That
    # context is harmless to hand to start_span (an invalid parent starts a
    # fresh root, the same outcome as passing None), but returning it here
    # would blur "we got a real parent" with "extraction quietly no-opped".
    # Checking the span it actually carries keeps the two distinguishable.
    if not get_current_span(ctx).get_span_context().is_valid:
        return None
    return ctx


def _get_tracer(config: Config):
    from opentelemetry.exporter.otlp.json.file import FileSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    config.path.parent.mkdir(parents=True, exist_ok=True)
    resource = Resource.create({"service.name": _RESOURCE_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(str(config.path))))
    return provider.get_tracer(_TRACER_NAME)


def detect_tool_plumbing_error(ctx: HookContext) -> tuple[str, str] | None:
    """Detect tool plumbing errors (unknown_tool or missing_mcp) in HookContext.

    Returns (error_type, error_message) or None.
    """
    raw = ctx.raw or {}
    err_type = raw.get("error_type") or raw.get("error_code")
    err_msg = raw.get("error_message") or raw.get("error") or ""

    if err_type in ("unknown_tool", "missing_mcp"):
        return str(err_type), str(err_msg or err_type)

    if ctx.tool in ("unknown_tool", "missing_mcp"):
        return ctx.tool, str(err_msg or ctx.tool)

    err_str = str(raw.get("error") or raw.get("tool_error") or "").lower()
    if "unknown_tool" in err_str or "unknown tool" in err_str:
        return "unknown_tool", str(raw.get("error") or raw.get("tool_error"))
    if "missing_mcp" in err_str or "missing mcp" in err_str or "mcp tool missing" in err_str:
        return "missing_mcp", str(raw.get("error") or raw.get("tool_error"))

    tool_calls = ctx.tool_calls or raw.get("tool_calls") or ()
    if ctx.event == "PostToolBatch" or not ctx.tool or tool_calls:
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            c_type = call.get("error_type") or call.get("error_code")
            c_msg = call.get("error_message") or call.get("error") or call.get("tool_error") or ""
            c_tool = call.get("tool_name") or call.get("tool") or ""

            if c_type in ("unknown_tool", "missing_mcp"):
                return str(c_type), str(c_msg or c_type)
            if c_tool in ("unknown_tool", "missing_mcp"):
                return str(c_tool), str(c_msg or c_tool)

            c_err_str = str(
                call.get("error") or call.get("tool_error") or call.get("error_message") or ""
            ).lower()
            if "unknown_tool" in c_err_str or "unknown tool" in c_err_str:
                return "unknown_tool", str(c_msg or "unknown_tool")
            if (
                "missing_mcp" in c_err_str
                or "missing mcp" in c_err_str
                or "mcp tool missing" in c_err_str
            ):
                return "missing_mcp", str(c_msg or "missing_mcp")

    return None


def record_tool_plumbing_error(
    ctx: HookContext,
    error_type: str = "unknown_tool",
    error_message: str | None = None,
    config: Config | None = None,
) -> None:
    """Instrument tool plumbing errors with OTEL exception events and StatusCode.ERROR."""
    if config is None:
        config = resolve()
    if config is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode

        tracer = _get_tracer(config)
        parent_ctx = _extract_parent_context()
        attrs = _attributes(
            {
                "session_id": ctx.session_id,
                "client": ctx.client,
                "event": ctx.event,
                "tool": ctx.tool or error_type,
                "error_type": error_type,
                "error_message": error_message,
            }
        )
        msg = error_message or f"Tool plumbing error: {error_type}"
        start_ns = time.time_ns()
        span = tracer.start_span(
            f"tool.error.{error_type}",
            context=parent_ctx,
            start_time=start_ns,
            attributes=attrs,
        )
        span.record_exception(Exception(msg))
        span.set_status(Status(StatusCode.ERROR, description=msg))
        span.end(end_time=time.time_ns())
    except Exception as exc:
        print(f"rbg otel trace: error recording tool plumbing error: {exc!r}", file=sys.stderr)
        raise


def detect_agent_idle_timeout(ctx: HookContext) -> str | None:
    """Detect agent idle or timeout status on Stop / SubagentStop events."""
    if ctx.event not in ("Stop", "SubagentStop"):
        return None
    raw = ctx.raw or {}
    reason = str(raw.get("reason") or raw.get("stop_reason") or raw.get("status") or "").lower()
    if "timeout" in reason or raw.get("timeout"):
        return "timeout"
    if "idle" in reason or raw.get("idle"):
        return "idle"
    return None


def record_agent_idle_timeout(
    ctx: HookContext,
    event_type: str = "idle",
    details: dict | None = None,
    config: Config | None = None,
) -> None:
    """Instrument agent idle/timeout events on Stop / SubagentStop."""
    if config is None:
        config = resolve()
    if config is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode

        tracer = _get_tracer(config)
        parent_ctx = _extract_parent_context()
        attrs = {
            "session_id": ctx.session_id,
            "client": ctx.client,
            "event": ctx.event,
            "reason": event_type,
            "idle": event_type == "idle",
            "timeout": event_type == "timeout",
        }
        if details:
            attrs.update(details)
        attrs = _attributes(attrs)

        start_ns = time.time_ns()
        span = tracer.start_span(
            f"agent.{event_type}",
            context=parent_ctx,
            start_time=start_ns,
            attributes=attrs,
        )
        if event_type == "timeout":
            msg = f"Agent operation timed out on {ctx.event}"
            span.record_exception(TimeoutError(msg))
            span.set_status(Status(StatusCode.ERROR, description=msg))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end(end_time=time.time_ns())
    except Exception as exc:
        print(f"rbg otel trace: error recording agent idle/timeout: {exc!r}", file=sys.stderr)
        raise


def record_send_message(
    ctx: HookContext,
    target_agent: str | None = None,
    parent_agent: str | None = None,
    config: Config | None = None,
) -> str | None:
    """Instrument SendMessage tool call with parent/target span linkage and traceparent propagation."""
    if config is None:
        config = resolve()
    if config is None:
        return None
    try:
        from opentelemetry.trace import Status, StatusCode

        tracer = _get_tracer(config)
        parent_ctx = _extract_parent_context()
        raw_input = ctx.raw.get("tool_input") or {}
        if not target_agent and isinstance(raw_input, dict):
            target_agent = (
                raw_input.get("recipient")
                or raw_input.get("target")
                or raw_input.get("recipient_id")
                or raw_input.get("target_agent")
            )
        if not parent_agent:
            parent_agent = ctx.session_id or "parent"

        attrs = _attributes(
            {
                "session_id": ctx.session_id,
                "client": ctx.client,
                "event": ctx.event,
                "tool": "SendMessage",
                "parent_agent": parent_agent,
                "target_agent": target_agent,
            }
        )
        start_ns = time.time_ns()
        span = tracer.start_span(
            "agent.send_message",
            context=parent_ctx,
            start_time=start_ns,
            attributes=attrs,
        )
        span_ctx = span.get_span_context()
        new_traceparent = f"00-{span_ctx.trace_id:032x}-{span_ctx.span_id:016x}-01"
        span.set_attribute("propagated_traceparent", new_traceparent)
        span.set_status(Status(StatusCode.OK))
        span.end(end_time=time.time_ns())
        return new_traceparent
    except Exception as exc:
        print(f"rbg otel trace: error recording SendMessage: {exc!r}", file=sys.stderr)
        raise


def record_subagent_stop(
    ctx: HookContext,
    has_unsent_output: bool | None = None,
    unsent_content: str | None = None,
    config: Config | None = None,
) -> None:
    """Instrument SubagentStop event handling to inspect for unsent output and record status/warning spans."""
    if config is None:
        config = resolve()
    if config is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode

        tracer = _get_tracer(config)
        parent_ctx = _extract_parent_context()
        if has_unsent_output is None:
            raw = ctx.raw or {}
            has_unsent_output = bool(
                raw.get("unsent_output")
                or raw.get("has_unsent_output")
                or raw.get("unreported_output")
                or raw.get("output_unsent")
            )
            if not unsent_content and isinstance(raw.get("unsent_output"), str):
                unsent_content = raw.get("unsent_output")

        attrs = {
            "session_id": ctx.session_id,
            "client": ctx.client,
            "event": "SubagentStop",
            "has_unsent_output": has_unsent_output,
        }
        if unsent_content:
            attrs["unsent_content"] = str(unsent_content)
        attrs = _attributes(attrs)

        start_ns = time.time_ns()
        span = tracer.start_span(
            "agent.subagent_stop",
            context=parent_ctx,
            start_time=start_ns,
            attributes=attrs,
        )
        if has_unsent_output:
            msg = "Subagent stopped with unsent output"
            span.set_attribute("warning", "unsent_output_detected")
            span.record_exception(Exception(msg))
            span.set_status(Status(StatusCode.ERROR, description=msg))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end(end_time=time.time_ns())
    except Exception as exc:
        print(f"rbg otel trace: error recording SubagentStop: {exc!r}", file=sys.stderr)
        raise


def sink_for(
    config: Config | None,
    ctx: HookContext,
    eval_config: evaluator.Config,
    loaded: dict[str, rules.Rule],
    temperature: str | None = None,
    sweep_id: str | None = None,
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

    ``sweep_id`` is likewise taken from the caller when given, so this sink's
    spans and ``evaluator_trace``'s JSON Lines records carry the identical id
    for the same tool call — the join key a reader needs to line up one
    channel's record against the other's span for the same evaluation, rather
    than two independently-generated ids that merely describe the same sweep.
    Omitted, this generates its own (only relevant for a caller that runs this
    sink alone).
    """
    if config is None:
        return None

    try:
        from opentelemetry.trace import Status, StatusCode

        tracer = _get_tracer(config)
    except Exception as exc:
        print(f"rbg otel trace: error initializing tracer: {exc!r}", file=sys.stderr)
        raise

    if sweep_id is None:
        sweep_id = uuid.uuid4().hex[:12]
    if temperature is None:
        temperature = evaluator_trace.sweep_temperature(ctx.session_id)
    content = evaluator.render_content(ctx.tool, ctx.raw.get("tool_input"))
    parent_ctx = _extract_parent_context()
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
                context=parent_ctx,
                start_time=start_ns,
                attributes=attrs,
            )
            if outcome.error:
                span.set_status(Status(StatusCode.ERROR, description=outcome.error))
            else:
                span.set_status(Status(StatusCode.OK))
            span.end(end_time=end_ns)
        except Exception as exc:
            if not reported_failure:
                print(
                    f"rbg otel trace: could not emit span to {config.path}: {exc!r}",
                    file=sys.stderr,
                )
                reported_failure = True
            raise

    return _on_outcome
