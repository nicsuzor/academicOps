#!/usr/bin/env python3
"""Pre-commit hook: Framework integrity checks.

Consolidates framework-specific pre-commit validations into one script.
Designed to run fast on specific files (suitable for pre-commit) while
also supporting full-codebase scans (for CI via --full flag).

Checks:
1. Index wikilinks: WORKFLOWS.md wikilinks resolve to workflows/*.md files
2. Index skills: SKILLS.md entries resolve to skills/*/SKILL.md or commands/*.md
3. Workflow length: Workflow files must be <= 100 lines (C1 constraint)
4. Full wikilinks: All wikilinks across the codebase resolve (--full mode, CI only)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

WORKFLOW_MAX_LINES = 100


def check_index_wikilinks(plugin_root: Path) -> list[str]:
    """Validate WORKFLOWS.md wikilinks resolve to workflow files."""
    errors: list[str] = []
    wikilink_pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

    workflows_index = plugin_root / "WORKFLOWS.md"
    if not workflows_index.exists():
        return errors

    content = workflows_index.read_text()
    wikilinks = wikilink_pattern.findall(content)

    # Build set of existing workflow stems
    workflows_dir = plugin_root / "workflows"
    existing = set()
    if workflows_dir.exists():
        existing = {f.stem for f in workflows_dir.glob("*.md")}

    for target in wikilinks:
        target = target.strip()

        # Only check targets that look like workflow references:
        # all-lowercase, hyphenated, no path separators, no spaces
        if target != target.lower():
            continue
        if "/" in target or " " in target:
            continue

        if target not in existing:
            errors.append(f"WORKFLOWS.md: [[{target}]] -> no file workflows/{target}.md")

    return errors


def check_index_skills(plugin_root: Path) -> list[str]:
    """Validate SKILLS.md entries resolve to skill or command files."""
    errors: list[str] = []

    skills_index = plugin_root / "SKILLS.md"
    if not skills_index.exists():
        return errors

    content = skills_index.read_text()

    # Extract skill names from the table (first column: `/skillname`)
    skill_pattern = re.compile(r"^\|\s*`/([^`]+)`", re.MULTILINE)
    skill_names = skill_pattern.findall(content)

    # Build set of existing skills and commands
    skills_dir = plugin_root / "skills"
    commands_dir = plugin_root / "commands"

    existing: set[str] = set()
    if skills_dir.exists():
        existing |= {
            d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        }
    if commands_dir.exists():
        existing |= {f.stem for f in commands_dir.glob("*.md")}

    for name in skill_names:
        if name not in existing:
            errors.append(
                f"SKILLS.md: /{name} -> no file skills/{name}/SKILL.md or commands/{name}.md"
            )

    return errors


def check_workflow_length(plugin_root: Path) -> list[str]:
    """Validate workflow files are <= WORKFLOW_MAX_LINES lines."""
    errors: list[str] = []

    workflows_dir = plugin_root / "workflows"
    if not workflows_dir.exists():
        return errors

    for path in sorted(workflows_dir.glob("*.md")):
        line_count = len(path.read_text().splitlines())
        if line_count > WORKFLOW_MAX_LINES:
            errors.append(f"workflows/{path.name}: {line_count} lines (max {WORKFLOW_MAX_LINES})")

    return errors


def check_full_wikilinks(root: Path) -> list[str]:
    """Full codebase wikilink check. Delegates to audit_framework_health.

    Slow - for CI only, not pre-commit.
    """
    sys.path.insert(0, str(root / "scripts"))
    try:
        from audit_framework_health import HealthMetrics, check_wikilinks

        metrics = HealthMetrics()
        check_wikilinks(root, metrics)
        return [f"{link['file']}: [[{link['target']}]]" for link in metrics.broken_wikilinks]
    except ImportError:
        print(
            "WARNING: audit_framework_health not available, skipping full scan",
            file=sys.stderr,
        )
        return []


def main() -> int:
    """Run framework integrity checks.

    Default: fast index + length checks (suitable for pre-commit).
    --full: also run full codebase wikilink scan (for CI).
    """
    full_mode = "--full" in sys.argv
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    plugin_root = root / "aops-core"
    if not plugin_root.is_dir():
        print(f"Error: Plugin root not found: {plugin_root}", file=sys.stderr)
        return 1

    all_errors: list[str] = []

    # 1. Index wikilink integrity
    all_errors.extend(check_index_wikilinks(plugin_root))

    # 2. Skills index integrity
    all_errors.extend(check_index_skills(plugin_root))

    # 3. Workflow length constraint
    all_errors.extend(check_workflow_length(plugin_root))

    # 4. Full codebase wikilinks (CI only)
    if full_mode:
        all_errors.extend(check_full_wikilinks(root))

    if all_errors:
        print(f"FAIL: {len(all_errors)} framework integrity issue(s):")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    mode = "full" if full_mode else "index + length"
    print(f"OK: Framework integrity checks passed ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
