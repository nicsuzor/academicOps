#!/usr/bin/env python3
"""Editing and layout verification utilities for .excalidraw files. Stdlib + matplotlib for render.

Usage: excal-edit.py FILE fit <id> "<new text>"
       excal-edit.py FILE restack [<id>] [--gap GAP]
       excal-edit.py FILE overlap [--baseline BASELINE]
       excal-edit.py FILE arrows
       excal-edit.py FILE render [OUT.png] [--region X0,Y0,X1,Y1]

  fit      recomputes text bounding box for element <id> (text or container)
           with <new text>, center-grows its container if needed to prevent text
           overflow, and saves the file.
  restack  repositions sibling texts inside a card container (or all card
           containers if <id> is omitted) vertically so none overprints
           another, without moving the card. Fails closed if text overflows card.
  overlap  checks AABB collisions between non-nested sibling elements (including
           sibling texts inside a card, excluding bound text-container pairs and
           frame-child pairs). Accepts --baseline <file_or_spec> to allowlist
           known intentional collisions. Exits 1 on overlap.
  arrows   checks every arrow's polyline against every shape's interior, flagging
           any arrow that cuts through a box it is not bound to at either end
           (the craft rule: route around unrelated boxes, never through them).
           Exact segment/rectangle intersection, not sampling. Background zone
           rectangles (a shape fully containing 3+ other shapes) are treated
           as scenery, not obstacles — same spirit as `overlap`'s nesting
           exclusion. Exits 1 on a hit.
  render   renders a visual preview (boxes, text, arrows) using matplotlib.
           Properly inverts y-axis (Excalidraw y grows downward). Pass
           --region X0,Y0,X1,Y1 to crop to one area of a large canvas instead
           of the full extent — the whole-canvas render is illegible past a
           couple hundred elements.
"""

import json
import sys
from pathlib import Path


def live_elements(doc):
    return [e for e in doc.get("elements", []) if not e.get("isDeleted")]


def element_text(e):
    """What a text element actually says.

    `text` is the wrapped copy Excalidraw paints; `originalText` is the
    unwrapped source it re-wraps `text` from on the next layout pass, which
    makes `originalText` the one that survives. On a file damaged by a writer
    that set `text` alone, `text` holds a label that is already doomed — so
    read `originalText` and report what will still be there. `excalidraw-view.py
    check` fails the file when the two disagree.
    """
    return e.get("originalText") or e.get("text", "") or ""


def get_label(e, by_id):
    if e.get("type") == "text":
        return element_text(e).replace("\n", " / ")
    for b in e.get("boundElements") or []:
        if b.get("type") == "text" and b["id"] in by_id:
            return element_text(by_id[b["id"]]).replace("\n", " / ")
    return ""


def _is_zone_shape(shape, all_shapes):
    """Detect whether a shape is a background zone containing other shapes."""

    def _fully_contains(outer, inner):
        if outer is inner:
            return False
        ox, oy, ow, oh = outer["x"], outer["y"], outer["width"], outer["height"]
        ix, iy, iw, ih = inner["x"], inner["y"], inner["width"], inner["height"]
        return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh

    return sum(1 for other in all_shapes if _fully_contains(shape, other)) >= 3


def get_card_texts(container, els, by_id):
    """Discover text elements belonging to a card container without assuming naming conventions.

    1. Structural discovery (primary):
       All live text elements where `text.containerId == container["id"]`
       or `text.id` is listed in `container.boundElements` (type 'text').
    2. Geometric fallback:
       If no structural texts exist and container is not a background zone,
       find live text elements whose bounding box falls inside this container.
       If a text falls inside multiple containers, assign to the innermost (smallest area).
    """
    cid = container["id"]
    structural_texts = []

    bound_text_ids = {
        b["id"]
        for b in (container.get("boundElements") or [])
        if b.get("type") == "text" and b["id"] in by_id
    }

    for e in els:
        if e.get("type") == "text":
            if e.get("containerId") == cid or e["id"] in bound_text_ids:
                if e not in structural_texts:
                    structural_texts.append(e)

    if structural_texts:
        return structural_texts

    all_shapes = [
        e
        for e in els
        if e.get("type") in ("rectangle", "diamond", "ellipse")
        and e.get("width", 0) > 0
        and e.get("height", 0) > 0
    ]
    if _is_zone_shape(container, all_shapes):
        return []

    cx, cy, cw, ch = container["x"], container["y"], container["width"], container["height"]
    geom_texts = []
    for e in els:
        if e.get("type") == "text" and not e.get("containerId"):
            tx, ty, tw, th = e.get("x", 0), e.get("y", 0), e.get("width", 0), e.get("height", 0)
            if tx >= cx - 1 and ty >= cy - 1 and tx + tw <= cx + cw + 1 and ty + th <= cy + ch + 1:
                # Check innermost container: does another non-zone shape inside `container` contain `e`?
                nested = False
                for other in all_shapes:
                    if other is not container and not _is_zone_shape(other, all_shapes):
                        ox, oy, ow, oh = other["x"], other["y"], other["width"], other["height"]
                        if ox >= cx and oy >= cy and ox + ow <= cx + cw and oy + oh <= cy + ch:
                            if (
                                tx >= ox - 1
                                and ty >= oy - 1
                                and tx + tw <= ox + ow + 1
                                and ty + th <= oy + oh + 1
                            ):
                                nested = True
                                break
                if not nested:
                    geom_texts.append(e)
    return geom_texts


