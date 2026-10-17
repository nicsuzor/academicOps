# ruff: noqa: E701, E702, E741
import collections
import json
import sys

d = json.load(open(sys.argv[1]))
sts = d["statements"]
rels = d.get("relations", [])
args = d["arguments"]


def tt(x):
    return x if isinstance(x, str) else x.get("title")


inc = collections.defaultdict(list)
out = collections.defaultdict(list)
for r in rels:
    f, t = tt(r["from"]), tt(r["to"])
    inc[t].append((f, r["relationType"]))
    out[f].append((t, r["relationType"]))
titled = [t for t in sts if not t.startswith("Untitled")]
KINDP = ["conflict", "unanswered", "missing", "needs-evidence", "duplicate", "evidence", "theory"]
KMAP = {
    "conflict": "conflict",
    "unanswered": "unans",
    "missing": "missing",
    "needs-evidence": "needs",
    "duplicate": "dup",
    "evidence": "evidence",
    "theory": "theory",
}
nodes = {}
for t in titled:
    s = sts[t]
    m = next((m for m in s["members"] if m.get("text")), s["members"][0])
    data = m.get("data") or {}
    tags = s.get("tags", [])
    kind = next((KMAP[k] for k in KINDP if k in tags), None)
    lv = data.get("level")
    if "Reform" in t:
        kind = "reform"
    if kind is None:
        kind = "hero" if lv in (0, 1) else ("conc" if lv in (2, 3) else "claim")
    if lv in (0, 1) and kind in ("claim", "conc"):
        kind = "hero"
    nodes[t] = dict(
        title=t,
        num=t.split(" ")[0],
        text=m.get("text", ""),
        level=lv,
        kind=kind,
        tags=tags,
        words=data.get("words"),
        reason=data.get("reason", ""),
        source=data.get("source", ""),
        locator=data.get("locator", ""),
        children=[],
        attackers=[],
        parent=None,
        rel=None,
    )
for t in titled:
    for f, k in inc[t]:
        if f in nodes and k in ("support", "attack"):
            nodes[f]["parent"] = t
            nodes[f]["rel"] = k
            (nodes[t]["children"] if k == "support" else nodes[t]["attackers"]).append(f)
warr = {}
for at, a in args.items():
    pcs = a.get("pcs", [])
    concl = [p["title"] for p in pcs if p.get("role") in ("conclusion", "main-conclusion")]
    prem = [p["title"] for p in pcs if p.get("role") == "premise"]
    if concl:
        warr[concl[-1]] = dict(title=at, premises=prem, desc=a.get("description", ""))
under = [r for r in rels if r["relationType"] == "undercut"]
for r in under:
    f, t = tt(r["from"]), tt(r["to"])
    if f in nodes and t in args:
        c = [
            p["title"]
            for p in args[t].get("pcs", [])
            if p.get("role") in ("conclusion", "main-conclusion")
        ]
        if c:
            nodes[f]["parent"] = c[-1]
            nodes[f]["rel"] = "undercut"
            nodes[c[-1]]["attackers"].append(f)
report = dict(
    statements=len(titled),
    relations=len(rels),
    roots=[t for t in nodes if not nodes[t]["parent"] and not out[t]],
    levels=dict(collections.Counter(n["level"] for n in nodes.values())),
    tags=dict(collections.Counter(tg for n in nodes.values() for tg in n["tags"])),
    warrants=len(warr),
    undercuts=[(tt(r["from"]), tt(r["to"])) for r in under],
)
json.dump(dict(nodes=nodes, warrants=warr, report=report), open(sys.argv[2], "w"), indent=1)
print(json.dumps(report))
