#!/usr/bin/env -S uv run python
import os
import re
from collections import defaultdict
from pathlib import Path

import yaml

CORE_AGENTS_DIR = Path("aops-core/agents")
GH_AGENTS_DIR = Path(".github/agents")
SKILLS_DIR = Path("aops-core/skills")
COMPLIANCE_FILE = Path("specs/audit/AGENT-COMPLIANCE-MATRIX.md")
REMEDIATION_FILE = Path("specs/audit/AGENT-REMEDIATION-BACKLOG.md")
TOOL_MATRIX_FILE = Path("specs/audit/AGENT-TOOLS.md")

PASCAL_TOOLS = {
    "Read",
    "Edit",
    "Write",
    "Bash",
    "Grep",
    "Glob",
    "Agent",
    "Skill",
    "TodoWrite",
    "AskUserQuestion",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
}

VALID_MCP_SERVERS = {
    "pkb",
    "playwright",
    "outlook",
    "discord",
    "computer-use",
    "context7",
    "claude-in-chrome",
    "Claude_Preview",
}

EXCLUSIVE_INTENT = {
    "mcp__plugin_aops-core_pkb__batch_archive": "pauli",
    "mcp__plugin_aops-core_pkb__bulk_reparent": "pauli",
    "mcp__plugin_aops-core_pkb__merge_node": "pauli",
    "mcp__playwright__*": "marsha",
    "Edit": "rbg",  # on .agents/rules/* - but we just track the tool for now
}

# Gemini-form built-in tool names produced by build.py's GEMINI_TOOL_NAME_MAP.
# These should never appear in frontmatter tools/allowed-tools lists in source.
GEMINI_BUILTIN_NAMES = {
    "read_file",
    "write_file",
    "replace",
    "glob",
    "grep_search",
    "run_shell_command",
    "activate_skill",
    "web_fetch",
    "google_web_search",
}

# Matches Gemini-form MCP tool names: mcp_ followed by non-underscore.
# Canonical form always starts with mcp__ (double underscore).
# Requires at least two underscore-separated segments after mcp_ to distinguish
# from prose words like "mcp_servers" in YAML config keys.
_GEMINI_MCP_PATTERN = re.compile(r"\bmcp_(?!_)[a-zA-Z0-9-]+(?:_[a-zA-Z0-9-]+)+\b")


def is_gemini_tool_name(name: str) -> bool:
    """Return True if name is a Gemini-transformed tool name that should not appear in source."""
    if name in GEMINI_BUILTIN_NAMES:
        return True
    # mcp__server__tool → mcp_server_tool under Gemini transform (__ → _)
    if _GEMINI_MCP_PATTERN.fullmatch(name):
        return True
    return False


def find_gemini_mcp_names_in_text(text: str) -> list[str]:
    """Find Gemini-form MCP tool names (mcp_server_tool) in body text.

    Only scans for MCP-form names (not built-in aliases like read_file)
    to avoid false positives in legitimate documentation prose.
    """
    return _GEMINI_MCP_PATTERN.findall(text)


def check_gemini_names(root: Path | None = None) -> list[tuple[str, str, str]]:
    """Scan aops-core/**/*.md for Gemini-form tool names that escaped from build output.

    Returns list of (file_path, location, name) triples.
    Frontmatter tools/allowed-tools lists: checked for both MCP-form and built-in aliases.
    Body text: checked for MCP-form only (avoids false positives on prose).
    """
    if root is None:
        root = Path(__file__).parent.parent.resolve()

    core_dir = root / "aops-core"
    violations: list[tuple[str, str, str]] = []

    for md_file in sorted(core_dir.glob("**/*.md")):
        try:
            content = md_file.read_text()
        except OSError:
            continue

        fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                fm = {}

            for field in ("tools", "allowed-tools"):
                tools = fm.get(field, [])
                if not isinstance(tools, list):
                    continue
                for t in tools:
                    if isinstance(t, str) and is_gemini_tool_name(t):
                        rel = str(md_file.relative_to(root))
                        violations.append((rel, f"frontmatter {field}", t))

            # Body text: MCP-form scan only
            parts = content.split("---", 2)
            body = parts[2] if len(parts) >= 3 else ""
        else:
            body = content

        for match in _GEMINI_MCP_PATTERN.finditer(body):
            rel = str(md_file.relative_to(root))
            violations.append((rel, "body text", match.group(0)))

    return violations


def is_valid_tool_name(name):
    if name in PASCAL_TOOLS:
        return True
    if name.startswith("mcp__"):
        return True
    return False


def get_server_from_tool(tool):
    if tool in PASCAL_TOOLS:
        return "Built-in"
    if tool.startswith("mcp__"):
        parts = tool.split("__")
        if parts[1].startswith("plugin_"):
            return parts[1].replace("plugin_", "")
        return parts[1]
    return "Unknown"


