"""Context loaders for hydration - consolidated load_xxx() functions.

This module consolidates the 13 near-identical context loading functions
from hooks/user_prompt_submit.py into a unified structure.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

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
    get_sessions_repo,
    get_skills_dir,
    get_summaries_dir,
    get_transcripts_dir,
    get_tests_dir,
    get_workflows_dir,
)

# Environment variables to display in hydrator context
MONITORED_ENV_VARS = (
    "AOPS",
    "ACA_DATA",
    "AOPS_SESSIONS",
    "POLECAT_HOME",
    "NTFY_TOPIC",
    "HYDRATION_GATE_MODE",
    "CUSTODIET_MODE",
    "CLAUDE_SESSION_ID",
)


def _strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


@lru_cache(maxsize=8)
def _load_framework_file(filename: str) -> str:
    """Load a framework markdown file, stripping frontmatter.

    Cached to avoid repeated file I/O within a single hook invocation.

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


def load_framework_paths() -> str:
    """Generate the Framework Paths table dynamically."""
    try:
        plugin_root = get_plugin_root()
        aops_root = get_aops_root()

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
            f"| Sessions  | {get_sessions_repo()} |",
            f"| Transcripts | {get_transcripts_dir()} |",
            f"| Summaries | {get_summaries_dir()} |",
            f"| Projects  | {get_projects_dir()} |",
            f"| Data Logs | {get_logs_dir()} |",
            f"| Context   | {get_context_dir()} |",
            f"| Goals     | {get_goals_dir()} |",
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"(Error gathering framework paths: {e})"


def load_tools_index() -> str:
    """Load TOOLS.md for hydrator context."""
    plugin_root = get_plugin_root()
    tools_path = plugin_root / "TOOLS.md"

    if not tools_path.exists():
        return "(TOOLS.md not found)"

    content = tools_path.read_text()
    return _strip_frontmatter(content)


# Alias for backwards compatibility
def load_mcp_tools_context() -> str:
    """Load tools index (alias for load_tools_index)."""
    return load_tools_index()


def load_environment_variables_context() -> str:
    """List relevant environment variables."""
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
        return f"<!-- Project paths skipped: {e} -->"


def _load_project_rules() -> str:
    """Load project-specific rules from .agent/rules/ in cwd."""
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
            pass

    return "\n".join(lines)


def _load_project_workflows(prompt: str = "") -> str:
    """Load project-specific workflows from .agent/workflows/ in cwd."""
    cwd = Path.cwd()
    project_agent_dir = cwd / ".agent"

    if not project_agent_dir.exists():
        return ""

    project_index = project_agent_dir / "WORKFLOWS.md"
    if project_index.exists():
        content = project_index.read_text()
        return f"\n\n## Project-Specific Workflows ({cwd.name})\n\n{_strip_frontmatter(content)}"

    workflows_dir = project_agent_dir / "workflows"
    if not workflows_dir.exists():
        return ""

    workflow_files = sorted(workflows_dir.glob("*.md"))
    if not workflow_files:
        return ""

    lines = [f"\n\n## Project-Specific Workflows ({cwd.name})", ""]
    lines.append(f"Location: `{workflows_dir}`")
    lines.append(
        "The following workflows are available locally. READ them if relevant to the user request.\n"
    )
    lines.append("| Workflow | Description | Triggers | File |")
    lines.append("|----------|-------------|----------|------|")

    included_workflows = []
    prompt_lower = prompt.lower()

    import yaml

    for wf_file in workflow_files:
        try:
            content = wf_file.read_text()
            name = wf_file.stem
            desc = ""
            triggers = ""

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_raw = parts[1]
                    try:
                        fm = yaml.safe_load(frontmatter_raw)
                        if isinstance(fm, dict):
                            name = fm.get("title", name)
                            desc = fm.get("description", "").replace("\n", " ").strip()
                            triggers_list = fm.get("triggers", [])
                            if isinstance(triggers_list, list):
                                triggers = ", ".join(triggers_list)
                            elif isinstance(triggers_list, str):
                                triggers = triggers_list
                    except (yaml.YAMLError, ValueError, TypeError):
                        pass

            desc_table = desc.replace("|", "-")[:100] + ("..." if len(desc) > 100 else "")
            triggers_table = triggers.replace("|", "-")
            lines.append(f"| {name} | {desc_table} | {triggers_table} | `{wf_file.name}` |")

            filename_keywords = set(
                wf_file.stem.lower().replace("-", " ").replace("_", " ").split()
            )
            if (
                any(
                    re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower)
                    for kw in filename_keywords
                )
                or wf_file.stem.lower() in prompt_lower
            ):
                header_name = name
                if name != wf_file.stem:
                    header_name = f"{name} ({wf_file.stem})"
                included_workflows.append(
                    f"\n\n### {header_name} (Project Instructions)\n\n{_strip_frontmatter(content)}"
                )
        except OSError:
            pass

    result = "\n".join(lines)
    if included_workflows:
        result += "\n" + "".join(included_workflows)
    return result


