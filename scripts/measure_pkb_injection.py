#!/usr/bin/env python3
"""Measurement harness for the pkb `UserPromptSubmit` injection hook.

Answers three questions with numbers, not impression, before anyone touches
`plugins/pkb/hooks/handlers.py`:

1. **Hook overhead** — the cost `dispatch.py` + `handlers.py` add on top of
   the search itself: process spawn, module import, string handling. Measured
   by staging the real hook files with a stub `pkb` binary (instant, fixed
   output) so the timing isolates hook plumbing from backend/network latency.
2. **Backend search latency and payload size** — timed directly against the
   live PKB MCP server at `$PKB_MCP_URL`, the same endpoint the real `pkb`
   CLI resolves to. There is no `pkb` binary in this execution environment
   (verified: absent from PATH, cwd, and every plugin's shipped `bin/`, and
   no source for it anywhere reachable) — see NOTES below. This is the
   closest faithful proxy available for what a real fire pays.
3. **Retrieval relevance** on a fixed, versioned prompt set spanning the two
   topic families named in task_206a0832: (A) instruction auditing / plugin
   structure, and (B) agent design / evidence standards. Scoring rule is a
   stated, mechanical keyword-domain match against each prompt's declared
   keyword set — never a model judging its own homework.

Usage:

    uv run --with fastmcp scripts/measure_pkb_injection.py --repeats 3 \\
        --out /tmp/pkb_measure.json

Requires `$PKB_MCP_URL` in the environment (no default, per project rule).
Writes a JSON report to --out (or stdout) and a human-readable summary to
stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
PKB_HOOKS = REPO_ROOT / "plugins" / "pkb" / "hooks"

# --------------------------------------------------------------------------
# Fixed, versioned prompt set. Both families are turns Nic plausibly types;
# wording fixed here so a re-run is measuring drift in the backend, not
# drift in the prompt set.
# --------------------------------------------------------------------------

PROMPT_FAMILIES: dict[str, list[str]] = {
    "instruction_auditing_plugin_structure": [
        "let's audit the agent instruction files across plugins for duplication and drift",
        "check whether the README contract matches the plugin manifest structure",
        "review the hook set and dispatch contract before we add a new one",
        "does the pkb plugin duplicate anything that should live in lib/",
        "walk the plugin directory layout and confirm nothing violates the no-duplication axiom",
    ],
    "agent_design_evidence_standards": [
        "what evidence standard should james use before accepting a subagent's report",
        "design the verification rubric for judging a subagent's claim",
        "how should agents cite basis tags for load-bearing claims",
        "what does premise-check look for in a report before it reaches nic",
        "review whether marsha's QA pass actually verifies runtime behaviour",
    ],
}

# Mechanical relevance rule: a result counts "on-topic" for a family if any
# keyword below appears (case-insensitive substring) in its title, type, or
# extract. Not semantic, not model-judged -- reproducible by grep.
FAMILY_KEYWORDS: dict[str, list[str]] = {
    "instruction_auditing_plugin_structure": [
        "plugin",
        "instruction",
        "audit",
        "readme",
        "architecture",
        "hook",
        "agent definition",
        "manifest",
        "directory",
        "duplicat",
        "structure",
    ],
    "agent_design_evidence_standards": [
        "evidence",
        "basis",
        "verif",
        "rubric",
        "agent design",
        "subagent",
        "claim",
        "citation",
        "premise",
        "qa",
        "marsha",
        "hearsay",
    ],
}

OFF_TOPIC_MARKERS = ["osb", "plenary", "transcript"]


@dataclass
class SearchSample:
    prompt: str
    family: str
    latency_ms: float
    payload_bytes: int
    result_ids: list[str] = field(default_factory=list)
    result_titles: list[str] = field(default_factory=list)
    result_scores: list[float] = field(default_factory=list)
    on_topic: list[bool] = field(default_factory=list)
    off_topic_marker_hits: int = 0


def _dist(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    return {
        "n": n,
        "min": s[0],
        "median": statistics.median(s),
        "mean": statistics.fmean(s),
        "p95": s[min(n - 1, int(round(0.95 * (n - 1))))],
        "max": s[-1],
    }


# --------------------------------------------------------------------------
# 1. Hook overhead: real dispatch.py + handlers.py, stub `pkb` binary.
# --------------------------------------------------------------------------


def measure_hook_overhead(repeats: int) -> dict:
    tmp = Path(
        subprocess.run(["mktemp", "-d"], capture_output=True, text=True, check=True).stdout.strip()
    )
    hooks_dir = tmp / "hooks"
    shutil.copytree(LIB_HOOKS, hooks_dir, ignore=shutil.ignore_patterns("__pycache__"))
    for item in PKB_HOOKS.iterdir():
        if item.name == "__pycache__":
            continue
        if item.is_dir():
            shutil.copytree(item, hooks_dir / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, hooks_dir / item.name)

    stub = tmp / "pkb"
    stub.write_text(
        "#!/bin/sh\necho '1. Stub result (score: 0.50)'\necho '   stub/doc.md'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    payload = json.dumps(
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "measure hook overhead with a stub backend",
            "cwd": str(tmp),
        }
    )

    latencies = []
    try:
        for _ in range(repeats):
            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, str(hooks_dir / "dispatch.py"), "claude", "UserPromptSubmit"],
                input=payload,
                text=True,
                capture_output=True,
                timeout=30,
                cwd=str(hooks_dir),
            )
            t1 = time.perf_counter()
            if proc.returncode != 0:
                raise RuntimeError(f"dispatch.py failed: {proc.stderr}")
            latencies.append((t1 - t0) * 1000)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {"distribution_ms": _dist(latencies), "raw_ms": latencies}


# --------------------------------------------------------------------------
# 2 & 3. Backend latency, payload size, relevance -- live MCP server.
# --------------------------------------------------------------------------


async def _one_search(client, prompt: str, family: str) -> SearchSample:
    t0 = time.perf_counter()
    res = await client.call_tool("pkb__search", {"query": prompt, "limit": 5, "format": "json"})
    t1 = time.perf_counter()
    text = next((getattr(b, "text", "") for b in res.content if getattr(b, "text", "")), "")
    payload_bytes = len(text.encode())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"results": []}

    sample = SearchSample(
        prompt=prompt,
        family=family,
        latency_ms=(t1 - t0) * 1000,
        payload_bytes=payload_bytes,
    )
    keywords = FAMILY_KEYWORDS[family]
    for r in data.get("results", []):
        haystack = f"{r.get('title', '')} {r.get('type', '')} {r.get('extract', '')}".lower()
        sample.result_ids.append(r.get("id", ""))
        sample.result_titles.append(r.get("title", ""))
        sample.result_scores.append(r.get("score", 0.0))
        sample.on_topic.append(any(kw in haystack for kw in keywords))
        if any(m in haystack for m in OFF_TOPIC_MARKERS):
            sample.off_topic_marker_hits += 1
    return sample


async def measure_backend(repeats: int) -> list[SearchSample]:
    from fastmcp import Client  # local import: optional dependency, only needed here

    url = os.environ["PKB_MCP_URL"]
    samples: list[SearchSample] = []
    async with Client(url) as client:
        # Warm-up call, excluded from the distribution -- first call pays
        # model/index cold-start, which every subsequent real fire does not.
        await client.call_tool("pkb__search", {"query": "warmup", "limit": 1})
        for family, prompts in PROMPT_FAMILIES.items():
            for prompt in prompts:
                for _ in range(repeats):
                    samples.append(await _one_search(client, prompt, family))
    return samples


def summarize_relevance(samples: list[SearchSample]) -> dict:
    by_family: dict[str, dict] = {}
    for family in PROMPT_FAMILIES:
        fam_samples = [s for s in samples if s.family == family]
        precisions = []
        all_ids: list[str] = []
        off_topic_hits = 0
        for s in fam_samples:
            if s.on_topic:
                precisions.append(sum(s.on_topic) / len(s.on_topic))
            all_ids.extend(s.result_ids)
            off_topic_hits += s.off_topic_marker_hits
        unique_ratio = (len(set(all_ids)) / len(all_ids)) if all_ids else None
        by_family[family] = {
            "precision_at_5_mean": statistics.fmean(precisions) if precisions else None,
            "precision_at_5_per_prompt": precisions,
            "unique_result_ratio": unique_ratio,
            "total_result_slots": len(all_ids),
            "unique_result_ids": len(set(all_ids)),
            "off_topic_marker_hits": off_topic_hits,
        }
    return by_family


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repeats", type=int, default=3, help="repeats per prompt / hook overhead run")
    ap.add_argument("--out", type=str, default="", help="write JSON report here (default: stdout)")
    ap.add_argument("--skip-backend", action="store_true", help="hook-overhead measurement only")
    args = ap.parse_args()

    report: dict = {"repeats": args.repeats}

    print("Measuring hook overhead (stub backend, real dispatch.py)...", file=sys.stderr)
    report["hook_overhead"] = measure_hook_overhead(args.repeats)

    if not args.skip_backend:
        if "PKB_MCP_URL" not in os.environ:
            print("PKB_MCP_URL not set; skipping backend measurement.", file=sys.stderr)
        else:
            print("Measuring live backend search latency + relevance...", file=sys.stderr)
            samples = asyncio.run(measure_backend(args.repeats))
            latencies = [s.latency_ms for s in samples]
            payloads = [s.payload_bytes for s in samples]
            all_scores = [sc for s in samples for sc in s.result_scores]
            report["backend"] = {
                "latency_ms": _dist(latencies),
                "payload_bytes": _dist([float(p) for p in payloads]),
                "result_score": _dist(all_scores),
                "relevance_by_family": summarize_relevance(samples),
                "samples": [asdict(s) for s in samples],
            }

    out_text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"Wrote report to {args.out}", file=sys.stderr)
    else:
        print(out_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
