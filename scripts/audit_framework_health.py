#!/usr/bin/env python3
"""
Framework health metrics collector.

Measures framework governance health with quantifiable metrics.
Outputs JSON report + markdown summary for tracking over time.

Metrics tracked:
1. Files not in INDEX.md
2. Skills without specs
3. Axioms/Heuristics without enforcement mapping
4. Orphan files (no inbound wikilinks)
5. Broken wikilinks
6. SKILL.md files > 500 lines
7. Specs without standard sections
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
}

# Files/patterns to exclude from accounting
EXCLUDE_PATTERNS = {
    "reference-graph.json",
    "reference-graph.csv",
    ".gitignore",
    ".gitmodules",
    "uv.lock",
    "pyproject.toml",
    "__init__.py",
    "conftest.py",
    "git-post-commit-sync-aops",  # Git hook (no extension, listed in INDEX.md)
}

# Patterns (prefix match) to exclude
EXCLUDE_PREFIXES = (
    "health-baseline-",  # Temporary health reports
)

# Standard spec sections (at least some should be present)
SPEC_SECTIONS = {
    "user story",
    "acceptance criteria",
    "design",
    "related specs",
}


@dataclass
class HealthMetrics:
    """Container for all health metrics."""

    # File accounting
    files_not_in_index: list[str] = field(default_factory=list)
    files_in_index_but_missing: list[str] = field(default_factory=list)

    # Skill-spec coverage
    skills_without_specs: list[str] = field(default_factory=list)

    # Enforcement mapping
    axioms_without_enforcement: list[str] = field(default_factory=list)
    heuristics_without_enforcement: list[str] = field(default_factory=list)

    # Link graph health
    orphan_files: list[str] = field(default_factory=list)
    broken_wikilinks: list[dict[str, str]] = field(default_factory=list)

    # Content quality
    oversized_skills: list[dict[str, int]] = field(default_factory=list)
    specs_missing_sections: list[dict[str, list[str]]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "files_not_in_index": len(self.files_not_in_index),
                "files_missing": len(self.files_in_index_but_missing),
                "skills_without_specs": len(self.skills_without_specs),
                "axioms_without_enforcement": len(self.axioms_without_enforcement),
                "heuristics_without_enforcement": len(
                    self.heuristics_without_enforcement
                ),
                "orphan_files": len(self.orphan_files),
                "broken_wikilinks": len(self.broken_wikilinks),
                "oversized_skills": len(self.oversized_skills),
                "specs_missing_sections": len(self.specs_missing_sections),
            },
            "details": {
                "files_not_in_index": self.files_not_in_index,
                "files_in_index_but_missing": self.files_in_index_but_missing,
                "skills_without_specs": self.skills_without_specs,
                "axioms_without_enforcement": self.axioms_without_enforcement,
                "heuristics_without_enforcement": self.heuristics_without_enforcement,
                "orphan_files": self.orphan_files,
                "broken_wikilinks": self.broken_wikilinks,
                "oversized_skills": self.oversized_skills,
                "specs_missing_sections": self.specs_missing_sections,
            },
        }


def iter_framework_files(root: Path) -> Iterator[Path]:
    """Iterate over all significant framework files."""
    for path in root.rglob("*"):
        # Skip directories
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        # Skip excluded files
        if path.name in EXCLUDE_PATTERNS:
            continue
        # Skip files matching prefix patterns
        if any(path.name.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
            continue
        # Only include files
        if path.is_file():
            yield path


def extract_index_files(index_path: Path) -> set[str]:
    """Extract file paths mentioned in INDEX.md."""
    if not index_path.exists():
        return set()

    content = index_path.read_text()
    files: set[str] = set()

    # Match patterns like:
    # ├── filename.ext
    # │   ├── subfile.ext
    # Also match [[wikilinks]]
    # Note: Allow spaces in filenames with [a-zA-Z0-9_\-./\s]
    tree_pattern = re.compile(r"[├└│─\s]+([a-zA-Z0-9_\-./][a-zA-Z0-9_\-./\s]*\.[a-z]+)")
    wikilink_pattern = re.compile(r"\[\[([^\]|]+)\]\]")

    for match in tree_pattern.finditer(content):
        files.add(match.group(1))

    for match in wikilink_pattern.finditer(content):
        target = match.group(1)
        if not target.startswith("http"):
            files.add(target)

    return files


def check_file_accounting(root: Path, metrics: HealthMetrics) -> None:
    """Check if all files are accounted for in INDEX.md."""
    index_path = root / "INDEX.md"
    index_files = extract_index_files(index_path)

    # Get actual files (relative paths)
    actual_files: set[str] = set()
    for path in iter_framework_files(root):
        rel = str(path.relative_to(root))
        # Skip test files, data directories, and lib/ (submodules/imported libraries)
        if rel.startswith("tests/") and not rel.endswith("conftest.py"):
            continue
        if "/data/" in rel:
            continue
        if rel.startswith("lib/"):
            continue
        actual_files.add(rel)

    # Files in filesystem but not in index
    for f in sorted(actual_files):
        # Normalize - check if filename or path is in index
        filename = Path(f).name
        if f not in index_files and filename not in index_files:
            # Check if it's a wikilink format (without extension)
            stem = Path(f).stem
            if stem not in index_files and f"{stem}.md" not in index_files:
                metrics.files_not_in_index.append(f)


def check_skill_spec_coverage(root: Path, metrics: HealthMetrics) -> None:
    """Check if all skills have corresponding specs."""
    skills_dir = root / "skills"
    specs_dir = root / "specs"

    if not skills_dir.exists():
        return

    # Get skill names
    skill_names: set[str] = set()
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir() and not skill_path.name.startswith("."):
            skill_names.add(skill_path.name)

    # Get spec names (looking for *-skill.md pattern)
    spec_skills: set[str] = set()
    if specs_dir.exists():
        for spec_path in specs_dir.glob("*-skill.md"):
            # Extract skill name from spec filename
            name = spec_path.stem.replace("-skill", "")
            spec_skills.add(name)

    # Find skills without specs
    for skill in sorted(skill_names):
        if skill not in spec_skills:
            metrics.skills_without_specs.append(skill)


def check_enforcement_mapping(root: Path, metrics: HealthMetrics) -> None:
    """Check if axioms and heuristics are mapped to enforcement in enforcement-map.md."""
    axioms_path = root / "AXIOMS.md"
    heuristics_path = root / "HEURISTICS.md"
    rules_path = root / "indices/enforcement-map.md"

    if not rules_path.exists():
        return

    rules_content = rules_path.read_text().lower()

    # Extract axiom numbers from AXIOMS.md
    if axioms_path.exists():
        axioms_content = axioms_path.read_text()
        # Match patterns like "1. **..." or "#1" or "Axiom #1"
        axiom_pattern = re.compile(r"^\d+\.\s+\*\*", re.MULTILINE)
        axiom_count = len(axiom_pattern.findall(axioms_content))

        for i in range(1, axiom_count + 1):
            # Check if axiom is mentioned in enforcement-map.md
            patterns = [f"a#{i}", f"axiom #{i}", f"axiom {i}", f"##{i}"]
            if not any(p in rules_content for p in patterns):
                # Also check for "axiom x" placeholder
                if "axiom x" not in rules_content:
                    metrics.axioms_without_enforcement.append(f"A#{i}")

    # Extract heuristic numbers from HEURISTICS.md
    if heuristics_path.exists():
        heuristics_content = heuristics_path.read_text()
        # Match patterns like "## H1:" or "## H23:"
        heuristic_pattern = re.compile(r"^##\s+H(\d+):", re.MULTILINE)
        heuristic_nums = [
            int(m.group(1)) for m in heuristic_pattern.finditer(heuristics_content)
        ]

        for h in heuristic_nums:
            patterns = [f"h#{h}", f"h{h}", f"heuristic #{h}", f"heuristic {h}"]
            if not any(p in rules_content for p in patterns):
                metrics.heuristics_without_enforcement.append(f"H#{h}")


def normalize_wikilink_target(target: str, root: Path) -> str | None:
    """Normalize a wikilink target to canonical form (with .md extension).

    Returns the canonical path if it resolves to a file, None otherwise.
    """
    # Already has .md extension
    if target.endswith(".md"):
        if (root / target).exists():
            return target
        return None

    # Try adding .md extension
    with_ext = f"{target}.md"
    if (root / with_ext).exists():
        return with_ext

    # Check if it exists as-is (might be a directory or non-md file)
    if (root / target).exists():
        path = root / target
        if path.is_file() and path.suffix == ".md":
            return target
        return None

    return None


def check_wikilinks(root: Path, metrics: HealthMetrics) -> None:
    """Check for broken wikilinks and orphan files."""
    wikilink_pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

    # Build set of all file paths (canonical form only - with .md extension)
    all_files: set[str] = set()
    file_stems: set[str] = set()

    for path in iter_framework_files(root):
        if path.suffix == ".md":
            rel = str(path.relative_to(root))
            all_files.add(rel)  # Only add canonical form (with .md)
            file_stems.add(path.stem)

    # Track incoming references (canonical paths only)
    incoming_refs: dict[str, int] = {f: 0 for f in all_files}

    # Conceptual terms that are intentionally not files (definitions, concepts)
    # These are valid wikilinks in Obsidian for creating concept notes later
    conceptual_terms = {
        # Framework concepts
        "NO OTHER TRUTHS",
        "categorical-imperative",
        "wikilinks",
        "brackets",
        "Obsidian",
        "meetings",
        "pre-commit",
        "experiments",
        "LOG",
        "STYLE",
        "daily",
        "task",
        "zotmcp",
        "academicOps",
        "memory server",
        "ADHD",
        "Just-in-Time",
        "Semantic Search",
        "meta-framework",
        "synthesis.json",
        "AOPS",
        "X",
        "task skill",
        "testing-with-live-data",
        "Cognitive Load Dashboard Spec",
        "hypervisor",
        "/qa",
        "goal",
        "meta",
        "supervise",
        "prompts",
        # Test/docs placeholders
        "LOG.md",
        "experiments/LOG.md",
        "Testing Framework Overview",
        "^",
        # Tool names (referenced in commands and tests)
        "AskUserQuestion",
        "TodoWrite",
        "Read",
        "Glob",
        "Grep",
        "Write",
        "Edit",
        # Template/example placeholders in skill docs
        "Goal Name",
        "Topic",
        "Other Note",
        "Parent Project",
        "nonexistent.md",
        "0, 2, 4",
        "folder/file.md",
        "../sibling/file.md",
        "../framework/SKILL.md",
        "projects",
        "project",
        "other-project",
        "another-project",
        "concept",
        "another-concept",
        "...",
        "templates/daily.md",
        "skills/tasks.backup/",
        "skills/README.md",
        # Extractor entity types
        "Event",
        "Institution",
        "Person",
        # Workflow placeholders (may be created later)
        "workflows/capture",
        "workflows/validate",
        "workflows/prune",
        # Planned/conceptual references
        "matplotlib-plot-types",
        "matplotlib-styling",
        "linear-models",
        "glm",
        "discrete-choice",
        "time-series",
        "stats-diagnostics",
        "dbt-patterns",
        "matplotlib-api",
        "matplotlib-common-issues",
        "seaborn-functions",
        "seaborn-objects",
        "seaborn-examples",
        # Example/template wikilinks in skill docs
        "Related Note",
        "Note Title",
        "folder/subfolder/Note",
        "../projects/<project>",
        "wiki-links",
        "'A', 'B'",
        # Test conceptual terms
        "Claude Code",
        "CWD",
        "test_marker_hook",
    }

    # Hook and script files (these are correctly linked by filename in Obsidian)
    # Include both full names (with extension) and stems (without extension)
    hook_files: set[str] = set()
    if (root / "hooks").exists():
        for p in (root / "hooks").glob("*.py"):
            hook_files.add(p.name)
            hook_files.add(p.stem)  # Without extension
        for p in (root / "hooks").glob("*.sh"):
            hook_files.add(p.name)
            hook_files.add(p.stem)

    script_files: set[str] = set()
    if (root / "scripts").exists():
        for p in (root / "scripts").glob("*.py"):
            script_files.add(p.name)
            script_files.add(p.stem)
        for p in (root / "scripts").glob("*.sh"):
            script_files.add(p.name)
            script_files.add(p.stem)

    # Lib files (referenced in lib/lib.md)
    lib_files: set[str] = set()
    if (root / "lib").exists():
        for p in (root / "lib").glob("*.py"):
            lib_files.add(p.name)
            lib_files.add(p.stem)

    # Prompts files (referenced in hooks/hooks.md)
    prompt_files: set[str] = set()
    prompts_dir = root / "hooks" / "prompts"
    if prompts_dir.exists():
        for p in prompts_dir.glob("*.md"):
            prompt_files.add(p.name)
            prompt_files.add(p.stem)
            prompt_files.add(f"prompts/{p.name}")  # Allow prompts/file.md

    # Test files
    test_files: set[str] = set()
    tests_dir = root / "tests"
    if tests_dir.exists():
        for p in tests_dir.glob("*.py"):
            test_files.add(p.name)
            test_files.add(p.stem)

    # Build set of all filenames (not just stems) for shortest-path matching
    all_filenames: set[str] = set()
    for path in iter_framework_files(root):
        if path.suffix == ".md":
            all_filenames.add(path.name)

    # Cross-vault links (files in $ACA_DATA, not $AOPS) - valid in Obsidian
    cross_vault_prefixes = (
        "ACCOMMODATIONS",
        "CORE",
        "STATE",
        "data/",
        "projects/",
        "tasks/",
        "sessions/",
    )

    # Internal anchor references (same-document refs like H7, H7b)
    internal_ref_pattern = re.compile(r"^H\d+[a-z]?$")

    # Build set of skill names (for skill-to-spec resolution)
    skill_names: set[str] = set()
    skills_dir = root / "skills"
    if skills_dir.exists():
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and not skill_path.name.startswith("."):
                skill_names.add(skill_path.name)

    # Scan all markdown files for wikilinks
    for path in root.rglob("*.md"):
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        # Skip files matching exclude prefixes
        if any(path.name.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
            continue

        try:
            content = path.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue

        rel_path = str(path.relative_to(root))

        for match in wikilink_pattern.finditer(content):
            target = match.group(1).strip()

            # Handle escaped brackets (trailing backslash)
            if target.endswith("\\"):
                target = target.rstrip("\\")

            # Skip URLs
            if target.startswith("http"):
                continue

            # Skip conceptual terms (not meant to be files)
            if target in conceptual_terms:
                continue

            # Skip cross-vault links (files in $ACA_DATA)
            if any(target.startswith(prefix) for prefix in cross_vault_prefixes):
                continue

            # Skip internal anchor references
            if internal_ref_pattern.match(target):
                continue

            # Skip anchor links (contain #)
            if "#" in target:
                continue

            # Try to resolve target
            resolved = False

            # Check if it's a skill name → resolve to spec
            if target in skill_names:
                spec_path = root / "specs" / f"{target}-skill.md"
                if spec_path.exists():
                    resolved = True

            # Check if it's a hook, script, lib, prompt, or test file (linked by filename)
            if not resolved and target in hook_files:
                resolved = True
            if not resolved and target in script_files:
                resolved = True
            if not resolved and target in lib_files:
                resolved = True
            if not resolved and target in prompt_files:
                resolved = True
            if not resolved and target in test_files:
                resolved = True

            # Check against all filenames (Obsidian shortest-path matching)
            if not resolved and target in all_filenames:
                resolved = True

            # Check relative paths (references/*, instructions/*, workflows/*)
            # These resolve within the same skill directory in Obsidian
            if not resolved and target.startswith(
                ("references/", "instructions/", "workflows/", "templates/", "scripts/")
            ):
                # Try to find this file in any skill directory
                for skill_dir in skills_dir.iterdir() if skills_dir.exists() else []:
                    if skill_dir.is_dir() and (skill_dir / target).exists():
                        resolved = True
                        break

            # Check direct match and normalize to canonical form
            canonical = normalize_wikilink_target(target, root)
            if canonical:
                resolved = True
                if canonical in incoming_refs:
                    incoming_refs[canonical] += 1
            elif target in all_files or target in file_stems:
                resolved = True
                # Normalize: if target matches a stem, find canonical path
                if f"{target}.md" in incoming_refs:
                    incoming_refs[f"{target}.md"] += 1
                elif target in incoming_refs:
                    incoming_refs[target] += 1

            # Check if it's a path like specs/foo
            if not resolved:
                target_path = root / target
                if target_path.exists():
                    resolved = True
                elif (root / f"{target}.md").exists():
                    resolved = True

            # Handle full vault paths like academicOps/skills/foo/SKILL
            if not resolved and target.startswith("academicOps/"):
                # Strip vault prefix and check if file exists
                relative_target = target.replace("academicOps/", "", 1)
                if (root / relative_target).exists():
                    resolved = True
                elif (root / f"{relative_target}.md").exists():
                    resolved = True

            if not resolved:
                metrics.broken_wikilinks.append(
                    {
                        "file": rel_path,
                        "target": target,
                    }
                )

    # Find orphans (files with no incoming references)
    # Exclude expected orphans (entry points, commands, utility files, etc.)
    expected_orphan_prefixes = [
        "commands/",  # Commands are invoked, not linked
        "agents/",  # Agents are invoked, not linked
        "hooks/",  # Hooks are registered, not linked
        "scripts/",  # Scripts are run, not linked
        "tests/",  # Tests are run, not linked
        "lib/",  # Lib modules are imported, not linked
        ".claude/",  # Config files
    ]
    # Skill subdirectories are linked via relative paths from their SKILL.md
    # The reference counter doesn't resolve these properly yet (TODO: fix)
    expected_orphan_skill_subdirs = [
        "/references/",
        "/instructions/",
        "/templates/",
        "/workflows/",
        "/scripts/",
        "/tests/",
        "/resources/",  # Additional skill internal dirs
    ]
    expected_orphan_names = [
        "README.md",
        "CLAUDE.md",
        "GEMINI.md",
        "INDEX.md",  # Entry points
        "CLAUDE",
        "GEMINI",
        "FRAMEWORK",
        "AGENTS",
        "INDEX",  # Root entry points (no extension)
        "SKILL.md",
        "SKILL",
        "README",  # Skill entry points
    ]

    for file_path, ref_count in incoming_refs.items():
        if ref_count == 0:
            # Check if expected orphan
            is_expected = False
            for prefix in expected_orphan_prefixes:
                if file_path.startswith(prefix):
                    is_expected = True
                    break
            if Path(file_path).name in expected_orphan_names:
                is_expected = True
            # Check if it's a skill subdirectory file (linked via relative paths)
            if file_path.startswith("skills/"):
                for subdir in expected_orphan_skill_subdirs:
                    if subdir in file_path:
                        is_expected = True
                        break

            if not is_expected:
                metrics.orphan_files.append(file_path)


def check_namespace_collisions(root: Path) -> list[tuple[str, str, str]]:
    """Check for namespace collisions across framework objects.

    Per H8: Framework objects (skills, commands, hooks, agents) must have
    unique names across all namespaces. Claude Code treats same-named
    commands as model-only, causing "can only be invoked by Claude" errors.

    Returns:
        List of (name, namespace1, namespace2) tuples for each collision.
    """
    # Collect all names by namespace
    commands: set[str] = set()
    commands_dir = root / "commands"
    if commands_dir.exists():
        commands = {p.stem for p in commands_dir.glob("*.md")}

    skills: set[str] = set()
    skills_dir = root / "skills"
    if skills_dir.exists():
        skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}

    agents: set[str] = set()
    agents_dir = root / "agents"
    if agents_dir.exists():
        agents = {p.stem for p in agents_dir.glob("*.md")}

    hooks: set[str] = set()
    hooks_dir = root / "hooks"
    if hooks_dir.exists():
        hooks = {p.stem for p in hooks_dir.glob("*.py")}

    namespaces = [
        ("commands", commands),
        ("skills", skills),
        ("agents", agents),
        ("hooks", hooks),
    ]

    collisions: list[tuple[str, str, str]] = []
    for i, (ns1, set1) in enumerate(namespaces):
        for ns2, set2 in namespaces[i + 1 :]:
            for name in set1 & set2:
                collisions.append((name, ns1, ns2))
    return collisions


def check_skill_sizes(root: Path, metrics: HealthMetrics) -> None:
    """Check for oversized SKILL.md files (> 500 lines)."""
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                line_count = len(skill_md.read_text().splitlines())
                if line_count > 500:
                    metrics.oversized_skills.append(
                        {
                            "skill": skill_path.name,
                            "lines": line_count,
                        }
                    )
            except (UnicodeDecodeError, PermissionError):
                continue


def check_spec_sections(root: Path, metrics: HealthMetrics) -> None:
    """Check if specs have standard sections."""
    specs_dir = root / "specs"
    if not specs_dir.exists():
        return

    for spec_path in specs_dir.glob("*.md"):
        try:
            content = spec_path.read_text().lower()
        except (UnicodeDecodeError, PermissionError):
            continue

        missing: list[str] = []
        for section in SPEC_SECTIONS:
            # Check for ## Section or # Section
            if f"## {section}" not in content and f"# {section}" not in content:
                missing.append(section)

        # Only report if missing more than half the sections
        if len(missing) > len(SPEC_SECTIONS) // 2:
            metrics.specs_missing_sections.append(
                {
                    "spec": spec_path.name,
                    "missing": missing,
                }
            )


def generate_markdown_report(metrics: HealthMetrics) -> str:
    """Generate markdown summary report."""
    data = metrics.to_dict()
    summary = data["summary"]

    lines = [
        "# Framework Health Report",
        "",
        f"Generated: {data['generated']}",
        "",
        "## Summary",
        "",
        "| Metric | Count | Status |",
        "|--------|-------|--------|",
    ]

    def status_emoji(count: int, threshold: int = 0) -> str:
        if count <= threshold:
            return "✅"
        if count <= threshold + 5:
            return "⚠️"
        return "❌"

    lines.append(
        f"| Files not in INDEX.md | {summary['files_not_in_index']} | {status_emoji(summary['files_not_in_index'], 5)} |"
    )
    lines.append(
        f"| Skills without specs | {summary['skills_without_specs']} | {status_emoji(summary['skills_without_specs'], 3)} |"
    )
    lines.append(
        f"| Axioms without enforcement | {summary['axioms_without_enforcement']} | {status_emoji(summary['axioms_without_enforcement'], 5)} |"
    )
    lines.append(
        f"| Heuristics without enforcement | {summary['heuristics_without_enforcement']} | {status_emoji(summary['heuristics_without_enforcement'], 10)} |"
    )
    lines.append(
        f"| Orphan files | {summary['orphan_files']} | {status_emoji(summary['orphan_files'], 3)} |"
    )
    lines.append(
        f"| Broken wikilinks | {summary['broken_wikilinks']} | {status_emoji(summary['broken_wikilinks'])} |"
    )
    lines.append(
        f"| Oversized skills | {summary['oversized_skills']} | {status_emoji(summary['oversized_skills'])} |"
    )
    lines.append(
        f"| Specs missing sections | {summary['specs_missing_sections']} | {status_emoji(summary['specs_missing_sections'], 10)} |"
    )

    # Add details sections if there are issues
    details = data["details"]

    if details["files_not_in_index"]:
        lines.extend(
            [
                "",
                "## Files Not in INDEX.md",
                "",
            ]
        )
        for f in details["files_not_in_index"][:20]:  # Limit to 20
            lines.append(f"- `{f}`")
        if len(details["files_not_in_index"]) > 20:
            lines.append(f"- ... and {len(details['files_not_in_index']) - 20} more")

    if details["skills_without_specs"]:
        lines.extend(
            [
                "",
                "## Skills Without Specs",
                "",
            ]
        )
        for s in details["skills_without_specs"]:
            lines.append(f"- {s}")

    if details["broken_wikilinks"]:
        lines.extend(
            [
                "",
                "## Broken Wikilinks",
                "",
            ]
        )
        for link in details["broken_wikilinks"][:20]:
            lines.append(f"- `{link['file']}` → `[[{link['target']}]]`")

    if details["orphan_files"]:
        lines.extend(
            [
                "",
                "## Orphan Files",
                "",
            ]
        )
        for f in details["orphan_files"]:
            lines.append(f"- `{f}`")

    if details["oversized_skills"]:
        lines.extend(
            [
                "",
                "## Oversized Skills (> 500 lines)",
                "",
            ]
        )
        for s in details["oversized_skills"]:
            lines.append(f"- {s['skill']}: {s['lines']} lines")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit framework health metrics")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Framework root directory (default: $AOPS or current dir)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--markdown",
        "-m",
        action="store_true",
        help="Output markdown report to stdout",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output JSON to stdout",
    )
    args = parser.parse_args()

    # Determine root
    if args.root:
        root = args.root.resolve()
    elif "AOPS" in os.environ:
        root = Path(os.environ["AOPS"]).resolve()
    else:
        root = Path.cwd().resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    # Collect metrics
    metrics = HealthMetrics()

    print("Checking file accounting...", file=sys.stderr)
    check_file_accounting(root, metrics)

    print("Checking skill-spec coverage...", file=sys.stderr)
    check_skill_spec_coverage(root, metrics)

    print("Checking enforcement mapping...", file=sys.stderr)
    check_enforcement_mapping(root, metrics)

    print("Checking wikilinks...", file=sys.stderr)
    check_wikilinks(root, metrics)

    print("Checking skill sizes...", file=sys.stderr)
    check_skill_sizes(root, metrics)

    print("Checking spec sections...", file=sys.stderr)
    check_spec_sections(root, metrics)

    # Output
    if args.json:
        print(json.dumps(metrics.to_dict(), indent=2))
    elif args.markdown:
        print(generate_markdown_report(metrics))
    elif args.output:
        args.output.write_text(json.dumps(metrics.to_dict(), indent=2))
        print(f"Wrote {args.output}", file=sys.stderr)
        # Also write markdown report
        md_path = args.output.with_suffix(".md")
        md_path.write_text(generate_markdown_report(metrics))
        print(f"Wrote {md_path}", file=sys.stderr)
    else:
        # Default: print markdown to stdout
        print(generate_markdown_report(metrics))

    # Return exit code based on health
    summary = metrics.to_dict()["summary"]
    total_issues = sum(summary.values())
    if total_issues > 50:
        return 2  # Critical
    if total_issues > 20:
        return 1  # Warning
    return 0


if __name__ == "__main__":
    sys.exit(main())
