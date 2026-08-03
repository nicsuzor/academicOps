#!/usr/bin/env python3
"""Token-cheap projections of an .excalidraw file. Stdlib only.

Usage: excalidraw-view.py FILE [summary|map|style|check]

  summary  element count, type histogram, canvas extents, max index,
           index-order sanity (default when no mode given)
  map      one line per element: shapes with their bound label text
           resolved, free text, arrows as from->to ids — the whole
           diagram's semantics at ~6% of the file size
  style    modal style values (roughness, fillStyle, fontFamily, ...)
           to copy into new elements so they match the house look
  check    structural validation — run before and after every write;
           exit 1 on any failure
"""

import json
import sys
from collections import Counter


def live(doc):
    return [e for e in doc["elements"] if not e.get("isDeleted")]


def label_of(e, texts):
    for b in e.get("boundElements") or []:
        if b.get("type") == "text" and b["id"] in texts:
            return texts[b["id"]].get("text", "").replace("\n", " / ")
    return ""


def cmd_summary(doc):
    els = live(doc)
    idx = [e.get("index") for e in els]
    print(f"elements: {len(els)}  types: {dict(Counter(e['type'] for e in els))}")
    xs = [e["x"] for e in els] + [e["x"] + e["width"] for e in els]
    ys = [e["y"] for e in els] + [e["y"] + e["height"] for e in els]
    print(f"extents: x [{min(xs):.0f}, {max(xs):.0f}]  y [{min(ys):.0f}, {max(ys):.0f}]")
    print(f"max index: {max(i for i in idx if i)}")
    ok = all(i is not None for i in idx) and idx == sorted(idx)
    print(f"array order == index order: {ok}")


def cmd_map(doc):
    els = live(doc)
    texts = {e["id"]: e for e in els if e["type"] == "text"}
    for e in els:
        if e["type"] == "text" and e.get("containerId"):
            continue  # shown as its container's label
        if e["type"] == "arrow":
            s = (e.get("startBinding") or {}).get("elementId", "-")
            t = (e.get("endBinding") or {}).get("elementId", "-")
            print(f"{e['id']}\tarrow\t{s} -> {t}")
        elif e["type"] == "text":
            body = e.get("text", "").replace("\n", " / ")
            print(f"{e['id']}\ttext\t{e['x']:.0f},{e['y']:.0f}\t{body}")
        else:
            geo = f"{e['x']:.0f},{e['y']:.0f}\t{e['width']:.0f}x{e['height']:.0f}"
            print(
                f"{e['id']}\t{e['type']}\t{geo}\t{e.get('backgroundColor')}\t{label_of(e, texts)}"
            )


def cmd_style(doc):
    els = live(doc)
    for key in (
        "roughness",
        "fillStyle",
        "strokeStyle",
        "strokeWidth",
        "fontFamily",
        "fontSize",
        "opacity",
    ):
        vals = Counter(e[key] for e in els if key in e)
        if vals:
            print(f"{key}: modal={vals.most_common(1)[0][0]}  all={dict(vals)}")
    rd = Counter(json.dumps(e.get("roundness")) for e in els if e["type"] == "rectangle")
    if rd:
        print(f"roundness (rectangles): modal={rd.most_common(1)[0][0]}")


def cmd_check(doc):
    els = live(doc)
    ids = [e["id"] for e in els]
    by_id = {e["id"]: e for e in els}
    fails = []
    if len(ids) != len(set(ids)):
        fails.append("duplicate ids: " + str([i for i, c in Counter(ids).items() if c > 1]))
    idx = [e.get("index") for e in els]
    if any(i is None for i in idx):
        fails.append("elements missing index: " + str([e["id"] for e in els if not e.get("index")]))
    elif idx != sorted(idx):
        fails.append("elements array is not sorted by index — file will not open")
    if len(idx) != len(set(idx)):
        fails.append("duplicate indices: " + str([i for i, c in Counter(idx).items() if c > 1]))
    for e in els:
        for side in ("startBinding", "endBinding"):
            ref = (e.get(side) or {}).get("elementId")
            if ref and ref not in by_id:
                fails.append(f"{e['id']}.{side} -> missing element {ref}")
        cid = e.get("containerId")
        if cid:
            bound = [b["id"] for b in (by_id.get(cid, {}).get("boundElements") or [])]
            if cid not in by_id:
                fails.append(f"text {e['id']} bound to missing container {cid}")
            elif e["id"] not in bound:
                fails.append(f"container {cid} lacks boundElements backref to text {e['id']}")
        for b in e.get("boundElements") or []:
            if b["id"] not in by_id:
                fails.append(f"{e['id']}.boundElements -> missing element {b['id']}")
    if fails:
        print("FAIL")
        for f in fails:
            print(" ", f)
        sys.exit(1)
    print(f"OK: {len(els)} elements, ids unique, index-sorted, all bindings resolve")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    doc = json.load(open(sys.argv[1]))
    mode = sys.argv[2] if len(sys.argv) > 2 else "summary"
    {"summary": cmd_summary, "map": cmd_map, "style": cmd_style, "check": cmd_check}[mode](doc)


if __name__ == "__main__":
    main()
