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
from pathlib import Path
from typing import Any

from lib.file_index import get_formatted_relevant_paths, get_relevant_file_paths
from lib.hook_utils import (
    cleanup_old_temp_files as _cleanup_temp,
)
from lib.hook_utils import (
    get_hook_temp_dir,
)
from lib.hook_utils import (
    write_temp_file as _write_temp,
)
from lib.paths import (
    get_aops_root,
    get_commands_dir,
    get_config_dir,
    get_context_dir,
    get_data_root,
    get_goals_dir,
    get_hooks_dir,
    get_indices_dir,
    get_logs_dir,
    get_plugin_root,
    get_projects_dir,
    get_sessions_dir,
    get_skills_dir,
    get_tests_dir,
    get_workflows_dir,
)
from lib.session_reader import extract_router_context
from lib.session_state import (
    clear_hydration_pending,
    set_hydration_pending,
    set_hydration_temp_path,
)
from lib.template_loader import load_template

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"

# Temp directory category (matches hydration_gate.py)
TEMP_CATEGORY = "hydrator"

# Environment variables to display in hydrator context
# <!-- NS: no magic literals, no repetition. -->
MONITORED_ENV_VARS = (
    "AOPS",
    "ACA_DATA",
    "POLECAT_HOME",
    "NTFY_TOPIC",
    "HYDRATION_GATE_MODE",
    "CUSTODIET_MODE",
    "TASK_GATE_MODE",
    "CLAUDE_SESSION_ID",
)


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


def load_tools_index() -> str:
    """Load TOOLS.md for hydrator context.

    Pre-loads curated tool reference so hydrator can route work effectively.
    Returns content after frontmatter separator.
    """
    plugin_root = get_plugin_root()
    tools_path = plugin_root / "TOOLS.md"

    if not tools_path.exists():
        return "(TOOLS.md not found)"

    content = tools_path.read_text()

    # Skip frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content.strip()


# Alias for backwards compatibility with template placeholder name
def load_mcp_tools_context() -> str:
    """Load tools index (alias for load_tools_index).

    Kept for backwards compatibility with existing template placeholder.
    """
    return load_tools_index()


def load_environment_variables_context() -> str:
    """List relevant environment variables."""
    # <!-- NS: no magic literals. -->
    # <!-- @claude 2026-02-07: Fixed. Extracted to MONITORED_ENV_VARS constant at module level. -->
    lines = ["## Environment Variables", ""]
    lines.append("| Variable | Value |")
    lines.append("|----------|-------|")
    for var in MONITORED_ENV_VARS:
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


def _load_framework_file(filename: str) -> str:
    """Load a framework markdown file, stripping frontmatter.

    Args:
        filename: Name of file in plugin root (e.g., "AXIOMS.md")

    Returns:
        File content with frontmatter stripped.

    Raises:
        FileNotFoundError: If file doesn't exist (fail-fast per P#8)
    """
    plugin_root = get_plugin_root()
    filepath = plugin_root / filename
    content = filepath.read_text()
    return _strip_frontmatter(content)


def _load_project_rules() -> str:
    """Load project-specific rules from .agent/rules/ in cwd.

    Projects can define their own rules in .agent/rules/*.md.
    These are project-wide conventions that apply to ALL work in the project
    (test patterns, code style, architectural constraints, etc.).

    Rules are pre-loaded and included in hydrator context so the agent
    has immediate access without needing to Read() them.

    Returns:
        Project rules section with all rule file contents, or empty string if none found.
    """
    cwd = Path.cwd()
    rules_dir = cwd / ".agent" / "rules"

    if not rules_dir.exists():
        return ""

    rule_files = sorted(rules_dir.glob("*.md"))
    if not rule_files:
        return ""

    lines = [f"\n\n## Project Rules ({cwd.name})", ""]
    lines.append(f"Location: `{rules_dir}`\n")
    lines.append(
        "These rules apply to ALL work in this project. Follow them as binding constraints.\n"
    )

    for rule_file in rule_files:
        try:
            content = rule_file.read_text()
            rule_name = rule_file.stem.replace("-", " ").replace("_", " ").title()
            lines.append(f"### {rule_name}\n")
            lines.append(_strip_frontmatter(content))
            lines.append("")
        except OSError:
            pass  # Skip unreadable files

    return "\n".join(lines)


