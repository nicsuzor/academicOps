"""Tests for branch protection ruleset synchronization logic in scripts/sync_main_ruleset.py."""

import sys
from pathlib import Path

# Add scripts directory to path to import sync_main_ruleset
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_main_ruleset  # noqa: E402


def test_validate_payload_refuses_push_blocking_without_bypass():
    """Ruleset with update/pull_request rule and no bypass actors must fail validation."""
    data = {
        "name": "lock main against pushes",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": [],
        "rules": [{"type": "update"}, {"type": "deletion"}],
    }
    payload = sync_main_ruleset.build_payload(data)
    valid, err = sync_main_ruleset.validate_payload(payload)
    assert not valid
    assert "refusing to apply" in err
    assert "no bypass_actors" in err


def test_validate_payload_accepts_when_integration_bypass_present():
    """Ruleset with push-blocking rule and integration bypass actor passes validation."""
    data = {
        "name": "lock main against pushes",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": [
            {
                "actor_id": 2921286,
                "actor_type": "Integration",
                "bypass_mode": "always",
            }
        ],
        "rules": [{"type": "update"}, {"type": "deletion"}, {"type": "non_fast_forward"}],
    }
    payload = sync_main_ruleset.build_payload(data)
    valid, err = sync_main_ruleset.validate_payload(payload)
    assert valid
    assert err == ""


def test_build_payload_preserves_structure():
    """build_payload correctly extracts standard ruleset fields."""
    data = {
        "name": "test ruleset",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"]}},
        "bypass_actors": None,
        "rules": [{"type": "deletion"}],
    }
    payload = sync_main_ruleset.build_payload(data)
    assert payload["name"] == "test ruleset"
    assert payload["target"] == "branch"
    assert payload["enforcement"] == "active"
    assert payload["bypass_actors"] == []
    assert payload["rules"] == [{"type": "deletion"}]
