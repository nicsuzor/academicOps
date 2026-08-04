#!/usr/bin/env python3
"""Token-cheap projections of an .excalidraw file. Stdlib only.

Usage: excalidraw-view.py FILE [summary|map|style|check]
       excalidraw-view.py FILE.excalidrawlib lib
       excalidraw-view.py FILE.excalidrawlib item SELECTOR --after INDEX [--at X,Y]

  summary  element count, type histogram, canvas extents, max index,
           index-order sanity (default when no mode given)
  map      one line per element: shapes with their bound label text
           resolved, free text, arrows as from->to ids — the whole
           diagram's semantics at ~6% of the file size
  style    modal style values (roughness, fillStyle, fontFamily, ...)
           to copy into new elements so they match the house look
  check    structural validation — run before and after every write;
           exit 1 on any failure
  lib      list the items in a .excalidrawlib: selector, name, element
           count, size
  item     emit one library item as a JSON array of elements ready to
           append — fresh ids, seeds and internal references, indices
           minted after --after (pass the target's max index, from
           `summary`), optionally translated so its top-left sits at
           --at X,Y. SELECTOR is a name substring or #N from `lib`.
"""

import json
import random
import sys
import time
from collections import Counter

INDEX_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


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


def lib_items(doc):
    """Library items as (name, elements), across both file formats.

    v2 files carry named dicts under `libraryItems`; v1 files carry bare
    element arrays under `library`, with no names — those are addressable
    only by position.
    """
    if "libraryItems" in doc:
        return [
            (it.get("name") or f"(unnamed {n})", it.get("elements") or [])
            for n, it in enumerate(doc["libraryItems"])
        ]
    return [("(unnamed)", els) for els in doc.get("library") or []]


def extent(els):
    xs = [e["x"] for e in els] + [e["x"] + e.get("width", 0) for e in els]
    ys = [e["y"] for e in els] + [e["y"] + e.get("height", 0) for e in els]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def cmd_lib(doc, _args):
    items = lib_items(doc)
    print(f"{len(items)} items  (format v{doc.get('version')}, source {doc.get('source', '?')})")
    for n, (name, els) in enumerate(items):
        _, _, w, h = extent(els) if els else (0, 0, 0, 0)
        types = "+".join(sorted({e["type"] for e in els}))
        print(f"#{n}\t{name}\t{len(els)} els\t{w:.0f}x{h:.0f}\t{types}")


def new_id():
    return "".join(random.choices(INDEX_ALPHABET + "_-", k=21))


def mint_indices(after, count):
    """Keys that sort immediately after `after`, in ascending order.

    A fixed-width suffix on a common prefix keeps lexicographic order
    equal to numeric order, and any suffix sorts after the bare prefix.
    """
    if count > len(INDEX_ALPHABET) ** 2:
        sys.exit(f"cannot mint {count} indices after {after}")
    return [after + INDEX_ALPHABET[i // 62] + INDEX_ALPHABET[i % 62] for i in range(count)]


def cmd_item(doc, args):
    if not args:
        sys.exit("item mode needs a SELECTOR (a name substring or #N from `lib`)")
    selector, opts = args[0], args[1:]
    after = at = None
    while opts:
        flag, opts = opts[0], opts[1:]
        if flag == "--after" and opts:
            after, opts = opts[0], opts[1:]
        elif flag == "--at" and opts:
            at, opts = [float(v) for v in opts[0].split(",")], opts[1:]
        else:
            sys.exit(f"unrecognised argument: {flag}")
    if not after:
        sys.exit("item mode needs --after INDEX — the target file's max index, from `summary`")

    items = lib_items(doc)
    if selector.startswith("#"):
        picked = [items[int(selector[1:])]]
    else:
        picked = [it for it in items if selector.lower() in it[0].lower()]
    if len(picked) != 1:
        names = ", ".join(f"#{n} {name}" for n, (name, _) in enumerate(items))
        sys.exit(f"selector {selector!r} matched {len(picked)} items; choose one of: {names}")
    els = json.loads(json.dumps(picked[0][1]))
    if not els:
        sys.exit(f"library item {selector!r} has no elements")

    ids = {e["id"]: new_id() for e in els}
    groups = {g: new_id() for e in els for g in e.get("groupIds") or []}
    dx = dy = 0.0
    if at:
        x0, y0, _, _ = extent(els)
        dx, dy = at[0] - x0, at[1] - y0
    stamp = int(time.time() * 1000)
    for e, index in zip(els, mint_indices(after, len(els)), strict=True):
        e["id"] = ids[e["id"]]
        e["x"] += dx
        e["y"] += dy
        e["index"] = index
        e["seed"] = random.randint(1, 2**31 - 1)
        e["versionNonce"] = random.randint(1, 2**31 - 1)
        e["version"] = 1
        e["updated"] = stamp
        e["isDeleted"] = False
        e["groupIds"] = [groups[g] for g in e.get("groupIds") or []]
        for key in ("containerId", "frameId"):
            if e.get(key):
                e[key] = ids.get(e[key])
        for b in e.get("boundElements") or []:
            b["id"] = ids.get(b["id"], b["id"])
        for side in ("startBinding", "endBinding"):
            if e.get(side) and e[side].get("elementId"):
                e[side]["elementId"] = ids.get(e[side]["elementId"])
    json.dump(els, sys.stdout, indent=2)
    print()


MODES = {
    "summary": cmd_summary,
    "map": cmd_map,
    "style": cmd_style,
    "check": cmd_check,
    "lib": cmd_lib,
    "item": cmd_item,
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    doc = json.load(open(sys.argv[1]))
    mode = sys.argv[2] if len(sys.argv) > 2 else "summary"
    if mode not in MODES:
        sys.exit(f"unknown mode {mode!r}; expected one of: {', '.join(MODES)}")
    if mode in ("lib", "item"):
        MODES[mode](doc, sys.argv[3:])
    else:
        MODES[mode](doc)


if __name__ == "__main__":
    main()
