#!/usr/bin/env python3
"""Pretty task viewer: paginated, color, minimal fields.

Usage:
    python3 scripts/task_view.py [page] [--sort=priority|date|due] [--per-page=N]

Defaults:
    page=1, sort=priority (ascending int), per-page=10
    --sort=date uses created desc
    --sort=due uses due asc (None last)
"""
from __future__ import annotations
import sys, json, shutil
from pathlib import Path
from datetime import datetime, timezone
# Base data directory (relative to this script): ../data

ROOT = Path(__file__).resolve().parents[2]  # parent repo root
DATA_DIR = ROOT / "data"
# -------- args --------
page = 1
sort = "priority"
per_page = 10
for arg in sys.argv[1:]:
    if arg.startswith("--sort="):
        sort = arg.split("=", 1)[1].strip()
    elif arg.startswith("--per-page="):
        try:
            per_page = max(1, int(arg.split("=", 1)[1]))
        except Exception:
            pass
    else:
        try:
            page = max(1, int(arg))
        except Exception:
            pass

# -------- rebuild view inline --------
def load_task(path: Path):
    try:
        with path.open() as f:
            t = json.load(f)
            t['_filename'] = path.name
            return t
    except Exception as e:
        print(json.dumps({'error':'load_failed','file':path.name,'detail':str(e)}), file=sys.stderr)
        return None

def sort_key(t):
    pri = t.get('priority')
    if pri is None: pri = 9999
    return (pri, t.get('due') or '9999', t.get('created') or '9999')

def rebuild():
    """Rebuild data/views/current.json from tasks/inbox
    Sorted by priority (null last), due, created.
    """
    inbox = DATA_DIR / 'tasks/inbox'
    queue = DATA_DIR / 'tasks/queue'
    archived = DATA_DIR / 'tasks/archived'
    cand_paths = []
    if inbox.exists():
        cand_paths.extend(inbox.glob('*.json'))
    if queue.exists():
        cand_paths.extend(queue.glob('*.json'))
    tasks = []
    for p in cand_paths:
        t = load_task(p)
        if not t:
            continue
        # Skip archived tasks regardless of folder if marked
        if t.get('archived_at'):
            continue
        # Also skip anything inside archived folder for safety
        if archived.exists() and p.parent.resolve() == archived.resolve():
            continue
        tasks.append(t)
    tasks.sort(key=sort_key)

    view = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'task_count': len(tasks),
        'tasks': tasks
    }
    out_path = DATA_DIR / 'views/current.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(view, indent=2, default=str))
    return view

data = rebuild()
tasks = data.get("tasks", [])

    # index already applied in rebuild

def parse_iso(ts: str):
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        s = str(ts)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

# -------- sort --------
def due_key(t):
    d = parse_iso(t.get("due"))
    return (d is None, d or datetime.max.replace(tzinfo=timezone.utc), t.get("priority") if isinstance(t.get("priority"), int) else 9999)

def prio_key(t):
    p = t.get("priority")
    if not isinstance(p, int):
        p = 9999
    # tie-breakers: due asc, created asc
    d = parse_iso(t.get("due")) or datetime.max.replace(tzinfo=timezone.utc)
    c = parse_iso(t.get("created")) or datetime.max.replace(tzinfo=timezone.utc)
    return (p, d, c)

def created_key(t):
    c = parse_iso(t.get("created")) or datetime.min.replace(tzinfo=timezone.utc)
    return c

if sort == "priority":
    tasks_sorted = sorted(tasks, key=prio_key)
elif sort == "date":
    # created desc
    tasks_sorted = sorted(tasks, key=created_key, reverse=True)
elif sort == "due":
    # due asc (None last)
    tasks_sorted = sorted(tasks, key=due_key)
else:
    tasks_sorted = tasks

total = len(tasks_sorted)
start = (page - 1) * per_page
end = min(start + per_page, total)
if start >= total and total > 0:
    # clamp to last page
    last_page = (total - 1) // per_page + 1
    page = last_page
    start = (page - 1) * per_page
    end = min(start + per_page, total)

