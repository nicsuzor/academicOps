"""End-to-end tests for web bundle standalone operation.

Tests verify that Claude Code can operate correctly in a project with
a bundled .claude/ directory (created by sync_web_bundle.py) WITHOUT
requiring the full aOps environment ($AOPS, $ACA_DATA).

This tests the "remote workflow" scenario where:
- User clones a project with bundled .claude/
- No aOps framework installed globally
- Claude Code Web or local CLI should still work

Test categories:
1. Bundle structure validation
2. Settings file validity
3. Claude Code execution in bundled environment
4. Skill discovery and invocation
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _claude_cli_available() -> bool:
    """Check if claude CLI command is available in PATH."""
    return shutil.which("claude") is not None


def run_claude_in_project(
    prompt: str,
    project_path: Path,
    timeout_seconds: int = 120,
    env_override: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute Claude Code in a project directory with minimal environment.

    This simulates the remote/web workflow where AOPS and ACA_DATA
    are NOT available - only the bundled .claude/ directory.

    Args:
        prompt: Prompt to send to Claude
        project_path: Project directory with .claude/ bundle
        timeout_seconds: Command timeout
        env_override: Additional environment variables (for testing)

    Returns:
        Dictionary with success, output, result, error keys
    """
    if not _claude_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "claude CLI not found in PATH",
        }

    cmd = ["claude", "-p", prompt, "--output-format", "json"]

    # Build minimal environment - explicitly EXCLUDE AOPS and ACA_DATA
    # to simulate remote environment
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "TERM": os.environ.get("TERM", "xterm"),
        # API keys needed for Claude to work
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    }

    # Add any overrides for testing
    if env_override:
        env.update(env_override)

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"Exit code {result.returncode}: {result.stderr}",
            }

        try:
            parsed = json.loads(result.stdout)
            return {
                "success": True,
                "output": result.stdout,
                "result": parsed,
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"JSON parse error: {e}",
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": f"Timeout after {timeout_seconds}s",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": str(e),
        }


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def writing_repo() -> Path:
    """Get the writing repo path (real bundled project).

    Note: ACA_DATA points to ~/writing/data/ (the data subdirectory),
    but the .claude bundle is at ~/writing/.claude (repo root).
    We need the repo root, not the data directory.
    """
    # ACA_DATA is ~/writing/data, so go up one level for repo root
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        path = Path(aca_data).parent  # ~/writing/data -> ~/writing
    else:
        path = Path.home() / "writing"

    if not path.exists():
        pytest.skip(f"Writing repo not found at {path}")

    return path


@pytest.fixture
def bundled_claude_dir(writing_repo: Path) -> Path:
    """Get the .claude directory in the writing repo."""
    claude_dir = writing_repo / ".claude"
    if not claude_dir.exists():
        pytest.skip(f"No .claude bundle at {claude_dir}")
    return claude_dir


# =============================================================================
# Bundle Structure Tests
# =============================================================================


class TestBundleStructure:
    """Verify the bundled .claude/ directory has correct structure."""

    def test_claude_dir_exists(self, bundled_claude_dir: Path) -> None:
        """Test that .claude directory exists."""
        assert bundled_claude_dir.exists(), ".claude directory should exist"
        assert bundled_claude_dir.is_dir(), ".claude should be a directory"

    def test_has_settings_json(self, bundled_claude_dir: Path) -> None:
        """Test that settings.json exists and is valid JSON."""
        settings_path = bundled_claude_dir / "settings.json"
        assert settings_path.exists(), "settings.json should exist"

        content = settings_path.read_text()
        settings = json.loads(content)  # Should not raise

        assert isinstance(settings, dict), "settings.json should be a dict"

    def test_has_claude_md(self, bundled_claude_dir: Path) -> None:
        """Test that CLAUDE.md exists with expected content."""
        claude_md = bundled_claude_dir / "CLAUDE.md"
        assert claude_md.exists(), "CLAUDE.md should exist"

        content = claude_md.read_text()
        assert (
            "aOps" in content or "skill" in content.lower()
        ), "CLAUDE.md should reference aOps or skills"

    def test_has_skills_directory(self, bundled_claude_dir: Path) -> None:
        """Test that skills directory exists with content."""
        skills_dir = bundled_claude_dir / "skills"
        assert skills_dir.exists(), "skills/ directory should exist"
        assert skills_dir.is_dir(), "skills should be a directory"

        # Should have at least some skills
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert len(skill_dirs) > 5, f"Expected many skills, found {len(skill_dirs)}"

    def test_has_aops_bundle_marker(self, bundled_claude_dir: Path) -> None:
        """Test that .aops-bundle marker exists (identifies managed bundle)."""
        marker = bundled_claude_dir / ".aops-bundle"
        assert marker.exists(), ".aops-bundle marker should exist"

    def test_has_version_file(self, bundled_claude_dir: Path) -> None:
        """Test that .aops-version exists for tracking."""
        version_file = bundled_claude_dir / ".aops-version"
        assert version_file.exists(), ".aops-version should exist"

        content = version_file.read_text().strip()
        # Should be a git SHA or "unknown"
        assert len(content) > 0, "Version file should not be empty"


