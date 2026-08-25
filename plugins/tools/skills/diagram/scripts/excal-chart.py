#!/usr/bin/env python3
"""excal-chart.py — build an Excalidraw containment chart from a declarative spec.

Generic. Nothing about any particular chart lives here: the spec carries the
data, the encoding, and the composition. Use it whenever a chart's job is
"show me a hierarchy and the state of the things in it" — task trees, org
charts, service maps, file/module structure, curriculum maps.

WHY A SPEC AND NOT A SCRIPT
A hand-rolled generator per chart re-implements (and re-breaks) the same
invariants every time: two text layers, fixed-width z-order indices, nesting
declared at every depth, headers sized to their own title. Those are baked in
here and validated on the way out.

OBJECTIVE AND AUDIENCE ARE REQUIRED
The tool refuses to run without them, on purpose. Almost every bad chart is a
chart whose author never said who it was for or what decision it serves, and
then reached for "make it look nice" instead. Write them first; the layout and
encoding decisions fall out of them. See SKILL.md "Objective and audience".

HONESTY ABOUT SUBSETS
A frame that draws fewer children than the node actually has gets an automatic
"showing k of n" line. Set `children_total` on the node (an adapter reads it
from the source system). Never hand-write that number, and never label a
partial draw as if it were complete — a chart that silently omits siblings
reads as an inventory and lies like one.

USAGE
  python3 excal-chart.py SPEC.json OUT.excalidraw
  python3 excal-chart.py SPEC.json OUT.excalidraw --check   # validate spec only

SPEC (JSON)
  objective   str, required, >=20 chars — the decision this chart serves
  audience    str, required, >=10 chars — who reads it and what they know
  tiers       {name: {width, label, sub}}         size vocabulary
  encoding    {size, fill, border_style, border_color, border_width,
               badges[], show_id, palette{}}     field -> visual channel
  nodes       {id: {label, sub, data{}, children[], children_total}}
  roots       [{id, at:[x,y], max_width}]         top-level frames (composition)
  free        [{id, at:[x,y]}]                    ungrouped cards
  panels      [{id, at, width, title, lines[[text,color]]}]  legends/notes

Channels resolve as {"field": F, "map": {...}, "default": D} against node.data,
or {"const": V}. A badge additionally takes {"when_true": TEXT} to render only
for truthy values.
"""

import datetime
import hashlib
import json
import os
import shutil
import sys

LH = 1.25
CHARW = 0.58  # conservative advance width for Virgil; over-estimating
# widths grows boxes, which is the safe direction
PAD, GAP = 22, 18


def die(msg):
    print(f"excal-chart: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- text metrics
def charw(fs):
    return fs * CHARW


def wrap(s, fs, maxw):
    out = []
    for para in str(s).split("\n"):
        line = ""
        for w in para.split(" "):
            t = (line + " " + w).strip()
            if len(t) * charw(fs) <= maxw or not line:
                line = t
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def theight(n, fs):
    return round(n * fs * LH, 2)


def sd(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:7], 16)


# ---------------------------------------------------------------- channel eval
def resolve(chan, data, fallback=None):
    """Resolve one visual channel against a node's data dict."""
    if chan is None:
        return fallback
    if "const" in chan:
        return chan["const"]
    val = data.get(chan.get("field"))
    if "map" in chan:
        return chan["map"].get(str(val), chan.get("default", fallback))
    return val if val is not None else chan.get("default", fallback)