# Assign index after full sort and pagination basis (1-based across full list)
for i, t in enumerate(tasks_sorted, start=1):
    t["index"] = i
subset = tasks_sorted[start:end]

# -------- formatting --------
term_width = shutil.get_terminal_size((100, 20)).columns
def color(s, code): return f"\033[{code}m{s}\033[0m"
BOLD="1"; DIM="2"; RED="31"; YELLOW="33"; GREEN="32"; CYAN="36"; GREY="90"

def prio_color(p):
    if p == 1: return RED
    if p == 2: return YELLOW
    if p == 3: return GREEN
    return GREY

def fmt_date(ts):
    dt = parse_iso(ts)
    return dt.strftime("%Y-%m-%d") if dt else "—"

def clip(text, width):
    if text is None: return ""
    s = str(text).replace("\n", " ").strip()
    return s if len(s) <= width else s[:max(0, width-1)] + "…"

generated = data.get("generated", "")
# concise header focused on controls; drop verbose timestamp
header = f"Tasks: {total} • Page {page}/{max(1,(total-1)//per_page+1)} • sort={sort}"
print(color(header, BOLD))

if not subset:
    print(color("No tasks to show.", GREY))
    sys.exit(0)

# layout: [#.] [P#] [⏰ +3d] — Title with inline tags
# make columns compact and compute dynamic widths for nicer wrapping
idx_col = max(3, len(str(total)) + 1)  # e.g., " 12."
prio_col = 3                           # e.g., "P1" (plus a space in print)
due_col = 7                            # space for "⏰ +3d" (or blank)
padding = 2
title_w = max(20, term_width - (idx_col + 1 + prio_col + 1 + due_col + 3 + padding))

def due_delta_str(ts):
    """Return a short relative due string like -2d, +3d (negative means overdue)."""
    d = parse_iso(ts)
    if not d:
        return ""
    now = datetime.now(timezone.utc)
    # normalize to days
    delta_days = int((d.date() - now.date()).days)
    if delta_days == 0:
        return "0d"
    sign = "-" if delta_days < 0 else "+"
    return f"{sign}{abs(delta_days)}d"

def urgency_level(t):
    """Return an integer urgency bucket 3 (high) to 1 (low) used to vary height."""
    p = t.get("priority") if isinstance(t.get("priority"), int) else 999
    d = parse_iso(t.get("due"))
    days = None
    if d:
        days = (d.date() - datetime.now(timezone.utc).date()).days
    # high urgency if P1 or overdue/within 1 day
    if p == 1 or (days is not None and days <= 1):
        return 3
    # medium if P2 or due within a week
    if p == 2 or (days is not None and days <= 7):
        return 2
    return 1

def wrap_lines(text: str, width: int, max_lines: int):
    """Wrap text to width returning up to max_lines lines; preserve simple bullets."""
    import textwrap
    if not text:
        return []
    # Keep bullets by treating them as prefixes
    lines = []
    for raw in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        bullet = ""
        for b in ("- ", "* ", "• ", "– "):
            if raw.startswith(b):
                bullet = b
                raw = raw[len(b):]
                break
        wrapped = textwrap.wrap(raw, width=width, break_long_words=False, replace_whitespace=False)
        if not wrapped:
            continue
        if bullet:
            lines.append(bullet + wrapped[0])
            for cont in wrapped[1:]:
                lines.append("  " + cont)
        else:
            lines.extend(wrapped)
        if len(lines) >= max_lines:
            return lines[:max_lines]
    return lines[:max_lines]

def wrap_title(text: str, first_width: int, next_width: int, max_lines: int):
    """Wrap a single-line title allowing a different width for the first line.
    No hard word breaking; conservative and fast.
    """
    if not text:
        return [""]
    words = str(text).strip().split()
    lines = []
    current = ""
    width = max(8, first_width)
    for w in words:
        if not current:
            if len(w) <= width:
                current = w
            else:
                # long token: clip to width
                current = w[:max(1, width-1)] + "…"
        else:
            if len(current) + 1 + len(w) <= width:
                current += " " + w
            else:
                lines.append(current)
                if len(lines) >= max_lines:
                    return lines
                width = max(8, next_width)
                current = w if len(w) <= width else (w[:max(1, width-1)] + "…")
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]

