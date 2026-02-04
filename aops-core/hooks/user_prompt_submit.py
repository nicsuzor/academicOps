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
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.hook_utils import (
    cleanup_old_temp_files as _cleanup_temp,
    get_hook_temp_dir,
    write_temp_file as _write_temp,
)
from lib.paths import (
    get_plugin_root,
    get_aops_root,
    get_data_root,
    get_skills_dir,
    get_hooks_dir,
    get_commands_dir,
    get_tests_dir,
    get_config_dir,
    get_workflows_dir,
    get_indices_dir,
    get_sessions_dir,
    get_projects_dir,
    get_logs_dir,
    get_context_dir,
    get_goals_dir,
)
from lib.file_index import get_formatted_relevant_paths
from lib.session_reader import extract_router_context
from lib.session_state import (
    set_hydration_pending,
    set_hydration_temp_path,
    clear_hydration_pending,
    set_gates_bypassed,
    clear_reflection_output,
    get_or_create_session_state,
    save_session_state,
)
from lib.template_loader import load_template

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"

# Temp directory category (matches hydration_gate.py)
TEMP_CATEGORY = "hydrator"

# Debug log - opt-in via AOPS_DEBUG_LOG environment variable
# If not set, debug logging is disabled (no-op)
_DEBUG_LOG_PATH: Path | None = None
if "AOPS_DEBUG_LOG" in os.environ:
    _DEBUG_LOG_PATH = Path(os.environ["AOPS_DEBUG_LOG"])


def _log_debug(msg: str) -> None:
    """Log debug message to file if AOPS_DEBUG_LOG is set."""
    if _DEBUG_LOG_PATH is None:
        return
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            ts = datetime.now().isoformat()
            f.write(f"[{ts}] {msg}\n")
    except OSError as e:
        # Debug logging failure is non-fatal but we log to stderr for visibility
        import sys
        print(f"Debug log write failed: {e}", file=sys.stderr)


FILE_PREFIX = "hydrate_"


def get_hydration_temp_dir(input_data: dict[str, Any] | None = None) -> Path:
    """Get the temporary directory for hydration context.

    Uses shared hook_utils for consistent temp directory resolution.
    """
    return get_hook_temp_dir(TEMP_CATEGORY, input_data)


# Intent envelope max length
INTENT_MAX_LENGTH = 500


