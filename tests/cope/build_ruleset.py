"""Assemble all discovered CoPE rules across all three layers into JSONL format.

Discovers rules from:
Layer 1: axioms (plugin shipped floor)
Layer 2: project-local (.agents/rules/)
Layer 3: user-scoped ($ACA_DATA/.agents/rules/)

Usage:
    python3 build_ruleset.py [cwd] [output_file]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def find_hooks() -> Path:
    # 1. Try plugin cache
    cache = list(Path("/home/nic/.claude/plugins/cache/aops/rbg").glob("*/hooks"))
    if cache:
        return sorted(cache)[-1]
    # 2. Try repo path
    repo_hooks = Path(__file__).resolve().parents[2] / "plugins" / "rbg" / "hooks"
    if repo_hooks.is_dir():
        return repo_hooks
    raise RuntimeError("Could not locate rbg hooks directory")


HOOKS = find_hooks()
sys.path.insert(0, str(HOOKS))

import rules  # noqa: E402

HERE = Path(__file__).parent
DEFAULT_OUT = HERE / "cope_rules.jsonl"


def main() -> None:
    cwd = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/nic/src/academicOps")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    loaded = rules.load(HOOKS.parent, cwd)

    rows = []
    for _slug, r in sorted(loaded.items()):
        rows.append(
            {
                "slug": r.slug,
                "layer": r.layer,
                "trigger": r.trigger,
                "description": r.description,
                "body": r.body,
                "path": str(r.path),
            }
        )

    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    layer_counts = {1: 0, 2: 0, 3: 0}
    for r in rows:
        layer_counts[r["layer"]] = layer_counts.get(r["layer"], 0) + 1

    print(f"Discovered {len(rows)} rules across 3 layers (cwd={cwd}):")
    print(f"  Layer 1 (Axioms):        {layer_counts[1]}")
    print(f"  Layer 2 (Project-local): {layer_counts[2]}")
    print(f"  Layer 3 (User-scoped):   {layer_counts[3]}")
    print(f"Assembled rules written to: {out_path}")


if __name__ == "__main__":
    main()
