#!/usr/bin/env python3
"""Weight-calc substrate blind-spot prototype.

Reads ~/brain/tasks/*.md frontmatter, replicates the existing
propagation-only algorithm from mem/src/graph_store.rs::compute_downstream_metrics
in Python, then applies Option 1 (foundational floor) and Option 2
(teleport) for comparison.

Spike output for task-f20b70eb. NOT production code — does not write back
to the PKB. Read-only analysis.

Usage:
    python scripts/weight_calc_substrate_prototype.py [tasks_dir]

Defaults to ~/brain/tasks. Writes a comparison table to stdout and to
scripts/prototype_output.txt.
"""

from __future__ import annotations

import os
import sys
from collections import deque
from collections.abc import Iterable
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("install pyyaml: uv pip install pyyaml (or pip install pyyaml)")


# Mirror mem/src/graph_store.rs::compute_downstream_metrics constants
PRIORITY_WEIGHTS = {0: 5.0, 1: 3.0, 2: 2.0, 3: 1.0}
DEFAULT_PRIORITY_WEIGHT = 0.5
COMPLETED_STATUSES = {"done", "merged", "cancelled", "archived"}
EDGE_WEIGHTS = {
    "blocks": 1.0,
    "soft_blocks": 0.3,
    "children": 0.5,
}
MAX_DEPTH = 20

# Option 1 calibration
FOUNDATIONAL_MULTIPLIER = 5.0  # P0 → 25.0, P1 → 15.0, P2 → 10.0

# Option 2 calibration (PageRank-style, d = 0.85)
TELEPORT_DAMPING = 0.85

# Curated substrate candidates (would be `foundational: true` in frontmatter)
SUBSTRATE_TASK_IDS = {
    "task-491ce1f9",
    "task-357d72e2",
    "aops-aaa98cf7",
}


def parse_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter from a markdown file. Returns None on failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return fm


def load_tasks(tasks_dir: Path) -> dict[str, dict]:
    """Load all tasks from a directory of markdown files keyed by id."""
    tasks: dict[str, dict] = {}
    for path in sorted(tasks_dir.glob("*.md")):
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        tid = fm.get("id")
        if not tid:
            continue
        tasks[tid] = fm
    return tasks


def base_weight(task: dict) -> float:
    """Mirror base_weights computation from graph_store.rs."""
    status = task.get("status")
    if status in COMPLETED_STATUSES or status is None:
        return 0.0
    pw = PRIORITY_WEIGHTS.get(task.get("priority", 2), DEFAULT_PRIORITY_WEIGHT)
    dm = 2.0 if task.get("due") else 1.0
    return pw * dm


def neighbors(task: dict, known_ids: set[str]) -> Iterable[tuple[str, float]]:
    """Yield (neighbor_id, edge_factor) for blocks/soft_blocks/children/contributes_to."""
    for edge_kind, factor in EDGE_WEIGHTS.items():
        for nid in task.get(edge_kind, []) or []:
            if nid in known_ids:
                yield nid, factor
    # contributes_to is a list of dicts {target, weight, resolved_to}
    for ct in task.get("contributes_to", []) or []:
        if not isinstance(ct, dict):
            continue
        resolved = ct.get("resolved_to") or ct.get("target")
        if resolved in known_ids:
            weight_val = ct.get("weight")
            yield resolved, float(weight_val if weight_val is not None else 1.0)


def compute_downstream_weights(tasks: dict[str, dict]) -> dict[str, float]:
    """Replicate compute_downstream_metrics. Returns {id: downstream_weight}."""
    ids = list(tasks)
    known = set(ids)
    bw = {tid: base_weight(t) for tid, t in tasks.items()}
    adj = {tid: list(neighbors(t, known)) for tid, t in tasks.items()}

    weights: dict[str, float] = {}
    for start in ids:
        total = 0.0
        visited = {start}
        # BFS queue: (node_id, depth, edge_factor)
        q: deque[tuple[str, int, float]] = deque()
        for nid, factor in adj[start]:
            if nid not in visited:
                visited.add(nid)
                q.append((nid, 1, factor))
        while q:
            tid, depth, ef = q.popleft()
            b = bw.get(tid, 0.0)
            if b > 0.0:
                total += (1.0 / depth) * b * ef
            if depth < MAX_DEPTH:
                for nid, factor in adj[tid]:
                    if nid not in visited:
                        visited.add(nid)
                        q.append((nid, depth + 1, ef * factor))
        weights[start] = round(total * 100) / 100
    return weights


