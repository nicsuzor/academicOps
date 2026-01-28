"""
File index for selective path injection.

Maps keywords and component names to specific file paths, enabling the
prompt hydrator to receive only relevant file locations based on prompt content.

Design principle: Hydrator (haiku) receives relevant paths, not all paths.
This saves tokens and provides focused context.

Usage:
    from lib.file_index import get_relevant_file_paths

    paths = get_relevant_file_paths("fix the prompt hydrator routing logic")
    # Returns paths related to: hydrator, routing, hooks
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from lib.paths import get_aops_root


@dataclass
class FileEntry:
    """A file with its path, description, and matching keywords."""

    path: str  # Relative to $AOPS (e.g., "aops-core/agents/prompt-hydrator.md")
    description: str  # What this file does
    keywords: tuple[str, ...]  # Keywords that trigger inclusion

    def absolute_path(self) -> Path:
        """Return absolute path."""
        return get_aops_root() / self.path


# File index organized by category
# Each entry maps keywords to specific files with descriptions
FILE_INDEX: tuple[FileEntry, ...] = (
    # --- Core Framework Files ---
    FileEntry(
        path="aops-core/AXIOMS.md",
        description="Inviolable principles (failure = system failure)",
        keywords=(
            "axiom",
            "axioms",
            "principle",
            "principles",
            "governance",
            "rule",
            "enforcement",
        ),
    ),
    FileEntry(
        path="aops-core/HEURISTICS.md",
        description="Operational guidelines (violation = friction, not failure)",
        keywords=(
            "heuristic",
            "heuristics",
            "guideline",
            "guidelines",
            "best practice",
            "operational",
        ),
    ),
    FileEntry(
        path="aops-core/WORKFLOWS.md",
        description="Workflow decision tree and routing",
        keywords=("workflow", "workflows", "routing", "decision tree", "flow"),
    ),
    FileEntry(
        path="aops-core/SKILLS.md",
        description="Skills index with invocation patterns",
        keywords=("skill", "skills", "command", "slash command"),
    ),
    FileEntry(
        path="indices/enforcement-map.md",
        description="Maps principles to enforcement mechanisms",
        keywords=(
            "enforcement",
            "enforcement-map",
            "hook enforcement",
            "gate",
            "policy",
        ),
    ),
    # --- Prompt Hydration System ---
    FileEntry(
        path="aops-core/agents/prompt-hydrator.md",
        description="Prompt hydrator agent definition (routing logic)",
        keywords=(
            "hydrator",
            "prompt-hydrator",
            "prompt hydration",
            "routing",
            "triage",
        ),
    ),
    FileEntry(
        path="aops-core/specs/prompt-hydration.md",
        description="Prompt hydration system spec",
        keywords=("hydrator", "prompt-hydrator", "hydration spec", "routing spec"),
    ),
    FileEntry(
        path="aops-core/hooks/user_prompt_submit.py",
        description="UserPromptSubmit hook (builds hydrator context)",
        keywords=(
            "user prompt",
            "prompt submit",
            "hook",
            "userpromptsubmit",
            "context injection",
        ),
    ),
    FileEntry(
        path="aops-core/hooks/templates/prompt-hydrator-context.md",
        description="Template for hydrator temp file",
        keywords=("hydrator template", "context template", "hydrator context"),
    ),
    FileEntry(
        path="aops-core/hooks/templates/prompt-hydration-instruction.md",
        description="Short instruction template for main agent",
        keywords=("hydration instruction", "instruction template"),
    ),
    # --- Workflow System ---
    FileEntry(
        path="aops-core/specs/workflow-system-spec.md",
        description="Workflow architecture and composition rules",
        keywords=(
            "workflow spec",
            "workflow system",
            "workflow architecture",
            "bases",
            "composition",
        ),
    ),
    FileEntry(
        path="aops-core/specs/workflow-constraints.md",
        description="Constraint checking and verification",
        keywords=("constraint", "constraints", "verification", "predicate"),
    ),
    FileEntry(
        path="workflows/feature-dev.md",
        description="Feature development workflow",
        keywords=("feature", "feature-dev", "development", "implement", "new feature"),
    ),
    FileEntry(
        path="workflows/debugging.md",
        description="Debugging workflow",
        keywords=("debug", "debugging", "investigate", "bug", "error", "fix"),
    ),
    FileEntry(
        path="workflows/framework-change.md",
        description="Framework governance change workflow",
        keywords=(
            "framework change",
            "governance",
            "framework modification",
            "aops change",
        ),
    ),
    FileEntry(
        path="workflows/decompose.md",
        description="Task decomposition workflow",
        keywords=("decompose", "decomposition", "break down", "subtask", "breakdown"),
    ),
    FileEntry(
        path="workflows/tdd-cycle.md",
        description="Test-driven development workflow (in aops-core)",
        keywords=("tdd", "test driven", "test first", "failing test"),
    ),
    FileEntry(
        path="workflows/base-tdd.md",
        description="TDD base pattern (composable)",
        keywords=("tdd", "test driven", "base-tdd"),
    ),
    FileEntry(
        path="workflows/base-task-tracking.md",
        description="Task tracking base pattern",
        keywords=("task tracking", "base-task", "task workflow"),
    ),
    FileEntry(
        path="workflows/simple-question.md",
        description="Simple question workflow (no task needed)",
        keywords=("simple question", "question", "explain", "what is"),
    ),
    # --- Task System ---
    FileEntry(
        path="aops-core/specs/work-management.md",
        description="Task system architecture and lifecycle",
        keywords=("task", "tasks", "work management", "task system", "task lifecycle"),
    ),
    FileEntry(
        path="aops-core/lib/task_storage.py",
        description="Task file storage implementation",
        keywords=("task storage", "task file", "task persistence"),
    ),
    FileEntry(
        path="aops-core/lib/task_index.py",
        description="Task index and graph relationships",
        keywords=("task index", "task graph", "dependencies", "blockers"),
    ),
    # --- Hooks ---
    FileEntry(
        path="aops-core/specs/hook-router.md",
        description="Hook routing and lifecycle spec",
        keywords=("hook", "hooks", "hook router", "pretooluse", "posttooluse"),
    ),
    FileEntry(
        path="aops-core/hooks/pre_tool_use.py",
        description="PreToolUse hook dispatcher",
        keywords=("pretooluse", "pre tool", "tool gate", "tool validation"),
    ),
    FileEntry(
        path="aops-core/hooks/post_tool_use.py",
        description="PostToolUse hook dispatcher",
        keywords=("posttooluse", "post tool", "after tool"),
    ),
    FileEntry(
        path="aops-core/hooks/gates/task_required_gate.py",
        description="Task-required gate (blocks Write/Edit without task)",
        keywords=("task gate", "task required", "write gate", "edit gate"),
    ),
    FileEntry(
        path="aops-core/hooks/gates/hydration_gate.py",
        description="Hydration gate (ensures hydrator was invoked)",
        keywords=("hydration gate", "hydrator gate"),
    ),
    # --- Agent System ---
    FileEntry(
        path="aops-core/agents/critic.md",
        description="Critic agent for plan review",
        keywords=("critic", "review", "plan review", "second opinion"),
    ),
    FileEntry(
        path="aops-core/agents/custodiet.md",
        description="Custodiet agent (ultra vires detection)",
        keywords=("custodiet", "ultra vires", "authority", "scope violation"),
    ),
    FileEntry(
        path="aops-core/specs/ultra-vires-custodiet.md",
        description="Ultra vires detection spec",
        keywords=("ultra vires", "custodiet spec", "authority violation"),
    ),
    FileEntry(
        path="aops-core/agents/qa.md",
        description="QA agent for verification",
        keywords=("qa", "quality", "verification", "validate", "test"),
    ),
    FileEntry(
        path="aops-core/agents/worker.md",
        description="Worker agent for task execution",
        keywords=("worker", "task worker", "executor"),
    ),
    # --- Skills ---
    FileEntry(
        path="aops-core/skills/commit/SKILL.md",
        description="Commit skill for git operations",
        keywords=("commit", "git", "push", "/commit"),
    ),
    FileEntry(
        path="aops-core/skills/remember/SKILL.md",
        description="Remember skill for knowledge persistence",
        keywords=("remember", "memory", "persist", "knowledge", "/remember"),
    ),
    FileEntry(
        path="aops-core/skills/framework/SKILL.md",
        description="Framework development skill",
        keywords=("framework skill", "framework dev", "/framework"),
    ),
    FileEntry(
        path="aops-core/skills/audit/SKILL.md",
        description="Audit skill for governance checking",
        keywords=("audit", "governance", "compliance", "/audit"),
    ),
    FileEntry(
        path="aops-core/skills/session-insights/SKILL.md",
        description="Session insights skill",
        keywords=("session insights", "insights", "reflection", "/session-insights"),
    ),
    FileEntry(
        path="aops-core/skills/hypervisor/SKILL.md",
        description="Hypervisor skill for batch processing",
        keywords=("hypervisor", "batch", "parallel", "/hypervisor"),
    ),
    # --- Specs ---
    FileEntry(
        path="aops-core/specs/enforcement.md",
        description="Enforcement architecture spec",
        keywords=("enforcement spec", "policy enforcement", "gate architecture"),
    ),
    FileEntry(
        path="aops-core/specs/plugin-architecture.md",
        description="Plugin system architecture",
        keywords=("plugin", "plugin architecture", "aops-core", "aops-tools"),
    ),
    FileEntry(
        path="aops-core/specs/verification-system.md",
        description="Verification and predicate system",
        keywords=("verification", "predicate", "assertion", "check"),
    ),
    FileEntry(
        path="aops-core/specs/framework-observability.md",
        description="Observability and logging spec",
        keywords=("observability", "logging", "metrics", "tracing"),
    ),
    FileEntry(
        path="aops-core/specs/session-insights-prompt.md",
        description="Session insights prompt engineering",
        keywords=("session insights", "transcript", "analysis"),
    ),
    # --- Session Management ---
    FileEntry(
        path="aops-core/lib/session_state.py",
        description="Session state management",
        keywords=("session state", "session", "state management"),
    ),
    FileEntry(
        path="aops-core/lib/session_reader.py",
        description="Session transcript reading",
        keywords=("session reader", "transcript", "conversation history"),
    ),
    FileEntry(
        path="aops-core/scripts/transcript.py",
        description="Transcript processing script",
        keywords=("transcript", "session transcript", "transcript parser"),
    ),
    # --- Paths and Config ---
    FileEntry(
        path="aops-core/lib/paths.py",
        description="Path resolution functions",
        keywords=("paths", "path resolution", "directory", "location"),
    ),
    FileEntry(
        path="aops-core/scripts/generate_framework_paths.py",
        description="Generate FRAMEWORK-PATHS.md",
        keywords=("framework paths", "path generation", "generate paths"),
    ),
    FileEntry(
        path="FRAMEWORK-PATHS.md",
        description="Resolved absolute paths (generated)",
        keywords=("framework paths", "absolute paths", "directory paths"),
    ),
)


def _normalize_text(text: str) -> str:
    """Normalize text for keyword matching (lowercase, collapse whitespace)."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_keywords_from_prompt(prompt: str) -> set[str]:
    """Extract potential keywords from prompt for matching."""
    normalized = _normalize_text(prompt)

    # Split into words and bigrams for matching
    words = set(normalized.split())

    # Also check for multi-word phrases
    # This allows matching "prompt hydrator" as a phrase
    return words | {normalized}


