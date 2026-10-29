# ruff: noqa: E701, E702, E741
"""DEPRECATED: Legacy panel layout script retired in favor of automated rebuild (specs/tools/argument-map-rendering.md).

Panel layout for a claim tree: headline sentences, nested panels, leaves packed under their section,
arrows only for moves between panels. Input: tree.json from tree_lint.py.
Usage:
  gen_panels.py tree.json overview out.excalidraw [links.json]
  gen_panels.py tree.json chapter out.excalidraw "<chapter title>"
Tree levels: 0 root, 1 parts (rows), 2 chapters (panels), 3 sections (columns), 4+ leaves (boxes).
links.json: [{"from": "<chapter title>", "to": "<chapter title>", "label": "<inference in words>"}, ...]
"""

import json
import random
import string
import sys
import textwrap

random.seed(11)
KIND = {
    "claim": dict(bg="#fff3bf", stroke="#e67700"),
    "evidence": dict(bg="#d3f9d8", stroke="#2b8a3e"),
    "theory": dict(bg="#e5dbff", stroke="#7048e8"),
    "gap": dict(bg="#fff4e6", stroke="#f08c00", style="dashed"),
    "objection": dict(bg="#ffe3e3", stroke="#e03131"),
    "warrant": dict(bg="#f8f9fa", stroke="#868e96", style="dotted"),
}
INK = "#1e1e1e"
QUIET = "#5c5f66"
PANEL = "#f1f3f5"
PANELSTROKE = "#adb5bd"
T = json.load(open(sys.argv[1]))
N = T["nodes"]
WAR = T["warrants"]
mode = sys.argv[2]
out = sys.argv[3]
root = (
    next(t for t in N if N[t]["parent"] is None and N[t]["level"] == 0)
    if mode == "overview"
    else sys.argv[4]
)
LINKS = json.load(open(sys.argv[4])) if (mode == "overview" and len(sys.argv) > 4) else []
S = 1.0 if mode == "overview" else 1.35  # chapter canvases run larger


def simplify(n):
    k = n["kind"]
    tags = n["tags"]
    if k in ("missing", "needs"):
        return "gap"
    if k in ("unans", "conflict"):
        return "objection"
    if k == "dup":
        return "theory" if "theory" in tags else ("evidence" if "evidence" in tags else "claim")
    return "claim" if k in ("hero", "conc", "reform", "claim") else k


def label(t):
    n = N[t]
    txt = n["text"]
    k = n["kind"]
    pre = {
        "missing": "MISSING: ",
        "needs": "NEEDS EVIDENCE: ",
        "unans": "OBJECTION: ",
        "conflict": "CONFLICT: ",
    }.get(k, "")
    if k == "dup":
        txt += " (also drawn in another chapter)"
    return pre + txt


CW = 0.62


def wrap(text, maxw, font):
    cpl = max(10, int((maxw - 28) / (font * CW)))
    lines = []
    for p in text.split("\n"):
        lines += textwrap.wrap(p, cpl, break_on_hyphens=False) or [""]
    return lines


els = []


def rid():
    return "".join(random.choices(string.ascii_letters + string.digits, k=10))


def base(t, x, y, w, h, **kw):
    e = dict(
        id=kw.pop("id", rid()),
        type=t,
        x=x,
        y=y,
        width=w,
        height=h,
        angle=0,
        strokeColor=INK,
        backgroundColor="transparent",
        fillStyle="solid",
        strokeWidth=2,
        strokeStyle="solid",
        roughness=2,
        opacity=100,
        groupIds=[],
        frameId=None,
        index="a0",
        roundness=None,
        seed=random.randint(1, 2**31),
        version=1,
        versionNonce=random.randint(1, 2**31),
        isDeleted=False,
        boundElements=[],
        updated=1760000000000,
        link=None,
        locked=False,
    )
    e.update(kw)
    return e


def slug(t):
    return "".join(c if c.isalnum() else "-" for c in t)[:40]