def apply_floor(
    tasks: dict[str, dict],
    weights: dict[str, float],
    flagged: set[str],
) -> dict[str, float]:
    """Option 1: foundational floor."""
    out = dict(weights)
    for tid in flagged:
        if tid not in tasks:
            continue
        prio = tasks[tid].get("priority", 2)
        floor = PRIORITY_WEIGHTS.get(prio, DEFAULT_PRIORITY_WEIGHT) * FOUNDATIONAL_MULTIPLIER
        out[tid] = max(out.get(tid, 0.0), floor)
    return out


def apply_teleport(
    tasks: dict[str, dict],
    weights: dict[str, float],
    d: float = TELEPORT_DAMPING,
) -> dict[str, float]:
    """Option 2: uniform teleport. final = computed + (1-d) * mean_active_weight."""
    # Align with base_weight: status=None is treated as completed (returns 0.0 there)
    inactive_statuses = COMPLETED_STATUSES | {None}
    active = [w for tid, w in weights.items() if tasks[tid].get("status") not in inactive_statuses]
    if not active:
        return weights
    mean_w = sum(active) / len(active)
    floor = (1.0 - d) * mean_w
    out: dict[str, float] = {}
    for tid, w in weights.items():
        if tasks[tid].get("status") in inactive_statuses:
            out[tid] = w
        else:
            out[tid] = w + floor
    return out


def main(argv: list[str]) -> int:
    default_tasks_dir = (
        Path(os.environ.get("ACA_DATA", os.path.expanduser("~"))) / "brain" / "tasks"
    )
    tasks_dir = Path(argv[1]) if len(argv) > 1 else default_tasks_dir
    if not tasks_dir.is_dir():
        print(f"tasks dir not found: {tasks_dir}", file=sys.stderr)
        return 1

    tasks = load_tasks(tasks_dir)
    if not tasks:
        print(f"no tasks loaded from {tasks_dir}", file=sys.stderr)
        return 1

    active_count = sum(1 for t in tasks.values() if t.get("status") not in COMPLETED_STATUSES)
    print(f"Loaded {len(tasks)} tasks from {tasks_dir} ({active_count} active)")
    print(f"Substrate candidates: {sorted(SUBSTRATE_TASK_IDS)}")
    print()

    computed = compute_downstream_weights(tasks)
    with_floor = apply_floor(tasks, computed, SUBSTRATE_TASK_IDS)
    with_teleport = apply_teleport(tasks, computed)
    with_both = apply_teleport(tasks, with_floor)

    # Comparison table for substrate candidates + top-10 for context
    lines = []
    header = f"{'task_id':<22} {'prio':>4} {'status':<12} {'computed':>10} {'+floor':>10} {'+teleport':>10} {'+both':>10}"
    lines.append(header)
    lines.append("-" * len(header))

    lines.append("# Substrate candidates")
    for tid in sorted(SUBSTRATE_TASK_IDS):
        if tid not in tasks:
            lines.append(f"{tid:<22} (not found)")
            continue
        t = tasks[tid]
        lines.append(
            f"{tid:<22} {t.get('priority', '-')!s:>4} {t.get('status', '-'):<12} "
            f"{computed[tid]:>10.2f} {with_floor[tid]:>10.2f} "
            f"{with_teleport[tid]:>10.2f} {with_both[tid]:>10.2f}"
        )

    lines.append("")
    lines.append("# Top 10 by computed downstream_weight (for sanity)")
    top = sorted(computed.items(), key=lambda kv: -kv[1])[:10]
    for tid, _ in top:
        t = tasks[tid]
        lines.append(
            f"{tid:<22} {t.get('priority', '-')!s:>4} {t.get('status', '-'):<12} "
            f"{computed[tid]:>10.2f} {with_floor[tid]:>10.2f} "
            f"{with_teleport[tid]:>10.2f} {with_both[tid]:>10.2f}"
        )

    out = "\n".join(lines)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
