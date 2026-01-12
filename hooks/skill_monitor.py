"""Skill Monitor for PreToolUse hook - domain drift detection and injection.

Detects when tool operations shift to a different domain than the active skill,
and injects relevant skill context to guide the agent.

This is a soft enforcement gate - it injects context but doesn't block.
"""

from __future__ import annotations

import os
from typing import Any

from lib.session_state import load_hydrator_state

# Domain patterns from REMINDERS.md - ordered by priority (framework > python > analyst)
# Framework patterns are checked first since hooks/*.py should be framework, not python
DOMAIN_PATTERNS: dict[str, list[str]] = {
    "framework": [
        "hooks/",
        "skills/",
        "agents/",
        "commands/",
        "AXIOMS",
        "HEURISTICS",
        "REMINDERS",
    ],
    "python-dev": [".py", "pytest", "mypy", "ruff"],
    "analyst": ["dbt/", "streamlit", ".sql"],
}

# Priority order for domain detection (higher priority domains checked first)
DOMAIN_PRIORITY = ["framework", "analyst", "python-dev"]

# Skill context summaries for injection (brief, not full skill files)
# For framework, see skills/framework/conventions-summary.md for comprehensive version
SKILL_SUMMARIES: dict[str, str] = {
    "framework": """Key constraints (see conventions-summary.md for full context):
- Categorical imperative: Every change must be justifiable as universal rule
- HALT protocol: Stop, state, ask, document when uncertain
- Skill delegation: User data ops require skill invocation
- Plan-mode required for infrastructure changes
Invoke Skill(skill='framework') for component patterns.""",
    "python-dev": """Key constraints:
- Fail-fast: No defaults, no fallbacks, no silent failures
- Type hints required on all functions
- Use pytest for testing, mypy for type checking
- Follow existing code patterns in the codebase""",
    "analyst": """Key constraints:
- Research data is immutable - never modify source data
- Use dbt for data transformations
- Streamlit for dashboards
- Document all data lineage""",
}


def get_cwd() -> str:
    """Get current working directory from environment."""
    return os.environ.get("CLAUDE_CWD", os.getcwd())


def detect_domain(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Detect domain from tool name and input args.

    Extracts file paths and commands from tool input, then matches
    against DOMAIN_PATTERNS.

    Args:
        tool_name: Name of the tool being called
        tool_input: Tool input arguments

    Returns:
        Domain name if detected, None otherwise
    """
    # Collect all text to search for domain signals
    search_texts: list[str] = []

    # File paths from various tools
    if "file_path" in tool_input:
        search_texts.append(tool_input["file_path"])
    if "path" in tool_input:
        search_texts.append(tool_input["path"])
    if "pattern" in tool_input:
        search_texts.append(tool_input["pattern"])

    # Commands from Bash
    if "command" in tool_input:
        search_texts.append(tool_input["command"])

    if not search_texts:
        return None

    combined_text = " ".join(search_texts)

    # Check domains in priority order
    for domain in DOMAIN_PRIORITY:
        patterns = DOMAIN_PATTERNS[domain]
        for pattern in patterns:
            if pattern in combined_text:
                return domain

    return None


def check_drift(active_skill: str, detected_domain: str | None) -> bool:
    """Check if there's drift between active skill and detected domain.

    Args:
        active_skill: Currently active skill from hydrator state
        detected_domain: Domain detected from tool operation

    Returns:
        True if drift detected, False otherwise
    """
    # No drift if no domain detected
    if detected_domain is None:
        return False

    # No drift if no active skill (nothing to drift from)
    if not active_skill:
        return False

    # Drift if domains don't match
    return active_skill != detected_domain


def inject_skill_context(skill_name: str) -> str:
    """Generate skill context injection markdown.

    Args:
        skill_name: Name of skill to inject context for

    Returns:
        Markdown string with skill context
    """
    summary = SKILL_SUMMARIES.get(skill_name, "No specific constraints documented.")

    return f"""## Skill Context Injection

Domain shifted to: {skill_name}
Active skill: {skill_name}

{summary}
"""


def check_skill_monitor(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Main entry point - check for domain drift and return injection if needed.

    Args:
        tool_name: Name of tool being called
        tool_input: Tool input arguments

    Returns:
        Skill context injection string if drift detected, None otherwise
    """
    cwd = get_cwd()

    # Load hydrator state to get active skill
    state = load_hydrator_state(cwd)
    if state is None:
        # No state = no active skill = no drift detection possible
        return None

    active_skill = state.get("active_skill", "")

    # Detect domain from tool operation
    detected_domain = detect_domain(tool_name, tool_input)

    # Check for drift
    if check_drift(active_skill, detected_domain):
        return inject_skill_context(detected_domain)  # type: ignore[arg-type]

    return None
