#!/usr/bin/env python3
"""Render an argument map from its Argdown source to Excalidraw, SVG, and overview page."""

from __future__ import annotations

import argparse
import base64
import json
import random
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import yaml

CW = 0.62
DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

STYLE: dict[str, dict[str, str]] = {
    "claim": {"bg": "#fff9db", "stroke": "#e67700", "style": "solid"},
    "argument": {"bg": "#fff3bf", "stroke": "#d9480f", "style": "solid"},
    "evidence": {"bg": "#d3f9d8", "stroke": "#2b8a3e", "style": "solid"},
    "theory": {"bg": "#e5dbff", "stroke": "#7048e8", "style": "solid"},
    "gap": {"bg": "#fff4e6", "stroke": "#f08c00", "style": "dashed"},
    "objection": {"bg": "#ffe3e3", "stroke": "#e03131", "style": "solid"},
    "fork": {"bg": "#e7f5ff", "stroke": "#1971c2", "style": "dashed"},
    "neutral": {"bg": "#f8f9fa", "stroke": "#868e96", "style": "solid"},
}


def make_index_keys(n: int) -> list[str]:
    """Generate monotonically increasing fractional index keys for Excalidraw elements."""
    out: list[str] = []
    length = 1
    while len(out) < n:
        lead = chr(ord("a") + length - 1)
        for v in range(62**length):
            digs: list[str] = []
            x = v
            for _ in range(length):
                digs.append(DIGITS[x % 62])
                x //= 62
            out.append(lead + "".join(reversed(digs)))
            if len(out) == n:
                break
        length += 1
    return out


def wrap_text(text: str, max_w: int, font_size: int) -> list[str]:
    """Wrap text to fit within max width in pixels for Virgil font."""
    cpl = max(10, int((max_w - 28) / (font_size * CW)))
    lines: list[str] = []
    for paragraph in text.split("\n"):
        p = paragraph.strip()
        if not p:
            continue
        lines.extend(textwrap.wrap(p, width=cpl, break_on_hyphens=False) or [""])
    return lines or [""]


def slugify(text: str) -> str:
    """Create a clean kebab-case/snake-case identifier from a title."""
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", s)[:40]


def determine_kind(tags: list[str], is_argument: bool) -> str:
    """Determine visual style kind from semantic tags."""
    low_tags = [t.lower() for t in tags]
    if any(t in low_tags for t in ["missing", "needs-evidence", "needs", "placeholder"]):
        return "gap"
    if any(t in low_tags for t in ["unanswered", "conflict", "unans"]):
        return "objection"
    if any(t in low_tags for t in ["fork"]):
        return "fork"
    if any(t in low_tags for t in ["evidence", "done"]):
        return "evidence"
    if any(t in low_tags for t in ["theory"]):
        return "theory"
    return "argument" if is_argument else "claim"


