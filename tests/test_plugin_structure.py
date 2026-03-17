#!/usr/bin/env python3
"""
Smoke tests for aops-core plugin structure.

Verifies that the plugin has all required components and can be loaded.
"""

from pathlib import Path

import pytest

# Plugin root directory (updated for v1.1 structure)
PLUGIN_ROOT = Path(__file__).parent.parent / "aops-core"


class TestPluginStructure:
    """Verify plugin directory structure."""

    def test_plugin_json_exists(self) -> None:
        """Plugin manifest must exist."""
        manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        assert manifest.exists(), f"Missing plugin manifest: {manifest}"

    def test_required_directories_exist(self) -> None:
        """All required directories must exist."""
        required_dirs = ["skills", "agents", "hooks", "lib"]
        for dir_name in required_dirs:
            dir_path = PLUGIN_ROOT / dir_name
            assert dir_path.is_dir(), f"Missing required directory: {dir_name}"


class TestCoreSkills:
    """Verify skills directory exists."""

    def test_skills_directory_exists(self) -> None:
        """Skills directory must exist."""
        skills_dir = PLUGIN_ROOT / "skills"
        assert skills_dir.is_dir(), "Missing skills directory"


class TestCoreAgents:
    """Verify core agents are present."""

    CORE_AGENTS = ["prompt-hydrator", "custodiet", "qa", "effectual-planner"]

    def test_all_core_agents_present(self) -> None:
        """All 5 core agents must be present."""
        agents_dir = PLUGIN_ROOT / "agents"
        for agent_name in self.CORE_AGENTS:
            agent_file = agents_dir / f"{agent_name}.md"
            assert agent_file.exists(), f"Missing core agent: {agent_name}"


class TestCoreHooks:
    """Verify core hooks are present."""

    CORE_HOOKS = ["router.py", "unified_logger.py", "user_prompt_submit.py"]

    def test_all_core_hooks_present(self) -> None:
        """All core hooks must be present."""
        hooks_dir = PLUGIN_ROOT / "hooks"
        for hook_name in self.CORE_HOOKS:
            hook_file = hooks_dir / hook_name
            assert hook_file.exists(), f"Missing core hook: {hook_name}"

    def test_hook_templates_exist(self) -> None:
        """Hook templates directory must exist with content."""
        templates_dir = PLUGIN_ROOT / "hooks" / "templates"
        assert templates_dir.is_dir(), "Missing hooks/templates directory"
        templates = list(templates_dir.glob("*.md"))
        assert len(templates) > 0, "No template files in hooks/templates/"


class TestCoreLib:
    """Verify core library files are present."""

    CORE_LIB_FILES = ["paths.py", "session_state.py", "session_reader.py"]

    def test_all_core_lib_files_present(self) -> None:
        """All core lib files must be present."""
        lib_dir = PLUGIN_ROOT / "lib"
        for lib_name in self.CORE_LIB_FILES:
            lib_file = lib_dir / lib_name
            assert lib_file.exists(), f"Missing core lib file: {lib_name}"


class TestGovernanceFiles:
    """Verify enforced axioms and heuristics are present."""

    def test_axioms_file_exists(self) -> None:
        """AXIOMS.md must exist in framework directory."""
        axioms_file = PLUGIN_ROOT / "AXIOMS.md"
        assert axioms_file.exists(), "Missing AXIOMS.md"

    def test_heuristics_file_exists(self) -> None:
        """HEURISTICS.md must exist in framework directory."""
        heuristics_file = PLUGIN_ROOT / "HEURISTICS.md"
        assert heuristics_file.exists(), "Missing HEURISTICS.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
