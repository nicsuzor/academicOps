"""Reflection detection utilities for session monitoring.

Provides simple API for detecting Framework Reflection sections in text.
Wraps the more comprehensive transcript_parser.parse_framework_reflection.

Usage:
    from lib.reflection_detector import has_reflection, detect_reflection

    # Simple boolean check
    if has_reflection(text):
        print("Reflection found")

    # Get parsed reflection data
    reflection = detect_reflection(text)
    if reflection:
        print(f"Outcome: {reflection.get('outcome')}")
"""

from typing import Any

from lib.transcript_parser import parse_framework_reflection


def has_reflection(text: str) -> bool:
    """Check if text contains a Framework Reflection section.

    Quick boolean check for reflection presence. Use detect_reflection()
    if you need the parsed reflection data.

    Args:
        text: Text that may contain a Framework Reflection section

    Returns:
        True if a Framework Reflection section is found
    """
    return parse_framework_reflection(text) is not None


def detect_reflection(text: str) -> dict[str, Any] | None:
    """Detect and parse Framework Reflection from text.

    Extracts structured fields from the Framework Reflection format:
    - prompts, guidance_received, followed, outcome, accomplishments,
    - friction_points, root_cause, proposed_changes, next_step

    Args:
        text: Text that may contain a Framework Reflection section

    Returns:
        Dict with parsed fields, or None if no reflection found
    """
    return parse_framework_reflection(text)


def detect_reflection_in_messages(messages: list[str]) -> dict[str, Any] | None:
    """Detect reflection in a list of message texts.

    Searches through messages (newest first is typical) and returns
    the first reflection found.

    Args:
        messages: List of message text strings to search

    Returns:
        Parsed reflection dict from first message containing one, or None
    """
    for message in messages:
        reflection = parse_framework_reflection(message)
        if reflection:
            return reflection
    return None