def load_framework_paths() -> str:
    """Generate the Framework Paths table dynamically.

    Previously read from .agent/PATHS.md, now generated on fly.
    """
    try:
        plugin_root = get_plugin_root()
        aops_root = get_aops_root()
        # data_root = get_data_root()  # May raise if not set, handled by catch-all

        # Build path table dynamically
        lines = [
            "## Resolved Paths",
            "",
            "These are the concrete absolute paths for this framework instance:",
            "",
            "| Path Variable | Resolved Path |",
            "|--------------|---------------|",
            f"| $AOPS        | {aops_root} |",
            f"| $PLUGIN_ROOT | {plugin_root} |",
            f"| $ACA_DATA    | {get_data_root()} |",
            "",
            "## Framework Directories",
            "",
            "| Directory | Absolute Path |",
            "|-----------|---------------|",
            f"| Skills    | {get_skills_dir()} |",
            f"| Hooks     | {get_hooks_dir()} |",
            f"| Commands  | {get_commands_dir()} |",
            f"| Tests     | {get_tests_dir()} |",
            f"| Config    | {get_config_dir()} |",
            f"| Workflows | {get_workflows_dir()} |",
            f"| Indices   | {get_indices_dir()} |",
            "",
            "## Data Directories",
            "",
            "| Directory | Absolute Path |",
            "|-----------|---------------|",
            f"| Sessions  | {get_sessions_dir()} |",
            f"| Projects  | {get_projects_dir()} |",
            f"| Data Logs | {get_logs_dir()} |",
            f"| Context   | {get_context_dir()} |",
            f"| Goals     | {get_goals_dir()} |",
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"(Error gathering framework paths: {e})"


def load_mcp_tools_context() -> str:
    """List available MCP tools and servers."""
    # These are the known servers in the framework
    servers = {
        "task_manager": "Manages the hierarchical task system (create, update, complete, decompose)",
        "memory": "Semantic memory retrieval and recall",
        "outlook": "Integration with Outlook calendar and messages",
    }

    lines = ["## Available MCP Servers", ""]
    lines.append("| Server | Description |")
    lines.append("|--------|-------------|")
    for name, desc in servers.items():
        lines.append(f"| {name} | {desc} |")

    return "\n".join(lines)


def load_environment_variables_context() -> str:
    """List relevant environment variables."""
    vars_to_check = [
        "AOPS",
        "ACA_DATA",
        "POLECAT_HOME",
        "NTFY_TOPIC",
        "HYDRATION_GATE_MODE",
        "CUSTODIET_MODE",
        "TASK_GATE_MODE",
        "CLAUDE_SESSION_ID",
    ]

    lines = ["## Environment Variables", ""]
    lines.append("| Variable | Value |")
    lines.append("|----------|-------|")
    for var in vars_to_check:
        value = os.environ.get(var, "(not set)")
        lines.append(f"| {var} | `{value}` |")

    return "\n".join(lines)


def load_project_paths_context() -> str:
    """Load project-specific paths from polecat.yaml."""
    polecat_config = Path.home() / ".aops" / "polecat.yaml"
    if not polecat_config.exists():
        return ""

    try:
        import yaml
        with open(polecat_config) as f:
            config = yaml.safe_load(f)

        projects = config.get("projects", {})
        if not projects:
            return ""

        lines = ["## Project-Specific Paths", ""]
        lines.append("| Project | Path | Default Branch |")
        lines.append("|---------|------|----------------|")
        for slug, proj in projects.items():
            path = proj.get("path", "")
            branch = proj.get("default_branch", "main")
            lines.append(f"| {slug} | `{path}` | {branch} |")
        return "\n".join(lines)
    except Exception as e:
        # Don't fail the whole hook if yaml or polecat.yaml loading fails
        return f"<!-- Project paths skipped: {e} -->"


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
        # Internal dict lookup - empty list for unlisted files is correct (no keywords = no match)
        keywords = workflow_keywords.get(wf_file.name)
        if keywords is None:
            keywords = []
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
    plugin_root = get_plugin_root()
    workflows_path = plugin_root / "WORKFLOWS.md"

    if not workflows_path.exists():
        return "(WORKFLOWS.md not found)"

    content = workflows_path.read_text()
    base_workflows = _strip_frontmatter(content)

    # Append project-specific workflows if present (passing prompt for relevance detection)
    project_workflows = _load_project_workflows(prompt)

    return base_workflows + project_workflows


def load_project_context_index() -> str:
    """Load JIT project context index from .agent/context-map.json.

    Returns a markdown list of available topics and file paths.
    Does NOT read the files - leaves that decision to the agent (P#49).

    Returns:
        Formatted markdown index, or empty string.
    """
    cwd = Path.cwd()
    map_file = cwd / ".agent" / "context-map.json"

    if not map_file.exists():
        return ""

    try:
        context_map = json.loads(map_file.read_text())
    except (json.JSONDecodeError, OSError):
        return ""

    # Validate structure - docs array is required if context-map exists
    if "docs" not in context_map:
        return ""  # No docs key = graceful skip (optional feature)
    docs = context_map["docs"]
    if not isinstance(docs, list):
        return ""  # Invalid structure = graceful skip

    if not docs:
        return ""

    lines = []

    # Header handled in template

    for doc in docs:
        # Validate required fields per doc entry
        if not isinstance(doc, dict):
            continue  # Skip malformed entries
        topic = doc.get("topic")
        if topic is None:
            topic = "Unknown"
        topic = topic.replace("_", " ").title()
        path = doc.get("path")
        if path is None:
            path = ""
        desc = doc.get("description")
        if desc is None:
            desc = ""
        keywords_list = doc.get("keywords")
        if keywords_list is None:
            keywords_list = []
        keywords = ", ".join(keywords_list)

        entry = f"- **{topic}** (`{path}`)"
        if desc:
            entry += f": {desc}"
        if keywords:
            entry += f" [Keywords: {keywords}]"

        lines.append(entry)

    if not lines:
        return ""

    return "\n".join(lines)


def load_axioms() -> str:
    """Load AXIOMS.md for hydrator context.

    Pre-loads axioms so hydrator can select relevant principles.
    Returns content after frontmatter separator.
    """
    plugin_root = get_plugin_root()
    axioms_path = plugin_root / "AXIOMS.md"

    # Fail fast, raises if file doesn't exist
    content = axioms_path.read_text()

    # Skip frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content.strip()


# <!-- NS: these repetitive functions should be refactored. -->
def load_heuristics() -> str:
    """Load HEURISTICS.md for hydrator context.

    Pre-loads heuristics so hydrator doesn't need to Read() at runtime.
    Returns content after frontmatter separator.
    """
    plugin_root = get_plugin_root()
    heuristics_path = plugin_root / "HEURISTICS.md"

    # Fail fast, raises if file doesn't exist
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
    plugin_root = get_plugin_root()
    skills_path = plugin_root / "SKILLS.md"

    # Fail fast, raises if file doesn't exist
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
    plugin_root = get_plugin_root()
    task_cli_path = plugin_root / "scripts" / "task_cli.py"

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
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id is None:
        raise ValueError("CLAUDE_SESSION_ID not set - cannot save session state")
    if not session_id:
        raise ValueError("CLAUDE_SESSION_ID is empty - cannot save session state")
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

    # Load available MCP tools and servers
    mcp_tools = load_mcp_tools_context()

    # Load relevant environment variables
    env_vars = load_environment_variables_context()

    # Load project-specific paths
    project_paths = load_project_paths_context()

    # Pre-load stable framework docs (reduces hydrator runtime I/O)
    workflows_index = load_workflows_index(prompt)
    skills_index = load_skills_index()
    axioms = load_axioms()
    heuristics = load_heuristics()

    # Get task work state (active and inbox tasks)
    task_state = get_task_work_state()

    # Get relevant file paths based on prompt keywords (selective injection)
    relevant_files = get_formatted_relevant_paths(prompt, max_files=10)

    # Load JIT project context index (P#49: Agent decides what to read)
    project_context_index = load_project_context_index()

    # Build full context for temp file
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        framework_paths=framework_paths,
        mcp_tools=mcp_tools,
        env_vars=env_vars,
        project_paths=project_paths,
        project_context_index=project_context_index,
        relevant_files=relevant_files,
        workflows_index=workflows_index,
        skills_index=skills_index,
        axioms=axioms,
        heuristics=heuristics,
        task_state=task_state,
    )

    # Write to temp file (raises IOError on failure - fail-fast)
    temp_path = write_temp_file(full_context, input_data)

    # Store temp path in session state so hydration gate can include it in block message
    set_hydration_temp_path(session_id, str(temp_path))

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


