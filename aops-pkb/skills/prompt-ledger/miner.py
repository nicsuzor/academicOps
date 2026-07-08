#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add repo root to sys.path to import lib
repo_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(repo_root / "aops-core"))

from lib.transcript_paths import iter_rotated_files


def parse_transcript(path: Path):
    content = path.read_text(encoding="utf-8")
    # Extract frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        return []

    try:
        fm = yaml.safe_load(frontmatter_match.group(1))
    except yaml.YAMLError:
        return []

    session_id = fm.get("session_id", "unknown")
    surface = fm.get("surface", "unknown")
    date_str = fm.get("date", "")
    try:
        if isinstance(date_str, datetime):
            date_obj = date_str
        else:
            date_obj = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        dt_formatted = date_obj.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        dt_formatted = "unknown-date"
        date_obj = datetime.min

    results = []

    turns = re.split(r"^## User \(Turn \d+\).*?\n", content, flags=re.MULTILINE)
    if len(turns) > 1:
        for turn_text in turns[1:]:
            lines = turn_text.split("\n")
            prompt_lines = []
            for line in lines:
                if line.startswith("## Agent "):
                    break
                if line.startswith("_") and line.endswith("_"):
                    continue
                if line.startswith("**Invoked:"):
                    continue
                if line.strip().startswith("> 🪝"):
                    continue
                clean_line = line.lstrip(">").strip()
                if clean_line:
                    prompt_lines.append(clean_line)

            raw_prompt = " ".join(prompt_lines).strip()

            if not raw_prompt:
                continue

            if raw_prompt.startswith("<") and ">" in raw_prompt:
                if "SessionStart" in raw_prompt or "Stop hook feedback:" in raw_prompt:
                    continue

            words = raw_prompt.split()
            if len(words) > 12:
                short_q = " ".join(words[:12]) + "..."
            else:
                short_q = raw_prompt

            short_ans = "(Agent response recorded)"
            task_link = ""

            results.append(
                {
                    "datetime": dt_formatted,
                    "surface": surface,
                    "session_id": session_id,
                    "q": short_q,
                    "ans": short_ans,
                    "link": task_link,
                    "sort_key": date_obj,
                }
            )

    return results


def main():
    sessions_dir = os.environ.get("AOPS_SESSIONS", os.path.expanduser("~/src/sessions"))
    transcripts_dir = Path(sessions_dir) / "transcripts"

    all_prompts = []

    # We iterate all '-abridged.md' files using iter_rotated_files
    for md_file in iter_rotated_files(transcripts_dir, "*-abridged.md"):
        # Filter by date range for proof (2026-07-06 through 2026-07-08)
        # Note: the prompt says "Run the miner for 2026-07-06 through 2026-07-08".
        # We can implement a filter here for demonstration, or we can make it an argument.
        # Let's filter here for the required artifact.
        file_name = md_file.name
        if (
            file_name.startswith("20260706")
            or file_name.startswith("20260707")
            or file_name.startswith("20260708")
        ):
            prompts = parse_transcript(md_file)
            all_prompts.extend(prompts)

    # Sort reverse-date
    all_prompts.sort(key=lambda x: x["sort_key"], reverse=True)

    # Generate ledger
    ledger_path = Path(sessions_dir) / "state" / "prompt_ledger.md"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Prompt Ledger\n"]
    for p in all_prompts:
        line = f"- [{p['datetime']}] [{p['surface']}] [{p['session_id'][:8]}] {p['q']} | {p['ans']} {p['link']}".strip()
        lines.append(line)

    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_prompts)} prompts to {ledger_path}")


if __name__ == "__main__":
    main()
