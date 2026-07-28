"""Prompt ledger generation logic."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from transcripts.domain.secret_redaction import redact_secrets

logger = logging.getLogger(__name__)


def generate_prompt_ledger(sessions_dir: Path, since_arg: str | None) -> int:
    """Build $AOPS_SESSIONS/state/prompt_ledger.md from existing sidecar JSON files.

    Walks sessions_dir/transcripts/ (YYYY-MM layout or flat) and extracts user prompts.

    Returns 0 when every sidecar was read. A sidecar that cannot be parsed is a
    session missing from the ledger, so it is logged, named in the ledger
    itself, and returned as exit status 1 — the ledger is still written, but a
    caller that only checks the status learns the run was incomplete. Skipping
    it silently is how an artifact that will not parse goes unnoticed: the
    session simply stops appearing, and nothing anywhere says why.
    """
    since_date: date | None = None
    if since_arg:
        try:
            since_date = datetime.strptime(since_arg, "%Y-%m-%d").date()
            since_dt = datetime.combine(since_date, datetime.min.time(), tzinfo=UTC) - timedelta(
                days=1
            )
        except ValueError:
            logger.error("Error: --since must be YYYY-MM-DD, got %r", since_arg)
            return 1
    else:
        since_date = None
        since_dt = datetime.now(UTC) - timedelta(days=7)

    transcripts_dir = sessions_dir / "transcripts"
    if not transcripts_dir.is_dir():
        logger.info("No transcripts directory found at %s", transcripts_dir)
        return 0

    # Glob JSON sidecar files
    json_paths = list(transcripts_dir.glob("**/*.json"))

    rows: list[dict] = []
    unreadable: list[tuple[str, str]] = []

    for path in json_paths:
        name = (
            str(path.relative_to(sessions_dir)) if path.is_relative_to(sessions_dir) else str(path)
        )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            # An unparseable sidecar is a whole session dropped from the
            # ledger. Say so: on the log, in the artifact, and in the status.
            logger.error("Sidecar %s could not be read, so its prompts are missing: %s", name, exc)
            unreadable.append((name, str(exc)))
            continue

        # Check has_user_context
        if not data.get("has_user_context", True):
            continue

        user_prompts = data.get("user_prompts") or []
        if not user_prompts:
            continue

        session_id = data.get("session_id", "")[:8]
        project = data.get("project") or "adhoc"
        started_at_raw = data.get("started_at") or data.get("date")

        try:
            session_dt = (
                datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
                if started_at_raw
                else None
            )
        except ValueError:
            session_dt = None

        for prompt in user_prompts:
            text = prompt.get("text") or ""
            # Filter noise
            if text.startswith("[Request interrupted"):
                continue

            prompt_ts = prompt.get("timestamp") or started_at_raw
            try:
                prompt_dt = (
                    datetime.fromisoformat(prompt_ts.replace("Z", "+00:00")) if prompt_ts else None
                )
            except ValueError:
                prompt_dt = None

            effective_dt = prompt_dt or session_dt
            if effective_dt:
                if since_date is not None:
                    if effective_dt.date() < since_date:
                        continue
                elif effective_dt < since_dt:
                    continue

            # Shorten question
            collapsed = re.sub(r"\s+", " ", text).strip()
            question = collapsed[:140] + ("…" if len(collapsed) > 140 else "")

            # Infer outcome and links
            task_id = data.get("task_id")
            pr_number = data.get("pr_number")

            link_parts = []
            if pr_number:
                link_parts.append(f"PR #{pr_number}")
            if task_id:
                link_parts.append(f"task:{task_id}")
            link = " ".join(link_parts)

            insights = data.get("insights") or ""
            outcome = insights.strip()[:140] + ("…" if len(insights.strip()) > 140 else "")

            display_dt = effective_dt.strftime("%Y-%m-%d %H:%M") if effective_dt else "unknown-time"

            rows.append(
                {
                    "sort_key": effective_dt or since_dt,
                    "display_dt": display_dt,
                    "project": project,
                    "session_id": session_id,
                    "question": question,
                    "outcome": outcome,
                    "link": link,
                }
            )

    # Sort reverse chronological
    rows.sort(key=lambda r: r["sort_key"], reverse=True)

    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "# Prompt Ledger",
        "",
        f"<!-- generated by `transcripts.runner --ledger` on {generated_at}. -->",
        "",
    ]
    if unreadable:
        lines.extend(
            [
                "> [!WARNING]",
                f"> {len(unreadable)} session sidecar(s) could not be parsed. Their prompts are "
                "missing from the list below, and this ledger is incomplete until they are "
                "repaired or removed:",
                *(f"> - `{name}` — {reason}" for name, reason in unreadable),
                "",
            ]
        )
    for row in rows:
        lines.append(
            f"- [{row['display_dt']}] [{row['project']}] [{row['session_id']}] "
            f"[{row['question']}] [{row['outcome']}] [{row['link']}]"
        )

    state_dir = sessions_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = state_dir / "prompt_ledger.md"
    # Rows embed raw user prompt text, which is the exact vector of the
    # 2026-06-01 leak this module's redaction was written for: a prompt
    # carrying an env dump landed verbatim in the tracked ledger.
    ledger_path.write_text(redact_secrets("\n".join(lines) + "\n"), encoding="utf-8")

    logger.info("Generated prompt ledger at %s with %d rows", ledger_path, len(rows))
    if unreadable:
        logger.error(
            "Prompt ledger is incomplete: %d of %d sidecar(s) could not be read",
            len(unreadable),
            len(json_paths),
        )
        return 1
    return 0
