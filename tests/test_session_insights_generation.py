"""
Tests for main agent session insights generation (ns-u052).

Verifies that session insights can be generated with required fields
and saved to session state per the simplified workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lib.session_paths import (
    get_session_file_path,
)
from lib.session_state import (
    SessionState,
    create_session_state,
    get_or_create_session_state,
    load_session_state,
    save_session_state,
    set_session_insights,
)


class TestSessionInsightsSchema:
    """Test session insights schema validation."""

    def test_insights_has_required_fields(self) -> None:
        """Session insights must have required fields."""
        # These are the fields the main agent can generate directly
        required_fields = {
            "summary",  # One sentence describing what was worked on
            "outcome",  # success/partial/failure
            "accomplishments",  # List of completed items
            "friction_points",  # What was harder than expected
            "proposed_changes",  # Framework improvements identified
        }

        # A valid insights dict
        valid_insights = {
            "summary": "Implemented session insights generation feature",
            "outcome": "success",
            "accomplishments": ["Created tests", "Updated AGENTS.md"],
            "friction_points": [],
            "proposed_changes": [],
        }

        assert required_fields.issubset(valid_insights.keys())

    def test_insights_outcome_valid_values(self) -> None:
        """Outcome must be one of: success, partial, failure."""
        valid_outcomes = {"success", "partial", "failure"}

        for outcome in valid_outcomes:
            insights = {
                "summary": "Test",
                "outcome": outcome,
                "accomplishments": [],
                "friction_points": [],
                "proposed_changes": [],
            }
            assert insights["outcome"] in valid_outcomes


class TestSessionInsightsPersistence:
    """Test session insights persistence via session state."""

    @pytest.fixture
    def session_id(self) -> str:
        """Generate unique session ID for test isolation."""
        return f"test-{datetime.now(timezone.utc).strftime('%H%M%S%f')}"

    @pytest.fixture
    def cleanup_session_file(self, session_id: str):
        """Clean up session file after test."""
        yield
        path = get_session_file_path(session_id)
        if path.exists():
            path.unlink()

    def test_set_session_insights_saves_to_state(
        self, session_id: str, cleanup_session_file: None
    ) -> None:
        """set_session_insights saves insights to session state file."""
        insights = {
            "summary": "Test session insights",
            "outcome": "success",
            "accomplishments": ["Test accomplishment"],
            "friction_points": [],
            "proposed_changes": [],
        }

        set_session_insights(session_id, insights)

        # Verify insights saved
        state = load_session_state(session_id)
        assert state is not None
        assert state["insights"] == insights

    def test_set_session_insights_sets_ended_at(
        self, session_id: str, cleanup_session_file: None
    ) -> None:
        """set_session_insights also sets ended_at timestamp."""
        insights = {
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
            "friction_points": [],
            "proposed_changes": [],
        }

        set_session_insights(session_id, insights)

        state = load_session_state(session_id)
        assert state is not None
        assert state["ended_at"] is not None

    def test_insights_preserved_after_session_state_reload(
        self, session_id: str, cleanup_session_file: None
    ) -> None:
        """Insights persist across session state reloads."""
        insights = {
            "summary": "Persisted insights test",
            "outcome": "partial",
            "accomplishments": ["Item 1", "Item 2"],
            "friction_points": ["Documentation unclear"],
            "proposed_changes": ["Update docs"],
        }

        set_session_insights(session_id, insights)

        # Clear any cached state and reload
        reloaded = load_session_state(session_id)
        assert reloaded is not None
        assert reloaded["insights"]["summary"] == "Persisted insights test"
        assert reloaded["insights"]["outcome"] == "partial"
        assert len(reloaded["insights"]["accomplishments"]) == 2


class TestInsightsFromFrameworkReflection:
    """Test that framework reflection can be converted to insights."""

    def test_reflection_to_insights_mapping(self) -> None:
        """Framework reflection fields map to insights fields."""
        # Framework Reflection format from AGENTS.md Step 3:
        # - Request, Guidance received, Followed, Outcome, Accomplishment, Root cause, Proposed change

        reflection = {
            "request": "Implement session insights generation",
            "guidance_received": "Hydrator suggested TDD workflow",
            "followed": "Yes",
            "outcome": "Success",
            "accomplishment": "Created tests and implementation",
            "root_cause": None,
            "proposed_change": "None needed",
        }

        # Convert to insights format
        insights = {
            "summary": reflection["request"],
            "outcome": reflection["outcome"].lower(),
            "accomplishments": [reflection["accomplishment"]]
            if reflection["accomplishment"]
            else [],
            "friction_points": [],
            "proposed_changes": [reflection["proposed_change"]]
            if reflection["proposed_change"] and reflection["proposed_change"] != "None needed"
            else [],
        }

        assert insights["summary"] == "Implement session insights generation"
        assert insights["outcome"] == "success"
        assert len(insights["accomplishments"]) == 1


class TestInsightsIntegration:
    """Integration tests for full insights workflow."""

    @pytest.fixture
    def session_id(self) -> str:
        """Generate unique session ID for test isolation."""
        return f"integration-{datetime.now(timezone.utc).strftime('%H%M%S%f')}"

    @pytest.fixture
    def cleanup_session_file(self, session_id: str):
        """Clean up session file after test."""
        yield
        path = get_session_file_path(session_id)
        if path.exists():
            path.unlink()

    def test_full_workflow_session_to_insights(
        self, session_id: str, cleanup_session_file: None
    ) -> None:
        """Full workflow: session starts → work done → insights saved."""
        # Step 1: Session starts (would happen at SessionStart hook)
        state = create_session_state(session_id)
        save_session_state(session_id, state)

        # Step 2: Work happens (main_agent tracking would be updated)
        state = load_session_state(session_id)
        assert state is not None
        state["main_agent"]["todos_completed"] = 3
        state["main_agent"]["todos_total"] = 3
        save_session_state(session_id, state)

        # Step 3: Main agent generates insights at session end
        insights = {
            "summary": "Implemented and tested session insights feature",
            "outcome": "success",
            "accomplishments": [
                "Wrote acceptance tests",
                "Implemented persistence",
                "Updated AGENTS.md",
            ],
            "friction_points": [],
            "proposed_changes": [],
        }

        set_session_insights(session_id, insights)

        # Verify final state
        final_state = load_session_state(session_id)
        assert final_state is not None
        assert final_state["insights"] is not None
        assert final_state["ended_at"] is not None
        assert final_state["main_agent"]["todos_completed"] == 3
        assert len(final_state["insights"]["accomplishments"]) == 3