def audit_agent(file_path, is_gh=False):
    with open(file_path) as f:
        content = f.read()

    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return {
            "agent": str(file_path),
            "name": file_path.stem.replace(".agent", ""),
            "schema_ok": "❌ No FM",
            "naming_ok": "❌",
            "referential_ok": "❌",
            "skills_declared": "❌",
            "subagents_declared": "❌",
            "notes": "Missing frontmatter",
            "tools": [],
        }

    try:
        fm = yaml.safe_load(fm_match.group(1)) or {}
    except Exception as e:
        return {
            "agent": str(file_path),
            "name": file_path.stem.replace(".agent", ""),
            "schema_ok": "❌ Invalid YAML",
            "naming_ok": "❌",
            "referential_ok": "❌",
            "skills_declared": "❌",
            "subagents_declared": "❌",
            "notes": f"YAML error: {e}",
            "tools": [],
        }

    notes = []

    # schema_ok
    required = ["name", "description"]
    if not is_gh:
        required += ["model", "tools"]

    missing = [r for r in required if r not in fm]
    schema_ok = "✅" if not missing else f"❌ Missing: {', '.join(missing)}"

    # naming_ok
    tools = fm.get("tools", [])
    if not isinstance(tools, list):
        tools = []
        schema_ok = "❌ tools not list"

    invalid_names = [t for t in tools if not is_valid_tool_name(t)]
    naming_ok = "✅" if not invalid_names else f"❌ Legacy: {', '.join(invalid_names)}"

    # skills_declared
    has_skill_tool = "Skill" in tools
    skills_field = fm.get("skills")
    skills_declared = "✅"
    if has_skill_tool and skills_field is None:
        skills_declared = "❌ Missing skills:"
    elif not has_skill_tool and skills_field is not None:
        notes.append("Has skills: but no Skill tool")

    # subagents_declared
    has_agent_tool = "Agent" in tools
    subagents_field = fm.get("subagents")
    subagents_declared = "✅"
    if has_agent_tool and subagents_field is None:
        subagents_declared = "❌ Missing subagents:"
    elif not has_agent_tool and subagents_field is not None:
        notes.append("Has subagents: but no Agent tool")

    # referential_ok
    referential_ok = "✅"
    ref_errors = []

    # Check mcpServers
    mcp_servers = fm.get("mcpServers", [])
    if not isinstance(mcp_servers, list):
        ref_errors.append("mcpServers not list")
    else:
        for s in mcp_servers:
            if s not in VALID_MCP_SERVERS:
                ref_errors.append(f"Unknown MCP: {s}")

    # Check skills
    if isinstance(skills_field, list) and skills_field != ["*"]:
        for s in skills_field:
            if not (SKILLS_DIR / s).exists():
                ref_errors.append(f"Unknown skill: {s}")

    # Check subagents
    if isinstance(subagents_field, list) and subagents_field != ["*"]:
        for a in subagents_field:
            if not (CORE_AGENTS_DIR / f"{a}.md").exists():
                ref_errors.append(f"Unknown agent: {a}")

    if ref_errors:
        referential_ok = f"❌ {', '.join(ref_errors)}"

    return {
        "agent": str(file_path),
        "name": fm.get("name", file_path.stem.replace(".agent", "")),
        "schema_ok": schema_ok,
        "naming_ok": naming_ok,
        "referential_ok": referential_ok,
        "skills_declared": skills_declared,
        "subagents_declared": subagents_declared,
        "notes": "; ".join(notes),
        "tools": tools,
    }


def audit_skill(file_path):
    with open(file_path) as f:
        content = f.read()

    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return str(file_path), "❌ No FM"

    try:
        fm = yaml.safe_load(fm_match.group(1)) or {}
    except Exception:
        return str(file_path), "❌ Invalid YAML"

    if "allowed-tools" in fm:
        return str(file_path), "✅"
    return str(file_path), "❌ Missing allowed-tools"


