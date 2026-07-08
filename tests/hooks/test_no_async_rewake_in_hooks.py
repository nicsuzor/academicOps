import json
from pathlib import Path


def test_no_async_rewake_in_hooks_json():
    """CI Guard for #2181 (fix direction B)

    Ensures asyncRewake is never configured in hooks.json since it
    causes Claude Code 2.1.204 to silently discard JSON payload,
    destroying the block-mode handover capabilities.
    """
    hooks_file = Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "hooks.json"

    with open(hooks_file) as f:
        data = json.load(f)

    for event_name, hook_blocks in data.get("hooks", {}).items():
        for block in hook_blocks:
            for hook in block.get("hooks", []):
                assert "asyncRewake" not in hook, (
                    f"asyncRewake found in {event_name} hook. "
                    f"This must be absent to preserve JSON-block delivery."
                )
                assert "rewakeMessage" not in hook, (
                    f"rewakeMessage found in {event_name} hook, but asyncRewake is retired."
                )
                assert "rewakeSummary" not in hook, (
                    f"rewakeSummary found in {event_name} hook, but asyncRewake is retired."
                )
