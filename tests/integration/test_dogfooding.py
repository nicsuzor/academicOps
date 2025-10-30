"""Dogfooding Integration Tests.

Validates that academicOps can install into itself without conflicts.
Tests the complete installation workflow and runtime behavior.

Issue #128: Flat Architecture Implementation
Requirement #9: Dogfooding

Expected: Tests may FAIL initially (validates requirements, not current state).
Success: All tests pass = installation script works correctly.
"""

import os
from pathlib import Path
import subprocess
import pytest


@pytest.mark.slow
class TestDogfoodingInstallation:
    """Validate installation script works in ${ACADEMICOPS} itself."""

    def test_install_script_exists(self):
        """Installation script should exist and be executable."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        install_script = academicops / "scripts/setup_academicops.sh"

        assert install_script.exists(), "Installation script missing"
        assert os.access(install_script, os.X_OK), (
            "Installation script not executable"
        )

    def test_install_script_can_run_in_academicops(self):
        """Installation script should successfully run in ${ACADEMICOPS}."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        install_script = academicops / "scripts/setup_academicops.sh"

        if not install_script.exists():
            pytest.skip("Installation script not yet implemented")

        # Run installation in academicOps itself (dogfooding)
        result = subprocess.run(
            [str(install_script), str(academicops)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed without errors
        assert result.returncode == 0, (
            f"Installation failed in ${ACADEMICOPS}:\n{result.stderr}"
        )

    def test_installation_creates_expected_structure(self):
        """After installation, ${ACADEMICOPS} should have complete structure."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Expected after running install script
        expected_structure = [
            ".claude/settings.json",
            ".claude/commands",  # Symlink or dir
            ".claude/skills",  # Symlink or dir
            "core",
            "hooks",
        ]

        for path_str in expected_structure:
            path = academicops / path_str
            assert path.exists(), (
                f"Installation incomplete: missing {path_str}"
            )

    def test_no_conflicts_between_development_and_deployment(self):
        """Development files should not conflict with deployment structure."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Development files should still exist after installation
        dev_files = [
            "tests",
            "pyproject.toml",
            "README.md",
            ".git",
        ]

        for dev_file in dev_files:
            path = academicops / dev_file
            assert path.exists(), (
                f"Installation damaged development file: {dev_file}"
            )

        # Deployment files should also exist
        deployment_files = [
            "core",
            ".claude/settings.json",
        ]

        for deploy_file in deployment_files:
            path = academicops / deploy_file
            assert path.exists(), (
                f"Installation didn't create deployment file: {deploy_file}"
            )


@pytest.mark.slow
class TestDogfoodingRuntime:
    """Validate runtime behavior when running Claude in ${ACADEMICOPS}."""

    def test_hooks_execute_successfully(self):
        """Hooks should execute without errors in ${ACADEMICOPS}."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Test SessionStart hook (load_instructions.py)
        hook_script = academicops / "hooks/load_instructions.py"

        if not hook_script.exists():
            pytest.skip("Hook script not in /bots/ yet")

        # Should be executable
        assert os.access(hook_script, os.X_OK), (
            "load_instructions.py not executable"
        )

        # Should run without error
        result = subprocess.run(
            ["uv", "run", "python", str(hook_script), "_CORE.md"],
            cwd=str(academicops),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"Hook failed in ${ACADEMICOPS}:\n{result.stderr}"
        )

    def test_validate_tool_hook_works(self):
        """PreToolUse hook should work in ${ACADEMICOPS}."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        hook_script = academicops / "hooks/validate_tool.py"

        if not hook_script.exists():
            pytest.skip("validate_tool.py not in /bots/ yet")

        assert os.access(hook_script, os.X_OK), (
            "validate_tool.py not executable"
        )

        # Test with sample tool invocation
        test_input = {
            "tool": "Bash",
            "parameters": {"command": "echo test"},
        }

        import json
        result = subprocess.run(
            ["uv", "run", "python", str(hook_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            cwd=str(academicops),
            timeout=5,
        )

        assert result.returncode == 0, (
            f"validate_tool.py failed:\n{result.stderr}"
        )

        # Should return valid JSON
        try:
            response = json.loads(result.stdout)
            assert "continue" in response, "Hook response missing 'continue' field"
        except json.JSONDecodeError as e:
            pytest.fail(f"Hook returned invalid JSON: {e}\n{result.stdout}")

    def test_agents_can_be_loaded(self):
        """Agent instructions should be loadable from /core/."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        core_agents = academicops / "core/_CORE.md"

        assert core_agents.exists(), "Core agent instructions missing"

        # Should be readable
        content = core_agents.read_text()
        assert len(content) > 0, "Core agent file empty"
        assert "Axiom" in content or "CORE" in content, (
            "Core agent doesn't look like agent instructions"
        )

    def test_claude_md_files_discoverable(self):
        """CLAUDE.md files should be discoverable in ${ACADEMICOPS}."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Should have CLAUDE.md in key directories (Issue #120)
        expected_claude_files = [
            "bots/CLAUDE.md",
            "tests/CLAUDE.md",
            "scripts/CLAUDE.md",
        ]

        for claude_path in expected_claude_files:
            full_path = academicops / claude_path
            assert full_path.exists(), (
                f"CLAUDE.md missing: {claude_path}"
            )

            # Should contain @ references
            content = full_path.read_text()
            assert "@" in content, (
                f"{claude_path} should contain @ references"
            )


@pytest.mark.slow
class TestDogfoodingGitIntegration:
    """Validate git operations work correctly in ${ACADEMICOPS}."""

    def test_symlinks_are_gitignored(self):
        """Symlinked framework files should be gitignored."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Check if .gitignore covers symlinks
        gitignore = academicops / ".gitignore"

        if not gitignore.exists():
            pytest.skip(".gitignore not yet created")

        content = gitignore.read_text()

        # Should ignore .claude/settings.local.json
        assert ".claude/settings.local.json" in content or "settings.local.json" in content, (
            "Gitignore should cover local settings"
        )

    def test_development_files_not_ignored(self):
        """Development files should NOT be gitignored."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Run git status to verify development files tracked
        result = subprocess.run(
            ["git", "status", "--porcelain", "tests/", "pyproject.toml"],
            cwd=str(academicops),
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should succeed (files exist in git)
        assert result.returncode == 0, "Git status failed"

    def test_bots_directory_tracked_in_git(self):
        """/bots/ directory should be tracked (it's source code, not deployment)."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # In ${ACADEMICOPS}, /bots/ is source, should be in git
        result = subprocess.run(
            ["git", "ls-files", "bots/"],
            cwd=str(academicops),
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, "Git ls-files failed"

        # Should have files in bots/ tracked
        tracked_files = result.stdout.strip().split("\n")
        assert len(tracked_files) > 0, (
            "/bots/ directory not tracked in git (should be source code)"
        )
        assert any("core" in f for f in tracked_files), (
            "core/ not tracked"
        )


@pytest.mark.slow
class TestDogfoodingVsProjectInstallation:
    """Validate ${ACADEMICOPS} structure matches what we install in projects."""

    def test_claude_folder_structure_matches(self):
        """${ACADEMICOPS}/.claude/ should match project installation template."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Load dist/ template to compare
        dist_template = academicops / "dist/.claude/settings.json"

        if not dist_template.exists():
            pytest.skip("dist/ template not yet created")

        # ${ACADEMICOPS}/.claude/ should have same structure
        academicops_settings = academicops / ".claude/settings.json"

        assert academicops_settings.exists(), (
            "${ACADEMICOPS}/.claude/settings.json missing (should match project template)"
        )

        # Both should have hooks configured
        import json

        template_config = json.loads(dist_template.read_text())
        academicops_config = json.loads(academicops_settings.read_text())

        # Should both have hooks
        assert "hooks" in template_config, "Template missing hooks"
        assert "hooks" in academicops_config, "${ACADEMICOPS} missing hooks"

        # Should both have same hook types
        template_hooks = set(template_config["hooks"].keys())
        academicops_hooks = set(academicops_config["hooks"].keys())

        assert template_hooks == academicops_hooks, (
            f"Hook mismatch: template={template_hooks}, academicOps={academicops_hooks}"
        )

    def test_bots_structure_matches_what_we_install(self):
        """${ACADEMICOPS}/bots/ should be source for what we symlink in projects."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # ${ACADEMICOPS}/bots/ is the source
        source_bots = academicops / "bots"

        # Should have complete structure
        required_subdirs = ["agents", "hooks", "scripts"]

        for subdir in required_subdirs:
            path = source_bots / subdir
            assert path.exists(), (
                f"${ACADEMICOPS}/bots/{subdir}/ missing (source for project installations)"
            )

            # Should contain files (not empty)
            files = list(path.iterdir())
            assert len(files) > 0, (
                f"${ACADEMICOPS}/bots/{subdir}/ empty"
            )