class Chart:
    def __init__(self, spec):
        self.spec = spec
        self.nodes = spec["nodes"]
        self.enc = spec.get("encoding", {})
        self.tiers = spec.get("tiers") or {
            "A": {"width": 380, "label": 24, "sub": 13},
            "L": {"width": 300, "label": 18, "sub": 11.5},
            "M": {"width": 240, "label": 15, "sub": 11},
            "S": {"width": 200, "label": 12.5, "sub": 10},
        }
        self.pal = self.enc.get("palette", {})
        self.placed = {}
        self.els = []
        self.depth_of = {}
        self.overflow = []

    # ---------------------------------------------------------------- geometry
    def kids(self, cid):
        return self.nodes[cid].get("children") or []

    def tier(self, cid):
        t = resolve(self.enc.get("size"), self.nodes[cid].get("data", {}), "M")
        return t if t in self.tiers else "M"

    def font(self, cid):
        t = self.tiers[self.tier(cid)]
        return t["width"], t["label"], t["sub"]

    def subtitle(self, cid):
        """Node subtitle plus an automatic, non-negotiable subset disclosure."""
        n = self.nodes[cid]
        sub = n.get("sub") or ""
        total = n.get("children_total")
        drawn = len(self.kids(cid))
        if total is not None and drawn and drawn < total:
            note = f"showing {drawn} of {total}"
            sub = f"{sub}\n{note}" if sub else note
        return sub

    def card_size(self, cid):
        w, fs, sfs = self.font(cid)
        h = 10 + theight(len(wrap(self.nodes[cid]["label"], fs, w - 24)), fs)
        sub = self.subtitle(cid)
        if sub:
            h += theight(len(wrap(sub, sfs, w - 24)), sfs) + 5
        return w, round(max(h + 26, 56), 2)

    def hdr(self, cid, depth):
        fs = 19 if depth == 0 else 16
        h = 13 + theight(len(self.nodes[cid]["label"].split("\n")), fs)
        sub = self.subtitle(cid)
        if sub:
            h += 4 + theight(len(sub.split("\n")), 10.5)
        return round(h + 20, 2)

    def title_w(self, cid, depth):
        fs = 19 if depth == 0 else 16
        w = max(len(ln) * charw(fs) for ln in self.nodes[cid]["label"].split("\n"))
        sub = self.subtitle(cid)
        if sub:
            w = max(w, max(len(ln) * charw(10.5) for ln in sub.split("\n")))
        return round(w + 46, 2)

    def rows(self, cid, depth):
        mw = self.nodes[cid].get("max_width", 540)
        rows, cur, cw = [], [], 0
        for k in self.kids(cid):
            w, h = self.size(k, depth + 1)
            if cw and cw + GAP + w > mw:
                rows.append(cur)
                cur, cw = [], 0
            cur.append((k, w, h))
            cw = cw + (GAP if cw else 0) + w
        if cur:
            rows.append(cur)
        return rows

    def size(self, cid, depth=0):
        self.depth_of[cid] = depth
        if not self.kids(cid):
            return self.card_size(cid)
        rs = self.rows(cid, depth)
        W = max(
            max(sum(w for _, w, _ in r) + GAP * (len(r) - 1) for r in rs) + 2 * PAD,
            self.title_w(cid, depth),
        )
        H = (
            self.hdr(cid, depth)
            + sum(max(h for _, _, h in r) for r in rs)
            + GAP * (len(rs) - 1)
            + PAD
        )
        return round(W, 2), round(H, 2)

    def place(self, cid, x, y, depth=0):
        W, H = self.size(cid, depth)
        self.placed[cid] = (x, y, W, H)
        if not self.kids(cid):
            return
        yy = y + self.hdr(cid, depth)
        for r in self.rows(cid, depth):
            xx = x + PAD
            for k, w, _h in r:
                self.place(k, xx, yy, depth + 1)
                xx += w + GAP
            yy += max(h for _, _, h in r) + GAP

    # ---------------------------------------------------------------- emitters
    def rect(self, eid, x, y, w, h, bg, stroke, sw=1, style="solid"):
        e = {
            "type": "rectangle",
            "id": eid,
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(w, 2),
            "height": round(h, 2),
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": bg,
            "fillStyle": "solid",
            "strokeWidth": sw,
            "strokeStyle": style,
            "roughness": 2,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3},
            "seed": sd(eid),
            "version": 1,
            "versionNonce": sd(eid + "n"),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        self.els.append(e)
        return e

    def text(self, eid, x, y, txt, fs, color, align="left", w=None, container=None):
        lines = txt.split("\n")
        e = {
            "type": "text",
            "id": eid,
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(w if w else max(len(ln) for ln in lines) * charw(fs), 2),
            "height": theight(len(lines), fs),
            "angle": 0,
            "strokeColor": color,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": sd(eid),
            "version": 1,
            "versionNonce": sd(eid + "n"),
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "fontSize": fs,
            "fontFamily": 1,
            # both text layers, always: Excalidraw re-wraps `text` from
            # `originalText`, so setting only one silently loses the edit
            "text": txt,
            "originalText": txt,
            "textAlign": align,
            "verticalAlign": "top",
            "containerId": container,
            "autoResize": True,
            "lineHeight": LH,
        }
        self.els.append(e)
        return e

    def has(self, eid):
        return any(e["id"] == eid for e in self.els)

    def meta(self, cid, r, left, right, ybase):
        """Badge row, right-aligned, with the node id at the left.

        Badges are cheap to add and easy to overflow on a narrow card, where
        they silently print over the id. Overflow is counted and reported by
        the build rather than left for a human to spot in a render.
        """
        data = self.nodes[cid].get("data", {})
        off = 0
        id_w = (len(cid) * 9 * 0.62 + 26) if self.enc.get("show_id", True) else 0
        for i, b in enumerate(self.enc.get("badges", [])):
            val = data.get(b.get("field"))
            if "when_true" in b:
                if not val:
                    continue
                txt = b["when_true"]
            elif "map" in b:
                txt = b["map"].get(str(val))
                if not txt:
                    continue
            else:
                if val in (None, "", False):
                    continue
                txt = str(val)
            col = (b.get("color_map") or {}).get(str(val), b.get("color", "#8a8a8a"))
            eid = f"{cid}-badge{i}"
            self.text(eid, right - len(txt) * charw(11) - off, ybase, txt, 11, col)
            r["boundElements"].append({"id": eid, "type": "nested"})
            off += len(txt) * charw(11) + 16
        if off and left + id_w > right - off:
            self.overflow.append((cid, round(left + id_w - (right - off))))
        if self.enc.get("show_id", True):
            self.text(f"{cid}-id", left + 12, ybase + 1, cid, 9, self.pal.get("faint", "#a0a0a0"))
            r["boundElements"].append({"id": f"{cid}-id", "type": "nested"})

    def descendants(self, cid):
        for k in self.kids(cid):
            yield k
            yield from self.descendants(k)

    def draw(self, cid, depth=0):
        x, y, w, h = self.placed[cid]
        n = self.nodes[cid]
        data = n.get("data", {})
        sub = self.subtitle(cid)
        if self.kids(cid):
            bg = self.pal.get("frame" if depth == 0 else "subframe", "#eef2f6")
            r = self.rect(
                cid,
                x,
                y,
                w,
                h,
                bg,
                resolve(self.enc.get("border_color"), data, "#8a9bad"),
                resolve(self.enc.get("border_width"), data, 1),
                resolve(self.enc.get("border_style"), data, "solid"),
            )
            fs = 19 if depth == 0 else 16
            t = self.text(
                f"{cid}-label",
                x + 20,
                y + 13,
                n["label"],
                fs,
                self.pal.get("frame_ink", "#33414f"),
                container=cid,
            )
            r["boundElements"].append({"id": t["id"], "type": "text"})
            if sub:
                self.text(
                    f"{cid}-sub",
                    x + 20,
                    y + 15 + t["height"],
                    sub,
                    10.5,
                    self.pal.get("grey", "#6f6f6f"),
                )
                r["boundElements"].append({"id": f"{cid}-sub", "type": "nested"})
            self.meta(cid, r, x, x + w - 20, y + h - 19)
            for k in self.kids(cid):
                self.draw(k, depth + 1)
            # declare EVERY descendant, at every depth: an overlap checker must
            # be able to tell legitimate nesting from a real collision
            for k in self.descendants(cid):
                for suf in ("", "-label", "-sub", "-id") + tuple(
                    f"-badge{i}" for i in range(len(self.enc.get("badges", [])))
                ):
                    if self.has(k + suf):
                        r["boundElements"].append({"id": k + suf, "type": "nested"})
            return
        w_, fs, sfs = self.font(cid)
        r = self.rect(
            cid,
            x,
            y,
            w,
            h,
            resolve(self.enc.get("fill"), data, "#ffffff"),
            resolve(self.enc.get("border_color"), data, "#1e1e1e"),
            resolve(self.enc.get("border_width"), data, 1),
            resolve(self.enc.get("border_style"), data, "solid"),
        )
        ink = resolve(self.enc.get("label_color"), data, "#1e1e1e")
        t = self.text(
            f"{cid}-label",
            x + 12,
            y + 9,
            "\n".join(wrap(n["label"], fs, w - 24)),
            fs,
            ink,
            align="center",
            w=w - 24,
            container=cid,
        )
        r["boundElements"].append({"id": f"{cid}-label", "type": "text"})
        if sub:
            self.text(
                f"{cid}-sub",
                x + 12,
                y + 14 + t["height"],
                "\n".join(wrap(sub, sfs, w - 24)),
                sfs,
                self.pal.get("grey", "#6f6f6f"),
            )
            r["boundElements"].append({"id": f"{cid}-sub", "type": "nested"})
        self.meta(cid, r, x, x + w - 12, y + h - 17)

    def build(self):
        for root in self.spec.get("roots", []):
            self.nodes[root["id"]]["max_width"] = root.get("max_width", 540)
            self.place(root["id"], *root["at"])
        for f in self.spec.get("free", []):
            self.placed[f["id"]] = tuple(f["at"]) + self.card_size(f["id"])
        for root in self.spec.get("roots", []):
            self.draw(root["id"])
        for f in self.spec.get("free", []):
            self.draw(f["id"])
        for p in self.spec.get("panels", []):
            lines = p.get("lines", [])
            h = p.get("height", 44 + 23 * len(lines) + 14)
            pr = self.rect(
                p["id"],
                p["at"][0],
                p["at"][1],
                p.get("width", 352),
                h,
                "transparent",
                p.get("color", "#bdbdbd"),
                1,
                "dashed",
            )
            pt = self.text(
                f"{p['id']}-title",
                p["at"][0] + 16,
                p["at"][1] + 12,
                p["title"],
                14,
                self.pal.get("grey", "#6f6f6f"),
                container=p["id"],
            )
            pr["boundElements"].append({"id": pt["id"], "type": "text"})
            for i, ln in enumerate(lines):
                txt, col = ln if isinstance(ln, list) else [ln, "#1e1e1e"]
                eid = f"{p['id']}-{i}"
                self.text(eid, p["at"][0] + 16, p["at"][1] + 44 + i * 23, txt, 11.5, col)
                pr["boundElements"].append({"id": eid, "type": "nested"})
        for g in self.spec.get("groups", []):
            mem = [self.placed[m] for m in g["members"] if m in self.placed]
            if not mem:
                continue
            x0 = min(b[0] for b in mem) - 20
            y0 = min(b[1] for b in mem) - 52
            gr = self.rect(
                g["id"],
                x0,
                y0,
                max(b[0] + b[2] for b in mem) - x0 + 20,
                max(b[1] + b[3] for b in mem) - y0 + 20,
                "transparent",
                g.get("color", "#b0b0b0"),
                1,
                g.get("style", "dashed"),
            )
            gt = self.text(
                f"{g['id']}-label",
                x0 + 14,
                y0 + 8,
                g["label"],
                13,
                g.get("color", "#8a8a8a"),
                container=g["id"],
            )
            gr["boundElements"].append({"id": gt["id"], "type": "text"})
            for m in g["members"]:
                for suf in ("", "-label", "-sub", "-id") + tuple(
                    f"-badge{i}" for i in range(len(self.enc.get("badges", [])))
                ):
                    if self.has(m + suf):
                        gr["boundElements"].append({"id": m + suf, "type": "nested"})
        # fixed-width keys so lexicographic order IS numeric order, and the
        # array is serialised in ascending index order or the file won't open
        for i, e in enumerate(self.els):
            e["index"] = "a" + str(i).zfill(4)
        return self.els


