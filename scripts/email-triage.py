#!/usr/bin/env python3
"""
Single-step Email Triage script.

Capabilities:
- Fetch next unseen Outlook email using PowerShell (scripts/outlook-read.ps1), or accept --file <raw.json> for testing.
- Analyze locally to produce: classification (Action|Waiting|Reference|Optional|Noise), priority (High|Medium|Low), and a ≤12 line summary.
- Create a task JSON in the existing schema and store it in data/tasks/inbox (for Action/Waiting) or data/tasks/queue (others).
- Persist minimal processed metadata in data/emails/processed/<id>.json.

Notes:
- On Linux, PowerShell may be unavailable. Use --file for testing if PowerShell is not installed.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from logging import getLogger
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]  # repo root
SCRIPTS_DIR = ROOT / "scripts"
WORK_BASE = ROOT / "data" / "emails" / "work"
PROCESSED_DIR = ROOT / "data" / "emails" / "processed"
TASKS_INBOX = ROOT / "data" / "tasks" / "inbox"
TASKS_QUEUE = ROOT / "data" / "tasks" / "queue"
TASKS_ARCHIVED = ROOT / "data" / "tasks" / "archived"

# Default timeouts (seconds) with env overrides
PS_LIST_TIMEOUT = int(os.environ.get("TRIAGE_PS_LIST_TIMEOUT", "12"))
PS_FETCH_TIMEOUT = int(os.environ.get("TRIAGE_PS_FETCH_TIMEOUT", "20"))
LLM_TIMEOUT = int(os.environ.get("TRIAGE_LLM_TIMEOUT", "45"))


def find_powershell() -> str | None:
    # Try common PowerShell executables
    for exe in ["powershell.exe", "pwsh", "powershell"]:
        try:
            subprocess.run([exe, "-NoLogo", "-Command", "$PSVersionTable.PSVersion"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return exe
        except FileNotFoundError:
            continue
    return None


def json_load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Invalid JSON in {path}: {e}")


def json_dump(obj: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def task_id() -> str:
    """Generate a compact, date-scoped id: YYYYMMDD-<8hex>.

    Note: Removed time and host components to simplify filenames. Collisions
    are avoided via the short GUID component.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    try:
        import uuid
        u = uuid.uuid4().hex[:8]
    except Exception:
        u = f"{int(time.time()*1000)%0xffffffff:08x}"
    return f"{ts}-{u}"


# ---------------- Progress / Logging -----------------

def setup_logging(level: str = "INFO", use_color: bool = True):
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(lvl)
    # Try coloredlogs; else basicConfig
    try:
        if use_color:
            import coloredlogs  # type: ignore

            coloredlogs.install(level=lvl, fmt="%(asctime)s %(levelname)s %(message)s")
            return
    except Exception:
        pass
    # Fallback
    if not logger.handlers:
        logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


