#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Writes hydration context to temp file for token efficiency.
Returns short instruction telling main agent to spawn prompt-hydrator
with the temp file path.

Exit codes:
    0: Success
    1: Infrastructure failure (temp file write failed - fail-fast)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.hook_utils import (
    cleanup_old_temp_files as _cleanup_temp,
    get_hook_temp_dir,
    write_temp_file as _write_temp,
)
from lib.paths import get_aops_root
from lib.file_index import get_formatted_relevant_paths
from lib.session_reader import extract_router_context
from lib.session_state import (
    set_hydration_pending,
    clear_hydration_pending,
    set_gates_bypassed,
    clear_reflection_output,
)
from lib.template_loader import load_template

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"
SIMPLE_QUESTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "simple-question-instruction.md"

# Temp directory category (matches hydration_gate.py)
TEMP_CATEGORY = "hydrator"
FILE_PREFIX = "hydrate_"


def get_hydration_temp_dir(input_data: dict[str, Any] | None = None) -> Path:
    """Get the temporary directory for hydration context.

    Uses shared hook_utils for consistent temp directory resolution.
    """
    return get_hook_temp_dir(TEMP_CATEGORY, input_data)


# Intent envelope max length
INTENT_MAX_LENGTH = 500


def load_framework_paths() -> str:
    """Load the Resolved Paths section from .agent/PATHS.md.

    Returns just the path table, not the full file.
    """
    aops_root = get_aops_root()
    framework_path = aops_root / ".agent/PATHS.md"

    if not framework_path.exists():
        return "(.agent/PATHS.md not found - run: python3 aops-core/scripts/generate_framework_paths.py)"

    content = framework_path.read_text()

    # Extract the "Resolved Paths" section
    if "## Resolved Paths" in content:
        start = content.index("## Resolved Paths")
        # Find next section or end
        rest = content[start:]
        if "\n## " in rest[10:]:  # Skip the header we just found
            end = rest.index("\n## ", 10)
            return rest[:end].strip()
        return rest.strip()

    return "(Path table not found in .agent/PATHS.md)"


def _strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def _load_project_workflows(prompt: str = "") -> str:
    """Load project-specific workflows from .agent/workflows/ in cwd.

    Projects can define their own workflows in .agent/workflows/*.md.
    If a WORKFLOWS.md index exists in .agent/, use that; otherwise
    list available workflow files and include relevant content based on prompt.

    Args:
        prompt: User prompt to detect relevant workflow types

    Returns:
        Project workflows section, or empty string if none found.
    """
    cwd = Path.cwd()
    project_agent_dir = cwd / ".agent"

    if not project_agent_dir.exists():
        return ""

    # Check for project workflow index first
    project_index = project_agent_dir / "WORKFLOWS.md"
    if project_index.exists():
        content = project_index.read_text()
        return f"\n\n## Project-Specific Workflows ({cwd.name})\n\n{_strip_frontmatter(content)}"

    # Otherwise, list workflow files in .agent/workflows/
    workflows_dir = project_agent_dir / "workflows"
    if not workflows_dir.exists():
        return ""

    workflow_files = sorted(workflows_dir.glob("*.md"))
    if not workflow_files:
        return ""

    # Build a simple index from the files
    lines = [f"\n\n## Project-Specific Workflows ({cwd.name})", ""]
    lines.append(f"Location: `{workflows_dir}`\n")
    lines.append("| Workflow | File |")
    lines.append("|----------|------|")
    for wf in workflow_files:
        name = wf.stem.replace("-", " ").replace("_", " ").title()
        lines.append(f"| {name} | `{wf.name}` |")

    # Detect and include relevant workflow content based on prompt keywords
    prompt_lower = prompt.lower()
    workflow_keywords = {
        "TESTING.md": ["test", "pytest", "e2e", "unit test", "mock"],
        "DEBUGGING.md": ["debug", "investigate", "error", "traceback", "fix bug"],
        "DEVELOPMENT.md": ["develop", "implement", "feature", "add", "create"],
    }

    included_workflows = []
    for wf_file in workflow_files:
        keywords = workflow_keywords.get(wf_file.name, [])
        if any(kw in prompt_lower for kw in keywords):
            try:
                content = wf_file.read_text()
                included_workflows.append(
                    f"\n\n### {wf_file.stem} (Project Instructions)\n\n{_strip_frontmatter(content)}"
                )
            except (IOError, OSError):
                pass  # Skip unreadable files

    if included_workflows:
        lines.append("\n" + "".join(included_workflows))

    return "\n".join(lines)


