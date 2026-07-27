"""Three-layer rule loading for cope's evaluator.

Layer 1 ``axioms/`` (the plugin's own injected copy of ``lib/axioms/`` — the
floor) is loaded first; layer 2 ``$CWD/.agents/rules/*.md`` (project-local)
and layer 3 ``$ACA_DATA/.agents/rules/*.md`` (user-scoped) can only ADD new
slugs, never override one already claimed by an earlier layer — a later
layer adds obligations, it never weakens an axiom (specs/ARCHITECTURE.md,
cope). ``$ACA_DATA`` has no default; its absence is a missing layer, not an
error. A layer directory that is missing or unreadable degrades silently to
the layers that did load — cope must never block a session on its own
failure.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    slug: str  # filename stem — the identifier detectors.py keys off
    layer: int  # 1 axioms, 2 project-local, 3 user-scoped
    trigger: str
    description: str
    path: Path


def _parse(path: Path, layer: int) -> Rule | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cope: could not read rule file {path}: {exc!r}; skipping it", file=sys.stderr)
        return None

    trigger = ""
    description = ""
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

    return Rule(slug=path.stem, layer=layer, trigger=trigger, description=description, path=path)


def _load_dir(dir_path: Path, layer: int, *, always_on_only: bool) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    try:
        if not dir_path.is_dir():
            return rules
        paths = sorted(dir_path.glob("*.md"))
    except OSError as exc:
        print(
            f"cope: could not list rule directory {dir_path}: {exc!r}; skipping layer",
            file=sys.stderr,
        )
        return rules
    for md_path in paths:
        rule = _parse(md_path, layer)
        if rule is None:
            continue
        if always_on_only and rule.trigger != "always_on":
            continue
        rules[rule.slug] = rule
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
    for layer, dir_path, always_on_only in _layers(plugin_root, cwd):
        for slug, rule in _load_dir(dir_path, layer, always_on_only=always_on_only).items():
            rules.setdefault(slug, rule)
    return rules


def _layers(plugin_root: Path, cwd: Path) -> list[tuple[int, Path, bool]]:
    """Each layer's directory, and whether `trigger: always_on` is required.

    Layer 1 is the plugin's own shipped ``axioms/``, which also carries index
    and companion docs (``README.md``, ``AXIOMS-REVIEW.md``). Only the
    ``trigger: always_on`` files there are live rules — the same line the build
    draws in build/axioms.py when it emits a client's native rule mechanism.

    Layers 2 and 3 are directories the project and the user own. Every ``*.md``
    in a ``.agents/rules/`` directory is a rule by virtue of being there, so
    requiring frontmatter would silently drop a rule someone wrote plainly.
    """
    layers = [
        (1, plugin_root / "axioms", True),
        (2, cwd / ".agents" / "rules", False),
    ]
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        layers.append((3, Path(aca_data) / ".agents" / "rules", False))
    return layers
