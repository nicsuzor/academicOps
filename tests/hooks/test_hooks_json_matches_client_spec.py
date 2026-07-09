"""CI guard: aops-core/hooks/hooks.json's registered Claude event keys must
match client_spec.CLAUDE_ALL_EVENTS exactly (enforcer finding on PR #2192).

hooks.json is hand-maintained and independently lists the Claude-native event
keys it subscribes to; CLAUDE_ALL_EVENTS is documented as the SSoT for that
same set (specs/enforcement/GATES.md). Nothing generated hooks.json's keys
from CLAUDE_ALL_EVENTS, so the two could silently drift on a future CC
version bump (an event added to/renamed in one list without the other). This
test pins the invariant so drift fails CI instead of shipping silently.
"""

from __future__ import annotations

import json
from pathlib import Path

from hooks import client_spec as cs

HOOKS_JSON_PATH = Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "hooks.json"


def test_hooks_json_events_match_claude_all_events():
    data = json.loads(HOOKS_JSON_PATH.read_text())
    registered = set(data["hooks"].keys())
    canonical = set(cs.CLAUDE_ALL_EVENTS)

    missing_from_hooks_json = canonical - registered
    extra_in_hooks_json = registered - canonical

    assert not missing_from_hooks_json, (
        f"client_spec.CLAUDE_ALL_EVENTS has events not registered in hooks.json: "
        f"{sorted(missing_from_hooks_json)}. Add a subscription for each to "
        "aops-core/hooks/hooks.json."
    )
    assert not extra_in_hooks_json, (
        f"hooks.json registers events not in client_spec.CLAUDE_ALL_EVENTS: "
        f"{sorted(extra_in_hooks_json)}. Either add them to CLAUDE_ALL_EVENTS "
        "(if genuinely new Claude Code events) or remove the stale hooks.json entry."
    )
