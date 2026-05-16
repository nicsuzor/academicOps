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

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
COMMANDS_SRC = AOPS_CORE / "commands"
CONVERT_SCRIPT = REPO_ROOT / "scripts" / "convert_commands_to_toml.py"


# ---------------------------------------------------------------------------
# Part (a): Run the real convert script and validate output
# ---------------------------------------------------------------------------


class TestGeminiCommandBuild:
    """Run convert_commands_to_toml.py for real and check the output."""

    @pytest.fixture(scope="class")
    def built_commands_dir(self, tmp_path_factory):
        """Run the convert script once for the class and return the output directory."""
        class_tmp_path = tmp_path_factory.mktemp("gemini_build")
        output_dir = class_tmp_path / "commands"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(CONVERT_SCRIPT),
                "--output-dir",
                str(output_dir),
                "--no-gitignore",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"convert_commands_to_toml.py failed (exit {result.returncode}):\n{result.stderr}"
        )
        return output_dir

    def test_toml_files_exist_for_every_source_command(self, built_commands_dir: Path) -> None:
        """Every .md command in aops-core/commands/ must produce a .toml."""
        source_commands = {f.stem for f in COMMANDS_SRC.glob("*.md")}
        assert source_commands, "No source command .md files found — test setup broken"

        built_toml = {f.stem for f in built_commands_dir.glob("*.toml")}

        missing = source_commands - built_toml
        assert not missing, (
            f"Source commands missing from convert output (no .toml generated): {sorted(missing)}. "
            f"Built TOML files: {sorted(built_toml)}. "
            f"Output dir contents: {sorted(f.name for f in built_commands_dir.iterdir()) if built_commands_dir.exists() else 'DIR MISSING'}"
        )

    def test_toml_files_are_valid(self, built_commands_dir: Path) -> None:
        """Each generated .toml must parse and contain required fields."""
        toml_files = list(built_commands_dir.glob("*.toml"))
        assert toml_files, "No .toml files produced by convert script"

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
        """Import convert_command from the canonical location."""
        import importlib.util

        if not CONVERT_SCRIPT.exists():
            pytest.fail(
                f"Convert script not found at {CONVERT_SCRIPT}. "
                "build.py expects it there — was it moved to scripts/archived/?"
            )
        spec = importlib.util.spec_from_file_location("convert_commands", CONVERT_SCRIPT)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.convert_command

    @pytest.mark.parametrize(
        "command_file",
        sorted(COMMANDS_SRC.glob("*.md")),
        ids=lambda p: p.stem,
    )
    def test_each_command_converts_to_valid_toml(self, convert_command, command_file: Path) -> None:
        """Each source command must produce parseable TOML with description and prompt."""
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