# =============================================================================
# Settings Validation Tests
# =============================================================================


class TestSettingsValidity:
    """Verify settings.json is valid for Claude Code."""

    def test_settings_has_permissions(self, bundled_claude_dir: Path) -> None:
        """Test that settings.json has permissions block."""
        settings_path = bundled_claude_dir / "settings.json"
        settings = json.loads(settings_path.read_text())

        assert "permissions" in settings, "settings should have permissions key"
        perms = settings["permissions"]
        assert "allow" in perms, "permissions should have allow key"
        assert isinstance(perms["allow"], list), "allow should be a list"

    def test_settings_allows_read(self, bundled_claude_dir: Path) -> None:
        """Test that settings allows Read operations (minimum for web)."""
        settings_path = bundled_claude_dir / "settings.json"
        settings = json.loads(settings_path.read_text())

        allow_list = settings.get("permissions", {}).get("allow", [])
        assert "Read" in allow_list, "Web settings should allow Read"

    def test_settings_no_hooks_for_web(self, bundled_claude_dir: Path) -> None:
        """Test that web settings don't have hooks (would fail without $AOPS)."""
        settings_path = bundled_claude_dir / "settings.json"
        settings = json.loads(settings_path.read_text())

        # Web settings should NOT have hooks (they require $AOPS)
        if "hooks" in settings:
            hooks = settings["hooks"]
            # If hooks exist, they should be empty or not reference $AOPS
            for hook_type, hook_configs in hooks.items():
                for config in hook_configs:
                    if "hooks" in config:
                        for hook in config["hooks"]:
                            if hook.get("type") == "command":
                                cmd = hook.get("command", "")
                                assert (
                                    "$AOPS" not in cmd
                                ), f"Web settings hook references $AOPS: {cmd}"

    def test_settings_matches_web_template(self, bundled_claude_dir: Path) -> None:
        """Test that bundled settings match web template structure."""
        settings_path = bundled_claude_dir / "settings.json"
        settings = json.loads(settings_path.read_text())

        # Web settings should be minimal - check for web-specific comment
        comment = settings.get("$comment", "")
        # Either has web comment or is minimal (no hooks)
        is_web_config = "web" in comment.lower() or "hooks" not in settings
        assert (
            is_web_config
        ), "Settings should be web-compatible (no hooks or web comment)"


# =============================================================================
# Claude Code Execution Tests
# =============================================================================


