"""Assemble a cope evaluation test set from real Claude Code transcripts.

Emits exactly the CONTENT string the rbg PreToolUse hook sends to the evaluator
(evaluator.render_content: "Tool: {name}\nInput: {json, sort_keys}"), so a
verdict measured here is the verdict the live hook would have produced.

Sampling is stratified by tool name so the set is not 180 Bash calls: each tool
family gets a floor, the remainder is filled proportionally, and within a family
the picks are spread across distinct sessions rather than one busy transcript.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

PROJECTS = Path("/home/nic/.claude/projects")
OUT = Path(__file__).parent / "cope_testset.jsonl"
TARGET = 200
MAX_CONTENT_CHARS = 6000  # evaluator.MAX_CONTENT_CHARS
SEED = 20260801


def render_content(tool: str, tool_input: object) -> str:
    """Byte-identical to evaluator.render_content."""
    if isinstance(tool_input, (dict, list)):
        rendered = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    else:
        rendered = "" if tool_input is None else str(tool_input)
    if len(rendered) > MAX_CONTENT_CHARS:
        rendered = rendered[:MAX_CONTENT_CHARS] + " …[truncated]"
    return f"Tool: {tool}\nInput: {rendered}"


def family(tool: str) -> str:
    """Group tools into families so stratification is over kinds of action."""
    if tool.startswith("mcp__services__pkb__"):
        return "pkb"
    if tool.startswith("mcp__"):
        return "mcp-other"
    if tool in ("Task", "Agent"):
        return "subagent"
    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        return "mutate"
    if tool in ("Read", "Glob", "Grep"):
        return "read"
    if tool == "Bash":
        return "bash"
    return "other"


def harvest(paths):
    """Every tool_use block in the given transcripts, deduped on rendered content."""
    seen = set()
    rows = []
    for path in paths:
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        is_sub = "/subagents/" in str(path)
        for line in lines:
            line = line.strip()
            if not line or '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message") or {}
            if not isinstance(msg.get("content"), list):
                continue
            for blk in msg["content"]:
                if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                    continue
                tool = blk.get("name") or "?"
                content = render_content(tool, blk.get("input"))
                key = hashlib.sha256(content.encode()).hexdigest()[:16]
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "id": key,
                        "tool": tool,
                        "family": family(tool),
                        "caller": "subagent" if is_sub else "main",
                        "session": rec.get("sessionId") or path.stem,
                        "cwd": rec.get("cwd"),
                        "ts": rec.get("timestamp"),
                        "content": content,
                    }
                )
    return rows


def stratify(rows, target):
    """Floor per family, proportional remainder, sessions spread within a family."""
    rng = random.Random(SEED)
    by_fam = defaultdict(list)
    for r in rows:
        by_fam[r["family"]].append(r)

    fams = sorted(by_fam)
    floor = min(12, target // max(len(fams), 1))
    quota = {f: min(floor, len(by_fam[f])) for f in fams}

    remaining = target - sum(quota.values())
    pool = sum(max(0, len(by_fam[f]) - quota[f]) for f in fams)
    if remaining > 0 and pool > 0:
        for f in fams:
            spare = len(by_fam[f]) - quota[f]
            quota[f] += min(spare, round(remaining * spare / pool))

    picked = []
    for f in fams:
        bucket = by_fam[f]
        # round-robin over sessions so one chatty transcript can't own a family
        by_sess = defaultdict(list)
        for r in bucket:
            by_sess[r["session"]].append(r)
        for lst in by_sess.values():
            rng.shuffle(lst)
        order, sessions = [], list(by_sess)
        rng.shuffle(sessions)
        while any(by_sess[s] for s in sessions):
            for s in sessions:
                if by_sess[s]:
                    order.append(by_sess[s].pop())
        picked.extend(order[: quota[f]])

    rng.shuffle(picked)
    return picked[:target]


def main() -> None:
    paths = sorted(PROJECTS.rglob("*.jsonl"))
    rows = harvest(paths)
    picked = stratify(rows, TARGET)

    with OUT.open("w") as fh:
        for r in picked:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    counts = defaultdict(int)
    callers = defaultdict(int)
    for r in picked:
        counts[r["family"]] += 1
        callers[r["caller"]] += 1
    print(f"transcripts scanned : {len(paths)}")
    print(f"unique tool calls   : {len(rows)}")
    print(f"sampled             : {len(picked)} -> {OUT}")
    print("by family           :", dict(sorted(counts.items())))
    print("by caller           :", dict(callers))


if __name__ == "__main__":
    main()