def fetch_source_text(input_str: str) -> tuple[str, str]:
    """Resolve input path or note ID and return (content, stem_name)."""
    # 1. Stdin
    if input_str == "-":
        return sys.stdin.read(), "argmap_stdin"

    # 2. Local file path
    path = Path(input_str)
    if path.is_file():
        return path.read_text(encoding="utf-8"), path.stem

    # Clean stem if given a note ID
    clean_stem = Path(input_str).stem
    if not input_str.endswith((".md", ".argdown")) and "/" not in input_str:
        clean_stem = input_str

    # 3. Check for matching local files in notes/ or current directory
    candidates = list(Path.cwd().glob(f"**/*{input_str}*.md")) + list(
        Path.cwd().glob(f"**/*{input_str}*.argdown")
    )
    if candidates:
        candidate = candidates[0]
        return candidate.read_text(encoding="utf-8"), clean_stem

    # 4. Fetch via GitHub API if available
    try:
        r = subprocess.run(
            [
                "gh",
                "api",
                "repos/nicsuzor/brain/git/trees/main?recursive=1",
                "--jq",
                ".tree[].path",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        paths = [p for p in r.stdout.splitlines() if input_str in p and p.endswith(".md")]
        if paths:
            target_path = paths[0]
            res = subprocess.run(
                ["gh", "api", f"repos/nicsuzor/brain/contents/{target_path}", "--jq", ".content"],
                capture_output=True,
                text=True,
                check=True,
            )
            raw = base64.b64decode(res.stdout).decode("utf-8")
            return raw, clean_stem
    except Exception as exc:
        raise FileNotFoundError(f"Could not resolve input '{input_str}': {exc}") from exc

    raise FileNotFoundError(f"Input file or note ID not found: {input_str}")


def extract_argdown_block(text: str, block_index: int | None = None) -> tuple[str, dict[str, Any]]:
    """Extract Argdown source from markdown code block or return raw text, plus frontmatter."""
    blocks = list(re.finditer(r"```argdown\n([\s\S]*?)```", text))
    if not blocks:
        raw_argdown = text
    elif block_index is not None and 0 <= block_index < len(blocks):
        raw_argdown = blocks[block_index].group(1)
    else:
        # Check for block under "## Argdown source" heading
        source_match = re.search(
            r"##\s+Argdown source[\s\S]*?```argdown\n([\s\S]*?)```", text, re.IGNORECASE
        )
        if source_match:
            raw_argdown = source_match.group(1)
        else:
            best_block = max(blocks, key=lambda b: len(b.group(1).splitlines()))
            raw_argdown = best_block.group(1)

    # Extract YAML frontmatter from === ... === block if present
    frontmatter: dict[str, Any] = {}
    fm_match = re.search(r"^===\s*\n([\s\S]*?)\n===", raw_argdown)
    if fm_match:
        try:
            parsed = yaml.safe_load(fm_match.group(1))
            if isinstance(parsed, dict):
                frontmatter = parsed
        except Exception:
            pass

    return raw_argdown, frontmatter


def compile_argdown(argdown_text: str) -> dict[str, Any]:
    """Compile Argdown text to JSON using argdown CLI."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_file = Path(tmp_dir) / "source.argdown"
        input_file.write_text(argdown_text, encoding="utf-8")
        out_dir = Path(tmp_dir) / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        res = subprocess.run(
            ["argdown", "json", str(input_file), str(out_dir)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"argdown compilation failed:\n{res.stderr or res.stdout}")

        json_files = list(out_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError("argdown did not produce any JSON output file")

        with open(json_files[0], encoding="utf-8") as f:
            return json.load(f)


def build_excalidraw_canvas(
    data: dict[str, Any], frontmatter: dict[str, Any], filter_section: str | None = None
) -> dict[str, Any]:
    """Build an Excalidraw canvas JSON from compiled Argdown data."""
    sections = data.get("sections", [])
    stmts = data.get("statements", {})
    args = data.get("arguments", {})
    rels = data.get("relations", [])

    title = frontmatter.get("title") or data.get("settings", {}).get("title") or "Argument Map"
    author = frontmatter.get("author") or "Reconstructed from Argdown"
    job = frontmatter.get("job") or "Argument evaluation and structural review"

    sec_order: list[str] = []
    sec_info: dict[str, dict[str, Any]] = {}
    for s in sections:
        sid = s["id"]
        sec_order.append(sid)
        sec_info[sid] = {"title": s["title"], "nodes": []}

    if not sec_order:
        sec_order.append("default")
        sec_info["default"] = {"title": "Main Arguments", "nodes": []}

    for name, s in stmts.items():
        sec = s.get("section")
        if not sec and s.get("members"):
            sec = s["members"][0].get("section")
        if not sec or sec not in sec_info:
            sec = sec_order[0]

        text = ""
        tags = list(s.get("tags", []))
        for m in s.get("members", []):
            if m.get("text"):
                text = m["text"]
                break

        clean_text = text
        for t in tags:
            clean_text = re.sub(rf"#{re.escape(t)}\b", "", clean_text)
        clean_text = clean_text.strip()

        kind = determine_kind(tags, is_argument=False)
        node = {
            "id": "s_" + slugify(name),
            "orig_id": name,
            "type": "statement",
            "name": name,
            "title": f"[{name}]",
            "text": clean_text,
            "tags": tags,
            "kind": kind,
            "section": sec,
            "pcs": [],
        }
        sec_info[sec]["nodes"].append(node)

    for name, a in args.items():
        sec = a.get("section")
        if not sec and a.get("members"):
            sec = a["members"][0].get("section")
        if not sec or sec not in sec_info:
            sec = sec_order[0]

        text = ""
        tags = list(a.get("tags", []))
        for m in a.get("members", []):
            if m.get("text"):
                text = m["text"]
                break

        pcs_lines: list[str] = []
        for p in a.get("pcs", []):
            ptit = p.get("title", "")
            prole = p.get("role", "")
            if prole == "premise" and not ptit.startswith("Untitled"):
                pcs_lines.append(f"• [{ptit}]")
            elif prole in ("conclusion", "main-conclusion") and not ptit.startswith("Untitled"):
                pcs_lines.append(f"  → [{ptit}]")

        clean_text = text
        for t in tags:
            clean_text = re.sub(rf"#{re.escape(t)}\b", "", clean_text)
        clean_text = clean_text.strip()
        if pcs_lines and not clean_text:
            clean_text = "\n".join(pcs_lines)

        kind = determine_kind(tags, is_argument=True)
        node = {
            "id": "a_" + slugify(name),
            "orig_id": name,
            "type": "argument",
            "name": name,
            "title": f"<{name}>",
            "text": clean_text,
            "tags": tags,
            "kind": kind,
            "section": sec,
            "pcs": pcs_lines,
        }
        sec_info[sec]["nodes"].append(node)

    active_secs = [sid for sid in sec_order if sec_info[sid]["nodes"]]
    if filter_section:
        active_secs = [sid for sid in active_secs if sid == filter_section]
        if not active_secs:
            active_secs = [
                sid for sid in sec_order if filter_section.lower() in sec_info[sid]["title"].lower()
            ]

    elements: list[dict[str, Any]] = []
    node_rects: dict[str, dict[str, Any]] = {}

    def add_rect(
        bid: str,
        x: float,
        y: float,
        w: float,
        h: float,
        bg: str,
        stroke: str,
        style: str = "solid",
        sw: float = 2.0,
        roundness: int = 3,
    ) -> dict[str, Any]:
        r: dict[str, Any] = {
            "id": bid,
            "type": "rectangle",
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": bg,
            "fillStyle": "solid",
            "strokeWidth": sw,
            "strokeStyle": style,
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": "a0",
            "roundness": {"type": roundness} if roundness else None,
            "seed": random.randint(1, 2**31),
            "version": 1,
            "versionNonce": random.randint(1, 2**31),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        elements.append(r)
        return r

    def add_text(
        tid: str,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        font_size: int = 13,
        color: str = "#1e1e1e",
        align: str = "left",
        container_id: str | None = None,
    ) -> dict[str, Any]:
        lines = wrap_text(text, int(w), font_size)
        txt = "\n".join(lines)
        actual_h = max(h, len(lines) * font_size * 1.3)
        t: dict[str, Any] = {
            "id": tid,
            "type": "text",
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(actual_h),
            "angle": 0,
            "strokeColor": color,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": "a0",
            "roundness": None,
            "seed": random.randint(1, 2**31),
            "version": 1,
            "versionNonce": random.randint(1, 2**31),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
            "text": txt,
            "originalText": text,
            "fontSize": font_size,
            "fontFamily": 1,
            "textAlign": align,
            "verticalAlign": "middle" if container_id else "top",
            "containerId": container_id,
            "lineHeight": 1.3,
            "autoResize": False,
        }
        elements.append(t)
        return t

    def add_card(node: dict[str, Any], x: float, y: float, w: float) -> float:
        st = STYLE.get(node["kind"], STYLE["neutral"])
        tag_str = " ".join(f"#{t}" for t in node["tags"])
        header_text = node["title"] + (f"  {tag_str}" if tag_str else "")
        full_content = header_text + ("\n\n" + node["text"] if node["text"] else "")

        lines = wrap_text(full_content, int(w), 13)
        h = max(90, int(len(lines) * 13 * 1.3 + 36))

        r = add_rect(node["id"], x, y, w, h, st["bg"], st["stroke"], st["style"], sw=2.0)
        tx = add_text(
            "txt_" + node["id"],
            x + 14,
            y + 14,
            w - 28,
            h - 28,
            full_content,
            font_size=13,
            color="#1e1e1e",
            align="left",
            container_id=r["id"],
        )
        r["boundElements"].append({"id": tx["id"], "type": "text"})

        node_rects[node["name"]] = {"x": x, "y": y, "w": w, "h": h, "id": r["id"], "elem": r}
        return float(h)

    START_X = 80.0
    START_Y = 60.0
    CARD_W = 460.0
    PANEL_PAD = 24.0
    PANEL_W = CARD_W + 2 * PANEL_PAD
    PGAP = 50.0
    CARD_GAP = 20.0

    # Header and Legend
    HEADER_W = 1200.0
    LEGEND_W = 1500.0
    hdr_text = f"{title}\n\nAuthor: {author}\nJob: {job}\nNodes: {len(stmts)} statements, {len(args)} arguments | Relations: {len(rels)}"
    h_lines = wrap_text(hdr_text, int(HEADER_W - 40), 14)
    hdr_h = max(160, int(len(h_lines) * 14 * 1.3 + 40))

    r_hdr = add_rect(
        "b_header",
        START_X,
        START_Y,
        HEADER_W,
        float(hdr_h),
        "#e9ecef",
        "#adb5bd",
        sw=1.5,
        roundness=3,
    )
    tx_hdr = add_text(
        "txt_header",
        START_X + 20,
        START_Y + 20,
        HEADER_W - 40,
        float(hdr_h - 40),
        hdr_text,
        font_size=14,
        color="#1e1e1e",
        container_id=r_hdr["id"],
    )
    r_hdr["boundElements"].append({"id": tx_hdr["id"], "type": "text"})

    leg_text = "Legend & Visual Encoding:\n\n• Gold/Yellow: Claim / Thesis / Core Argument\n• Green: Stated Empirical Evidence / Literature Finding\n• Purple: Theoretical Warrant / Scholarship\n• Amber (dashed): Gap (#missing premise, #needs-evidence, #placeholder)\n• Red: Objection (#unanswered objection, #conflict)\n• Blue (dashed): Author Fork (#fork)\n• Arrows: Solid Green = Support (+>), Dashed Red = Attack (->), Dotted = Undercut (_>)"
    l_lines = wrap_text(leg_text, int(LEGEND_W - 40), 13)
    leg_h = max(hdr_h, int(len(l_lines) * 13 * 1.3 + 40))

    r_leg = add_rect(
        "b_legend",
        START_X + HEADER_W + 40,
        START_Y,
        LEGEND_W,
        float(leg_h),
        "#f8f9fa",
        "#adb5bd",
        sw=1.5,
        roundness=3,
    )
    tx_leg = add_text(
        "txt_legend",
        START_X + HEADER_W + 60,
        START_Y + 20,
        LEGEND_W - 40,
        float(leg_h - 40),
        leg_text,
        font_size=13,
        color="#495057",
        container_id=r_leg["id"],
    )
    r_leg["boundElements"].append({"id": tx_leg["id"], "type": "text"})

    curr_y = START_Y + max(hdr_h, leg_h) + 50.0

    # Separate Thesis from other parts
    thesis_sec = None
    other_secs: list[str] = []
    if not filter_section and active_secs and "thesis" in sec_info[active_secs[0]]["title"].lower():
        thesis_sec = active_secs[0]
        other_secs = active_secs[1:]
    else:
        other_secs = active_secs

    # Thesis section banner and cards
    if thesis_sec:
        th_nodes = sec_info[thesis_sec]["nodes"]
        th_title = sec_info[thesis_sec]["title"]
        th_w = max(HEADER_W + LEGEND_W + 40.0, len(th_nodes) * (CARD_W + 40.0))

        r_th_bar = add_rect(
            "b_thesis_bar", START_X, curr_y, th_w, 42.0, "#ffe066", "#f59f00", sw=2.0, roundness=3
        )
        tx_th_bar = add_text(
            "txt_thesis_bar",
            START_X + 20,
            curr_y + 10,
            th_w - 40,
            22.0,
            f"THESIS SPINE · {th_title}",
            font_size=16,
            color="#e67700",
            align="center",
            container_id=r_th_bar["id"],
        )
        r_th_bar["boundElements"].append({"id": tx_th_bar["id"], "type": "text"})
        curr_y += 42.0 + 20.0

        th_bottoms: list[float] = []
        for idx, tn in enumerate(th_nodes):
            tx_pos = START_X + idx * (CARD_W + 40.0)
            th_h = add_card(tn, tx_pos, curr_y, CARD_W)
            th_bottoms.append(curr_y + th_h)
        curr_y = max(th_bottoms) + 60.0

    # Arrange parts in grid
    COLS = 4 if not filter_section else 1
    num_parts = len(other_secs)
    actual_cols = min(num_parts, COLS) if num_parts > 0 else 1

    part_idx = 0
    while part_idx < num_parts:
        row_secs = other_secs[part_idx : part_idx + actual_cols]
        row_y = curr_y
        row_panel_heights: list[float] = []

        for sid in row_secs:
            pnodes = sec_info[sid]["nodes"]
            p_lines = wrap_text(sec_info[sid]["title"], int(PANEL_W - 2 * PANEL_PAD), 16)
            th_title_h = max(30, int(len(p_lines) * 16 * 1.3))
            panel_content_h = th_title_h + 20.0
            for pn in pnodes:
                tag_str = " ".join(f"#{t}" for t in pn["tags"])
                full_content = (
                    pn["title"]
                    + (f"  {tag_str}" if tag_str else "")
                    + ("\n\n" + pn["text"] if pn["text"] else "")
                )
                lines = wrap_text(full_content, int(CARD_W), 13)
                ch = max(90, int(len(lines) * 13 * 1.3 + 36))
                panel_content_h += ch + CARD_GAP
            panel_total_h = panel_content_h + 2 * PANEL_PAD
            row_panel_heights.append(float(panel_total_h))

        max_row_h = max(row_panel_heights) if row_panel_heights else 200.0

        for c_idx, sid in enumerate(row_secs):
            px = START_X + c_idx * (PANEL_W + PGAP)
            p_title = sec_info[sid]["title"]
            pnodes = sec_info[sid]["nodes"]

            add_rect(
                f"panel_{slugify(sid)}",
                px,
                row_y,
                PANEL_W,
                max_row_h,
                "#f1f3f5",
                "#adb5bd",
                sw=1.5,
                roundness=3,
            )
            p_lines = wrap_text(p_title, int(PANEL_W - 2 * PANEL_PAD), 16)
            th_title_h = max(30, int(len(p_lines) * 16 * 1.3))
            add_text(
                f"txt_panel_{slugify(sid)}",
                px + PANEL_PAD,
                row_y + PANEL_PAD,
                PANEL_W - 2 * PANEL_PAD,
                float(th_title_h),
                p_title,
                font_size=16,
                color="#1e1e1e",
                align="left",
            )

            card_y = row_y + PANEL_PAD + th_title_h + 20.0
            for pn in pnodes:
                ch = add_card(pn, px + PANEL_PAD, card_y, CARD_W)
                card_y += ch + CARD_GAP

        curr_y += max_row_h + 80.0
        part_idx += actual_cols

    # Connect relations with arrows
    for idx, r in enumerate(rels):
        from_name = r.get("from")
        to_name = r.get("to")
        rtype = r.get("relationType", "support")

        if from_name not in node_rects or to_name not in node_rects:
            continue

        src = node_rects[from_name]
        tgt = node_rects[to_name]

        sc_x = src["x"] + src["w"] / 2
        sc_y = src["y"] + src["h"] / 2
        tc_x = tgt["x"] + tgt["w"] / 2
        tc_y = tgt["y"] + tgt["h"] / 2

        if abs(sc_x - tc_x) < 40:
            if tc_y > sc_y:
                p_start = (sc_x, src["y"] + src["h"])
                p_end = (tc_x, tgt["y"])
            else:
                p_start = (sc_x, src["y"])
                p_end = (tc_x, tgt["y"] + tgt["h"])
            waypoints = [p_start, p_end]
        elif tc_x > sc_x:
            p_start = (src["x"] + src["w"], sc_y)
            p_end = (tgt["x"], tc_y)
            mid_x = (p_start[0] + p_end[0]) / 2
            waypoints = [p_start, (mid_x, p_start[1]), (mid_x, p_end[1]), p_end]
        else:
            p_start = (src["x"], sc_y)
            p_end = (tgt["x"] + tgt["w"], tc_y)
            mid_x = (p_start[0] + p_end[0]) / 2
            waypoints = [p_start, (mid_x, p_start[1]), (mid_x, p_end[1]), p_end]

        ox, oy = waypoints[0]
        rel_pts = [[round(px - ox, 2), round(py - oy, 2)] for px, py in waypoints]
        xs = [p[0] for p in rel_pts]
        ys = [p[1] for p in rel_pts]
        ar_w = max(xs) - min(xs)
        ar_h = max(ys) - min(ys)

        ar_color = (
            "#2b8a3e" if rtype == "support" else ("#c92a2a" if rtype == "attack" else "#7048e8")
        )
        ar_style = "solid" if rtype == "support" else ("dashed" if rtype == "attack" else "dotted")

        ar_id = f"ar_{idx}_{slugify(from_name)}_{slugify(to_name)}"
        arrow: dict[str, Any] = {
            "id": ar_id,
            "type": "arrow",
            "x": float(ox),
            "y": float(oy),
            "width": float(ar_w),
            "height": float(ar_h),
            "angle": 0,
            "strokeColor": ar_color,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": ar_style,
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": "a0",
            "roundness": {"type": 2},
            "seed": random.randint(1, 2**31),
            "version": 1,
            "versionNonce": random.randint(1, 2**31),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
            "points": rel_pts,
            "lastCommittedPoint": None,
            "startBinding": {"elementId": src["id"], "focus": 0, "gap": 6},
            "endBinding": {"elementId": tgt["id"], "focus": 0, "gap": 6},
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "elbowed": False,
        }
        elements.append(arrow)
        src["elem"]["boundElements"].append({"id": ar_id, "type": "arrow"})
        tgt["elem"]["boundElements"].append({"id": ar_id, "type": "arrow"})

    keys = make_index_keys(len(elements))
    for e, k in zip(elements, keys, strict=True):
        e["index"] = k

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def generate_overview_markdown(
    data: dict[str, Any], frontmatter: dict[str, Any], stem: str, out_dir: Path
) -> str:
    """Generate the structured overview page describing the argument map and open issues."""
    sections = data.get("sections", [])
    stmts = data.get("statements", {})
    args = data.get("arguments", {})
    rels = data.get("relations", [])

    title = (
        frontmatter.get("title") or data.get("settings", {}).get("title") or f"{stem} Argument Map"
    )
    author = frontmatter.get("author") or "Reconstructed from Argdown"
    job = frontmatter.get("job") or "Argument evaluation and supervisory review"

    tag_counts: dict[str, int] = {}
    open_items: list[dict[str, str]] = []

    for name, s in {**stmts, **args}.items():
        tags = s.get("tags", [])
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
        low_tags = [t.lower() for t in tags]
        if any(
            t in low_tags
            for t in ["missing", "needs-evidence", "needs", "unanswered", "conflict", "fork"]
        ):
            sec = s.get("section", "General")
            text = ""
            for m in s.get("members", []):
                if m.get("text"):
                    text = m["text"]
                    break
            open_items.append(
                {
                    "name": name,
                    "tags": ", ".join(f"#{t}" for t in tags),
                    "section": sec,
                    "text": text[:120] + ("..." if len(text) > 120 else ""),
                }
            )

    support_cnt = sum(1 for r in rels if r.get("relationType") == "support")
    attack_cnt = sum(1 for r in rels if r.get("relationType") == "attack")
    undercut_cnt = sum(1 for r in rels if r.get("relationType") == "undercut")

    md: list[str] = [
        f"# {title}",
        "",
        f"**Author:** {author}  ",
        f"**Job:** {job}  ",
        f"**Canvas:** [{stem}.excalidraw]({stem}.excalidraw) · **Vector Map:** [{stem}.svg]({stem}.svg)",
        "",
        "## Summary Metrics",
        "",
        f"- **Statements:** {len(stmts)}",
        f"- **Arguments:** {len(args)}",
        f"- **Relations:** {len(rels)} ({support_cnt} support, {attack_cnt} attack, {undercut_cnt} undercut)",
        f"- **Sections / Parts:** {len(sections)}",
        "- **Open Issue Tags:** "
        + ", ".join(
            f"{cnt} #{t}"
            for t, cnt in tag_counts.items()
            if t in ["missing", "needs-evidence", "unanswered", "conflict", "fork"]
        )
        + (
            ", 0 open issues"
            if not any(
                t in tag_counts
                for t in ["missing", "needs-evidence", "unanswered", "conflict", "fork"]
            )
            else ""
        ),
        "",
        "## Map Preview",
        "",
        f"![{title}]({stem}.svg)",
        "",
        "## What the Argument Still Needs",
        "",
    ]

    if open_items:
        md.append("| Part / Section | Claim / Argument | Tags | Detail / Question |")
        md.append("| --- | --- | --- | --- |")
        for item in open_items:
            sec_name = item["section"]
            sec_title = next((s["title"] for s in sections if s["id"] == sec_name), sec_name)
            md.append(f"| {sec_title} | `{item['name']}` | {item['tags']} | {item['text']} |")
    else:
        md.append(
            "All load-bearing premises and inferences are supported and closed. No open issues recorded."
        )

    md.extend(["", "## Structure Outline", ""])
    for s in sections:
        md.append(f"### {s['title']}")
        sec_nodes: list[str] = []
        for name, sm in stmts.items():
            if sm.get("section") == s["id"] or (
                sm.get("members") and sm["members"][0].get("section") == s["id"]
            ):
                tgs = " ".join(f"#{t}" for t in sm.get("tags", []))
                sec_nodes.append(f"- `[{name}]` {tgs}")
        for name, am in args.items():
            if am.get("section") == s["id"] or (
                am.get("members") and am["members"][0].get("section") == s["id"]
            ):
                tgs = " ".join(f"#{t}" for t in am.get("tags", []))
                sec_nodes.append(f"- `<{name}>` {tgs}")
        if sec_nodes:
            md.extend(sec_nodes)
        else:
            md.append("*(No statements or arguments placed directly under this heading)*")
        md.append("")

    return "\n".join(md)


def render_argument_map(
    input_str: str,
    out_dir: str | Path | None = None,
    block_index: int | None = None,
) -> dict[str, str]:
    """Execute full argument map rendering pipeline and return output artifact paths."""
    out_path = Path(out_dir) if out_dir else Path.cwd()
    out_path.mkdir(parents=True, exist_ok=True)

    raw_text, stem = fetch_source_text(input_str)
    argdown_src, frontmatter = extract_argdown_block(raw_text, block_index=block_index)

    # 1. Compile Argdown
    data = compile_argdown(argdown_src)

    # 2. Build and save main Excalidraw canvas
    main_excal_path = out_path / f"{stem}.excalidraw"
    canvas_dict = build_excalidraw_canvas(data, frontmatter)
    with open(main_excal_path, "w", encoding="utf-8") as f:
        json.dump(canvas_dict, f, indent=2)

    # Validate canvas
    chk = subprocess.run(
        ["pkb-excalidraw", str(main_excal_path), "check"], capture_output=True, text=True
    )
    if chk.returncode != 0:
        print(
            f"Warning: pkb-excalidraw check reported issues:\n{chk.stdout}\n{chk.stderr}",
            file=sys.stderr,
        )

    ovl = subprocess.run(
        ["pkb-excalidraw", str(main_excal_path), "overlap"], capture_output=True, text=True
    )
    if ovl.returncode != 0:
        print(
            f"Warning: pkb-excalidraw overlap reported collisions:\n{ovl.stdout}\n{ovl.stderr}",
            file=sys.stderr,
        )

    # 3. Render SVG
    main_svg_path = out_path / f"{stem}.svg"
    subprocess.run(
        [
            "pkb-excalidraw",
            str(main_excal_path),
            "screenshot",
            "--out",
            str(main_svg_path),
            "--format",
            "svg",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    # 4. Generate overview markdown page
    overview_path = out_path / f"{stem}-overview.md"
    overview_content = generate_overview_markdown(data, frontmatter, stem, out_path)
    overview_path.write_text(overview_content, encoding="utf-8")

    artifacts: dict[str, str] = {
        "canvas": str(main_excal_path),
        "svg": str(main_svg_path),
        "overview": str(overview_path),
    }

    # 5. Build per-part canvases and SVGs
    sections = data.get("sections", [])
    for sec in sections:
        sid = sec["id"]
        sec_title = sec["title"]
        part_slug = slugify(sec_title)
        part_canvas = build_excalidraw_canvas(data, frontmatter, filter_section=sid)
        if len(part_canvas.get("elements", [])) <= 4:  # header + legend only
            continue
        part_excal_path = out_path / f"{stem}_{part_slug}.excalidraw"
        with open(part_excal_path, "w", encoding="utf-8") as f:
            json.dump(part_canvas, f, indent=2)
        part_svg_path = out_path / f"{stem}_{part_slug}.svg"
        subprocess.run(
            [
                "pkb-excalidraw",
                str(part_excal_path),
                "screenshot",
                "--out",
                str(part_svg_path),
                "--format",
                "svg",
            ],
            capture_output=True,
            text=True,
        )
        artifacts[f"part_{part_slug}_canvas"] = str(part_excal_path)
        artifacts[f"part_{part_slug}_svg"] = str(part_svg_path)

    return artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render argument maps from Argdown source.")
    parser.add_argument("input", help="Path to .argdown / .md file, PKB note ID, or '-' for stdin.")
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="Output directory for generated artifacts (default: current directory).",
    )
    parser.add_argument(
        "--block",
        "-b",
        type=int,
        default=None,
        help="Argdown code block index if input contains multiple fences.",
    )

    args = parser.parse_args(argv)
    try:
        results = render_argument_map(args.input, out_dir=args.out, block_index=args.block)
        print("Argument map rendered successfully:")
        for k, v in results.items():
            print(f"  {k}: {v}")
        return 0
    except Exception as exc:
        print(f"Error rendering argument map: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