def is_followup_prompt(session_id: str, prompt: str) -> bool:
    """Detect if this is a follow-up to existing session work.

    Follow-ups are interactive continuations that don't need full hydration
    ceremony (hydrator agent + critic). They inherit context from the active
    session.

    Returns True if ALL conditions met:
    1. Session already has work context (turns_since_hydration > 0 OR task bound)
    2. Prompt is short (< 30 words) - long prompts likely introduce new scope
    3. Prompt contains continuation markers indicating same-context work

    Rationale (aops-a63694ce):
    - Full hydration adds ceremony for simple requests like "save to daily note"
    - Follow-ups should inherit active task binding (no new task needed)
    - Context injection still happens via MCP tools (memory, tasks) which bypass gates
    """
    from lib.session_state import load_session_state

    # Check session state for existing work context
    state = load_session_state(session_id)
    if not state:
        return False

    # Check for existing work context - either hydrated or task-bound
    # Use explicit key checks for fail-fast (P#8)
    has_hydration_context = False
    has_task_context = False

    if "hydration" in state:
        hydration = state["hydration"]
        if "turns_since_hydration" in hydration:
            turns_since = hydration["turns_since_hydration"]
            if turns_since > 0:  # Has done work since hydration
                has_hydration_context = True

    if "state" in state:
        session_state_data = state["state"]
        if "current_task" in session_state_data:
            if session_state_data["current_task"]:  # Non-empty task ID
                has_task_context = True

    if not has_hydration_context and not has_task_context:
        return False  # No existing work - needs full hydration

    # Short prompt check (< 30 words)
    words = prompt.split()
    if len(words) > 30:
        return False  # Too long - likely new work scope

    # Continuation markers indicating same-context work
    continuation_markers = [
        # Pronouns referring to prior context
        "this", "that", "those", "these", "it",
        # Additive markers
        "also", "too", "as well", "while you're at it",
        # Repetition markers
        "same", "again", "another",
        # Action verbs for quick tasks
        "save", "add", "put", "update", "log", "note",
        # Continuation phrases
        "one more", "quick", "before you go",
    ]
    prompt_lower = prompt.lower()
    has_continuation = any(marker in prompt_lower for marker in continuation_markers)

    return has_continuation