def _load_global_workflow_content(prompt: str = "") -> str:
    """Selectively load the content of relevant global workflows and their bases."""
    import yaml

    from lib.file_index import get_relevant_file_paths

    relevant_paths = get_relevant_file_paths(prompt, max_files=20)
    workflow_paths = [p for p in relevant_paths if p["path"].startswith("workflows/")]

    if not workflow_paths:
        return ""

    plugin_root = get_plugin_root()
    included_content = {}  # Use dict to avoid duplicates: name -> content

    # Use a queue for breadth-first traversal of bases
    queue = [p["path"] for p in workflow_paths]
    processed = set()

    while queue:
        rel_path = queue.pop(0)
        if rel_path in processed:
            continue
        processed.add(rel_path)

        path = plugin_root / rel_path
        if not path.exists():
            continue

        try:
            raw_content = path.read_text()
            wf_name = Path(rel_path).stem

            # Parse frontmatter to find bases
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        fm = yaml.safe_load(parts[1])
                        if isinstance(fm, dict):
                            bases = fm.get("bases", [])
                            if isinstance(bases, list):
                                for base in bases:
                                    # Convert base ID to path (e.g. base-commit -> workflows/base-commit.md)
                                    base_path = f"workflows/{base}.md"
                                    if base_path not in processed:
                                        queue.append(base_path)
                    except Exception:
                        pass

            included_content[wf_name] = _strip_frontmatter(raw_content)
        except OSError:
            pass

    # Format output
    result = []
    # Reverse order so bases appear before the workflows that use them (or vice versa,
    # but breadth-first queue gives us workflows then bases)
    for name, content in included_content.items():
        result.append(f"\n\n### Workflow: {name}\n\n{content}")

    return "".join(result)


def load_workflows_index(prompt: str = "") -> str:
    """Load WORKFLOWS.md for hydrator context."""
    plugin_root = get_plugin_root()
    workflows_path = plugin_root / "WORKFLOWS.md"

    if not workflows_path.exists():
        return "(WORKFLOWS.md not found)"

    content = workflows_path.read_text()
    base_workflows = _strip_frontmatter(content)

    project_workflows = _load_project_workflows(prompt)
    global_workflow_content = _load_global_workflow_content(prompt)

    return base_workflows + project_workflows + global_workflow_content


def load_project_context_index() -> str:
    """Load JIT project context index from .agent/context-map.json."""
    cwd = Path.cwd()
    map_file = cwd / ".agent" / "context-map.json"

    if not map_file.exists():
        return ""

    try:
        context_map = json.loads(map_file.read_text())
    except (json.JSONDecodeError, OSError):
        return ""

    if "docs" not in context_map:
        return ""
    docs = context_map["docs"]
    if not isinstance(docs, list) or not docs:
        return ""

    lines = []

    for doc in docs:
        if not isinstance(doc, dict):
            continue
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
    """Load AXIOMS.md for hydrator context."""
    return _load_framework_file("AXIOMS.md")


def load_heuristics() -> str:
    """Load HEURISTICS.md for hydrator context."""
    return _load_framework_file("HEURISTICS.md")


def load_skills_index() -> str:
    """Load SKILLS.md for hydrator context."""
    return _load_framework_file("SKILLS.md")


def load_scripts_index() -> str:
    """Load SCRIPTS.md for hydrator context."""
    try:
        return _load_framework_file("SCRIPTS.md")
    except FileNotFoundError:
        return ""


def load_glossary() -> str:
    """Load GLOSSARY.md for hydrator context.

    The glossary provides framework terminology definitions so the hydrator
    can interpret user prompts without filesystem exploration.
    """
    try:
        return _load_framework_file("GLOSSARY.md")
    except FileNotFoundError:
        return ""


def load_project_rules() -> str:
    """Load project-specific rules from .agent/rules/."""
    return _load_project_rules()


def get_task_work_state() -> str:
    """Query task system for current work state."""
    plugin_root = get_plugin_root()
    task_cli_path = plugin_root / "scripts" / "task_cli.py"

    if not task_cli_path.exists():
        return ""

    try:
        active_result = subprocess.run(
            ["python", str(task_cli_path), "list", "--status=active", "--limit=20"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = active_result.stdout.strip() if active_result.returncode == 0 else ""

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
        return ""