def _element_fingerprint(e):
    points = tuple(tuple(p) for p in e.get("points", [])) if e.get("points") else None
    return (
        e.get("x"),
        e.get("y"),
        e.get("width"),
        e.get("height"),
        e.get("angle"),
        e.get("index"),
        points,
        e.get("text"),
        e.get("originalText"),
        e.get("isDeleted"),
    )


def _restack_container_texts(container, texts, gap=5.0):
    """Restacks texts inside container vertically. Returns list of restacked text elements or raises ValueError."""
    if len(texts) < 2:
        return texts

    sorted_texts = sorted(texts, key=lambda t: (t.get("y", 0), t.get("index", "")))

    total_text_height = sum(t.get("height", 0) for t in sorted_texts) + gap * (
        len(sorted_texts) - 1
    )
    ch = container.get("height", 0)
    cy = container.get("y", 0)

    if total_text_height > ch:
        raise ValueError(
            f"total text height ({total_text_height:.1f}px) overflows container {container['id']!r} height ({ch:.1f}px)"
        )

    start_y = cy + (ch - total_text_height) / 2.0
    curr_y = start_y

    for t in sorted_texts:
        t["y"] = curr_y
        curr_y += t.get("height", 0) + gap

    return sorted_texts


def cmd_restack(doc_path, args):
    gap = 5.0
    target_id = None

    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--gap":
            if idx + 1 >= len(args):
                sys.exit("--gap requires a numeric value")
            gap = float(args[idx + 1])
            idx += 2
        elif not arg.startswith("--"):
            target_id = arg
            idx += 1
        else:
            sys.exit(f"unrecognised option: {arg}")

    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    els = doc.get("elements", [])
    live_els = live_elements(doc)
    by_id = {e["id"]: e for e in live_els}

    containers_to_restack = []

    if target_id:
        if target_id not in by_id:
            sys.exit(f"element id {target_id!r} not found in {doc_path}")
        target = by_id[target_id]
        if target.get("type") == "text":
            cid = target.get("containerId")
            if cid and cid in by_id:
                containers_to_restack.append(by_id[cid])
            else:
                all_shapes = [
                    e
                    for e in live_els
                    if e.get("type") in ("rectangle", "diamond", "ellipse")
                    and e.get("width", 0) > 0
                    and e.get("height", 0) > 0
                ]
                matching_containers = [
                    s for s in all_shapes if target in get_card_texts(s, live_els, by_id)
                ]
                if matching_containers:
                    containers_to_restack.append(matching_containers[0])
                else:
                    sys.exit(f"cannot determine container for text element {target_id!r}")
        else:
            containers_to_restack.append(target)
    else:
        all_shapes = [
            e
            for e in live_els
            if e.get("type") in ("rectangle", "diamond", "ellipse")
            and e.get("width", 0) > 0
            and e.get("height", 0) > 0
        ]
        for s in all_shapes:
            card_texts = get_card_texts(s, live_els, by_id)
            if len(card_texts) >= 2:
                containers_to_restack.append(s)

    if not containers_to_restack:
        if target_id:
            sys.exit(f"cannot determine text membership or no container for {target_id!r}")
        else:
            print("OK: no multi-text containers found to restack")
            return

    # Fail-closed fingerprinting before mutation
    fp_before = {e["id"]: _element_fingerprint(e) for e in els}

    restacked_any = False
    restacked_text_ids = set()

    for container in containers_to_restack:
        card_texts = get_card_texts(container, live_els, by_id)
        if len(card_texts) < 2:
            if target_id:
                sys.exit(f"container {container['id']!r} has fewer than 2 text elements to restack")
            continue

        try:
            _restack_container_texts(container, card_texts, gap=gap)
        except ValueError as err:
            sys.exit(f"restack failed: {err}")

        for t in card_texts:
            restacked_text_ids.add(t["id"])
        restacked_any = True
        print(f"Restacked {len(card_texts)} text element(s) in container {container['id']!r}")

    # Verify fail-closed invariants: no other elements modified
    fp_after = {e["id"]: _element_fingerprint(e) for e in els}
    for eid, fp_b in fp_before.items():
        fp_a = fp_after[eid]
        if eid not in restacked_text_ids:
            if fp_b != fp_a:
                sys.exit(f"invariant violation: non-restacked element {eid!r} was mutated")
        else:
            # For restacked text elements, check that only (x, y) changed, nothing else
            if fp_b[2:] != fp_a[2:]:
                sys.exit(
                    f"invariant violation: immutable properties of restacked text {eid!r} were mutated"
                )

    if restacked_any:
        with open(doc_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)