class ProgressUI:
    """Compact progress/status bar. Modes: rich, plain, none.

    Use begin()/done()/fail(). When mode is 'rich', shows an animated spinner and bar.
    In 'plain', prints compact step lines. In 'none', does nothing.
    """

    def __init__(self, mode: str = "auto", total: int = 6):
        self.total = total
        self.completed = 0
        self.current_label = ""
        self.mode = self._decide_mode(mode)
        self._rich_progress = None
        self._rich_task_id = None
        if self.mode == "rich":
            try:
                from rich.console import Console  # type: ignore
                from rich.progress import (
                    Progress,
                    SpinnerColumn,
                    TextColumn,
                    BarColumn,
                    MofNCompleteColumn,
                    TimeElapsedColumn,
                )  # type: ignore

                console = Console(stderr=True)
                self._rich_progress = Progress(
                    SpinnerColumn(style="cyan"),
                    TextColumn("{task.description}"),
                    BarColumn(bar_width=None),
                    MofNCompleteColumn(),
                    TimeElapsedColumn(),
                    transient=True,
                    console=console,
                )
                self._rich_progress.start()
                self._rich_task_id = self._rich_progress.add_task("Starting…", total=total)
            except Exception:
                self.mode = "plain"

    def _decide_mode(self, mode: str) -> str:
        if mode == "none":
            return "none"
        if mode == "plain":
            return "plain"
        if mode == "rich":
            return "rich"
        # auto
        try:
            import sys

            is_tty = sys.stderr.isatty() or sys.stdout.isatty()
            if is_tty:
                import rich  # noqa: F401

                return "rich"
        except Exception:
            pass
        return "plain"

    def begin(self, label: str):
        self.current_label = label
        if self.mode == "rich" and self._rich_progress is not None and self._rich_task_id is not None:
            self._rich_progress.update(self._rich_task_id, description=label)
        elif self.mode == "plain":
            sys.stderr.write(f"[ {self.completed}/{self.total} ] {label}…\r")
            sys.stderr.flush()

    def done(self, done_label: str | None = None):
        self.completed += 1
        label = done_label or self.current_label
        if self.mode == "rich" and self._rich_progress is not None and self._rich_task_id is not None:
            self._rich_progress.update(self._rich_task_id, advance=1, description=f"{label} ✓")
        elif self.mode == "plain":
            sys.stderr.write(" " * 120 + "\r")
            sys.stderr.write(f"✔ [{self.completed}/{self.total}] {label}\n")
            sys.stderr.flush()

    def fail(self, msg: str):
        if self.mode == "rich" and self._rich_progress is not None and self._rich_task_id is not None:
            self._rich_progress.update(self._rich_task_id, description=f"Failed: {msg}")
        elif self.mode == "plain":
            sys.stderr.write(" " * 120 + "\r")
            sys.stderr.write(f"✖ {msg}\n")
            sys.stderr.flush()

    def close(self):
        if self.mode == "rich" and self._rich_progress is not None:
            try:
                # Finish bar
                if self._rich_task_id is not None:
                    remaining = max(0, self.total - self.completed)
                    if remaining:
                        self._rich_progress.update(self._rich_task_id, advance=remaining)
                self._rich_progress.stop()
            except Exception:
                pass


def clip(s: str | None, n: int) -> str:
    if not s:
        return ""
    s2 = re.sub(r"\s+", " ", str(s)).strip()
    return s2 if len(s2) <= n else s2[: max(0, n - 1)] + "\u2026"


def get_field(d: dict, *paths, default=None):
    for p in paths:
        try:
            # support simple dotted paths (one level)
            if isinstance(p, str) and "." in p:
                k1, k2 = p.split(".", 1)
                v = d.get(k1, {})
                if isinstance(v, dict) and k2 in v:
                    return v[k2]
            elif p in d and d[p] is not None:
                return d[p]
        except Exception:
            continue
    return default


def already_processed(email_id: str) -> bool:
    return (PROCESSED_DIR / f"{email_id}.json").exists()