def get_relevant_file_paths(prompt: str, max_files: int = 10) -> list[dict[str, str]]:
    """
    Get file paths relevant to the given prompt.

    Analyzes the prompt for keywords and returns matching file entries.
    Returns only the most relevant files to avoid context bloat.

    Args:
        prompt: User's prompt text
        max_files: Maximum number of files to return (default 10)

    Returns:
        List of dicts with 'path', 'description', and 'absolute_path' keys.
        Sorted by relevance (more keyword matches first).
    """
    if not prompt:
        return []

    prompt_lower = _normalize_text(prompt)

    # Score each file entry by number of keyword matches
    scored_entries: list[tuple[int, FileEntry]] = []

    for entry in FILE_INDEX:
        score = 0
        for keyword in entry.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in prompt_lower:
                # Longer keyword matches are more specific, score higher
                score += len(keyword)

        if score > 0:
            scored_entries.append((score, entry))

    # Sort by score descending
    scored_entries.sort(key=lambda x: x[0], reverse=True)

    # Take top entries up to max_files
    results: list[dict[str, str]] = []
    for score, entry in scored_entries[:max_files]:
        try:
            abs_path = str(entry.absolute_path())
        except RuntimeError:
            # If AOPS not set, use relative path
            abs_path = f"$AOPS/{entry.path}"

        results.append(
            {
                "path": entry.path,
                "description": entry.description,
                "absolute_path": abs_path,
            }
        )

    return results


def format_file_paths_for_injection(file_paths: list[dict[str, str]]) -> str:
    """
    Format file paths as markdown for injection into hydrator context.

    Args:
        file_paths: List of file path dicts from get_relevant_file_paths()

    Returns:
        Markdown-formatted string for inclusion in hydrator context.
    """
    if not file_paths:
        return "(No specific files detected as relevant to this prompt)"

    lines = ["| File | Description |", "|------|-------------|"]

    for fp in file_paths:
        # Use relative path for readability, note absolute in description
        lines.append(f"| `{fp['path']}` | {fp['description']} |")

    return "\n".join(lines)


def get_formatted_relevant_paths(prompt: str, max_files: int = 10) -> str:
    """
    Convenience function: get relevant paths and format for injection.

    Args:
        prompt: User's prompt text
        max_files: Maximum number of files to return

    Returns:
        Markdown-formatted table of relevant file paths.
    """
    paths = get_relevant_file_paths(prompt, max_files)
    return format_file_paths_for_injection(paths)