def cmd_fit(doc_path, args):
    if len(args) < 2:
        sys.exit('fit mode requires: <id> "<new text>"')
    target_id, new_text = args[0], args[1]

    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    els = doc.get("elements", [])
    by_id = {e["id"]: e for e in els if not e.get("isDeleted")}

    if target_id not in by_id:
        sys.exit(f"element id {target_id!r} not found in {doc_path}")

    target = by_id[target_id]
    text_elem = None
    container_elem = None

    if target.get("type") == "text":
        text_elem = target
        cid = text_elem.get("containerId")
        if cid and cid in by_id:
            container_elem = by_id[cid]
    else:
        container_elem = target
        # Find bound text
        for b in container_elem.get("boundElements") or []:
            if b.get("type") == "text" and b["id"] in by_id:
                text_elem = by_id[b["id"]]
                break
        if not text_elem:
            # Search fallback
            for e in els:
                if (
                    not e.get("isDeleted")
                    and e.get("type") == "text"
                    and e.get("containerId") == container_elem["id"]
                ):
                    text_elem = e
                    break

    if not text_elem:
        sys.exit(f"no text element associated with id {target_id!r}")

    # A divergence here means an earlier writer set one layer only, so this
    # element currently holds two different readings and the one on screen is
    # not necessarily the one that will survive. Say so before overwriting both.
    if "originalText" in text_elem:
        old_t = text_elem.get("text", "")
        old_o = text_elem.get("originalText", "")
        if old_t.split() != old_o.split():
            print(
                f"WARNING: {text_elem['id']!r} carried two different text layers before this "
                f"edit; both are being replaced.\n"
                f"  text (was):         {old_t!r}\n"
                f"  originalText (was): {old_o!r}",
                file=sys.stderr,
            )

    lines = new_text.split("\n")
    font_size = text_elem.get("fontSize", 20)
    max_len = max((len(line) for line in lines), default=0)
    num_lines = max(len(lines), 1)

    # Calculate estimated bounding box
    text_width = max(10.0, max_len * font_size * 0.56)
    text_height = max(10.0, num_lines * font_size * 1.25)

    # Both layers, always. `text` is the wrapped copy Excalidraw paints;
    # `originalText` is the unwrapped source it re-wraps from. Write `text`
    # alone and the next time the editor lays the element out it regenerates
    # `text` from the stale `originalText` and the edit is silently gone.
    text_elem["text"] = new_text
    if "originalText" in text_elem or text_elem.get("containerId"):
        text_elem["originalText"] = new_text

    if container_elem:
        cx = container_elem["x"] + container_elem["width"] / 2.0
        cy = container_elem["y"] + container_elem["height"] / 2.0

        pad_x = 40.0
        pad_y = 30.0
        new_cw = max(container_elem["width"], text_width + pad_x)
        new_ch = max(container_elem["height"], text_height + pad_y)

        container_elem["x"] = cx - new_cw / 2.0
        container_elem["y"] = cy - new_ch / 2.0
        container_elem["width"] = new_cw
        container_elem["height"] = new_ch

        text_elem["x"] = cx - text_width / 2.0
        text_elem["y"] = cy - text_height / 2.0
        text_elem["width"] = text_width
        text_elem["height"] = text_height

        print(
            f"Resized text {text_elem['id']!r} ({text_width:.1f}x{text_height:.1f}) and container {container_elem['id']!r} centered to {new_cw:.1f}x{new_ch:.1f}"
        )
    else:
        cx = text_elem["x"] + text_elem["width"] / 2.0
        cy = text_elem["y"] + text_elem["height"] / 2.0

        text_elem["width"] = text_width
        text_elem["height"] = text_height
        text_elem["x"] = cx - text_width / 2.0
        text_elem["y"] = cy - text_height / 2.0

        print(
            f"Resized standalone text {text_elem['id']!r} centered to {text_width:.1f}x{text_height:.1f}"
        )

    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def load_baseline(baseline_spec, doc_path):
    """Load baseline collision pairs from a file path or inline spec.

    Returns a set of frozenset({id1, id2}).
    """
    pairs = set()
    if not baseline_spec:
        p = Path(doc_path)
        candidates = [
            p.with_suffix(".baseline.json"),
            p.with_name(p.stem + ".baseline.json"),
            p.with_suffix(".baseline"),
            p.with_name(p.name + ".baseline"),
        ]
        for c in candidates:
            if c.exists():
                baseline_spec = str(c)
                break

    if not baseline_spec:
        return pairs

    path = Path(baseline_spec)
    if path.is_file():
        content = path.read_text(encoding="utf-8").strip()
        if content.startswith("{") or content.startswith("["):
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, list) and len(item) >= 2:
                            pairs.add(frozenset({str(item[0]), str(item[1])}))
                        elif isinstance(item, dict):
                            pair = item.get("pair") or item.get("elements")
                            if pair and len(pair) >= 2:
                                pairs.add(frozenset({str(pair[0]), str(pair[1])}))
                elif isinstance(data, dict):
                    colls = data.get("collisions") or data.get("baseline") or []
                    for item in colls:
                        if isinstance(item, list) and len(item) >= 2:
                            pairs.add(frozenset({str(item[0]), str(item[1])}))
                return pairs
            except json.JSONDecodeError:
                pass

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.replace(":", " ").replace(",", " ").split() if p]
            if len(parts) >= 2:
                pairs.add(frozenset({parts[0], parts[1]}))
        return pairs

    for item in baseline_spec.split(","):
        parts = [p for p in item.replace(":", " ").replace(";", " ").split() if p]
        if len(parts) >= 2:
            pairs.add(frozenset({parts[0], parts[1]}))
    return pairs


