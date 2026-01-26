# Gemini CLI Configuration for AcademicOps

This project uses the `academic-ops-core` extension to manage hooks, skills, and MCP servers.

## Active Configuration

- **Hooks**: Managed by `aops-core/gemini-extension.json` routing to `aops-core/hooks/gemini/router.py`
- **MCP Servers**: `task_manager` (Tasks v2)
- **Skills**: All skills in `aops-core/skills/` are available

## Usage

- Use `/help` to see available commands.
- Use `gemini skills list` to see available skills.
- Use `gemini hooks list` (if available) to see hooks.

## Paths

- **Root**: ${AOPS}
- **Data**: ${ACA_DATA}
