from pathlib import Path

import pytest
import yaml


def test_source_agent_tool_names():
    agents_dir = Path(__file__).parent.parent.parent / "aops-core" / "agents"
    if not agents_dir.exists():
        pytest.fail(f"Agents directory not found at {agents_dir}")

    for agent_file in agents_dir.glob("*.md"):
        content = agent_file.read_text()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        frontmatter = yaml.safe_load(parts[1])
        tools = frontmatter.get("tools", [])

        for idx, tool in enumerate(tools):
            # Tool names in Gemini must only contain lowercase letters, numbers, and single underscores
            assert "__" not in tool, (
                f"Agent {agent_file.name} tool {idx} ({tool}) contains double underscores. Use single underscores (e.g. mcp_pkb_search)."
            )
            assert not any(c.isupper() for c in tool), (
                f"Agent {agent_file.name} tool {idx} ({tool}) contains uppercase letters. Use snake_case (e.g. read_file, not Read)."
            )