def cmd_overlap(doc_path, args=None):
    args = args or []
    baseline_spec = None
    if "--baseline" in args:
        idx = args.index("--baseline")
        if idx + 1 >= len(args):
            sys.exit("--baseline requires a file path or inline collision pair string")
        baseline_spec = args[idx + 1]

    baseline_pairs = load_baseline(baseline_spec, doc_path)

    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    els = live_elements(doc)
    by_id = {e["id"]: e for e in els}

    # Identify nested pairs (container-text, frame-children)
    nested_pairs = set()
    for e in els:
        if e.get("type") == "text" and e.get("containerId"):
            cid = e["containerId"]
            nested_pairs.add((e["id"], cid))
            nested_pairs.add((cid, e["id"]))
        for b in e.get("boundElements") or []:
            nested_pairs.add((e["id"], b["id"]))
            nested_pairs.add((b["id"], e["id"]))
        if e.get("frameId"):
            fid = e["frameId"]
            nested_pairs.add((e["id"], fid))
            nested_pairs.add((fid, e["id"]))

    # Filter all 2D elements: shapes and text boxes (ignore arrows and lines)
    # Container-bound text is included so sibling texts in the same container are checked,
    # while the text-container pair is excluded via nested_pairs.
    shapes = [
        e
        for e in els
        if e.get("type") not in ("arrow", "line")
        and e.get("width", 0) > 0
        and e.get("height", 0) > 0
    ]

    collisions = []
    for i in range(len(shapes)):
        e1 = shapes[i]
        x1, y1, w1, h1 = e1["x"], e1["y"], e1["width"], e1["height"]
        for j in range(i + 1, len(shapes)):
            e2 = shapes[j]
            if (e1["id"], e2["id"]) in nested_pairs:
                continue

            # If an element is a container-bound text and the other is a non-text shape,
            # the geometric check belongs to the container vs shape, so skip the redundant sub-pair.
            if (
                e1.get("type") == "text" and e1.get("containerId") and e2.get("type") != "text"
            ) or (e2.get("type") == "text" and e2.get("containerId") and e1.get("type") != "text"):
                continue

            x2, y2, w2, h2 = e2["x"], e2["y"], e2["width"], e2["height"]

            overlap_w = min(x1 + w1, x2 + w2) - max(x1, x2)
            overlap_h = min(y1 + h1, y2 + h2) - max(y1, y2)

            if overlap_w > 1.0 and overlap_h > 1.0:
                collisions.append((e1, e2, overlap_w, overlap_h))

    active_collisions = []
    baselined_count = 0
    for e1, e2, ow, oh in collisions:
        pair = frozenset({e1["id"], e2["id"]})
        if pair in baseline_pairs:
            baselined_count += 1
        else:
            active_collisions.append((e1, e2, ow, oh))

    if active_collisions:
        msg_suffix = f" ({baselined_count} baselined ignored)" if baselined_count > 0 else ""
        print(f"FAIL: {len(active_collisions)} AABB collision(s) detected{msg_suffix}:")
        for e1, e2, ow, oh in active_collisions:
            lbl1 = get_label(e1, by_id) or e1["id"]
            lbl2 = get_label(e2, by_id) or e2["id"]
            print(
                f"  - [{e1['type']} {e1['id']}] ({lbl1!r}) overlaps [{e2['type']} {e2['id']}] ({lbl2!r}) by {ow:.1f}x{oh:.1f} px"
            )
        sys.exit(1)
    else:
        if baselined_count > 0:
            print(
                f"OK: no un-baselined overlapping non-nested sibling elements found ({baselined_count} intentional collision(s) ignored)"
            )
        else:
            print("OK: no overlapping non-nested sibling elements found")


