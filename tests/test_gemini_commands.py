"""Test that Gemini CLI commands are properly built and loadable.

Regression test: commands must be converted from markdown to TOML format
for Gemini CLI, and the resulting TOML must be valid and contain required
fields (description, prompt).

Root cause of regression: convert_commands_to_toml.py was moved to
scripts/archived/ but build.py still references scripts/convert_commands_to_toml.py.
The build silently skips conversion (check=False + exists() guard), then deletes
the .md source files, leaving Gemini with ZERO commands.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
COMMANDS_SRC = AOPS_CORE / "commands"


# ---------------------------------------------------------------------------
# Part (a): Build produces valid TOML command files for every source command
# ---------------------------------------------------------------------------


class TestGeminiCommandBuild:
    """Commands are converted to TOML during Gemini build."""

    def _build_gemini(self, tmp_path: Path) -> Path:
        """Run build.py for gemini platform into tmp_path and return commands dir."""
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "build.py"),
                "--dist-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            env={
                **__import__("os").environ,
                "ACA_DATA": str(tmp_path / "fake_aca_data"),
            },
            timeout=120,
        )
        # Build itself should succeed
        assert result.returncode == 0, f"Build failed:\n{result.stderr}"
        return tmp_path / "aops-gemini" / "commands"

    def test_toml_files_exist_for_every_source_command(self, tmp_path: Path) -> None:
        """Every .md command in aops-core/commands/ must produce a .toml in the Gemini dist."""
        source_commands = {f.stem for f in COMMANDS_SRC.glob("*.md")}
        assert source_commands, "No source command .md files found — test setup broken"

        commands_dir = self._build_gemini(tmp_path)
        built_toml = {f.stem for f in commands_dir.glob("*.toml")}

        missing = source_commands - built_toml
        assert not missing, (
            f"Source commands missing from Gemini build (no .toml generated): {sorted(missing)}. "
            f"Built TOML files: {sorted(built_toml)}. "
            f"Commands dir contents: {sorted(f.name for f in commands_dir.iterdir()) if commands_dir.exists() else 'DIR MISSING'}"
        )

    def test_no_md_files_remain_in_gemini_commands(self, tmp_path: Path) -> None:
        """Gemini commands dir must not contain .md files (only .toml)."""
        commands_dir = self._build_gemini(tmp_path)
        md_files = list(commands_dir.glob("*.md"))
        assert not md_files, (
            f"Markdown command files should not be in Gemini dist: {[f.name for f in md_files]}"
        )

    def test_toml_files_are_valid(self, tmp_path: Path) -> None:
        """Each generated .toml must parse and contain required fields."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        commands_dir = self._build_gemini(tmp_path)
        toml_files = list(commands_dir.glob("*.toml"))
        assert toml_files, "No .toml files found in Gemini commands dir"

        for toml_file in toml_files:
            content = toml_file.read_text()
            try:
                parsed = tomllib.loads(content)
            except Exception as e:
                pytest.fail(f"{toml_file.name} is not valid TOML: {e}")

            assert "description" in parsed, f"{toml_file.name} missing 'description' field"
            assert "prompt" in parsed, f"{toml_file.name} missing 'prompt' field"
            assert len(parsed["description"]) > 0, f"{toml_file.name} has empty description"
            assert len(parsed["prompt"]) > 0, f"{toml_file.name} has empty prompt"


# ---------------------------------------------------------------------------
# Part (b): Convert script is findable by build.py
# ---------------------------------------------------------------------------


class TestCommandConvertScriptAccessible:
    """The convert script must exist where build.py expects it."""

    def test_convert_script_exists_at_build_path(self) -> None:
        """build.py references scripts/convert_commands_to_toml.py — it must exist there."""
        # This is the exact path build.py uses (line ~898)
        expected_path = REPO_ROOT / "scripts" / "convert_commands_to_toml.py"
        assert expected_path.exists(), (
            f"build.py expects convert script at {expected_path} but it doesn't exist. "
            f"It may have been moved to scripts/archived/. "
            f"Either move it back or update the path in build.py."
        )


# ---------------------------------------------------------------------------
# Part (c): Unit test — convert_command produces valid TOML for each command
# ---------------------------------------------------------------------------


class TestConvertCommandUnit:
    """Direct unit tests for the TOML conversion of each command file."""

    @pytest.fixture
    def convert_command(self):
        """Import convert_command from whichever location the script exists."""
        # Try the expected location first, then archived
        for candidate in [
            REPO_ROOT / "scripts" / "convert_commands_to_toml.py",
            REPO_ROOT / "scripts" / "archived" / "convert_commands_to_toml.py",
        ]:
            if candidate.exists():
                import importlib.util

                spec = importlib.util.spec_from_file_location("convert_commands", candidate)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.convert_command
        pytest.skip("convert_commands_to_toml.py not found")

    @pytest.mark.parametrize(
        "command_file",
        sorted(COMMANDS_SRC.glob("*.md")),
        ids=lambda p: p.stem,
    )
    def test_each_command_converts_to_valid_toml(self, convert_command, command_file: Path) -> None:
        """Each source command must produce parseable TOML with description and prompt."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        toml_content = convert_command(command_file)
        assert toml_content, f"{command_file.name} produced empty TOML"

        try:
            parsed = tomllib.loads(toml_content)
        except Exception as e:
            pytest.fail(
                f"{command_file.name} produced invalid TOML: {e}\n\nContent:\n{toml_content}"
            )

        assert "description" in parsed, f"{command_file.name}: TOML missing 'description'"
        assert "prompt" in parsed, f"{command_file.name}: TOML missing 'prompt'"
