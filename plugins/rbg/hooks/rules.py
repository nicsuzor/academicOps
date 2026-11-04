"""Rule loading across three scopes for cope's evaluator.

Axioms in ``skills/axioms/`` (the baseline) are loaded first; project rules in
``$CWD/.agents/rules/*.md`` and user rules in ``$COPE_USER_RULES_DIR/*.md``
can only ADD new slugs, never override one already claimed by an earlier scope —
narrower scopes add obligations and never weaken an axiom (specs/ARCHITECTURE.md,
cope). ``$COPE_USER_RULES_DIR`` has no default; its absence is an absent user-rules scope, not an
error. A rule directory that is unreadable degrades to the scopes that did
load — cope must never block a session on its own failure.

Every scope takes the same marker, and it has three states:

``always_on``  a live rule; the policy goes to the evaluator on every tool call.
``off``        a real policy, deliberately parked. Silent — see below.
anything else  reference material — a path table, a naming convention, a stub —
               and reference material sent as a policy is a question the
               evaluator cannot answer.

``off`` is not the same as unmarked, which is why it is spelled out rather than
left to fall through. An unmarked file in a scope the user owns is reported, on
the assumption nobody meant to write a rule the evaluator never sees; ``off`` is
somebody saying they meant it, so reporting it would train the reader to skip
the report. Turning a rule off one file at a time, and back on the same way, is
the whole point of the marker having a third state.

A scope that thins out says so on stderr (``DEGRADED:``), which the client
captures into the transcript. That is the only channel these reports have: they
do not reach the agent's response and they do not reach the person. Nothing here
is rate-limited, because nothing here is read live. A rules directory nobody
wrote and a ``$COPE_USER_RULES_DIR`` nobody set are ordinary absences and stay silent —
see ``_layers``. A roster that loads to nothing is neither absence nor fault,
and is named on the response once per session — see ``handlers.evaluate``.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

#: A rule file or a whole layer could not be read — rules the session was
#: relying on are not being checked.
DEGRADED_RULES = "cope-rules"

#: Rule files are present but carry no ``trigger:`` marker this module knows, so
#: they reach agents as reading material and the evaluator never sees them.
DEGRADED_UNMARKED = "cope-rules-unmarked"

#: The marker on a live rule: its policy is sent to the evaluator every call.
TRIGGER_ON = "always_on"

#: The marker on a rule deliberately parked. Skipped like an unmarked file, but
#: never reported as one — the whole difference is that somebody chose it.
TRIGGER_OFF = "off"


@dataclass(frozen=True)
class Rule:
    slug: str  # filename stem — the identifier a verdict names
    layer: int  # 1 axioms, 2 project-local, 3 user-scoped
    trigger: str
    description: str
    body: str  # the rule text, frontmatter stripped — the policy sent to the evaluator
    path: Path


def _parse(path: Path, layer: int) -> Rule:
    text = path.read_text(encoding="utf-8")

    trigger = ""
    description = ""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                key, sep, value = line.partition(":")
                if not sep:
                    continue
                key = key.strip()
                value = value.strip()
                if key == "trigger":
                    trigger = value
                elif key == "description":
                    description = value
            body = text[end + len("\n---") :]

    return Rule(
        slug=path.stem,
        layer=layer,
        trigger=trigger,
        description=description,
        body=body.strip(),
        path=path,
    )


@dataclass(frozen=True)
class _Layer:
    number: int  # 1 axioms, 2 project-local, 3 user-scoped
    path: Path
    report_skips: bool  # name the *.md files dropped for want of the marker
    absent_note: str | None  # why an absent directory is worth a line; None = say nothing


def _load_dir(layer: _Layer) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    skipped: list[str] = []
    if not layer.path.is_dir():
        if layer.absent_note:
            print(
                "DEGRADED: ",
                DEGRADED_RULES,
                f"cope: there is no rule directory at {layer.path} ({layer.absent_note}), "
                f"so layer {layer.number} is not being checked",
                file=sys.stderr,
            )
        return rules
    paths = sorted(layer.path.glob("*.md"))
    for md_path in paths:
        rule = _parse(md_path, layer.number)
        if rule.trigger == TRIGGER_OFF:
            continue
        if rule.trigger != TRIGGER_ON:
            skipped.append(md_path.name)
            continue
        rules[rule.slug] = rule
    if skipped and layer.report_skips:
        print(
            "DEGRADED: ",
            DEGRADED_UNMARKED,
            f"cope: {', '.join(skipped)} in {layer.path} are read by agents but never "
            "evaluated — add `trigger: always_on` frontmatter to send a file to the evaluator",
            file=sys.stderr,
        )
    return rules


def load(plugin_root: Path, cwd: Path) -> dict[str, Rule]:
    """Load all three rule scopes and return slug -> Rule.

    A slug already claimed by an earlier scope is never replaced — axioms
    always win a collision, then project rules, then user rules. This is
    what "narrower scopes add obligations, never weaken an axiom" means at the
    data-structure level: a project or user rule file cannot shadow an
    axiom's entry just by reusing its filename.
    """
    rules: dict[str, Rule] = {}
    for layer in _layers(plugin_root, cwd):
        for slug, rule in _load_dir(layer).items():
            rules.setdefault(slug, rule)
    return rules


def _layers(plugin_root: Path, cwd: Path) -> list[_Layer]:
    """Each scope's directory, and what its silences are allowed to be.

    Every scope requires ``trigger: always_on``; a rules directory holds
    reference documents as well as policies, and only a policy can be
    classified. What differs per scope is what deserves reporting.

    The axioms scope is the plugin's own shipped ``skills/axioms/``, whose non-rule files are a
    known, curated set (``SKILL.md``, ``README.md``, ``AXIOMS-REVIEW.md``) that nobody in the
    session can act on — naming them every tool call would be noise. Project rules
    and user rules belong to the project and the user, who can act: a file skipped there
    is named, because a rule that quietly stops being evaluated is worse than
    one that was never written.

    An absent project-rules directory is the ordinary case — most projects carry no
    local rules — so it says nothing. An absent user-rules directory is a wrong
    ``$COPE_USER_RULES_DIR`` or a path that moved, since setting the variable is a claim
    that the directory exists; that is reported. ``$COPE_USER_RULES_DIR`` unset is not a
    mistake and stays silent.
    """
    layers = [
        _Layer(1, plugin_root / "skills" / "axioms", report_skips=False, absent_note=None),
        _Layer(2, cwd / ".agents" / "rules", report_skips=True, absent_note=None),
    ]
    cope_user_rules_dir = os.environ.get("COPE_USER_RULES_DIR")
    if cope_user_rules_dir:
        layers.append(
            _Layer(
                3,
                Path(cope_user_rules_dir),
                report_skips=True,
                absent_note="COPE_USER_RULES_DIR is set, so this layer was expected",
            )
        )
    return layers
