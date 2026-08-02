"""rbg's rule checks: one per surface, each scoped to the clients that have it.

``evaluate`` is the ``PreToolUse`` check — layer 1, turn by turn. It loads the
three-layer rule set (rules.py) and asks a Reflexes evaluator — a small language
model, remote or locally hosted (evaluator.py) — whether the tool call matches
each live rule. The judgment is the model's; rbg only composes the question and
reports what came back.

``rule_check`` is layer 2, at the session's stop. It is the one handler here
that carries a disposition, and what it withholds is the stop, not a tool call:
the agent gets another turn in which to run the check and show its evidence.
The disposition is legal because the thing being judged is whether the check has
happened at all, which is a fact about the session rather than a reading of a
rule. Registered on both ``Stop`` and ``SubagentStop``, rbg's rule check applies
equally to the face and to a stopping worker, so both events are wired.

One hook invocation is one process (dispatch.py runs, does its job, exits), so
the rule set is loaded once per call and cached at module scope for the life of
that process.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import evaluator
import evaluator_otel_trace
import evaluator_trace
import rules
from dispatch import HookContext, Result, block, load_message_pair, warn

_rules_cache: dict[str, rules.Rule] | None = None


def _loaded_rules(ctx: HookContext) -> dict[str, rules.Rule]:
    global _rules_cache
    if _rules_cache is None:
        plugin_root = ctx.hooks_dir.parent
        cwd = Path(ctx.raw.get("cwd") or Path.cwd())
        _rules_cache = rules.load(plugin_root, cwd)
    return _rules_cache


def _combine_sinks(*sinks):
    """Fan one ``on_outcome`` call out to every configured trace sink.

    ``evaluator.check()`` takes exactly one ``on_outcome`` callback, and
    ``evaluator_trace`` (JSON Lines) and ``evaluator_otel_trace`` (OTLP JSON)
    are independent, additive sinks — either, both, or neither may be
    configured. ``None`` entries (an unconfigured sink) are dropped; ``None``
    comes back when every sink is unconfigured, exactly what ``evaluator.check``
    already treats as "no sink at all".
    """
    live = [sink for sink in sinks if sink is not None]
    if not live:
        return None

    def _call(outcome: evaluator.EvalOutcome) -> None:
        for sink in live:
            sink(outcome)

    return _call


def evaluate(ctx: HookContext) -> Result | None:
    """Ask the evaluator whether this tool call matches any live rule.

    No evaluator configured is a clean no-op — rbg has nothing to ask with,
    which is not a failure of the session. Nothing matched is a no-op too. Only
    a rule the model actually flagged produces an advisory, and the advisory
    hands back the rule's own text so the agent can correct its own course.

    The advisory has two readers, so it is loaded as a pair
    (``load_message_pair``). The agent gets the rule text; the person watching
    gets one line naming what was flagged, because a check that only ever speaks
    to the agent leaves the person whose session it is with no idea it fired.

    An evaluator that could not answer is printed to stderr on every
    occurrence, and named to the agent and the person watching once per
    session (``evaluator.claim_outage_once``) — an outage that recurs on every
    tool call for a session's whole duration is worth one notice, not silence
    and not a line per call. The call still proceeds either way: a rule that
    went unjudged is not a rule that passed, and it is not grounds to hold
    anything up.

    Every rule this sweep asks about — matched, clean, or failed — is durably
    traced when ``COPE_EVALUATOR_TRACE_PATH`` is set (``evaluator_trace.py``),
    and again as an OTel span in OTLP JSON when
    ``COPE_EVALUATOR_OTEL_TRACE_PATH`` is set (``evaluator_otel_trace.py``) —
    two independent, additive sinks, either or both or neither. Tracing is a
    side channel: it changes nothing about what this function returns, and
    its own failures never reach the caller.
    """
    config = evaluator.resolve()
    if config is None:
        return None
    loaded = _loaded_rules(ctx)
    if not loaded or not ctx.tool:
        return None

    content = evaluator.render_content(ctx.tool, ctx.raw.get("tool_input"))
    policies = [(rule.slug, rule.body) for rule in sorted(loaded.values(), key=lambda r: r.slug)]

    trace_config = evaluator_trace.resolve()
    otel_config = evaluator_otel_trace.resolve()
    # sweep_temperature is a one-shot cold/warm marker keyed on session id: the
    # first sink to ask claims "cold" and every one after reads "warm". Taken
    # once here and handed to both sinks, so they agree on it for this sweep
    # instead of the second-built sink always reading one step warmer than
    # the first. Skipped entirely when neither sink is configured, so an
    # unconfigured session claims no marker.
    temperature = (
        evaluator_trace.sweep_temperature(ctx.session_id)
        if trace_config is not None or otel_config is not None
        else None
    )
    # One sweep_id per sweep, shared the same way: generated once here and
    # handed to both sinks so the JSON Lines trace and the OTel spans for this
    # exact tool call carry the identical id, joinable directly rather than by
    # a fuzzy match on timestamp and content.
    sweep_id = (
        uuid.uuid4().hex[:12] if trace_config is not None or otel_config is not None else None
    )
    json_on_outcome = (
        evaluator_trace.sink_for(
            trace_config, ctx, config, loaded, temperature=temperature, sweep_id=sweep_id
        )
        if trace_config is not None
        else None
    )
    otel_on_outcome = (
        evaluator_otel_trace.sink_for(
            otel_config, ctx, config, loaded, temperature=temperature, sweep_id=sweep_id
        )
        if otel_config is not None
        else None
    )
    on_outcome = _combine_sinks(json_on_outcome, otel_on_outcome)
    matches, failures = evaluator.check(
        config, policies, content, ctx.hooks_dir, on_outcome=on_outcome
    )

    outage = None
    if failures:
        detail = (
            f"rbg: the rule evaluator did not answer for {len(failures)} of "
            f"{len(policies)} rules, so those rules are not being checked"
        )
        print("DEGRADED: ", detail, "; ".join(failures), file=sys.stderr)
        if evaluator.claim_outage_once(ctx.session_id):
            agent_o, user_o = load_message_pair(ctx.hooks_dir, "evaluator-outage")
            outage = warn(
                agent_o.replace("{detail}", detail) if agent_o else detail,
                user_o.replace("{detail}", detail) if user_o else detail,
            )

    if not matches:
        return outage
    agent, user = load_message_pair(ctx.hooks_dir, "verdict")
    verdict = warn(
        agent.replace("{rules}", _matched(matches, loaded)).replace("{call}", content),
        user.replace("{rules}", _flagged(matches)) if user else None,
    )
    if outage is None:
        return verdict
    combined_user = " ".join(t for t in (verdict.user_text, outage.user_text) if t) or None
    return warn(f"{verdict.inject_text}\n\n{outage.inject_text}", combined_user)


def _flagged(matches: list[evaluator.Verdict]) -> str:
    """Just the names, for the one line the person watching gets.

    Every flagged rule is named, however many there are: a line that said
    "a rule" would leave them unable to tell a rule they care about from one
    they do not, which is the whole decision the line exists to support.
    """
    return ", ".join(f"`{verdict.slug}`" for verdict in matches)


def _matched(matches: list[evaluator.Verdict], loaded: dict[str, rules.Rule]) -> str:
    """One block per flagged rule: what it requires, and the rule text itself.

    The rule text is the correction — a rule named without its content is a
    scolding the agent cannot act on.
    """
    blocks = []
    for verdict in matches:
        rule = loaded[verdict.slug]
        head = f"### {rule.slug} (layer {rule.layer})"
        if rule.description:
            head += f" — {rule.description}"
        block = [head]
        if verdict.reason:
            block.append(f"The evaluator's reading: {verdict.reason}")
        block.append(rule.body)
        blocks.append("\n\n".join(block))
    return "\n\n".join(blocks)


def _digest(loaded: dict[str, rules.Rule]) -> str:
    """One line per live rule: slug, its layer, and the rule's own one-line
    description. Compressed on purpose — the rule bodies are already shipped as
    files; what a turn needs is the roster, not the text."""
    lines = []
    for rule in sorted(loaded.values(), key=lambda r: (r.layer, r.slug)):
        tail = f" — {rule.description}" if rule.description else ""
        lines.append(f"- **{rule.slug}** ({rule.layer}){tail}")
    return "\n".join(lines)


def rule_check(ctx: HookContext) -> Result | None:
    """Withhold the stop until the session's rule compliance has been checked
    and its evidence presented.

    Blocking, and the only handler here that is. Layer 1 advises on one tool
    call at a time and cannot see the shape of the finished work; this is the
    one moment a whole turn is available to judge, and it is the last one —
    after the stop lands there is nothing left to correct.

    Once per stop-chain, and that guard is dispatch.py's, not this handler's.

    ``background_tasks`` holds it silent while work is still running: nothing is
    being handed back yet, so there is nothing to check, and firing here would
    spend the chain's one block on a turn that is not the handback.

    No transcript is read here. What the hook does is oblige the check; running
    it, and judging what it finds, stays with the agent.
    """
    if ctx.raw.get("background_tasks"):
        return None

    reason = load_message_pair(ctx.hooks_dir, "rule-check")[0]
    if not reason:
        # A block is an instruction to do something. With no text there is no
        # instruction, and blocking would cost the agent a turn to be told
        # nothing — worse than not blocking. Fail open and say why.
        print(
            "DEGRADED: rbg: hooks/messages/rule-check.md is missing or empty, so the stop-side "
            "rule check cannot be asked for; letting the stop through",
            file=sys.stderr,
        )
        return None
    return block(reason)


HANDLERS = {
    "PreToolUse": [evaluate],
    "Stop": [rule_check],
    "SubagentStop": [rule_check],
}
