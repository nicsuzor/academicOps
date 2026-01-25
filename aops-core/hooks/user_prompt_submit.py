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
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

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
import hashlib

def get_hydration_temp_dir() -> Path:
    """Get the temporary directory for hydration context.

    1. Checks TMPDIR (provided by host CLI)
    2. If GEMINI_CLI set, calculates project-specific temp dir: ~/.gemini/tmp/sha256(AOPS)
    3. Fallback to /tmp/claude-hydrator
    """
    # 1. Check for standard temp dir env var
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        return Path(tmpdir)

    # 2. Gemini-specific discovery logic
    if os.environ.get("GEMINI_CLI"):
        try:
            # Determine project root (AOPS is set by setup.sh/settings.json)
            project_root = os.environ.get("AOPS")
            if not project_root:
                project_root = str(Path.cwd())
            
            # Calculate SHA256 hash of absolute project path (Gemini convention)
            abs_root = str(Path(project_root).resolve())
            project_hash = hashlib.sha256(abs_root.encode()).hexdigest()
            
            gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash
            if gemini_tmp.exists():
                return gemini_tmp
        except Exception:
            pass

    # 3. Default fallback for Claude Code
    return Path("/tmp/claude-hydrator")

TEMP_DIR = get_hydration_temp_dir()

# Cleanup threshold: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60

# Intent envelope max length
INTENT_MAX_LENGTH = 500


def load_framework_paths() -> str:
    """Load the Resolved Paths section from FRAMEWORK-PATHS.md.

    Returns just the path table, not the full file.
    """
    aops_root = get_aops_root()
    framework_path = aops_root / "FRAMEWORK-PATHS.md"

    if not framework_path.exists():
        return "(FRAMEWORK-PATHS.md not found - run: python3 aops-core/scripts/generate_framework_paths.py)"

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

    return "(Path table not found in FRAMEWORK-PATHS.md)"


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
    axioms_path = aops_root / "AXIOMS.md"

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
            ["python", str(task_cli_path), "list", "--status=active"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = active_result.stdout.strip() if active_result.returncode == 0 else ""

        # Get inbox work (ready to pick up)
        inbox_result = subprocess.run(
            ["python", str(task_cli_path), "list", "--status=inbox"],
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
            # Limit inbox work to first 10 lines to avoid context bloat
            inbox_lines = inbox.split("\n")[:12]
            sections.append(f"### Ready Tasks (inbox)\n\n" + "\n".join(inbox_lines))

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


def cleanup_old_temp_files() -> None:
    """Delete temp files older than 1 hour.

    Called on each hook invocation to prevent disk accumulation.
    """
    if not TEMP_DIR.exists():
        return

    cutoff = time.time() - CLEANUP_AGE_SECONDS
    for f in TEMP_DIR.glob("hydrate_*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass  # Ignore cleanup errors


def write_temp_file(content: str) -> Path:
    """Write content to temp file, return path.

    Raises:
        IOError: If temp file cannot be written (fail-fast)
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Use NamedTemporaryFile for unique names and proper handling
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="hydrate_",
        suffix=".md",
        dir=TEMP_DIR,
        delete=False,
    ) as f:
        f.write(content)
        return Path(f.name)


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
    # Cleanup old temp files first
    cleanup_old_temp_files()

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
    temp_path = write_temp_file(full_context)

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


def main():
    """Main hook entry point - writes context to temp file, returns short instruction."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception as e:
        # Fail-fast: no silent failures (P#8, P#25)
        print(f"ERROR: UserPromptSubmit hook failed to parse stdin JSON: {e}", file=sys.stderr)
        sys.exit(2)

    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")
    session_id = input_data.get("session_id", "")

    # Require session_id for state isolation
    if not session_id:
        # Fail-fast: session_id is required for state management (P#8, P#25)
        print("ERROR: UserPromptSubmit hook requires session_id for state isolation", file=sys.stderr)
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
            print(f"ERROR: UserPromptSubmit hook temp file write failed: {e}", file=sys.stderr)
            sys.exit(2)

    # Output JSON
    print(json.dumps(output_data))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
