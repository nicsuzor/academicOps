"""Score the test set against the live local cope model.

Imports rbg's own rules.py and evaluator.py rather than reimplementing them, so
what this measures is exactly what the PreToolUse hook would have decided — same
rule bodies, same classifier prompt, same wire protocol, same parsing.

Usage:  python3 run_copeset.py [limit]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# The *installed* plugin, not the repo source: this is the build the live
# PreToolUse hook runs, and the only copy that carries the injected axioms/
# directory and dispatch.py. Measuring against repo source would measure a
# rule set the session is not actually running under.
HOOKS = Path("/home/nic/.claude/plugins/cache/aops/rbg/0.5.0-geb3a4617/hooks")
sys.path.insert(0, str(HOOKS))

import evaluator  # noqa: E402
import rules  # noqa: E402

HERE = Path(__file__).parent
IN = HERE / "cope_testset.jsonl"
OUT = HERE / "cope_results.jsonl"


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    # Layer 2 is keyed on the session's cwd, so the rule set under test depends
    # on which directory you claim to be scoring for. Defaulting to the
    # scratchpad would silently drop every project-local rule.
    cwd = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/home/nic/junior")

    config = evaluator.resolve()
    if config is None:
        raise SystemExit("no evaluator configured (COPE_EVALUATOR_* unset) — refusing to guess")

    loaded = rules.load(HOOKS.parent, cwd)
    policies = [(r.slug, r.body) for r in sorted(loaded.values(), key=lambda r: r.slug)]
    print(f"model={config.model} url={config.url} rules={len(policies)}", file=sys.stderr)

    cases = [json.loads(line) for line in IN.read_text().splitlines() if line.strip()]
    if limit:
        cases = cases[:limit]

    started = time.monotonic()
    with OUT.open("w") as fh:
        for n, case in enumerate(cases, 1):
            t0 = time.monotonic()
            matches, failures = evaluator.check(config, policies, case["content"], HOOKS)
            fh.write(
                json.dumps(
                    {
                        "id": case["id"],
                        "tool": case["tool"],
                        "family": case["family"],
                        "caller": case["caller"],
                        "content": case["content"],
                        "flagged": [
                            {
                                "slug": v.slug,
                                "confidence": getattr(v, "confidence", None),
                                "reason": getattr(v, "reason", None),
                            }
                            for v in matches
                        ],
                        "n_flagged": len(matches),
                        "n_rules": len(policies),
                        "failures": failures,
                        "seconds": round(time.monotonic() - t0, 2),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            fh.flush()
            print(
                f"[{n}/{len(cases)}] {case['tool']:<28} flagged={len(matches):>2} "
                f"failed={len(failures):>2} {time.monotonic() - t0:.1f}s",
                file=sys.stderr,
            )

    print(f"done in {time.monotonic() - started:.0f}s -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