def _load_project_workflows(prompt: str = "") -> str:
    """Load project-specific workflows from .agent/workflows/ in cwd.

    Projects can define their own workflows in .agent/workflows/*.md.
    If a WORKFLOWS.md index exists in .agent/, use that; otherwise
    scan workflow files and build a semantic index for JIT reading.

    Args:
        prompt: User prompt for content-aware matching.

    Returns:
        Project workflows section, or empty string if none found.
    """
    cwd = Path.cwd()
    project_agent_dir = cwd / ".agent"

    if not project_agent_dir.exists():
        return ""

    # Check for project workflow index first
    # <!-- NS: Extract magic literals to a constants file. -->
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

    # Build a semantic index from frontmatter
    lines = [f"\n\n## Project-Specific Workflows ({cwd.name})", ""]
    lines.append(f"Location: `{workflows_dir}`")
    lines.append("The following workflows are available locally. READ them if relevant to the user request.\n")
    lines.append("| Workflow | Description | Triggers | File |")
    lines.append("|----------|-------------|----------|------|")

    included_workflows = []
    prompt_lower = prompt.lower()

    for wf_file in workflow_files:
        try:
            content = wf_file.read_text()
            name = wf_file.stem
            desc = ""
            triggers = ""
            
            # Parse frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_raw = parts[1]
                    import yaml
                    try:
                        fm = yaml.safe_load(frontmatter_raw)
                        if isinstance(fm, dict):
                            name = fm.get("title", name)  # Prefer title if available
                            desc = fm.get("description", "").replace("\n", " ").strip()
                            triggers_list = fm.get("triggers", [])
                            if isinstance(triggers_list, list):
                                triggers = ", ".join(triggers_list)
                            elif isinstance(triggers_list, str):
                                triggers = triggers_list
                    except yaml.YAMLError:
                        pass # Fallback to basics on parse error

            # Format table row - escape pipes
            desc_table = desc.replace("|", "-")[:100] + ("..." if len(desc) > 100 else "")
            triggers_table = triggers.replace("|", "-")
            lines.append(f"| {name} | {desc_table} | {triggers_table} | `{wf_file.name}` |")

            # Content injection logic based on prompt keywords
            filename_keywords = set(wf_file.stem.lower().replace("-", " ").replace("_", " ").split())
            if any(kw in prompt_lower for kw in filename_keywords) or wf_file.stem.lower() in prompt_lower:
                included_workflows.append(
                    f"\n\n### {wf_file.stem} (Project Instructions)\n\n{_strip_frontmatter(content)}"
                )
        except OSError:
            pass  # Skip unreadable files

    result = "\n".join(lines)
    if included_workflows:
        result += "\n" + "".join(included_workflows)
    return result


# <!-- NS: these repetitive functions should be refactored. -->
def _load_global_workflow_content(prompt: str = "") -> str:
    """Selectively load the content of relevant global workflows.

    Uses FILE_INDEX to identify relevant workflow files and includes
    their full content for the hydrator.
    """
    # Get relevant files from index
    relevant_paths = get_relevant_file_paths(prompt, max_files=5)

    # Filter for workflows in aops-core/workflows/
    workflow_paths = [p for p in relevant_paths if p["path"].startswith("workflows/")]

    if not workflow_paths:
        return ""

    plugin_root = get_plugin_root()
    included_content = []

    for wp in workflow_paths:
        path = plugin_root / wp["path"]
        if path.exists():
            try:
                content = path.read_text()
                # Use filename stem for header
                wf_name = Path(wp["path"]).stem
                included_content.append(
                    f"\n\n### Global Workflow: {wf_name}\n\n{_strip_frontmatter(content)}"
                )
            except OSError:
                pass

    return "".join(included_content)


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

    # Append relevant global workflow content (P#43: JIT context)
    global_workflow_content = _load_global_workflow_content(prompt)

    return base_workflows + project_workflows + global_workflow_content


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


# <!-- NS: replace all this with a jinja2 template for the hydrator. Don't generate any indices here, we do it as part of the audit skill already. -->


def load_axioms() -> str:
    """Load AXIOMS.md for hydrator context.

    Pre-loads axioms so hydrator can select relevant principles.
    Returns content after frontmatter separator.
    """
    return _load_framework_file("AXIOMS.md")


def load_heuristics() -> str:
    """Load HEURISTICS.md for hydrator context.

    Pre-loads heuristics so hydrator doesn't need to Read() at runtime.
    Returns content after frontmatter separator.
    """
    return _load_framework_file("HEURISTICS.md")


def load_skills_index() -> str:
    """Load SKILLS.md for hydrator context.

    Pre-loads skills index so hydrator can immediately recognize skill invocations
    without needing to search memory. Returns content after frontmatter separator.
    """
    return _load_framework_file("SKILLS.md")


def load_skills_index() -> str:
    """Load SKILLS.md for hydrator context.

    Pre-loads skills index so hydrator can immediately recognize skill invocations
    without needing to search memory. Returns content after frontmatter separator.
    """
    return _load_framework_file("SKILLS.md")


def load_scripts_index() -> str:
    """Load SCRIPTS.md for hydrator context.

    Pre-loads scripts index so hydrator can surface relevant utility scripts
    when user requests involve their functionality. Returns content after
    frontmatter separator. Returns empty string if SCRIPTS.md doesn't exist.
    """
    try:
        return _load_framework_file("SCRIPTS.md")
    except FileNotFoundError:
        return ""


def load_project_rules() -> str:
    """Load project-specific rules from .agent/rules/.

    Pre-loads all rule files so hydrator has immediate access to project
    constraints without needing to Read() them at runtime.

    Returns:
        Formatted project rules section, or empty string if none found.
    """
    return _load_project_rules()


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
    scripts_index = load_scripts_index()
    axioms = load_axioms()
    heuristics = load_heuristics()

    # Load project-specific rules from .agent/rules/ (P#60: Local over central)
    project_rules = load_project_rules()

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
        project_rules=project_rules,
        relevant_files=relevant_files,
        workflows_index=workflows_index,
        skills_index=skills_index,
        scripts_index=scripts_index,
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


def should_skip_hydration(prompt: str, session_id: str | None = None) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - Expanded slash commands (containing <command-name>/ tag)
    - User ignore shortcut (prompts starting with '.')
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
    return False