def load_workflows_index(prompt: str = "") -> str:
    """Load WORKFLOWS.md for hydrator context.

    Pre-loads workflow index so hydrator doesn't need to Read() at runtime.
    Also checks for project-specific workflows in .agent/workflows/.
    Returns content after frontmatter separator.

    Args:
        prompt: User prompt to detect relevant workflow types for project workflows
    """
    aops_root = get_aops_root()
    workflows_path = aops_root / "WORKFLOWS.md"

    if not workflows_path.exists():
        return "(WORKFLOWS.md not found)"

    content = workflows_path.read_text()
    base_workflows = _strip_frontmatter(content)

    # Append project-specific workflows if present (passing prompt for relevance detection)
    project_workflows = _load_project_workflows(prompt)

    return base_workflows + project_workflows


def load_axioms() -> str:
    """Load AXIOMS.md for hydrator context.

    Pre-loads axioms so hydrator can select relevant principles.
    Returns content after frontmatter separator.
    """
    aops_root = get_aops_root()
    axioms_path = aops_root / "aops-core" / "AXIOMS.md"

    if not axioms_path.exists():
        return "(AXIOMS.md not found)"

    content = axioms_path.read_text()

    # Skip frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content.strip()


def load_heuristics() -> str:
    """Load HEURISTICS.md for hydrator context.

    Pre-loads heuristics so hydrator doesn't need to Read() at runtime.
    Returns content after frontmatter separator.
    """
    aops_root = get_aops_root()
    heuristics_path = aops_root / "HEURISTICS.md"

    if not heuristics_path.exists():
        return "(HEURISTICS.md not found)"

    content = heuristics_path.read_text()

    # Skip frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content.strip()


def load_skills_index() -> str:
    """Load SKILLS.md for hydrator context.

    Pre-loads skills index so hydrator can immediately recognize skill invocations
    without needing to search memory. Returns content after frontmatter separator.
    """
    aops_root = get_aops_root()
    skills_path = aops_root / "SKILLS.md"

    if not skills_path.exists():
        return "(SKILLS.md not found - hydrator will use memory search for skill recognition)"

    content = skills_path.read_text()

    # Skip frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content.strip()


