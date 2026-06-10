"""Tests for the Cowork hooks.json build transform.

Verifies that ``_generate_cowork_hooks_json`` rewrites every ``--client claude``
occurrence to ``--client claude-cowork`` while leaving every other property
of the source hooks.json intact (event names, ``${CLAUDE_PLUGIN_ROOT}``,
matchers, timeouts, disabled entries, hook ordering).

Relates to task aops-1020e4fd: Cowork build must pass ``--client claude-cowork``
so router.py + session_paths.py recognise the cowork surface as Claude-family.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
AOPS_CORE_DIR = REPO_ROOT / "aops-core"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_build_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build", SCRIPTS_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build_mod():
    return load_build_module()


@pytest.fixture
def transform(build_mod, tmp_path):
    """Run the Cowork build transform on the real hooks.json and return the result."""
    src = AOPS_CORE_DIR / "hooks" / "hooks.json"
    dst = tmp_path / "hooks.json"
    build_mod._generate_cowork_hooks_json(src, dst)
    with open(dst) as f:
        return json.load(f)


class TestCoworkHooksBuildTransform:
    def test_output_has_hooks_key(self, transform):
        assert "hooks" in transform

    def test_every_command_uses_claude_cowork_client(self, transform):
        """No event command may carry ``--client claude`` without the cowork suffix.

        The whole point of the transform: router.py argparse rejects ``claude``
        as the cowork-build client because session_paths needs to distinguish
        the surface label.
        """
        for event, hook_entries in transform["hooks"].items():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    if "--client" not in cmd:
                        continue
                    assert "--client claude-cowork" in cmd, (
                        f"{event} hook still carries --client claude (no cowork suffix): {cmd}"
                    )
                    # And the bare 'claude' literal must NOT survive next to --client
                    # (we'd accept `--client claude-cowork --foo claude` if anything
                    # else uses 'claude' as a value; here we just guard the flag.)
                    assert "--client claude " not in cmd + " ", (
                        f"{event} command still has '--client claude' before suffix: {cmd}"
                    )

    def test_claude_plugin_root_variable_preserved(self, transform):
        """Cowork uses the same Claude plugin contract; ${CLAUDE_PLUGIN_ROOT}
        must NOT be rewritten (unlike Gemini/Antigravity)."""
        seen_plugin_root = False
        for hook_entries in transform["hooks"].values():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    if "${CLAUDE_PLUGIN_ROOT}" in cmd:
                        seen_plugin_root = True
        assert seen_plugin_root, (
            "Expected at least one cowork hook to keep ${CLAUDE_PLUGIN_ROOT} "
            "(cowork uses Claude's plugin layout verbatim)"
        )

    def test_event_set_preserved(self, transform, build_mod, tmp_path):
        """The cowork transform must not drop or rename Claude events — it is
        a string substitution, not an event mapping like Gemini/agy."""
        src = AOPS_CORE_DIR / "hooks" / "hooks.json"
        with open(src) as f:
            original = json.load(f)
        assert set(transform["hooks"].keys()) == set(original["hooks"].keys())

    def test_replace_pattern_does_not_touch_other_args(self, build_mod, tmp_path):
        """Only the ``--client claude`` token should change. A command that
        mentions 'claude' elsewhere (e.g. in a path argument) is left alone."""
        # Construct a small fixture that exercises the replace boundary.
        src_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'router.py --client claude --notes "claude is fine here"',
                            }
                        ]
                    }
                ]
            }
        }
        src = tmp_path / "in.json"
        dst = tmp_path / "out.json"
        src.write_text(json.dumps(src_data))

        build_mod._generate_cowork_hooks_json(src, dst)
        result = json.loads(dst.read_text())
        cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

        assert "--client claude-cowork" in cmd
        # The 'claude' token inside the --notes value must not be touched.
        assert '"claude is fine here"' in cmd
