"""Three-layer rule loading for cope's evaluator.

Layer 1 ``axioms/`` (the plugin's own injected copy of ``lib/axioms/`` — the
floor) is loaded first; layer 2 ``$CWD/.agents/rules/*.md`` (project-local)
and layer 3 ``$ACA_DATA/.agents/rules/*.md`` (user-scoped) can only ADD new
slugs, never override one already claimed by an earlier layer — a later
layer adds obligations, it never weakens an axiom (specs/ARCHITECTURE.md,
cope). ``$ACA_DATA`` has no default; its absence is a missing layer, not an
error. A layer directory that is unreadable degrades to the layers that did
load — cope must never block a session on its own failure.

Every layer takes the same marker: only ``trigger: always_on`` files are live
rules, the line build/axioms.py draws. Everything else in a rules directory is
reference material — a path table, a naming convention, a stub — and reference
material sent as a policy is a question the evaluator cannot answer. What is
skipped is named on stderr, so no layer thins out unnoticed.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    slug: str  # filename stem — the identifier a verdict names
    layer: int  # 1 axioms, 2 project-local, 3 user-scoped
    trigger: str
    description: str
    body: str  # the rule text, frontmatter stripped — the policy sent to the evaluator
    path: Path


def _parse(path: Path, layer: int) -> Rule | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cope: could not read rule file {path}: {exc!r}; skipping it", file=sys.stderr)
        return None

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
    try:
        if not layer.path.is_dir():
            if layer.absent_note:
                print(
                    f"cope: no rule directory at {layer.path} ({layer.absent_note}); "
                    f"layer {layer.number} loaded nothing",
                    file=sys.stderr,
                )
            return rules
        paths = sorted(layer.path.glob("*.md"))
    except OSError as exc:
        print(
            f"cope: could not list rule directory {layer.path}: {exc!r}; skipping layer",
            file=sys.stderr,
        )
        return rules
    for md_path in paths:
        rule = _parse(md_path, layer.number)
        if rule is None:
            continue
        if rule.trigger != "always_on":
            skipped.append(md_path.name)
            continue
        rules[rule.slug] = rule
    if skipped and layer.report_skips:
        print(
            f"cope: {layer.path}: {', '.join(skipped)} — read by agents, not evaluated: "
            "add `trigger: always_on` frontmatter to send a file to the evaluator",
            file=sys.stderr,
        )
    return rules


def load(plugin_root: Path, cwd: Path) -> dict[str, Rule]:
    """Load all three layers and return slug -> Rule.

    A slug already claimed by an earlier layer is never replaced — layer 1
    (axioms) always wins a collision, then layer 2, then layer 3. This is
    what "later layers add obligations, never weaken an axiom" means at the
    data-structure level: a project or user rule file cannot shadow an
    axiom's entry just by reusing its filename.
    """
    rules: dict[str, Rule] = {}
    for layer in _layers(plugin_root, cwd):
        for slug, rule in _load_dir(layer).items():
            rules.setdefault(slug, rule)
    return rules


def _layers(plugin_root: Path, cwd: Path) -> list[_Layer]:
    """Each layer's directory, and what its silences are allowed to be.

    Every layer requires ``trigger: always_on``; a rules directory holds
    reference documents as well as policies, and only a policy can be
    classified. What differs per layer is what deserves a line on stderr.

    Layer 1 is the plugin's own shipped ``axioms/``, whose non-rule files are a
    known, curated set (``README.md``, ``AXIOMS-REVIEW.md``) that nobody in the
    session can act on — naming them every tool call would be noise. Layers 2
    and 3 belong to the project and the user, who can act: a file skipped there
    is named once per load, because a rule that quietly stops being evaluated
    is worse than one that was never written.

    An absent layer-2 directory is the ordinary case — most projects carry no
    local rules — so it says nothing. An absent layer-3 directory is a wrong
    ``$ACA_DATA`` or a path that moved, since setting the variable is a claim
    that the layer exists; that gets a line. ``$ACA_DATA`` unset is not a
    mistake and stays silent.
    """
    layers = [
        _Layer(1, plugin_root / "axioms", report_skips=False, absent_note=None),
        _Layer(2, cwd / ".agents" / "rules", report_skips=True, absent_note=None),
    ]
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        layers.append(
            _Layer(
                3,
                Path(aca_data) / ".agents" / "rules",
                report_skips=True,
                absent_note="ACA_DATA is set, so this layer was expected",
            )
        )
    return layers