def validate_spec(spec):
    for f, minlen in (("objective", 20), ("audience", 10)):
        v = (spec.get(f) or "").strip()
        if len(v) < minlen:
            die(
                f"spec is missing a usable `{f}`.\n"
                f"  Every chart needs one. `objective` = the decision or action this\n"
                f"  chart makes possible ('choose what to do with a free afternoon'),\n"
                f"  not its subject ('the projects'). `audience` = who reads it, what\n"
                f"  they already know, and how they will view it.\n"
                f"  Write both before laying anything out — the layout and the encoding\n"
                f"  budget are derived from them. See SKILL.md 'Objective and audience'."
            )
    if not spec.get("nodes"):
        die("spec has no `nodes`")
    ids = set(spec["nodes"])
    for cid, n in spec["nodes"].items():
        if "label" not in n:
            die(f"node {cid} has no `label`")
        for k in n.get("children") or []:
            if k not in ids:
                die(f"node {cid} lists unknown child {k}")
        tot = n.get("children_total")
        if tot is not None and tot < len(n.get("children") or []):
            die(f"node {cid}: children_total {tot} < {len(n['children'])} drawn")
    seen = set()
    for _cid, n in spec["nodes"].items():
        for k in n.get("children") or []:
            if k in seen:
                die(f"child {k} appears under more than one parent")
            seen.add(k)
    for r in spec.get("roots", []) + spec.get("free", []):
        if r["id"] not in ids:
            die(f"composition references unknown node {r['id']}")


