#!/usr/bin/env python3
"""Tests for prompt intent classifier.

Tests that the intent classifier correctly analyzes prompts and returns
structured classification results for routing to appropriate skills.
"""

import json
from unittest.mock import MagicMock

import pytest


@pytest.mark.integration
def test_classify_prompt_returns_structured_result():
    """Test that classify_prompt returns dict with required keys.

    The classifier should return structured JSON with:
    - intent: string describing the detected intent
    - confidence: float between 0 and 1
    - recommended_skills: list of skill names
    - reasoning: string explaining the classification
    """
    # Arrange
    from hooks.intent_classifier import classify_prompt

    prompt = "help me debug this hook"

    # Mock Anthropic client response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "intent": "framework",
                "confidence": 0.9,
                "reasoning": "Hook debugging is a framework development task"
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    # Act
    result = classify_prompt(prompt, client=mock_client)

    # Assert: Result is a dict
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    # Assert: Required keys present
    assert "intent" in result, "Missing 'intent' key"
    assert "confidence" in result, "Missing 'confidence' key"
    assert "recommended_skills" in result, "Missing 'recommended_skills' key"
    assert "reasoning" in result, "Missing 'reasoning' key"

    # Assert: Types are correct
    assert isinstance(result["intent"], str), "intent must be a string"
    assert len(result["intent"]) > 0, "intent must be non-empty"

    assert isinstance(result["confidence"], float), "confidence must be a float"
    assert 0.0 <= result["confidence"] <= 1.0, "confidence must be between 0 and 1"

    assert isinstance(result["recommended_skills"], list), "recommended_skills must be a list"

    assert isinstance(result["reasoning"], str), "reasoning must be a string"

    # Assert: Specific values from mock
    assert result["intent"] == "framework"
    assert result["confidence"] == 0.9
    assert result["recommended_skills"] == ["framework"]
    assert "Hook debugging" in result["reasoning"]