def text_el(x, y, text, font, maxw, color=INK, align="left", bid=None):
    lines = wrap(text, maxw + 28, font)
    h = len(lines) * font * 1.3
    w = max(len(l) for l in lines) * font * CW
    e = base(
        "text",
        x,
        y,
        w,
        h,
        id=bid or rid(),
        text="\n".join(lines),
        originalText=text,
        fontSize=font,
        fontFamily=1,
        textAlign=align,
        verticalAlign="top",
        containerId=None,
        lineHeight=1.3,
        autoResize=False,
        strokeColor=color,
    )
    els.append(e)
    return e


def box(bid, x, y, w, text, font, kind, sw=1.5, center=False):
    lines = wrap(text, w, font)
    h = len(lines) * font * 1.3 + 24
    k = KIND[kind]
    r = base(
        "rectangle",
        x,
        y,
        w,
        h,
        id="box-" + bid,
        strokeColor=k["stroke"],
        backgroundColor=k["bg"],
        strokeStyle=k.get("style", "solid"),
        strokeWidth=sw,
        roundness={"type": 3},
    )
    tx = base(
        "text",
        x + 14,
        y + 12,
        w - 28,
        len(lines) * font * 1.3,
        id="txt-" + bid,
        text="\n".join(lines),
        originalText=text,
        fontSize=font,
        fontFamily=1,
        textAlign="center" if center else "left",
        verticalAlign="middle",
        containerId=r["id"],
        lineHeight=1.3,
        autoResize=False,
        strokeColor=INK,
    )
    r["boundElements"].append({"id": tx["id"], "type": "text"})
    els.append(r)
    els.append(tx)
    return r


def kids(t):
    return N[t]["children"] + N[t]["attackers"]


# ---------- one chapter panel ----------
def chapter_panel(ch, x, y, W):
    """Draw chapter `ch` as a panel at (x,y) with width W. Returns the panel rect."""
    pad = int(36 * S)
    gap = int(24 * S)
    n = N[ch]
    y0 = y
    cap = f"Chapter {ch.split(' ')[0]}" + (f" · {n['words']:,} words" if n.get("words") else "")
    text_el(x + pad, y + pad - 6, cap, int(14 * S), W - 2 * pad, QUIET)
    y += pad + int(14 * S) * 1.3 + 8
    hl = text_el(x + pad, y, n["text"], int(27 * S), W - 2 * pad, INK, bid="hl-" + slug(ch))
    y += hl["height"] + gap * 1.4
    secs = kids(ch)
    m = len(secs)
    cw = (W - 2 * pad - gap * (m - 1)) / m
    bottoms = []
    for i, s in enumerate(secs):
        sx = x + pad + i * (cw + gap)
        sy = y
        # section sub-panel: headline then leaves packed below
        inner = int(16 * S)
        yy = sy + inner
        sh = text_el(
            sx + inner,
            yy,
            n and N[s]["text"],
            int(17 * S),
            cw - 2 * inner,
            INK,
            bid="sh-" + slug(s),
        )
        yy += sh["height"] + inner
        for leaf in kids(s):
            ind = int(18 * S) if N[leaf]["rel"] == "attack" else 0
            r = box(
                slug(leaf),
                sx + inner + ind,
                yy,
                cw - 2 * inner - ind,
                label(leaf),
                int(12.5 * S),
                simplify(N[leaf]),
            )
            yy += r["height"] + int(10 * S)
            for rep in kids(leaf):  # replies to objections, indented further
                r2 = box(
                    slug(rep),
                    sx + inner + ind + int(18 * S),
                    yy,
                    cw - 2 * inner - ind - int(18 * S),
                    label(rep),
                    int(12.5 * S),
                    simplify(N[rep]),
                )
                yy += r2["height"] + int(10 * S)
        yy += inner - int(10 * S)
        sub = base(
            "rectangle",
            sx,
            sy,
            cw,
            yy - sy,
            id="sec-" + slug(s),
            strokeColor=PANELSTROKE,
            backgroundColor="#ffffff",
            strokeStyle="solid",
            strokeWidth=1,
            roughness=2,
            roundness={"type": 3},
        )
        els.insert(0, sub)
        bottoms.append(yy)
    y = max(bottoms) + pad
    panel = base(
        "rectangle",
        x,
        y0,
        W,
        y - y0,
        id="panel-" + slug(ch),
        strokeColor=PANELSTROKE,
        backgroundColor=PANEL,
        strokeStyle="solid",
        strokeWidth=1.5,
        roughness=2,
        roundness={"type": 3},
    )
    els.insert(0, panel)
    return panel


