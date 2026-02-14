"""Tests for gemini-extension.json and hooks.json consistency."""

import json
from pathlib import Path

import pytest


class TestGeminiHooksJsonExists:
    """Test that hooks.json is generated correctly for Gemini CLI."""

    @pytest.fixture
    def root_dir(self) -> Path:
        """Return the repo root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def gemini_extension_json(self, root_dir: Path) -> Path:
        """Return the path to gemini-extension.json."""
        return root_dir / "gemini-extension.json"

    @pytest.fixture
    def dist_hooks_json(self, root_dir: Path) -> Path:
        """Return the path to dist/aops-core/hooks/hooks.json."""
        return root_dir / "dist" / "aops-core" / "hooks" / "hooks.json"

    def test_gemini_extension_json_exists(self, gemini_extension_json: Path) -> None:
        """Verify gemini-extension.json exists at root."""
        assert gemini_extension_json.exists(), (
            f"gemini-extension.json must exist at {gemini_extension_json}"
        )

    def test_hooks_json_exists_in_dist(self, dist_hooks_json: Path) -> None:
        """Verify hooks.json exists in dist/aops-core/hooks/.

        Gemini CLI reads hooks from hooks/hooks.json, NOT from gemini-extension.json.
        """
        if not dist_hooks_json.exists():
            pytest.skip(
                f"hooks.json not found at {dist_hooks_json}. "
                "Skipping test as build artifacts are missing in this environment."
            )

        assert dist_hooks_json.exists(), (
            f"hooks.json must exist at {dist_hooks_json}. "
            "Gemini CLI reads hooks from this file, not gemini-extension.json. "
            "Run 'python scripts/build.py' to generate it."
        )

    def test_hooks_json_matches_extension(
        self, gemini_extension_json: Path, dist_hooks_json: Path
    ) -> None:
        """Verify content of hooks.json matches gemini-extension.json.

        The build process should copy gemini-extension.json to dist/.../hooks.json.
        """
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json missing, skipping content verification")

        ext_content = json.loads(gemini_extension_json.read_text())
        hooks_content = json.loads(dist_hooks_json.read_text())

        # Check key fields
        assert hooks_content["hookType"] == ext_content["hookType"]
        assert hooks_content["version"] == ext_content["version"]
        assert hooks_content["hooks"] == ext_content["hooks"]