@pytest.mark.slow
@pytest.mark.integration
class TestClaudeExecution:
    """Test Claude Code execution in bundled project."""

    def test_claude_starts_in_project(self, writing_repo: Path) -> None:
        """Test that Claude Code can start in the project directory."""
        if not _claude_cli_available():
            pytest.skip("claude CLI not available")

        result = run_claude_in_project(
            "Respond with just the word 'ok'",
            writing_repo,
            timeout_seconds=60,
        )

        assert result["success"], f"Claude should start: {result.get('error')}"

    def test_claude_can_read_files(self, writing_repo: Path) -> None:
        """Test that Claude can read files in the project."""
        if not _claude_cli_available():
            pytest.skip("claude CLI not available")

        result = run_claude_in_project(
            "Read the file .claude/CLAUDE.md and respond with 'found' if it exists",
            writing_repo,
            timeout_seconds=90,
        )

        assert result["success"], f"Claude should read files: {result.get('error')}"

    def test_claude_sees_skills(self, writing_repo: Path) -> None:
        """Test that Claude can see available skills from bundle."""
        if not _claude_cli_available():
            pytest.skip("claude CLI not available")

        result = run_claude_in_project(
            "What skills are available? Just list 3 skill names briefly.",
            writing_repo,
            timeout_seconds=90,
        )

        assert result["success"], f"Claude should see skills: {result.get('error')}"

        # The response should mention some skills
        output = result.get("output", "")
        # Check if common skill names appear
        has_skills = any(
            name in output.lower()
            for name in ["analyst", "python", "pdf", "task", "feature"]
        )
        assert has_skills, f"Response should mention skills: {output[:500]}"


# =============================================================================
# Standalone Script (No pytest required)
# =============================================================================


def main() -> int:
    """Run basic bundle validation without pytest.

    This can be run directly to validate a bundle:
        python tests/integration/test_web_bundle_e2e.py
    """
    print("=" * 70)
    print("WEB BUNDLE E2E VALIDATION")
    print("=" * 70)

    # Find writing repo
    # Note: ACA_DATA is ~/writing/data, we need ~/writing (repo root)
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        writing_path = Path(aca_data).parent  # ~/writing/data -> ~/writing
    else:
        writing_path = Path.home() / "writing"

    if not writing_path.exists():
        print(f"❌ FAIL: Writing repo not found at {writing_path}")
        return 1

    claude_dir = writing_path / ".claude"
    if not claude_dir.exists():
        print(f"❌ FAIL: No .claude bundle at {claude_dir}")
        return 1

    print(f"Testing bundle at: {claude_dir}\n")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Structure
    print("1. Checking bundle structure...")
    required = ["settings.json", "CLAUDE.md", "skills", ".aops-bundle"]
    for item in required:
        path = claude_dir / item
        if path.exists():
            print(f"   ✓ {item}")
            tests_passed += 1
        else:
            print(f"   ✗ {item} MISSING")
            tests_failed += 1

    # Test 2: Settings validity
    print("\n2. Validating settings.json...")
    settings_path = claude_dir / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if "permissions" in settings:
            print("   ✓ Has permissions block")
            tests_passed += 1
        else:
            print("   ✗ Missing permissions block")
            tests_failed += 1

        if settings.get("permissions", {}).get("allow"):
            print("   ✓ Has allow list")
            tests_passed += 1
        else:
            print("   ✗ Missing allow list")
            tests_failed += 1

        # Check for hooks with $AOPS (would fail in web)
        has_aops_hooks = False
        for hook_configs in settings.get("hooks", {}).values():
            for config in hook_configs:
                for hook in config.get("hooks", []):
                    if "$AOPS" in hook.get("command", ""):
                        has_aops_hooks = True
                        break

        if not has_aops_hooks:
            print("   ✓ No $AOPS-dependent hooks")
            tests_passed += 1
        else:
            print("   ✗ Contains $AOPS hooks (will fail in web)")
            tests_failed += 1

    except json.JSONDecodeError as e:
        print(f"   ✗ Invalid JSON: {e}")
        tests_failed += 1

    # Test 3: Skills count
    print("\n3. Checking skills...")
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        if skill_count >= 5:
            print(f"   ✓ Found {skill_count} skills")
            tests_passed += 1
        else:
            print(f"   ✗ Only {skill_count} skills (expected >= 5)")
            tests_failed += 1
    else:
        print("   ✗ Skills directory missing")
        tests_failed += 1

    # Test 4: Claude execution (if available)
    print("\n4. Testing Claude Code execution...")
    if _claude_cli_available():
        result = run_claude_in_project(
            "Respond with just 'ok'",
            writing_path,
            timeout_seconds=60,
        )
        if result["success"]:
            print("   ✓ Claude Code executes successfully")
            tests_passed += 1
        else:
            print(f"   ✗ Claude failed: {result.get('error')}")
            tests_failed += 1
    else:
        print("   ⚠ Skipped (claude CLI not in PATH)")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {tests_failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