def arrow(a, b, pts, label_txt, color="#5c7f5c"):
    gap = 6
    ox, oy = pts[0]
    rel = [[round(px - ox, 2), round(py - oy, 2)] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    ar = base(
        "arrow",
        ox,
        oy,
        max(xs) - min(xs),
        max(ys) - min(ys),
        strokeColor=color,
        strokeWidth=2.5,
        roughness=2,
        points=rel,
        lastCommittedPoint=None,
        startBinding={"elementId": a["id"], "focus": 0, "gap": gap},
        endBinding={"elementId": b["id"], "focus": 0, "gap": gap},
        startArrowhead=None,
        endArrowhead="arrow",
        elbowed=False,
        roundness={"type": 2},
    )
    a["boundElements"].append({"id": ar["id"], "type": "arrow"})
    b["boundElements"].append({"id": ar["id"], "type": "arrow"})
    els.append(ar)
    if label_txt:
        mx, my = pts[len(pts) // 2]
        lines = wrap(label_txt, 260, 14)
        w = max(len(l) for l in lines) * 14 * CW + 8
        h = len(lines) * 14 * 1.3
        tx = base(
            "text",
            mx - w / 2,
            my - h / 2,
            w,
            h,
            text="\n".join(lines),
            originalText=label_txt,
            fontSize=14,
            fontFamily=1,
            textAlign="center",
            verticalAlign="middle",
            containerId=ar["id"],
            lineHeight=1.3,
            autoResize=False,
            strokeColor=color,
        )
        ar["boundElements"].append({"id": tx["id"], "type": "text"})
        els.append(tx)


panels = {}
if mode == "overview":
    PW = 1480
    PGAP = 170
    ROWGAP = 260
    X0 = 0
    # thesis headline with a yellow slab behind it
    y = 0
    th = text_el(X0 + 40, y + 30, N[root]["text"], 44, 3 * PW + 2 * PGAP - 80, INK, bid="hl-thesis")
    slab = base(
        "rectangle",
        X0,
        y,
        3 * PW + 2 * PGAP,
        th["height"] + 60,
        id="panel-thesis",
        strokeColor="#e67700",
        backgroundColor="#ffec99",
        strokeStyle="solid",
        strokeWidth=3,
        roughness=2,
        roundness={"type": 3},
    )
    els.insert(0, slab)
    text_el(X0 + 40, y - 40, "Thesis", 15, 1200, QUIET)
    y += slab["height"] + ROWGAP * 0.7
    rows = []  # (chapter -> (row index, col index))
    grid = {}
    for ri, p in enumerate(N[root]["children"]):
        text_el(X0, y, p.split(" ", 1)[1] if " " in p else p, 36, 3 * PW + 2 * PGAP, INK)
        y += 36 * 1.3 + 10
        pc = text_el(X0, y, N[p]["text"], 20, 3 * PW + 2 * PGAP, QUIET)
        y += pc["height"] + 40
        chs = N[p]["children"]
        rowx = X0 + (3 - len(chs)) * (PW + PGAP) / 2
        bottoms = []
        for i, c in enumerate(chs):
            pr = chapter_panel(c, rowx + i * (PW + PGAP), y, PW)
            panels[c] = pr
            bottoms.append(pr["y"] + pr["height"])
            grid[c] = (ri, i)
        y = max(bottoms) + ROWGAP
    # cross-panel moves from links.json, labelled with the inference; routed by grid position
    P = panels

    def top(r, f=0.5):
        return (r["x"] + r["width"] * f, r["y"])

    def bot(r, f=0.5):
        return (r["x"] + r["width"] * f, r["y"] + r["height"])

    def left(r, f=0.5):
        return (r["x"], r["y"] + r["height"] * f)

    def right(r, f=0.5):
        return (r["x"] + r["width"], r["y"] + r["height"] * f)

    for L in LINKS:
        fa = next((t for t in P if t == L["from"] or t.startswith(L["from"] + " ")), None)
        tb = next((t for t in P if t == L["to"] or t.startswith(L["to"] + " ")), None)
        if not fa or not tb:
            continue
        a, b = P[fa], P[tb]
        (ra, ca), (rb, cb) = grid[fa], grid[tb]
        if ra == rb and abs(ca - cb) == 1:  # neighbours in a row: side to side
            s0, e0 = (right(a, 0.5), left(b, 0.5)) if cb > ca else (left(a, 0.5), right(b, 0.5))
            pts = [s0, ((s0[0] + e0[0]) / 2, s0[1] - 30), e0]
        elif ra == rb:  # same row, not neighbours: over the top
            s0 = top(a, 0.7)
            ytop = a["y"] - 70
            e0 = top(b, 0.3)
            pts = [s0, (s0[0] + 60, ytop), ((s0[0] + e0[0]) / 2, ytop - 20), (e0[0] - 60, ytop), e0]
        elif abs(ra - rb) == 1:  # adjacent rows: through the row gap
            s0 = bot(a, 0.3) if rb > ra else top(a, 0.3)
            e0 = top(b, 0.6) if rb > ra else bot(b, 0.6)
            pts = [s0, ((s0[0] + e0[0]) / 2, (s0[1] + e0[1]) / 2), e0]
        else:  # further apart: round the left margin
            s0 = left(a, 0.6)
            xm = min(r["x"] for r in P.values()) - 120
            e0 = left(b, 0.35)
            pts = [s0, (xm, s0[1]), (xm - 40, (s0[1] + e0[1]) / 2), (xm, e0[1]), e0]
        arrow(a, b, pts, L.get("label", ""))
    # legend
    lx, ly = X0, y - ROWGAP + 40
    text_el(
        lx,
        ly,
        "Legend · panels are chapters, white columns are sections, small boxes are the reasons each section rests on. Arrows mark only the moves between chapters, labelled with the inference.",
        15,
        2600,
        QUIET,
    )
    ly += 50
    for i, (k, lab) in enumerate(
        [
            ("claim", "Claim"),
            ("evidence", "Evidence"),
            ("theory", "Theory or scholarship"),
            ("gap", "Gap: missing step or needs evidence"),
            ("objection", "Objection or conflict to answer"),
        ]
    ):
        box(f"leg{i}", lx + i * 330, ly, 300, lab, 14, k, center=True)
else:
    pr = chapter_panel(root, 0, 0, 1900)
    panels[root] = pr
    ws = [(c, w) for c, w in WAR.items() if c in N and (c == root or N[c]["parent"] == root)]
    if ws:
        x = pr["x"] + pr["width"] + 120
        y = pr["y"]
        text_el(x, y, "Warrant blocks: the premises that together license a claim", 17, 420, QUIET)
        y += 50
        for c, w in ws:
            txt = (
                w["title"].split(" ")[0]
                + ": "
                + " + ".join(p.split(" ")[0] for p in w["premises"])
                + "  →  "
                + c
            )
            r = box("W-" + slug(c), x, y, 440, txt, 13, "warrant")
            y += r["height"] + 14
allel = els
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
for i, e in enumerate(allel):
    e["index"] = "b" + B62[i // 62] + B62[i % 62]
json.dump(
    {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": allel,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    },
    open(out, "w"),
    indent=1,
)
print(out, "elements", len(allel))