def fetch_next_email_via_powershell(page_size=20, max_pages=10) -> dict | None:
    ps_exe = find_powershell()
    if not ps_exe:
        raise RuntimeError("PowerShell not found. Install PowerShell or run with --file to supply a raw email JSON.")
    ps1 = SCRIPTS_DIR / "outlook-read.ps1"
    if not ps1.exists():
        raise RuntimeError(f"PS1 not found: {ps1}")

    temp_dir = SCRIPTS_DIR / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for page in range(1, max_pages + 1):
        page_file = temp_dir / f"outlook_page_{page}.json"
        try:
            res = subprocess.run(
                [
                    ps_exe,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-PageSize",
                    str(page_size),
                    "-PageNumber",
                    str(page),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=PS_LIST_TIMEOUT,
            )
            page_file.write_text(res.stdout or "", encoding="utf-8")
            page_json = json.loads(res.stdout or "{}")
        except Exception:
            # skip this page on any error/timeout
            continue
        emails = page_json.get("emails") or []
        ids = [e.get("id") for e in emails if isinstance(e, dict) and e.get("id")]
        for eid in ids:
            if not already_processed(eid):
                full_file = temp_dir / f"email_{re.sub(r'[^A-Za-z0-9]', '_', eid)}.json"
                try:
                    res_full = subprocess.run(
                        [
                            ps_exe,
                            "-NoProfile",
                            "-NonInteractive",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(ps1),
                            "-GetEmailById",
                            str(eid),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=PS_FETCH_TIMEOUT,
                    )
                    full_file.write_text(res_full.stdout or "", encoding="utf-8")
                    if res_full.returncode == 0 and res_full.stdout:
                        try:
                            return json.loads(res_full.stdout)
                        except Exception:
                            # fall through to try next id
                            pass
                except Exception:
                    # Timeout or other error; try next id
                    continue
    return None


class TriageResult(BaseModel):
    classification: str = Field(description="One of: Action, Waiting, Reference, Optional, Noise")
    abstract: Optional[str] = None
    summary: Optional[str] = None
    analysis: Optional[str] = None
    requires_reply: Optional[bool] = None
    action_required: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = Field(default=None, description="High|Medium|Low")
    time_estimate: Optional[float] = None
    response_draft: Optional[str] = None
    reasoning: Optional[str] = None


def _read_prompt() -> str:
    analyzer_tpl = ROOT / "templates" / "email" / "triage.md"
    analyzer = analyzer_tpl.read_text(encoding="utf-8")
    return analyzer.strip()


def _collect_strategy_context(max_files: int = 12, max_chars: int = 2000) -> list[dict]:
    parts: list[dict] = []
    for folder in [ROOT / "data" / "goals", ROOT / "data" / "projects"]:
        if not folder.exists():
            continue
        for md in sorted(folder.glob("**/*.md"))[:max_files]:
            try:
                text = md.read_text(encoding="utf-8")[:max_chars]
                if text.strip():
                    # Each file as a separate part to help caching
                    parts.append({"text": f"# {md.name}\n\n" + text})
            except Exception:
                continue
    return parts


def analyze_email_llm(raw: dict, llm_timeout: int | None = None) -> TriageResult:
    from google import genai

    client = genai.Client()  # Uses ADC by default
    # Model selection: prefer fast model for triage
    model_name = (
        os.environ.get("TRIAGE_FAST_MODEL")
        or os.environ.get("FAST_MODEL")
        or os.environ.get("TRIAGE_MODEL")
        or "gemini-2.5-flash"
    )

    # Collect strategy context (inline limited excerpts)
    context_parts = _collect_strategy_context()

    subject = get_field(raw, "subject", "Subject", default="(no subject)") or ""
    sender_email = get_field(raw, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender", default="") or ""
    sender_name = get_field(raw, "senderName", "FromName", default="") or ""
    to_field = get_field(raw, "to", "To", default="")
    cc_field = get_field(raw, "cc", "Cc", default="")
    body_preview = get_field(raw, "snippet", "preview", "bodyPreview", "BodyPreview", "textBody", "TextBody", "body", "Body", default="")
    attachments = [a.get("fileName") or a.get("name") for a in (raw.get("attachments") or []) if isinstance(a, dict)]

    # Extract a cleaned body excerpt for analysis (strip quoted replies if possible)
    def _clean_body_for_analysis() -> str:
        raw_body = get_field(
            raw,
            "textBody",
            "TextBody",
            "body",
            "Body",
            default=body_preview or "",
        ) or ""
        try:
            # Optional dependency: email_reply_parser
            from email_reply_parser import EmailReplyParser  # type: ignore

            cleaned = EmailReplyParser.parse_reply(str(raw_body))
        except Exception:
            cleaned = str(raw_body)
        # Keep payload small for fast model
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:4000]

    user_payload = {
        "email": {
            "subject": subject,
            "from": {"name": sender_name, "email": sender_email},
            "to": to_field,
            "cc": cc_field,
            "preview": body_preview,
            "body_excerpt": _clean_body_for_analysis(),
            "has_attachments": bool(attachments),
            "attachments": attachments,
        }
    }

    system_instruction = _read_prompt()
    # Build a single user message that includes instruction + limited context + email payload
    if context_parts:
        context_text = "\n\n".join([p.get("text", "") for p in context_parts if isinstance(p, dict)])
    else:
        context_text = ""
    user_text = (
        system_instruction
        + ("\n\n[CONTEXT]\n" + context_text if context_text else "")
        + "\n\n[EMAIL JSON]\n"
        + json.dumps(user_payload, ensure_ascii=False)
    )
    contents = [{"role": "user", "parts": [{"text": user_text}]}]

    # Optional request timeout to avoid hangs
    if llm_timeout is None:
        llm_timeout = LLM_TIMEOUT
    try:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=contents,
                request_options={"timeout": llm_timeout},
            )
        except TypeError:
            # Older SDKs may not accept request_options
            resp = client.models.generate_content(model=model_name, contents=contents)
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")

    # Helper to extract JSON from arbitrary text
    def _extract_json(txt: str) -> dict:
        if not txt:
            return {}
        # 1) direct parse
        try:
            return json.loads(txt)
        except Exception:
            pass
        # 2) fenced code block ```json ... ```
        m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", txt, re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        # 3) first { ... last } slice
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(txt[start : end + 1])
            except Exception:
                pass
        return {}

    # Parse structured JSON response (best-effort)
    result: Optional[TriageResult] = None
    try:
        # New SDK: response may expose .text
        txt = getattr(resp, "text", None) or getattr(resp, "output_text", None)
        if not txt and hasattr(resp, "candidates") and resp.candidates:
            parts = resp.candidates[0].content.parts if hasattr(resp.candidates[0], "content") else []
            # Concatenate any text parts
            buf = []
            for p in parts or []:
                val = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
                if val:
                    buf.append(val)
            txt = "\n".join(buf) if buf else None
        data = _extract_json(txt or "")
        result = TriageResult(**data)
    except Exception as e:
        raise RuntimeError(f"Failed to parse structured output: {e}")

    return result


def build_task_json(raw: dict, classification: str, prio_num: int, summary: str) -> dict:
    subject = get_field(raw, "subject", "Subject", default="(no subject)")
    sender_email = get_field(raw, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender", default=None)
    sender_name = get_field(raw, "senderName", "FromName", default=None)
    preview = clip(get_field(raw, "snippet", "preview", "bodyPreview", "BodyPreview", "textBody", "TextBody", "body", "Body", default=""), 160)
    email_id = get_field(raw, "id", "Id", default=None)

    t = {
        "id": task_id(),
        "priority": prio_num,
        "classification": classification,
        "type": "email_reply",
        "title": f"Email: {subject}",
        "preview": preview,
        "description": summary,
        "project": "",
        "created": iso_now(),
        "due": None,
        "source": {},
        "metadata": {
            "email_id": email_id,
            "sender": sender_email,
            "sender_name": sender_name,
        },
    }
    return t


def persist_processed(raw: dict, classification: str, priority_str: str, summary: str, analysis: str | None = None) -> Path:
    email_id = get_field(raw, "id", "Id")
    if not email_id:
        raise RuntimeError("Missing email id in raw object")

    # Keep the cleaned body for local search/reference
    def _clean_full_body() -> str:
        body = get_field(raw, "textBody", "TextBody", "body", "Body", default="") or ""
        try:
            from email_reply_parser import EmailReplyParser  # type: ignore

            cleaned = EmailReplyParser.parse_reply(str(body))
        except Exception:
            cleaned = str(body)
        return cleaned

    minimal = {
        "id": get_field(raw, "id", "Id"),
        "subject": get_field(raw, "subject", "Subject"),
        "senderAddress": get_field(raw, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender"),
        "senderName": get_field(raw, "senderName", "FromName", "sender"),
        "to": get_field(raw, "to", "To", default=""),
        "cc": get_field(raw, "cc", "Cc", default=""),
        "hasAttachments": bool(get_field(raw, "hasAttachments", default=False)),
        "attachment_names": [a.get("fileName") or a.get("name") for a in (raw.get("attachments") or []) if isinstance(a, dict)],
        "size": get_field(raw, "size", default=None),
        "receivedTime": get_field(raw, "receivedTime", "date", "Date", default=None),
        "importance": get_field(raw, "importance", default="Normal"),
        "classification": classification,
        "priority": priority_str,
        "summary": summary,
        "analysis": analysis or None,
        "body": _clean_full_body(),
        "processed_at": iso_now(),
    }
    out_path = PROCESSED_DIR / f"{email_id}.json"
    json_dump(minimal, out_path)
    return out_path


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_task_files() -> list[Path]:
    files: list[Path] = []
    for d in [TASKS_INBOX, TASKS_QUEUE, TASKS_ARCHIVED]:
        if d.exists():
            files.extend(sorted(d.glob("*.json")))
    return files


def find_task_by_email_id(email_id: str) -> tuple[Path, dict] | None:
    """Return (path, task) for the first task whose metadata.email_id matches."""
    if not email_id:
        return None
    for p in _iter_task_files():
        t = _load_json(p)
        if not isinstance(t, dict):
            continue
        mid = ((t.get("metadata") or {}).get("email_id"))
        if mid and str(mid) == str(email_id):
            return (p, t)
    return None


def save_or_update_task(task: dict, classification: str) -> Path:
    """Create a new task or update existing one if same email_id already tracked.

    - Moves file between inbox/queue as needed based on classification.
    - Preserves existing task id if updating.
    - Adds archived_at if already archived (no revive here).
    """
    email_id = ((task.get("metadata") or {}).get("email_id"))
    existing = find_task_by_email_id(email_id) if email_id else None

    # Decide destination directory by classification
    dest_dir = TASKS_INBOX if classification in ("Action", "Waiting") else TASKS_QUEUE
    dest_dir.mkdir(parents=True, exist_ok=True)

    if existing:
        old_path, old_task = existing
        # Do not modify archived tasks here; create a new follow-up if required
        if old_task.get("archived_at"):
            # Archived task found; create a brand new one to avoid reviving archives
            pass
        else:
            # Update selected fields in place
            old_task.update({
                "priority": task.get("priority", old_task.get("priority")),
                "classification": classification,
                "title": task.get("title", old_task.get("title")),
                "description": task.get("description", old_task.get("description")),
            })
            # Keep metadata but merge any new keys (e.g., response_draft)
            meta = old_task.get("metadata") or {}
            meta.update(task.get("metadata") or {})
            old_task["metadata"] = meta
            # Move file if directory changed
            new_path = dest_dir / old_path.name
            json_dump(old_task, new_path)
            if new_path != old_path and old_path.exists():
                try:
                    old_path.unlink()
                except Exception:
                    pass
            return new_path

    # Create new task
    path = dest_dir / f"{task['id']}.json"
    json_dump(task, path)
    # Best-effort git add/commit (non-fatal)
    try:
        env = os.environ.copy()
        # Prevent any interactive prompts (credentials, etc.)
        env.update({
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "true",
        })
        # Stage file with a short timeout and no stdin
        subprocess.run(
            ["git", "add", str(path)],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=3,
            env=env,
        )
        # Commit without hooks or GPG signing, with a short timeout
        subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "--no-gpg-sign",
                "--no-verify",
                "-m",
                f"Add task: {task['title']}",
            ],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=3,
            env=env,
        )
    except Exception:
        pass
    return path


def main():
    ap = argparse.ArgumentParser(description="Single-step email triage")
    ap.add_argument("--file", help="Raw email JSON file (skips PowerShell fetch)")
    ap.add_argument("--artifact", action="store_true", help="Write per-email artifacts under data/emails/work/<id>")
    ap.add_argument("--page-size", type=int, default=20)
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--progress", choices=["auto", "rich", "plain", "none"], default="auto", help="Progress display mode")
    ap.add_argument("--log", action="store_true", help="Use standard logging output instead of progress UI")
    ap.add_argument("--log-level", default=os.environ.get("TRIAGE_LOG_LEVEL", "INFO"))
    ap.add_argument("--no-color", action="store_true", help="Disable colored logs")
    args = ap.parse_args()

    ROOT.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    WORK_BASE.mkdir(parents=True, exist_ok=True)

    # Setup progress or logging
    if args.log:
        setup_logging(args.log_level, use_color=not args.no_color)
        log = logging.getLogger("triage")
        progress = None
    else:
        progress = ProgressUI(args.progress, total=6)
        log = None

    # 1. Fetch next unseen email (or load from --file)
    if log:
        log.info("[1/6] Fetching next email")
    else:
        progress.begin("Fetching next email")
    if args.file:
        raw = json_load(Path(args.file))
    else:
        raw = fetch_next_email_via_powershell(page_size=args.page_size, max_pages=args.max_pages)
        if raw is None:
            if log:
                log.info("No new emails found")
            else:
                progress.done("No new emails")
            print(json.dumps({"processed": 0, "created_tasks": 0, "by_classification": {}, "errors": [], "status": "no_new_emails"}))
            return 0
    # Brief context: {from} {subject}
    subj_ctx = (get_field(raw, "subject", "Subject", default="") or "").strip()
    sender_email_ctx = (get_field(raw, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender", default="") or "").strip()
    sender_name_ctx = (get_field(raw, "senderName", "FromName", default="") or "").strip()
    who_ctx = sender_name_ctx or sender_email_ctx or "Unknown"
    brief_fetch = clip(f"{who_ctx} {subj_ctx}", 100)
    if log:
        log.info("Fetched email: %s", brief_fetch)
    else:
        progress.done(f"Fetched email: {brief_fetch}")

    email_id = get_field(raw, "id", "Id")
    if not email_id:
        raise RuntimeError("Fetched email missing id")

    # Save raw artifact if requested
    work_dir = WORK_BASE / re.sub(r"[^A-Za-z0-9]", "_", str(email_id))
    raw_path = work_dir / "01_raw.json"
    if args.artifact:
        work_dir.mkdir(parents=True, exist_ok=True)
        json_dump(raw, raw_path)

    # 3. Analyze with LLM
    # Show model used in brief string
    model_name_display = (
        os.environ.get("TRIAGE_FAST_MODEL")
        or os.environ.get("FAST_MODEL")
        or os.environ.get("TRIAGE_MODEL")
        or "gemini-2.5-flash"
    )
    if log:
        log.info("[2/6] Analyzing with LLM: %s", model_name_display)
    else:
        progress.begin(f"Analyzing with LLM: {clip(model_name_display, 60)}")
    triage = analyze_email_llm(raw)
    if log:
        log.info("Analysis complete")
    else:
        progress.done("Analysis complete")

    # Normalize outputs
    if log:
        log.info("[3/6] Normalizing outputs")
    else:
        progress.begin("Normalizing outputs")
    cls_raw = (triage.classification or "").strip().lower()
    cls_map = {
        "urgent": "Action", "task": "Action", "action": "Action",
        "waiting": "Waiting",
        "info": "Reference", "reference": "Reference", "fyi": "Reference",
        "idea": "Optional", "optional": "Optional",
        "archive": "Noise", "spam": "Noise", "noise": "Noise",
    }
    classification = cls_map.get(cls_raw, triage.classification or "Reference")

    pr_map = {"high": ("High", 1), "medium": ("Medium", 2), "low": ("Low", 3)}
    p_tuple = pr_map.get((triage.priority or "").strip().lower(), ("Low", 3))
    priority_str, prio_num = p_tuple
    brief_norm = f"{classification} {priority_str}"
    if log:
        log.info("Outputs normalized: %s", brief_norm)
    else:
        progress.done(f"Outputs normalized: {brief_norm}")

    # Build human-friendly description
    subject = get_field(raw, "subject", "Subject", default="(no subject)") or ""
    sender_email = get_field(raw, "senderAddress", "sender_email", "senderEmailAddress", "From", "sender", default="") or ""
    sender_name = get_field(raw, "senderName", "FromName", default="") or ""
    who = (f"{sender_name} <{sender_email}>" if sender_email or sender_name else "Unknown").strip()
    abstract = (triage.abstract or "").strip()
    smry = (triage.summary or "").strip()
    due = (triage.due_date or "").strip() or "None"
    action_required = (triage.action_required or ("Reply" if triage.requires_reply else "None")).strip()

    bullets = []
    if abstract:
        bullets.append(abstract)
    if smry and smry != abstract:
        # split into lines and take up to 2 highlights
        for seg in re.split(r"[\n\r]+|\u2022|\.|;", smry):
            seg = seg.strip()
            if seg:
                bullets.append(seg)
            if len(bullets) >= 3:
                break
    bullet_lines = "\n".join([f"• {clip(b, 200)}" for b in bullets[:3]])
    # For the human task, keep description mostly as the short summary; include a few bullets
    description = (
        (smry or abstract or "").strip() + ("\n" + bullet_lines if bullet_lines else "")
    ).strip()

    # 4. Create task always; store to inbox normally
    if log:
        log.info("[4/6] Creating and saving task")
    else:
        progress.begin("Creating and saving task")
    task = build_task_json(raw, classification, prio_num, description)
    # include response draft if provided
    if triage.response_draft:
        task.setdefault("metadata", {})["response_draft"] = triage.response_draft
    task_path = save_or_update_task(task, classification)
    if args.artifact:
        json_dump(task, work_dir / "02_task.json")
    dest_ctx = "inbox" if classification in ("Action", "Waiting") else "queue"
    if log:
        log.info("Task saved: id=%s -> %s", task["id"], dest_ctx)
    else:
        progress.done(f"Task saved: id={task['id']} -> {dest_ctx}")

    # 5. Persist processed metadata
    if log:
        log.info("[5/6] Persisting processed metadata")
    else:
        progress.begin("Persisting processed metadata")
    processed_summary = smry or abstract or description
    processed_path = persist_processed(raw, classification, priority_str, processed_summary, analysis=(triage.analysis or None))
    if args.artifact:
        shutil.copy2(processed_path, work_dir / "03_processed.json")
    proc_name = (PROCESSED_DIR / f"{email_id}.json").name
    if log:
        log.info("Processed metadata saved: %s", proc_name)
    else:
        progress.done(f"Processed metadata saved: {proc_name}")

    # 6. Auto-archive clearly ignorable email (Noise only) for inbox zero momentum
    try:
        auto_archive = os.environ.get("TRIAGE_AUTO_ARCHIVE", "1") not in ("0", "false", "False")
        if auto_archive and classification == "Noise":
            if log:
                log.info("[6/6] Auto-archiving Noise email: id=%s", email_id)
            else:
                progress.begin(f"Auto-archiving (Noise): id={email_id}")
            email_id_final = get_field(raw, "id", "Id")
            if email_id_final:
                # Use the existing script that handles Outlook modifications
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS_DIR / "task_process.py"),
                        "modify",
                        str(email_id_final),
                        "--archive",
                    ],
                    cwd=str(ROOT),
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=12,
                )
            if log:
                log.info("Auto-archive attempted: id=%s", email_id)
            else:
                progress.done(f"Auto-archive attempted: id={email_id}")
    except Exception:
        # Non-fatal; archiving is best-effort only
        if log:
            log.warning("Auto-archive failed (non-fatal)")
        else:
            progress.fail("Auto-archive failed (non-fatal)")

    # Output per-email result JSON
    out = {
        "id": email_id,
        "classification": classification,
        "priority": priority_str,
        "task_id": task["id"],
        "summary": processed_summary,
    "analysis": triage.analysis or None,
        "stored": True,
        "task_path": str(task_path.relative_to(ROOT)),
        "processed_path": str(processed_path.relative_to(ROOT)),
    }
    # Close progress UI before emitting final JSON
    if not args.log and progress:
        progress.close()
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    logger = getLogger(__name__)
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception(json.dumps({"error": str(e)}))
        sys.exit(1)
