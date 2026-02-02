#!/usr/bin/env python3
"""Tests for Gemini hooks.json structure and content.

Validates that the build process generates a valid hooks.json for Gemini CLI
with correct event names and structure.

Regression test for: hooks not loading in Gemini (aops-7280cd2f)
"""

import json
import os
from pathlib import Path

import pytest

# Valid Gemini CLI hook event names
VALID_GEMINI_EVENTS = {
    "SessionStart",
    "BeforeAgent",
    "BeforeTool",
    "AfterTool",
    "SessionEnd",
}

# Events that exist in Claude but NOT in Gemini
INVALID_GEMINI_EVENTS = {
    "SubagentStop",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "PreCompact",
    "Notification",
}


@pytest.fixture
def aops_root() -> Path:
    """Get AOPS root from environment or infer from test location."""
    aops = os.environ.get("AOPS")
    if aops:
        return Path(aops)
    # Infer from test file location
    return Path(__file__).parent.parent


@pytest.fixture
def dist_hooks_json(aops_root: Path) -> Path:
    """Path to the generated hooks.json in dist."""
    return aops_root / "dist" / "aops-core" / "hooks" / "hooks.json"


@pytest.fixture
def gemini_extension_json(aops_root: Path) -> Path:
    """Path to the gemini-extension.json in dist."""
    return aops_root / "dist" / "aops-core" / "gemini-extension.json"


class TestGeminiHooksJsonExists:
    """Tests that hooks.json exists in the correct location."""

    def test_hooks_json_exists_in_dist(self, dist_hooks_json: Path) -> None:
        """Verify hooks.json exists in dist/aops-core/hooks/.

        Gemini CLI reads hooks from hooks/hooks.json, NOT from gemini-extension.json.
        """
        assert dist_hooks_json.exists(), (
            f"hooks.json must exist at {dist_hooks_json}. "
            "Gemini CLI reads hooks from this file, not gemini-extension.json. "
            "Run 'python scripts/build.py' to generate it."
        )

    def test_hooks_json_is_valid_json(self, dist_hooks_json: Path) -> None:
        """Verify hooks.json contains valid JSON."""
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        try:
            with open(dist_hooks_json) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"hooks.json contains invalid JSON: {e}")


class TestGeminiHooksJsonStructure:
    """Tests that hooks.json has the correct structure for Gemini CLI."""

    def test_has_hooks_key(self, dist_hooks_json: Path) -> None:
        """Verify hooks.json has a 'hooks' top-level key."""
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        with open(dist_hooks_json) as f:
            data = json.load(f)

        assert "hooks" in data, (
            "hooks.json must have a 'hooks' key at top level. "
            f"Found keys: {list(data.keys())}"
        )

    def test_hooks_is_object(self, dist_hooks_json: Path) -> None:
        """Verify 'hooks' value is an object/dict."""
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        with open(dist_hooks_json) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        assert isinstance(hooks, dict), (
            f"hooks.json 'hooks' must be an object, got {type(hooks).__name__}"
        )


class TestGeminiHooksEventNames:
    """Tests that hooks.json uses valid Gemini event names."""

    def test_all_events_are_valid_gemini_events(self, dist_hooks_json: Path) -> None:
        """Verify all event names in hooks.json are valid for Gemini CLI.

        Gemini CLI will warn/error on invalid event names like 'SubagentStop'.
        Per P#27: Warning messages are errors - we must not generate invalid events.
        """
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        with open(dist_hooks_json) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        event_names = set(hooks.keys())

        invalid_events = event_names - VALID_GEMINI_EVENTS
        assert not invalid_events, (
            f"hooks.json contains invalid Gemini event names: {invalid_events}. "
            f"Valid events are: {VALID_GEMINI_EVENTS}. "
            "These will cause 'Invalid hook event name' warnings in Gemini CLI."
        )

    def test_no_claude_event_names(self, dist_hooks_json: Path) -> None:
        """Verify Claude-specific event names are not present.

        Claude uses different event names (PreToolUse vs BeforeTool).
        Build.py should translate these.
        """
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        with open(dist_hooks_json) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        event_names = set(hooks.keys())

        claude_events = event_names & INVALID_GEMINI_EVENTS
        assert not claude_events, (
            f"hooks.json contains Claude event names: {claude_events}. "
            "Build.py should translate these to Gemini equivalents."
        )

    def test_has_core_events(self, dist_hooks_json: Path) -> None:
        """Verify hooks.json includes the core hook events."""
        if not dist_hooks_json.exists():
            pytest.skip("hooks.json doesn't exist - run build.py first")

        with open(dist_hooks_json) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        event_names = set(hooks.keys())

        # These are the minimum required events for the framework
        required_events = {"SessionStart", "BeforeTool", "AfterTool"}
        missing = required_events - event_names

        assert not missing, (
            f"hooks.json missing required events: {missing}. "
            f"Present events: {event_names}"
        )


class TestGeminiExtensionJson:
    """Tests that gemini-extension.json contains hooks (injected by build)."""

    def test_hooks_in_extension_manifest(self, gemini_extension_json: Path) -> None:
        """Verify gemini-extension.json HAS a 'hooks' key.

        The build script explicitly injects hooks into the manifest to ensure
        reliable loading in the Gemini CLI. This regression test ensures
        that injection is happening.
        """
        if not gemini_extension_json.exists():
            pytest.skip("gemini-extension.json doesn't exist - run build.py first")

        with open(gemini_extension_json) as f:
            data = json.load(f)

        assert "hooks" in data, (
            "gemini-extension.json MUST have a 'hooks' key. "
            "Build script should inject hooks/hooks.json content into the manifest."
        )