def _point_in_rect(px, py, x, y, w, h):
    return x <= px <= x + w and y <= py <= y + h


def _seg_seg_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def _segment_intersects_rect(p0, p1, x, y, w, h):
    if _point_in_rect(p0[0], p0[1], x, y, w, h) or _point_in_rect(p1[0], p1[1], x, y, w, h):
        return True
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    return any(_seg_seg_intersect(p0, p1, e0, e1) for e0, e1 in edges)


def cmd_arrows(doc_path):
    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    els = live_elements(doc)
    by_id = {e["id"]: e for e in els}

    all_shapes = [
        e
        for e in els
        if e.get("type") in ("rectangle", "diamond", "ellipse")
        and e.get("width", 0) > 0
        and e.get("height", 0) > 0
    ]

    # A background zone (large group-label rectangle a dozen real boxes sit
    # inside) is not an obstacle an arrow must route around — it is scenery,
    # the same way `overlap` treats a frame's own children as nested rather
    # than colliding. There is no frameId for this diagram's zone rectangles,
    # so detect it structurally instead: a shape that fully contains several
    # other shapes is a background, not a node an arrow can meaningfully cut
    # "through". Real nodes never contain other real nodes here.
    def _fully_contains(outer, inner):
        if outer is inner:
            return False
        ox, oy, ow, oh = outer["x"], outer["y"], outer["width"], outer["height"]
        ix, iy, iw, ih = inner["x"], inner["y"], inner["width"], inner["height"]
        return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh

    obstacles = [
        s for s in all_shapes if sum(1 for other in all_shapes if _fully_contains(s, other)) < 3
    ]
    arrows = [e for e in els if e.get("type") == "arrow"]

    crossings = []
    for arrow in arrows:
        points = arrow.get("points", [])
        if len(points) < 2:
            continue
        ax_, ay_ = arrow.get("x", 0), arrow.get("y", 0)
        abs_pts = [(ax_ + p[0], ay_ + p[1]) for p in points]
        endpoint_ids = {
            (arrow.get("startBinding") or {}).get("elementId"),
            (arrow.get("endBinding") or {}).get("elementId"),
        }
        for shape in obstacles:
            if shape["id"] in endpoint_ids:
                continue
            x, y, w, h = shape["x"], shape["y"], shape["width"], shape["height"]
            for i in range(len(abs_pts) - 1):
                if _segment_intersects_rect(abs_pts[i], abs_pts[i + 1], x, y, w, h):
                    crossings.append((arrow, shape))
                    break

    if crossings:
        print(f"FAIL: {len(crossings)} arrow/box crossing(s) detected:")
        for arrow, shape in crossings:
            alabel = get_label(arrow, by_id) or arrow["id"]
            slabel = get_label(shape, by_id) or shape["id"]
            print(
                f"  - arrow [{arrow['id']}] ({alabel!r}) cuts through "
                f"[{shape['type']} {shape['id']}] ({slabel!r}) it is not bound to"
            )
        sys.exit(1)
    else:
        print("OK: no arrow crosses an unrelated shape's interior")


