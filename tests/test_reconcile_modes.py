"""Reconcile runs in two modes from one skill.

``check`` is the short pass a supervisor runs over the tasks it is handed;
``sweep`` is the long pass over the whole graph that runs as a scheduled run.
The procedure has one owner (specs/workflows/reconcile.md, constraint 1), so
both modes live in the reconcile skill and every caller names the mode it runs.

These checks read ``plugins/`` directly, so they hold on a source-only checkout.
"""

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IDA = PROJECT_ROOT / "plugins" / "ida"
SKILL = IDA / "skills" / "reconcile" / "SKILL.md"
CONSOLIDATION = IDA / "skills" / "remember" / "references" / "consolidation.md"
SARA = IDA / "agents" / "sara.md"
SPEC = PROJECT_ROOT / "specs" / "workflows" / "reconcile.md"

# Steps that read beyond the tasks a supervisor was handed. They belong to the sweep.
GRAPH_WIDE_STEPS = [
    "Load active tasks",
    "Demote affected tasks",
    "Cancel on world-facts",
    "Reconcile pull requests",
]


def frontmatter(path: Path) -> dict:
    _, block, _ = path.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(block)


def section(path: Path, heading: str) -> str:
    """Body of the level-2 section titled ``heading``, up to the next level-2 heading."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(heading)}\b.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"{path.relative_to(PROJECT_ROOT)} has no '## {heading}' section"
    return match.group(1)


def test_description_routes_to_both_modes():
    description = frontmatter(SKILL)["description"]
    assert "check" in description and "sweep" in description, description


def test_check_mode_is_scoped_to_the_tasks_it_is_handed():
    check = section(SKILL, "Check")
    assert "task ID" in check
    leaked = [step for step in GRAPH_WIDE_STEPS if step in check]
    assert not leaked, f"graph-wide steps in the supervisor check: {leaked}"
    assert "sweep" in check, "check must hand what it does not cover to the sweep"


def test_sweep_mode_carries_the_graph_wide_steps():
    sweep = section(SKILL, "Sweep")
    missing = [step for step in GRAPH_WIDE_STEPS if step not in sweep]
    assert not missing, f"sweep lacks graph-wide steps: {missing}"


def test_sweep_names_how_a_scheduled_run_invokes_it():
    sweep = section(SKILL, "Sweep")
    assert "scheduled" in sweep
    assert "/ida:reconcile sweep" in sweep


def test_consolidation_cycle_delegates_to_the_sweep():
    text = CONSOLIDATION.read_text(encoding="utf-8")
    assert "/ida:reconcile sweep" in text


def test_supervisor_runs_the_check():
    text = SARA.read_text(encoding="utf-8")
    assert "/ida:reconcile check" in text


def test_spec_maps_each_context_to_a_mode():
    contexts = section(SPEC, "Invocation contexts")
    assert "`check`" in contexts and "`sweep`" in contexts
