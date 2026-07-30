"""cope's advisories: one per surface, each scoped to the clients that have it.

``evaluate`` is the ``PreToolUse`` check. It loads the three-layer rule set
(rules.py) and asks a Reflexes evaluator — a small language model, remote or
locally hosted (evaluator.py) — whether the tool call matches each live rule.
The judgment is the model's; cope only composes the question and reports what
came back. Nothing about a rule's meaning is decided by matching text against
a pattern.

``inject_ruleset`` is the ``UserPromptSubmit`` (agy ``PreInvocation``) advisory.
That surface carries a prompt, not a tool call, so there is nothing for the
evaluator to judge there. What it can do is state the rule set that is live for
the turn. It is scoped to agy because Claude Code fires both events and is
already covered by ``evaluate``, and because the pkb plugin owns Claude's
``UserPromptSubmit`` injection.

Both are advisory only — they return a ``Result`` (context injected for the
agent to read), never a permission decision; see lib/hooks/result.py and
specs/ARCHITECTURE.md, Enforcement. Real enforcement is a separate merge-stage
check.

One hook invocation is one process (dispatch.py runs, does its job, exits), so
the rule set is loaded once per call and cached at module scope for the life of
that process — there is no server to keep warm.
"""

from __future__ import annotations

from pathlib import Path

import sys
import evaluator
from dispatch import load_message_pair
import rules
from dispatch import HookContext
from dispatch import Result, warn

_rules_cache: dict[str, rules.Rule] | None = None


def only_on(*client_names: str):
    """Declare the clients a handler runs for.

    dispatch.py reads the ``only_on_clients`` attribute this sets and skips the
    handler for every other client. An undeclared handler runs for all of them,
    so this is opt-in: it exists to state a scope out loud, at the point of
    definition, rather than leaving it as an ``if ctx.client`` buried in a
    handler body that still costs a process to reach.
    """

    def declare(handler):
        handler.only_on_clients = frozenset(client_names)
        return handler

    return declare


def _loaded_rules(ctx: HookContext) -> dict[str, rules.Rule]:
    global _rules_cache
    if _rules_cache is None:
        plugin_root = ctx.hooks_dir.parent
        cwd = Path(ctx.raw.get("cwd") or Path.cwd())
        _rules_cache = rules.load(plugin_root, cwd)
    return _rules_cache


def evaluate(ctx: HookContext) -> Result | None:
    """Ask the evaluator whether this tool call matches any live rule.

    No evaluator configured is a clean no-op — cope has nothing to ask with,
    which is not a failure of the session. Nothing matched is a no-op too. Only
    a rule the model actually flagged produces an advisory, and the advisory
    hands back the rule's own text so the agent can correct its own course.

    The advisory has two readers, so it is loaded as a pair (lib/hooks/
    messages.py). The agent gets the rule text; the person watching gets one
    line naming what was flagged, because a check that only ever speaks to the
    agent leaves the person whose session it is with no idea it fired.

    An evaluator that could not answer reaches both of them for the same
    reason, once per session (lib/hooks/degraded.py). The call still proceeds:
    a rule that went unjudged is not a rule that passed, and it is not grounds
    to hold anything up.
    """
    config = evaluator.resolve()
    if config is None:
        return None
    loaded = _loaded_rules(ctx)
    if not loaded or not ctx.tool:
        return None

    content = evaluator.render_content(ctx.tool, ctx.raw.get("tool_input"))
    policies = [(rule.slug, rule.body) for rule in sorted(loaded.values(), key=lambda r: r.slug)]
    matches, failures = evaluator.check(config, policies, content, ctx.hooks_dir)

    if failures:
        print(
            "DEGRADED: ",
            f"cope: the rule evaluator did not answer for {len(failures)} of "
            f"{len(policies)} rules, so those rules are not being checked",
            "; ".join(failures),
        )

    if not matches:
        return None
    agent, user = load_message_pair(ctx.hooks_dir, "verdict")
    return warn(
        agent.replace("{rules}", _matched(matches, loaded)).replace("{call}", content),
        user.replace("{rules}", _flagged(matches)) if user else None,
    )


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


@only_on("agy")
def inject_ruleset(ctx: HookContext) -> Result | None:
    """State the live rule set for the turn, on the surface where the evaluator
    has no tool call to judge. Nothing loaded is nothing to say."""
    loaded = _loaded_rules(ctx)
    if not loaded:
        return None
    return warn(load_message_pair(ctx.hooks_dir, "ruleset")[0].replace("{rules}", _digest(loaded)))


HANDLERS = {
    "PreToolUse": [evaluate],
    "UserPromptSubmit": [inject_ruleset],
}