def cmd_render(doc_path, args):
    try:
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit(
            "render mode requires matplotlib ('uv run --with matplotlib script.py' or install matplotlib)"
        )

    rest = list(args)
    region = None
    if "--region" in rest:
        idx = rest.index("--region")
        if idx + 1 >= len(rest):
            sys.exit("--region requires X0,Y0,X1,Y1")
        x0, y0, x1, y1 = (float(v) for v in rest[idx + 1].split(","))
        region = (x0, y0, x1, y1)
        del rest[idx : idx + 2]

    out_path = rest[0] if rest else str(Path(doc_path).with_suffix(".png"))

    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    els = live_elements(doc)

    if not els:
        sys.exit("No elements to render")

    if region:
        rx0, ry0, rx1, ry1 = region

        def _in_region(e):
            ex, ey = e.get("x", 0), e.get("y", 0)
            ew, eh = e.get("width", 0), e.get("height", 0)
            if e.get("type") == "arrow":
                pts = e.get("points", [])
                if not pts:
                    return False
                abs_x = [ex + p[0] for p in pts]
                abs_y = [ey + p[1] for p in pts]
                ex, ey, ew, eh = (
                    min(abs_x),
                    min(abs_y),
                    max(abs_x) - min(abs_x),
                    max(abs_y) - min(abs_y),
                )
            return not (ex + ew < rx0 or ex > rx1 or ey + eh < ry0 or ey > ry1)

        els = [e for e in els if _in_region(e)]
        if not els:
            sys.exit(f"No elements intersect region {region}")

    fig, ax = plt.subplots(figsize=(14, 10))

    # Crucial: Excalidraw y grows downward; matplotlib y grows upward by default
    ax.invert_yaxis()

    for e in els:
        etype = e.get("type")
        x, y = e.get("x", 0), e.get("y", 0)
        w, h = e.get("width", 0), e.get("height", 0)
        bg = e.get("backgroundColor", "#ffffff")
        if bg == "transparent" or not bg:
            bg = "#ffffff"

        if etype in ("rectangle", "diamond", "ellipse"):
            rect = patches.Rectangle(
                (x, y), w, h, linewidth=1, edgecolor="#404040", facecolor=bg, alpha=0.5
            )
            ax.add_patch(rect)
        elif etype == "text":
            txt = element_text(e)
            ax.text(x, y, txt, fontsize=8, verticalalignment="top", color="#1a1a1a", wrap=True)
        elif etype == "arrow":
            points = e.get("points", [])
            if len(points) >= 2:
                px = [x + p[0] for p in points]
                py = [y + p[1] for p in points]
                ax.plot(px, py, color="#404040", linewidth=1.5, linestyle="--")
                ax.annotate(
                    "",
                    xy=(px[-1], py[-1]),
                    xytext=(px[-2], py[-2]),
                    arrowprops=dict(arrowstyle="->", color="#404040", lw=1.5),
                )

    if region:
        rx0, ry0, rx1, ry1 = region
        ax.set_xlim(rx0, rx1)
        ax.set_ylim(ry1, ry0)  # inverted: Excalidraw y grows downward
    else:
        ax.autoscale_view()
    ax.set_title(f"Excalidraw Render: {Path(doc_path).name}")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Rendered diagram to {out_path}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)

    doc_path = sys.argv[1]
    mode = sys.argv[2]
    args = sys.argv[3:]

    if mode == "fit":
        cmd_fit(doc_path, args)
    elif mode == "restack":
        cmd_restack(doc_path, args)
    elif mode == "overlap":
        cmd_overlap(doc_path, args)
    elif mode == "arrows":
        cmd_arrows(doc_path)
    elif mode == "render":
        cmd_render(doc_path, args)
    else:
        sys.exit(f"unknown mode {mode!r}; expected fit, restack, overlap, arrows, or render")


if __name__ == "__main__":
    main()