for t in subset:
    idx = t.get("index", 0)
    p = t.get("priority", None)
    due = t.get("due", None)
    title = t.get("title", "")
    project = t.get("project") or ""
    # Prefer new field names for description; fallbacks for older tasks
    summary = t.get("description") or t.get("summary") or t.get("preview") or ""
    classification = t.get("classification") or (t.get("metadata") or {}).get("classification")

    # Build columns
    idx_vis = f"{idx:>{idx_col-1}}."
    idx_str = color(idx_vis, BOLD)
    # compact priority indicator with leading P
    p_char = f"P{p}" if isinstance(p, int) else "P–"
    p_str = color(p_char, prio_color(p if isinstance(p,int) else 999))
    # relative due string only
    rel = due_delta_str(due)
    rel_text = f"⏰ {rel}" if rel else ""
    rel_vis = rel_text.rjust(due_col)
    # color relative by urgency similar to absolute
    d_parsed = parse_iso(due)
    due_color = CYAN
    if d_parsed:
        today = datetime.now(timezone.utc).date()
        if d_parsed.date() < today:
            due_color = RED
        elif d_parsed.date() == today:
            due_color = YELLOW
    due_str = color(rel_vis, due_color)

    # compute indentation for wrapped lines
    # space for index + space + prio + space + rel + space # + '—' + space
    left_pad = " " * (idx_col + 1 + prio_col + 1 + padding)

    # Title wrapping varies by urgency
    lvl = urgency_level(t)
    max_title_lines = 3 if lvl >= 3 else (2 if lvl == 2 else 1)
    # Inline category tags before title (classification then project)
    prefix_bits_plain = []
    if classification:
        prefix_bits_plain.append(f"[{classification}]")
    if project:
        prefix_bits_plain.append(f"[{project}]")
    prefix_plain = " ".join(prefix_bits_plain)
    prefix_len = len(prefix_plain) + (1 if prefix_plain else 0)
    prefix_colored = color(prefix_plain + (" " if prefix_plain else ""), DIM) if prefix_plain else ""

    # Wrap title considering reduced first-line width due to prefix
    first_w = max(8, title_w - prefix_len)
    title_lines = wrap_title(title, first_width=first_w, next_width=title_w, max_lines=max_title_lines)
    if not title_lines:
        title_lines = [""]

    # First line: columns + prefix + first title line
    print(f"{idx_str} {p_str} {due_str}  —  {prefix_colored}{color(title_lines[0], BOLD)}")
    
    # Continuation of wrapped title (aligned under the title start)
    cont_pad = left_pad + (" " * (prefix_len))
    for cont in title_lines[1:]:
        print(cont_pad + color(cont, BOLD))

    # Summary lines, deduplicated against title
    if summary:
        # allocate summary height by urgency
        max_summary = 5 if lvl >= 3 else (4 if lvl == 2 else 3)
        # width from the divider alignment
        sum_w = max(10, term_width - (idx_col + 1 + prio_col + 1 + due_col + 3 + padding))
        raw_lines = str(summary).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # drop lines that duplicate title text
        title_lc = " ".join(title_lines).lower().strip()
        cleaned = []
        for line in raw_lines:
            s = line.strip()
            if not s:
                continue
            if s.lower() in title_lc:
                continue
            cleaned.append(s)
            if len(cleaned) >= max_summary:
                break
        if cleaned:
            for line in wrap_lines("\n".join(cleaned), width=sum_w, max_lines=max_summary):
                print(left_pad + color(line, DIM))

print(color(f"Showing {start+1}-{end} of {total}. Use: page N, --per-page=N, --sort=priority|date|due", GREY))