def should_skip_hydration(prompt: str, session_id: str | None = None) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - Expanded slash commands (containing <command-name>/ tag)
    - User ignore shortcut (prompts starting with '.')
    - Follow-up prompts within active session work (requires session_id)
    """
    prompt_stripped = prompt.strip()
    # Agent/task completion notifications from background Task agents
    if prompt_stripped.startswith("<agent-notification>"):
        return True
    if prompt_stripped.startswith("<task-notification>"):
        return True
    # Expanded slash commands - the skill expansion IS the hydration
    # These contain <command-name>/xxx</command-name> tags from Claude Code
    if "<command-name>/" in prompt:
        return True
    # Skill invocations - generally skip hydration, UNLESS it's a pull command
    # /pull implies picking up a task, which requires context to understand
    if prompt_stripped.startswith("/"):
        return True
    # Slash command expansions (e.g. "# /pull ...")
    if prompt_stripped.startswith("# /"):
        return True
    # User ignore shortcut - user explicitly wants no hydration
    if prompt_stripped.startswith("."):
        return True
    # Follow-up prompts within active session work
    if session_id and is_followup_prompt(session_id, prompt_stripped):
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
        _log_debug(f"Input Parse Error: {e}")
        # Fail-fast: no silent failures (P#8, P#25)
        print(
            f"ERROR: UserPromptSubmit hook failed to parse stdin JSON: {e}",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        # Extract required fields with explicit validation
        prompt = input_data.get("prompt")
        if prompt is None:
            prompt = ""  # Empty prompt is valid (will skip hydration)
        transcript_path = input_data.get("transcript_path")  # Optional
        session_id = input_data.get("session_id")
        if session_id is None:
            session_id = ""  # Will be caught by validation below

        _log_debug(f"SID={session_id} Prompt='{prompt[:50]}...'")

        # Require session_id for state isolation
        if not session_id:
            msg = "ERROR: UserPromptSubmit hook requires session_id for state isolation"
            _log_debug(msg)
            print(msg, file=sys.stderr)
            sys.exit(2)

        # Clear reflection tracking flag for new user prompt
        # This tracks whether the agent outputs a Framework Reflection before session end
        clear_reflection_output(session_id)

        # Check for skip patterns FIRST before any state changes
        # Skip hydration for system messages, skill invocations, user ignore shortcut,
        # and follow-up prompts within active session work
        if should_skip_hydration(prompt, session_id):
            # Write state with hydration_pending=False so gate doesn't block
            write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
            # If '.' prefix, also set gates_bypassed for task_required_gate
            if prompt.strip().startswith("."):
                set_gates_bypassed(session_id, True)

            _log_debug("Skipping: should_skip_hydration=True")
            output_data = {
                "verdict": "allow",
                # No hydration needed
            }
            print(json.dumps(output_data))
            sys.exit(0)

        # Build hydration instruction (writes temp file)
        output_data: dict[str, Any] = {}
        exit_code = 0

        if prompt:
            _log_debug("Attempting to build hydration instruction...")
            hydration_instruction = build_hydration_instruction(
                session_id, prompt, transcript_path
            )
            output_data = {
                "verdict": "allow",
                "context_injection": hydration_instruction,
            }
            _log_debug("Hydration instruction built successfully")

        # Output JSON
        print(json.dumps(output_data))
        sys.exit(exit_code)

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        _log_debug(f"CRITICAL ERROR in main: {e}\n{tb}")
        # Fail-fast
        print(f"ERROR: UserPromptSubmit hook crashed: {e}", file=sys.stderr)
        sys.exit(2)
