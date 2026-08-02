"""Extract rbg enforcement events (cope PreToolUse advisory + Stop-hook block)
from a Claude Code session JSONL, with the surrounding turn."""

import json
import sys


def load(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def text_of(msg):
    if msg is None:
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    out = []
    for blk in content or []:
        if not isinstance(blk, dict):
            continue
        if blk.get("type") == "text":
            out.append(blk["text"])
        elif blk.get("type") == "tool_use":
            out.append(f"[tool_use {blk.get('name')}] {json.dumps(blk.get('input'))[:400]}")
        elif blk.get("type") == "thinking":
            out.append("[thinking] " + blk.get("thinking", "")[:300])
    return "\n".join(out)


def main(path, mode):
    rows = load(path)
    needle = {
        "stop": "Rule check before you stop",
        "cope": "A rule check flagged this call",
    }[mode]
    for i, row in enumerate(rows):
        blob = json.dumps(row)
        if needle not in blob:
            continue
        ts = row.get("timestamp", "")
        print("=" * 90)
        print(f"[{i}] ts={ts} type={row.get('type')} role={(row.get('message') or {}).get('role')}")
        print("-" * 40, "HOOK PAYLOAD (input to the agent)", "-" * 40)
        print(text_of(row.get("message"))[:4000])
        # next assistant turn = the agent's response to the hook
        for j in range(i + 1, min(i + 12, len(rows))):
            nxt = rows[j]
            if nxt.get("type") == "assistant":
                print("-" * 40, f"AGENT RESPONSE [{j}]", "-" * 40)
                print(text_of(nxt.get("message"))[:4000])
                break
        break


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
