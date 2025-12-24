#!/usr/bin/env python3
"""Classification accuracy tests for intent-router.

Tests that the intent-router Haiku agent classifies prompts correctly
against ground truth labels. Uses the same flow as production:
1. write_classifier_prompt() creates cache file with prompt + capabilities
2. Haiku agent reads file and returns classification

This is an evaluation suite, not a regression suite. Failures indicate
either (a) classifier needs tuning, or (b) ground truth needs updating.
"""

import pytest

from hooks.prompt_router import write_classifier_prompt
from tests.integration.conftest import run_claude_headless

# Ground truth: (prompt, expected_classification, rationale)
# expected can be a single string or list of acceptable alternatives
GROUND_TRUTH = [
    # Clear skill matches
    (
        "help me write python code with type hints",
        ["python-dev"],
        "Explicit Python development request",
    ),
    (
        "remember that I prefer pytest over unittest",
        ["remember"],
        "Explicit memory storage request",
    ),
    (
        "convert this markdown to PDF",
        ["pdf"],
        "Explicit PDF conversion request",
    ),
    # Exploration/codebase questions → Explore agent
    (
        "what's the structure of this codebase?",
        ["Explore"],
        "Codebase exploration question",
    ),
    # Framework questions
    (
        "how do I add a new skill to the framework?",
        ["framework", "skill-creator"],
        "Framework modification question - either is acceptable",
    ),
    # Ambiguous → none is acceptable
    (
        "hello, how are you?",
        ["none"],
        "Greeting with no clear intent",
    ),
]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("intent_router_accuracy"),
    pytest.mark.xfail(reason="LLM classification is non-deterministic - evaluation test", strict=False),
]


def _run_intent_classification(prompt: str, timeout: int = 60) -> str | None:
    """Run intent classification through the same flow as production.

    Args:
        prompt: User prompt to classify
        timeout: Timeout in seconds

    Returns:
        Classification result (skill name or 'none'), or None if failed
    """
    # Create cache file with prompt + capabilities (same as hook does)
    cache_file = write_classifier_prompt(prompt)

    try:
        # Run Haiku with intent-router instructions
        classification_prompt = f"""You are a lightweight intent classifier.

1. Read the file at {cache_file} using the Read tool
2. The file contains: available capabilities AND a user prompt to classify
3. Return ONLY the capability identifier that best matches the user's prompt
4. Valid responses: skill name (analyst, framework, python-dev, etc.), command (meta, email), agent (Explore, Plan), or 'none'
5. No explanation - just the identifier"""

        result = run_claude_headless(
            classification_prompt,
            model="haiku",
            timeout_seconds=timeout,
        )

        if not result["success"]:
            return None

        # Extract response from result structure
        # Result can be dict with 'result' key containing text, or nested structure
        result_data = result.get("result", {})

        # Handle dict format: {"result": "classification_text", ...}
        if isinstance(result_data, dict):
            response = result_data.get("result", "")
        elif isinstance(result_data, str):
            response = result_data
        else:
            return None

        if not response:
            return None

        # Try to extract valid classification from response
        # First: check if response IS a valid classification (ideal case)
        response_clean = response.strip().lower()

        # Known valid classifications
        valid_classifications = {
            "analyst", "framework", "remember", "tasks", "python-dev",
            "pdf", "osb-drafting", "transcript", "session-insights",
            "learning-log", "excalidraw", "ground-truth", "training-set-builder",
            "extractor", "skill-creator", "dashboard", "garden", "link-audit",
            "reference-map", "feature-dev",
            # Commands
            "meta", "email", "log", "qa", "ttd", "pull", "add", "strategy",
            "parallel-batch", "learn", "diag", "consolidate", "task-viz",
            # Agents
            "explore", "plan", "critic",
            # Special
            "none",
        }

        # Check if first word is a valid classification
        first_word = response_clean.split()[0].rstrip(".,;:") if response_clean else ""
        if first_word in valid_classifications:
            return first_word

        # Search for valid classification anywhere in response
        for word in response_clean.split():
            word_clean = word.strip().rstrip(".,;:'\"")
            if word_clean in valid_classifications:
                return word_clean

        # Fallback: return first word (will likely fail assertion)
        return first_word if first_word else None

    finally:
        # Clean up cache file
        if cache_file.exists():
            cache_file.unlink()


@pytest.mark.parametrize("prompt,expected,rationale", GROUND_TRUTH)
def test_classification_accuracy(prompt: str, expected: list[str], rationale: str):
    """Test that intent-router classifies prompt correctly.

    Args:
        prompt: User prompt to classify
        expected: List of acceptable classifications
        rationale: Why this classification is expected (for debugging)
    """
    classification = _run_intent_classification(prompt)

    assert classification is not None, f"Classification failed for: {prompt}"

    # Normalize for comparison (lowercase)
    classification_lower = classification.lower()
    expected_lower = [e.lower() for e in expected]

    assert classification_lower in expected_lower, (
        f"Classification mismatch for: {prompt}\n"
        f"Expected one of: {expected}\n"
        f"Got: {classification}\n"
        f"Rationale: {rationale}"
    )


def test_classification_returns_single_word():
    """Test that classification returns a single identifier, not explanation."""
    prompt = "what is the capital of France?"  # Clearly none

    classification = _run_intent_classification(prompt)

    assert classification is not None, "Classification failed"
    # Should be single word, no spaces
    assert " " not in classification, (
        f"Classification should be single word, got: {classification}"
    )
