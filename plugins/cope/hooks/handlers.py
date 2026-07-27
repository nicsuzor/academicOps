"""cope's advisories: one per surface, each scoped to the clients that have it.

``evaluate`` is the ``PreToolUse`` check. It loads the three-layer rule set
(rules.py), runs the built-in syntactic detectors (detectors.py) for whichever
axiom slugs are actually loaded, and injects a short, rule-naming advisory on
the first match.

``inject_ruleset`` is the ``UserPromptSubmit`` (agy ``PreInvocation``) advisory.
That surface carries a prompt, not a tool call, so no detector can run there —
there is no tool name and no tool input to match against. What it can do is
state the rule set that is live for the turn. It is scoped to agy because
Claude Code fires both events and is already covered by ``evaluate``, and
because the pkb plugin owns Claude's ``UserPromptSubmit`` injection.

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

import detectors
import rules
from context import HookContext
from result import Result, warn

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
    loaded = _loaded_rules(ctx)
    for slug, detector in detectors.DETECTORS.items():
        if slug not in loaded:
            continue  # this axiom isn't in scope at any loaded layer
        snippet = detector(ctx)
        if snippet is None:
            continue
        advisory = ctx.message(slug)
        return warn(f"{advisory}\n\nMatched in this call: `{snippet}`")
    return None


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
    """State the live rule set for the turn, on the surface where no detector
    can run. Nothing loaded is nothing to say."""
    loaded = _loaded_rules(ctx)
    if not loaded:
        return None
    return warn(ctx.message("ruleset").replace("{rules}", _digest(loaded)))


HANDLERS = {
    "PreToolUse": [evaluate],
    "UserPromptSubmit": [inject_ruleset],
}
