"""Tests for hydrator tool-awareness anti-patterns.

Regression tests to ensure the hydrator doesn't make feasibility judgments
based on tool availability assumptions. The hydrator cannot know what tools
the main agent has, so it must not claim tasks are "human tasks" or "not possible".

See: aops-XXXXXXXX (the original bug where hydrator claimed email search was human task)
"""

from pathlib import Path

# Paths to hydrator files
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
HYDRATOR_AGENT = AOPS_CORE / "agents" / "prompt-hydrator.md"
HYDRATOR_CONTEXT_TEMPLATE = AOPS_CORE / "hooks" / "templates" / "prompt-hydrator-context.md"


class TestHydratorAntiInstructions:
    """Test that hydrator has explicit anti-instructions about tool availability."""

    def test_agent_warns_about_tool_blindness(self) -> None:
        """Hydrator agent must explicitly state it doesn't know main agent's tools."""
        content = HYDRATOR_AGENT.read_text()

        # Must warn about tool blindness
        assert (
            "do NOT know what tools the main agent has" in content.lower()
            or "you do not know what tools" in content.lower()
        ), "Hydrator agent must warn about tool availability blindness"

    def test_agent_forbids_human_task_claims(self) -> None:
        """Hydrator agent must forbid claiming tasks are 'human tasks' based on tools."""
        content = HYDRATOR_AGENT.read_text()

        # Must have explicit prohibition
        assert "never" in content.lower() and "human task" in content.lower(), (
            "Hydrator agent must forbid 'human task' claims based on tool assumptions"
        )

    def test_agent_forbids_feasibility_judgments(self) -> None:
        """Hydrator agent must forbid feasibility judgments about tool availability."""
        content = HYDRATOR_AGENT.read_text()

        # Should have guidance about not making feasibility claims
        forbidden_patterns = [
            "agent cannot",
            "requires human intervention",
            "feasibility judgment",
        ]

        has_prohibition = any(
            "never" in content.lower() and pattern in content.lower()
            for pattern in forbidden_patterns
        )

        assert has_prohibition, "Hydrator agent must forbid feasibility judgments about tools"

    def test_agent_suggests_conditional_approach(self) -> None:
        """Hydrator agent must suggest conditional approach for uncertain tools."""
        content = HYDRATOR_AGENT.read_text()

        # Should suggest "if X is available, use it; otherwise ask user"
        assert "if" in content.lower() and "available" in content.lower(), (
            "Hydrator agent must suggest conditional approach for tool uncertainty"
        )


class TestContextTemplateWarnings:
    """Test that context template has appropriate warnings about tools section."""

    def test_template_has_tools_reference(self) -> None:
        """Context template must reference curated tools list."""
        content = HYDRATOR_CONTEXT_TEMPLATE.read_text()

        assert "curated" in content.lower() or "reference" in content.lower(), (
            "Context template must indicate tools list is a curated reference"
        )

    def test_template_forbids_feasibility_judgments(self) -> None:
        """Context template must forbid feasibility judgments based on tools list."""
        content = HYDRATOR_CONTEXT_TEMPLATE.read_text()

        assert "do not" in content.lower() and "feasibility" in content.lower(), (
            "Context template must forbid feasibility judgments from tools list"
        )

    def test_template_warns_about_additional_tools(self) -> None:
        """Context template must warn main agent may have additional tools."""
        content = HYDRATOR_CONTEXT_TEMPLATE.read_text()

        assert "additional tools" in content.lower() or "cannot see" in content.lower(), (
            "Context template must warn about unseen tools"
        )


class TestToolsIndexFunction:
    """Test the load_tools_index function behavior."""

    def test_loads_from_tools_md(self) -> None:
        """Tools function must load from TOOLS.md curated index."""
        # Read the source file
        user_prompt_submit = AOPS_CORE / "hooks" / "user_prompt_submit.py"
        content = user_prompt_submit.read_text()

        # Find the load_tools_index function
        assert "def load_tools_index" in content

        func_start = content.find("def load_tools_index")
        func_end = content.find("\ndef ", func_start + 1)
        func_body = content[func_start:func_end]

        # Should reference TOOLS.md
        assert "TOOLS.md" in func_body, "load_tools_index must read from TOOLS.md"

        # Should NOT have hardcoded server descriptions
        assert '"outlook"' not in func_body.lower(), (
            "load_tools_index must not have hardcoded server descriptions"
        )

    def test_tools_md_exists_and_has_content(self) -> None:
        """TOOLS.md must exist and contain tool descriptions."""
        tools_path = AOPS_CORE / "TOOLS.md"
        assert tools_path.exists(), "TOOLS.md must exist"

        content = tools_path.read_text()

        # Should have MCP servers section
        assert "MCP Servers" in content, "TOOLS.md must document MCP servers"

        # Should have standard tools section
        assert "Standard Tools" in content, "TOOLS.md must document standard tools"

        # Should include key servers
        assert "omcp" in content.lower(), "TOOLS.md must include omcp (email)"
        assert "zot" in content.lower(), "TOOLS.md must include zot (research)"
        assert "task_manager" in content.lower(), "TOOLS.md must include task_manager"

    def test_output_returns_curated_content(self) -> None:
        """Tools index output must return curated content from TOOLS.md."""
        import sys

        sys.path.insert(0, str(AOPS_CORE / "hooks"))

        try:
            from user_prompt_submit import load_tools_index

            output = load_tools_index()

            # Should have tools content (not empty or error)
            assert "Tools Index" in output or "MCP Servers" in output, (
                "load_tools_index must return TOOLS.md content"
            )
        finally:
            sys.path.pop(0)


# Forbidden output patterns - if hydrator output contains these, something is wrong
# These would need to be checked in E2E tests or manually
FORBIDDEN_HYDRATOR_OUTPUT_PATTERNS = [
    "fundamentally a human task",
    "the agent cannot",
    "this is not an executable task",
    "requires user action",  # for tool-related reasons
    "agent cannot assume",
    "cannot be performed by",
]


# Document these for manual testing
class TestDocumentForbiddenPatterns:
    """Document forbidden patterns for manual/E2E testing."""

    def test_forbidden_patterns_documented(self) -> None:
        """Ensure forbidden patterns are documented for manual testing."""
        assert len(FORBIDDEN_HYDRATOR_OUTPUT_PATTERNS) > 0

        # Create a markdown snippet that could be used in test plans
        "\n".join(f"- `{p}`" for p in FORBIDDEN_HYDRATOR_OUTPUT_PATTERNS)

        # This test exists to document the patterns
        # In a real E2E test, you'd check hydrator output against these
        assert "fundamentally a human task" in FORBIDDEN_HYDRATOR_OUTPUT_PATTERNS