def main():
    agent_results = []

    # Core Agents
    for f in sorted(CORE_AGENTS_DIR.glob("*.md")):
        agent_results.append(audit_agent(f))

    # GH Agents
    for f in sorted(GH_AGENTS_DIR.glob("*.agent.md")):
        agent_results.append(audit_agent(f, is_gh=True))

    # Skill Audit
    skill_results = []
    for f in sorted(SKILLS_DIR.glob("**/SKILL.md")):
        skill_results.append(audit_skill(f))

    # 1. Generate Compliance Matrix
    with open(COMPLIANCE_FILE, "w") as f:
        f.write("# Agent Compliance Matrix\n\n")
        f.write(
            f"Generated on {os.popen('date -u').read().strip()} from `scripts/audit_agent_compliance.py`.\n\n"
        )

        f.write("## Agents\n\n")
        f.write(
            "| Agent | Schema OK | Naming OK | Referential OK | Skills Declared | Subagents Declared | Notes |\n"
        )
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in agent_results:
            f.write(
                f"| {r['agent']} | {r['schema_ok']} | {r['naming_ok']} | {r['referential_ok']} | {r['skills_declared']} | {r['subagents_declared']} | {r['notes']} |\n"
            )

        f.write("\n## Skills (allowed-tools check)\n\n")
        f.write("| Skill | Conformance |\n")
        f.write("| :--- | :--- |\n")
        for s, res in skill_results:
            f.write(f"| {s} | {res} |\n")

    # 2. Generate Remediation Backlog — one-shot bootstrapper only.
    # The backlog is hand-edited after the initial run; regenerating it unconditionally
    # would silently overwrite manual tracking (in-progress, done, blocked) and
    # guarantee drift from the dynamic compliance matrix (A5 violation).
    if REMEDIATION_FILE.exists():
        print(
            f"Skipping {REMEDIATION_FILE} — file already exists. Edit manually or delete to regenerate."
        )
    else:
        with open(REMEDIATION_FILE, "w") as f:
            f.write("# Agent Compliance Remediation Backlog\n\n")
            f.write(
                "This backlog lists the actions required to bring all agents and skills into full compliance with the `Agent Authority` spec.\n\n"
            )

            f.write("## Core Agents\n\n")
            f.write("| Agent | Priority | Required Action |\n")
            f.write("| :--- | :--- | :--- |\n")
            f.write("| `james.md` | P1 | Add `skills:` and `subagents:` allowlists. |\n")
            f.write("| `junior.md` | P1 | Add `skills:` and `subagents:` allowlists. |\n")
            f.write("| `marsha.md` | P1 | Add `skills:` and `subagents:` allowlists. |\n")
            f.write("| `pauli.md` | P1 | Add `skills:` allowlist. |\n")
            f.write(
                "| `rbg.md` | P2 | Add `skills: []` and `subagents: []` for explicitness. |\n\n"
            )

            f.write("## Skills\n\n")
            f.write("| Skill | Required Action |\n")
            f.write("| :--- | :--- |\n")
            f.write("| `aops/SKILL.md` | Add `allowed-tools` block to frontmatter. |\n")
            f.write("| `end_session/SKILL.md` | Add `allowed-tools` block to frontmatter. |\n")
            f.write("| `planner/SKILL.md` | Add `allowed-tools` block to frontmatter. |\n")
            f.write("| `project/SKILL.md` | Add `allowed-tools` block to frontmatter. |\n")
            f.write("| `supervisor/SKILL.md` | Add `allowed-tools` block to frontmatter. |\n\n")

            f.write("## Tool Authority (Drift Remediation)\n\n")
            f.write("Based on `specs/audit/AGENT-TOOLS.md`:\n\n")
            f.write(
                "- **Exclusivity Enforcement**: Remove destructive PKB tools from `junior.md` (should be exclusive to `pauli`).\n"
            )
            f.write("- **Edit Tool**: Evaluate if `junior.md` needs `Edit`.\n")

    # 3. Generate Tool Matrix
    # Gather all tools and their owners
    tool_to_agents = defaultdict(list)
    all_agents = [r["name"] for r in agent_results]

    for r in agent_results:
        for t in r["tools"]:
            tool_to_agents[t].append(r["name"])

    # Group tools by server
    server_to_tools = defaultdict(list)
    for t in sorted(tool_to_agents.keys()):
        server = get_server_from_tool(t)
        server_to_tools[server].append(t)

    with open(TOOL_MATRIX_FILE, "w") as f:
        f.write("# Authoritative Agent × Tool Matrix\n\n")
        f.write(
            f"Generated on {os.popen('date -u').read().strip()} from `scripts/audit_agent_compliance.py`.\n\n"
        )

        f.write("## Exclusive Tools\n\n")
        f.write("| Tool | Intended Owner | Current Users | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for pattern, owner in EXCLUSIVE_INTENT.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                matches = [t for t in tool_to_agents if t.startswith(prefix)]
                for m in sorted(matches):
                    users = tool_to_agents[m]
                    status = "✅ Exclusive" if users == [owner] else "❌ Drifted"
                    f.write(f"| {m} | {owner} | {', '.join(users)} | {status} |\n")
            else:
                users = tool_to_agents.get(pattern, [])
                status = (
                    "✅ Exclusive" if users == [owner] else ("❌ Drifted" if users else "⚠️ Unused")
                )
                f.write(f"| {pattern} | {owner} | {', '.join(users)} | {status} |\n")

        f.write("\n## Full Matrix\n\n")
        # Header: Tool | agent1 | agent2 | ...
        f.write("| Tool | " + " | ".join(all_agents) + " |\n")
        f.write("| :--- | " + " | ".join([":---:"] * len(all_agents)) + " |\n")

        for server in sorted(server_to_tools.keys()):
            f.write(f"| **{server}** |" + " | ".join([""] * len(all_agents)) + " |\n")
            for t in server_to_tools[server]:
                row = [f"`{t}`"]
                for a in all_agents:
                    row.append("✅" if a in tool_to_agents[t] else "")
                f.write("| " + " | ".join(row) + " |\n")


if __name__ == "__main__":
    main()
