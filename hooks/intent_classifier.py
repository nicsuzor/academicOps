#!/usr/bin/env python3
"""Prompt intent classifier for routing to appropriate skills.

Uses Haiku model to classify user prompts and recommend skills.
"""

import json
import os

from anthropic import Anthropic, APITimeoutError

MODEL = "claude-3-5-haiku-latest"
TIMEOUT = 5.0

INTENT_TO_SKILLS = {
    "framework": ["framework"],
    "python": ["python-dev"],
    "analysis": ["analyst"],
    "knowledge": ["bmem"],
    "task": ["tasks"],
    "other": [],
}

CLASSIFICATION_PROMPT = """Classify this user prompt into one of these intents:
- framework: Framework development, automation infrastructure
- python: Python code, debugging, testing, implementation
- analysis: Data analysis, research data, dbt, streamlit
- knowledge: Knowledge base, memory, notes, bmem operations
- task: Task management, todo lists, workflow coordination
- other: Doesn't fit other categories

User prompt: {prompt}

Return JSON with these exact keys:
- intent: one of framework, python, analysis, knowledge, task, other
- confidence: float between 0.0 and 1.0
- reasoning: brief explanation (1-2 sentences)

Return ONLY valid JSON, no other text."""


def classify_prompt(prompt: str, client=None) -> dict:
    """Classify a prompt and return structured result.

    Args:
        prompt: User prompt to classify
        client: Optional Anthropic client (for testing). If None, creates from API key.

    Returns:
        Dict with keys: intent, confidence, recommended_skills, reasoning

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY environment variable not set and client is None
    """
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY environment variable not set"
            raise RuntimeError(msg)

        client = Anthropic(api_key=api_key, timeout=TIMEOUT)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[
                {"role": "user", "content": CLASSIFICATION_PROMPT.format(prompt=prompt)}
            ],
        )

        response_text = response.content[0].text
        result = json.loads(response_text)

        intent = result.get("intent", "other")
        confidence = float(result.get("confidence", 0.5))
        reasoning = result.get("reasoning", "")

        return {
            "intent": intent,
            "confidence": confidence,
            "recommended_skills": INTENT_TO_SKILLS.get(intent, []),
            "reasoning": reasoning,
        }
    except APITimeoutError:
        return {
            "intent": "other",
            "confidence": 0.0,
            "recommended_skills": [],
            "reasoning": "Classification timeout - returning default",
        }