def get_task_work_state() -> str:
    """Query task system for current work state.

    Returns formatted markdown with:
    - Active tasks (what user is actively working on)
    - Ready tasks (available work with no blockers)

    Gracefully returns empty string if task CLI not found or on failure.
    """
    # Get task CLI path
    aops_root = get_aops_root()
    task_cli_path = aops_root / "scripts" / "task_cli.py"

    if not task_cli_path.exists():
        return ""

    try:
        # Get active work
        active_result = subprocess.run(
            ["python", str(task_cli_path), "list", "--status=active", "--limit=20"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = active_result.stdout.strip() if active_result.returncode == 0 else ""

        # Get inbox work (ready to pick up)
        inbox_result = subprocess.run(
            ["python", str(task_cli_path), "list", "--status=inbox", "--limit=20"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        inbox = inbox_result.stdout.strip() if inbox_result.returncode == 0 else ""

        if not active and not inbox:
            return ""

        sections = []
        if active:
            sections.append(f"### Active Tasks\n\n{active}")
        if inbox:
            sections.append(f"### Incoming Tasks (inbox)\n\n{inbox}")

        return "\n\n".join(sections)

    except (subprocess.TimeoutExpired, OSError):
        return ""  # Graceful degradation


def get_session_id() -> str:
    """Get session ID from environment.

    Returns CLAUDE_SESSION_ID if set, raises ValueError otherwise.
    Session ID is required for state isolation.
    """
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id:
        raise ValueError("CLAUDE_SESSION_ID not set - cannot save session state")
    return session_id


def write_initial_hydrator_state(
    session_id: str, prompt: str, hydration_pending: bool = True
) -> None:
    """Write initial hydrator state with pending workflow.

    Called after processing prompt to set hydration pending flag.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: User's original prompt
        hydration_pending: Whether hydration gate should block until hydrator invoked
    """
    if hydration_pending:
        set_hydration_pending(session_id, prompt)
    else:
        clear_hydration_pending(session_id)


def cleanup_old_temp_files(input_data: dict[str, Any] | None = None) -> None:
    """Delete temp files older than 1 hour.

    Called on each hook invocation to prevent disk accumulation.
    """
    try:
        temp_dir = get_hydration_temp_dir(input_data)
        _cleanup_temp(temp_dir, FILE_PREFIX)
    except RuntimeError:
        pass  # Graceful degradation if temp dir resolution fails


def write_temp_file(content: str, input_data: dict[str, Any] | None = None) -> Path:
    """Write content to temp file, return path.

    Raises:
        IOError: If temp file cannot be written (fail-fast)
    """
    temp_dir = get_hydration_temp_dir(input_data)
    _cleanup_temp(temp_dir, FILE_PREFIX)  # Ensure cleanup happens before write
    return _write_temp(content, temp_dir, FILE_PREFIX)


def build_hydration_instruction(
    session_id: str, prompt: str, transcript_path: str | None = None
) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Writes full context to temp file, returns short instruction with file path.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: The user's original prompt
        transcript_path: Path to session transcript for context extraction

    Returns:
        Short instruction string (<300 tokens) with temp file path

    Raises:
        IOError: If temp file write fails (fail-fast per AXIOM #7)
    """
    # Build input_data for hook_utils resolution
    input_data = {"transcript_path": transcript_path} if transcript_path else None

    # Cleanup old temp files first
    cleanup_old_temp_files(input_data)

    # Extract session context from transcript
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                # ctx already includes "## Session Context" header
                session_context = f"\n\n{ctx}"
        except FileNotFoundError:
            # Expected: transcript may not exist yet for new sessions
            pass
        except Exception as e:
            # Unexpected: I/O errors, parsing failures - log but continue
            # Context is optional, so we degrade gracefully
            import logging

            logging.getLogger(__name__).debug(
                f"Context extraction failed (degrading gracefully): {type(e).__name__}: {e}"
            )

    # Load framework paths from FRAMEWORK-PATHS.md (DRY - single source of truth)
    framework_paths = load_framework_paths()

    # Pre-load stable framework docs (reduces hydrator runtime I/O)
    workflows_index = load_workflows_index(prompt)
    skills_index = load_skills_index()
    axioms = load_axioms()
    heuristics = load_heuristics()

    # Get task work state (active and inbox tasks)
    task_state = get_task_work_state()

    # Get relevant file paths based on prompt keywords (selective injection)
    relevant_files = get_formatted_relevant_paths(prompt, max_files=10)

    # Build full context for temp file
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        framework_paths=framework_paths,
        relevant_files=relevant_files,
        workflows_index=workflows_index,
        skills_index=skills_index,
        axioms=axioms,
        heuristics=heuristics,
        task_state=task_state,
    )

    # Write to temp file (raises IOError on failure - fail-fast)
    temp_path = write_temp_file(full_context, input_data)

    # Write initial hydrator state for downstream gates
    write_initial_hydrator_state(session_id, prompt)

    # Truncate prompt for description
    prompt_preview = prompt[:80].replace("\n", " ").strip()
    if len(prompt) > 80:
        prompt_preview += "..."

    # Build short instruction with file path
    instruction_template = load_template(INSTRUCTION_TEMPLATE_FILE)
    instruction = instruction_template.format(
        prompt_preview=prompt_preview,
        temp_path=str(temp_path),
    )

    return instruction


def should_skip_hydration(prompt: str) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - User ignore shortcut (prompts starting with '.')
    """
    prompt_stripped = prompt.strip()
    # Agent/task completion notifications from background Task agents
    if prompt_stripped.startswith("<agent-notification>"):
        return True
    if prompt_stripped.startswith("<task-notification>"):
        return True
    # Skill invocations - already have instructions, don't need routing
    if prompt_stripped.startswith("/"):
        return True
    # User ignore shortcut - user explicitly wants no hydration
    if prompt_stripped.startswith("."):
        return True
    return False


# Keywords that indicate work/action requests (not pure questions)
# These are checked with word boundaries to avoid false positives
# (e.g., "does" should not match "do", "commits" should not match "commit")
_ACTION_KEYWORDS = frozenset([
    # Imperatives
    "add", "create", "write", "implement", "fix", "update", "change", "modify",
    "delete", "remove", "refactor", "move", "rename", "build", "deploy",
    "execute", "install", "configure", "set up", "setup", "enable", "disable",
    # Request forms
    "can you", "could you", "would you", "please", "help me", "i need you to",
    "i want you to", "make", "let's",
    # File operations
    "edit", "save", "push", "merge", "pull request",
])

# Separate patterns that need word-boundary matching
# "commit" shouldn't match "commits" when talking about git history
# "do" shouldn't match "does" in questions
# "run" shouldn't match "running" when describing current state
_ACTION_KEYWORDS_WORD_BOUNDARY = frozenset([
    "commit", "do", "pr", "run",
])

# Interrogative starters that signal pure questions
_QUESTION_STARTERS = (
    "what ", "what's", "whats",
    "how ", "how's", "hows",
    "where ", "where's", "wheres",
    "when ", "when's", "whens",
    "why ", "why's", "whys",
    "which ",
    "who ", "who's", "whos",
    "is ", "are ", "was ", "were ",
    "does ", "do ", "did ",
    "can ", "could ", "would ", "should ",
    "has ", "have ", "had ",
    "explain", "describe", "tell me about", "tell me what",
)


def _has_word_boundary_match(text: str, word: str) -> bool:
    """Check if word appears with word boundaries in text.

    Returns True if 'word' appears as a standalone word in 'text',
    not as part of another word (e.g., 'do' matches ' do ' but not 'does').
    """
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text))


def is_pure_question(prompt: str) -> bool:
    """Detect if prompt is a pure informational question.

    Pure questions:
    - Start with interrogative words (what, how, where, why, when, which, who)
    - Don't contain action keywords (add, create, fix, implement, etc.)
    - Don't contain imperatives or request forms

    Returns True for questions that should fast-track to simple-question workflow.

    Examples that ARE pure questions:
    - "What is the hydrator?"
    - "How does the task system work?"
    - "Where are errors handled?"
    - "Why is this test failing?" (investigation question, not action request)
    - "Explain the architecture"

    Examples that are NOT pure questions:
    - "What should I add to fix this?" (contains "add", "fix")
    - "How can you help me implement X?" (contains "implement", "help me")
    - "Can you create a new file?" (contains "create", "can you")
    - "Please explain and then fix it" (contains "please", "fix")
    """
    prompt_lower = prompt.strip().lower()

    # Must start with interrogative or explanation request
    if not prompt_lower.startswith(_QUESTION_STARTERS):
        return False

    # Check for action keywords that indicate work request (substring match)
    for keyword in _ACTION_KEYWORDS:
        if keyword in prompt_lower:
            return False

    # Check for word-boundary keywords (avoid "do" matching "does", etc.)
    for keyword in _ACTION_KEYWORDS_WORD_BOUNDARY:
        if _has_word_boundary_match(prompt_lower, keyword):
            return False

    # No action keywords found - this is a pure question
    return True


def build_simple_question_instruction(prompt: str) -> str:
    """Build fast-track instruction for pure questions.

    Skips full hydration context (workflows, axioms, heuristics, task state)
    and returns a minimal instruction that routes directly to simple-question
    workflow behavior.

    Args:
        prompt: The user's question

    Returns:
        Short instruction string for answering directly
    """
    template = load_template(SIMPLE_QUESTION_TEMPLATE_FILE)
    return template.format(prompt=prompt)


def main():
    """Main hook entry point - writes context to temp file, returns short instruction."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception as e:
        # Fail-fast: no silent failures (P#8, P#25)
        print(
            f"ERROR: UserPromptSubmit hook failed to parse stdin JSON: {e}",
            file=sys.stderr,
        )
        sys.exit(2)

    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")
    session_id = input_data.get("session_id", "")

    # Require session_id for state isolation
    if not session_id:
        # Fail-fast: session_id is required for state management (P#8, P#25)
        print(
            "ERROR: UserPromptSubmit hook requires session_id for state isolation",
            file=sys.stderr,
        )
        sys.exit(2)

    # Clear reflection tracking flag for new user prompt
    # This tracks whether the agent outputs a Framework Reflection before session end
    clear_reflection_output(session_id)

    # Skip hydration for system messages, skill invocations, and user ignore shortcut
    if should_skip_hydration(prompt):
        # Write state with hydration_pending=False so gate doesn't block
        write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
        # If '.' prefix, also set gates_bypassed for task_required_gate
        if prompt.strip().startswith("."):
            set_gates_bypassed(session_id, True)
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",  # No hydration needed
            }
        }
        print(json.dumps(output_data))
        sys.exit(0)

    # Fast-track for pure questions - skip full hydration context
    if is_pure_question(prompt):
        # Write state with hydration_pending=False (no hydrator agent needed)
        write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
        simple_instruction = build_simple_question_instruction(prompt)
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": simple_instruction,
            }
        }
        print(json.dumps(output_data))
        sys.exit(0)

    # Build hydration instruction (writes temp file)
    output_data: dict[str, Any] = {}
    exit_code = 0

    if prompt:
        try:
            hydration_instruction = build_hydration_instruction(
                session_id, prompt, transcript_path
            )
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": hydration_instruction,
                }
            }
        except (IOError, OSError) as e:
            # Fail-fast on infrastructure errors (P#8, P#25)
            print(
                f"ERROR: UserPromptSubmit hook temp file write failed: {e}",
                file=sys.stderr,
            )
            sys.exit(2)

    # Output JSON
    print(json.dumps(output_data))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