def main():
    if len(sys.argv) < 3:
        die(__doc__.split("USAGE")[1].strip())
    spec_path, out_path = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    validate_spec(spec)
    if "--check" in sys.argv:
        print(f"spec OK: {len(spec['nodes'])} nodes, {len(spec.get('roots', []))} root frames")
        print(f"  objective: {spec['objective'][:70]}")
        print(f"  audience:  {spec['audience'][:70]}")
        return
    if os.path.exists(out_path):
        stamp = datetime.date.today().strftime("%Y%m%d")
        bak = f"{out_path}.bak-{stamp}"
        if not os.path.exists(bak):
            shutil.copy2(out_path, bak)
            print(f"backed up -> {bak}")
    prev = json.load(open(out_path)) if os.path.exists(out_path) else {}
    chart = Chart(spec)
    els = chart.build()
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": prev.get("source", "excal-chart.py"),
        "elements": els,
        "appState": prev.get("appState", {"viewBackgroundColor": "#ffffff"}),
        "files": prev.get("files", {}),
    }
    doc["appState"]["viewBackgroundColor"] = "#ffffff"
    json.dump(doc, open(out_path, "w"), indent=2, ensure_ascii=False)
    json.load(open(out_path))  # fresh re-parse: prove we wrote valid JSON
    xs = [e["x"] for e in els]
    ys = [e["y"] for e in els]
    print(
        f"wrote {out_path}: {len(els)} elements, "
        f"{sum(1 for e in els if e['type'] == 'rectangle')} rects"
    )
    print(f"  extent x {int(min(xs))}..{int(max(xs))}  y {int(min(ys))}..{int(max(ys))}")
    partial = [
        c
        for c, n in spec["nodes"].items()
        if n.get("children_total") is not None
        and 0 < len(n.get("children") or []) < n["children_total"]
    ]
    if partial:
        print(
            f"  subset disclosures emitted on {len(partial)} frame(s): "
            f"{', '.join(sorted(partial)[:6])}"
        )


if __name__ == "__main__":
    main()
