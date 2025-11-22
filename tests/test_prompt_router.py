#!/usr/bin/env python3
"""Tests for prompt intent router hook.

Tests that the router hook correctly reads stdin, calls the classifier,
and outputs additionalContext with skill recommendations.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
def test_router_reads_stdin_and_calls_classifier():
    """Test that router reads prompt from stdin and calls classifier."""
    from hooks.prompt_router import route_prompt

    # Input that would come from Claude Code
    input_data = {
        "session_id": "test-session",
        "prompt": "help me debug this hook",
    }

    # Mock the classifier
    mock_result = {
        "intent": "framework",
        "confidence": 0.9,
        "recommended_skills": ["framework"],
        "reasoning": "Hook debugging is a framework task",
    }

    with patch("hooks.prompt_router.classify_prompt", return_value=mock_result) as mock_classify:
        result = route_prompt(input_data)

        # Verify classifier was called with the prompt
        mock_classify.assert_called_once_with("help me debug this hook")

        # Verify result structure
        assert "additionalContext" in result
        assert "framework" in result["additionalContext"]


@pytest.mark.integration
def test_router_outputs_formatted_context():
    """Test that additionalContext includes skill, intent, confidence, reasoning."""
    from hooks.prompt_router import route_prompt

    input_data = {"prompt": "analyze this data with streamlit"}

    mock_result = {
        "intent": "analysis",
        "confidence": 0.85,
        "recommended_skills": ["analyst"],
        "reasoning": "Data analysis request",
    }

    with patch("hooks.prompt_router.classify_prompt", return_value=mock_result):
        result = route_prompt(input_data)

        context = result["additionalContext"]
        assert "analyst" in context
        assert "analysis" in context
        assert "85%" in context
        assert "Data analysis" in context


@pytest.mark.integration
def test_router_returns_empty_on_no_skills():
    """Test that router returns empty dict when no skills recommended."""
    from hooks.prompt_router import route_prompt

    input_data = {"prompt": "hello"}

    mock_result = {
        "intent": "other",
        "confidence": 0.5,
        "recommended_skills": [],
        "reasoning": "General greeting",
    }

    with patch("hooks.prompt_router.classify_prompt", return_value=mock_result):
        result = route_prompt(input_data)
        assert result == {}


@pytest.mark.integration
def test_router_continues_on_classifier_failure():
    """Test that router returns empty dict on classifier exception."""
    from hooks.prompt_router import route_prompt

    input_data = {"prompt": "test prompt"}

    with patch("hooks.prompt_router.classify_prompt", side_effect=RuntimeError("API error")):
        result = route_prompt(input_data)
        # Should return empty dict, not raise
        assert result == {}
