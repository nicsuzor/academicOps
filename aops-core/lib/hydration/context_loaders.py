import json
import re
from functools import lru_cache
from pathlib import Path

# --- Helper Utilities ---


@lru_cache
def get_plugin_root() -> Path:
    """Find the root of the plugin installation (where README.md/SKILLS.md live)."""
    # Start from this file's directory: aops-core/lib/hydration/
    current = Path(__file__).resolve().parent
    # Go up to aops-core/
    while current.name != "aops-core" and current.parent != current:
        current = current.parent
    if current.name == "aops-core":
        return current
    # Fallback if structure is weird (e.g. tests)
    return Path.cwd()


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content


def _load_framework_file(filename: str) -> str:
    """Load a framework documentation file from aops-core root.

    Raises FileNotFoundError if the file is missing — fail fast so deployment
    issues are surfaced immediately rather than causing silent degraded behavior.
    """
    path = get_plugin_root() / filename
    if not path.exists():
        raise FileNotFoundError(f"Framework file not found: {path}")
    return _strip_frontmatter(path.read_text())


# --- Context Loaders ---


def load_project_map() -> str:
    """Load project map for hydrator context."""
    # Try to load projects.json from current working directory
    projects_file = Path("projects.json")
    if not projects_file.exists():
        return ""

    try:
        content = projects_file.read_text()
        projects = json.loads(content)
        lines = []
        lines.append("\n\n## Known Projects (Workspace Map)")
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


def load_workflows_index(prompt: str = "") -> str:
    """Load WORKFLOWS.md for hydrator context."""
    plugin_root = get_plugin_root()
    workflows_path = plugin_root / "skills" / "hydrator" / "WORKFLOWS.md"

    if not workflows_path.exists():
        raise FileNotFoundError(f"Framework file not found: {workflows_path}")

    content = workflows_path.read_text()
    base_workflows = _strip_frontmatter(content)

    project_workflows = _load_project_workflows(prompt)

    return base_workflows + project_workflows


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
    return _load_framework_file("SCRIPTS.md")


def load_glossary() -> str:
    """Load GLOSSARY.md for hydrator context.

    The glossary provides framework terminology definitions so the hydrator
    can interpret user prompts without filesystem exploration.
    """
    return _load_framework_file("GLOSSARY.md")


def load_project_rules() -> str:
    """Load project-specific rules from .agent/rules/."""
    return _load_project_rules()


def get_task_work_state() -> str:
    """Query task system for current work state.

    Stub — Python task CLI removed; PKB is now Rust-native.
    Kept as no-op to avoid breaking hydration callers.
    """
    return ""


def load_environment_variables_context() -> str:
    """Load specific environment variables for context."""
    # Stub implementation to fix import error
    return ""


def load_framework_paths() -> str:
    """Load framework paths context."""
    # Stub implementation to fix import error
    return ""


def load_mcp_tools_context() -> str:
    """Load MCP tools context."""
    # Stub implementation to fix import error
    return ""


def load_project_paths_context() -> str:
    """Load project paths context."""
    return load_project_map()


MONITORED_ENV_VARS = ["AOPS", "GITHUB_WORKSPACE"]


def load_tools_index() -> str:
    """Load tools index context."""
    return ""
