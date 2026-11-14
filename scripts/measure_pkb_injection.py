#!/usr/bin/env python3
"""Measurement harness for the pkb `UserPromptSubmit` injection hook.

Answers two questions with numbers, not impression, before anyone touches
`plugins/ida/hooks/handlers.py`:

1. **Backend search latency and payload size** — timed directly against the
   live PKB MCP server at `$PKB_MCP_URL`, the endpoint the hook searches.
2. **Retrieval relevance** on a fixed, versioned prompt set spanning the two
   topic families: (A) instruction auditing / plugin
   structure, and (B) agent design / evidence standards. Scoring rule is a
   stated, mechanical keyword-domain match against each prompt's declared
   keyword set — never a model judging its own homework.

Usage:

    uv run python scripts/measure_pkb_injection.py --repeats 3 \\
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
import statistics
import sys
import time
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Fixed, versioned prompt set. Both families are turns the user plausibly types;
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
        "what does premise-check look for in a report before it reaches the user",
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
# Backend latency, payload size, relevance -- live MCP server.
# --------------------------------------------------------------------------


def _resolve_session_id() -> str:
    return (
        os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("ANTIGRAVITY_CONVERSATION_ID")
        or os.environ.get("AOPS_SESSION_ID")
        or str(uuid.uuid4())
    )


def _call_pkb_search(url: str, headers: dict[str, str], session_id: str, arguments: dict) -> str:
    req_headers = {
        "User-Agent": "academicOps/0.10 (measure-pkb-injection)",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "pkb_search",
        "x-session-id": session_id,
        **headers,
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "pkb_search",
            "arguments": {**arguments, "session_id": session_id},
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": {
                    "name": "academicOps",
                    "version": "0.10",
                },
            },
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=req_headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw_body = resp.read().decode("utf-8", errors="replace")
    parsed = None
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        for line in raw_body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    candidate = json.loads(line[5:].strip())
                    if isinstance(candidate, dict) and "result" in candidate:
                        parsed = candidate
                        break
                except json.JSONDecodeError:
                    continue
    if not isinstance(parsed, dict):
        return ""
    content = parsed.get("result", {}).get("content", [])
    return next(
        (item.get("text", "") for item in content if isinstance(item, dict) and item.get("text")),
        "",
    )


async def _one_search(
    url: str, headers: dict[str, str], session_id: str, prompt: str, family: str
) -> SearchSample:
    t0 = time.perf_counter()
    text = await asyncio.to_thread(
        _call_pkb_search,
        url,
        headers,
        session_id,
        {"query": prompt, "limit": 5, "format": "json"},
    )
    t1 = time.perf_counter()
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


def _resolve_mcp_headers() -> dict[str, str]:
    """Resolve MCP headers using the hook's own header resolution logic."""
    repo_root = Path(__file__).resolve().parent.parent
    hooks_dir = repo_root / "plugins" / "ida" / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))
    import importlib.util

    spec = importlib.util.spec_from_file_location("ida_pkb_handlers", hooks_dir / "handlers.py")
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "_resolve_mcp_headers"):
            return mod._resolve_mcp_headers()
    return {}


async def measure_backend(repeats: int) -> list[SearchSample]:
    url = os.environ["PKB_MCP_URL"]
    headers = _resolve_mcp_headers()
    session_id = _resolve_session_id()
    samples: list[SearchSample] = []
    # Warm-up call, excluded from the distribution -- first call pays
    # model/index cold-start, which every subsequent real fire does not.
    await asyncio.to_thread(
        _call_pkb_search, url, headers, session_id, {"query": "warmup", "limit": 1}
    )
    for family, prompts in PROMPT_FAMILIES.items():
        for prompt in prompts:
            for _ in range(repeats):
                samples.append(await _one_search(url, headers, session_id, prompt, family))
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
    ap.add_argument("--repeats", type=int, default=3, help="repeats per prompt")
    ap.add_argument("--out", type=str, default="", help="write JSON report here (default: stdout)")
    args = ap.parse_args()

    report: dict = {"repeats": args.repeats}

    if "PKB_MCP_URL" not in os.environ:
        print("PKB_MCP_URL not set; nothing to measure.", file=sys.stderr)
        return 1

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
