"""Axiom violation detection engine.

Analyzes code and tool calls for violations of framework axioms (AXIOMS.md).
Primary focus: P#8 (Fail-Fast), P#12 (DRY), P#26 (Verify First).
"""

from __future__ import annotations

import re
from typing import NamedTuple


class AxiomViolation(NamedTuple):
    """Represents a detected axiom violation."""

    axiom: str  # e.g., "P#8"
    pattern_name: str  # e.g., "env_get_default"
    message: str
    line_number: int | None = None
    context: str | None = None


class P8FallbackDetector:
    """Detects violations of P#8 (Fail-Fast: No fallbacks/defaults)."""

    # <!-- NS: this violates the 'no shitty nlp' axiom. -->
    AXIOM = "P#8"

    # Common "safe" defaults that don't necessarily violate fail-fast (existence checks)
    SAFE_DEFAULTS = {"None", "[]", "{}", "set()", "False", "0", "True", "''", '""'}

    # Regex patterns for common fallback signatures
    # Using re.MULTILINE and scanning full text
    PATTERNS = [
        # Env var with default: os.environ[dot]get or os.getenv with 2nd arg (any expression)
        (
            r"""(?:os\.(?:environ\.get|getenv))\s*\(\s*['"][^'"]+['"]\s*,\s*.+?\)""",
            "env_get_default",
            "Environment variable access with default. Use os.environ['VAR'] for fail-fast.",
        ),
        # try: ... except: pass (handles same line or next line)
        (
            r"""except\s*(?:\w+)?\s*:\s*(?:\n\s*)?pass\b""",
            "except_pass",
            "Silent exception suppression (except: pass). Handle errors explicitly or let them propagate.",
        ),
        # try: ... except: continue
        (
            r"""except\s*(?:\w+)?\s*:\s*(?:\n\s*)?continue\b""",
            "except_continue",
            "Silent exception suppression in loop (except: continue).",
        ),
        # val or "fallback" (assignment or return with fallback)
        (
            r"""\b\w+\s+or\s+['"][^'"]+['"]""",
            "or_fallback",
            "Value fallback using 'or default'. Use explicit checks and fail fast if value missing.",
        ),
        # .get(key, default) on dicts
        # We capture the default to check it logically
        (
            r"""\.get\s*\(\s*['"][^'"]+['"]\s*,\s*(?P<default>[^)]+)\)""",
            "dict_get_default",
            "Dictionary access with default value. Prefer dict['key'] for fail-fast.",
        ),
    ]

    def detect(self, code: str) -> list[AxiomViolation]:
        """Scan code for P#8 violations.

        Args:
            code: Source code to analyze.

        Returns:
            List of detected violations.
        """
        violations = []

        for pattern, name, message in self.PATTERNS:
            regex = re.compile(pattern, re.MULTILINE)
            for match in regex.finditer(code):
                # Logical check for dict_get_default
                if name == "dict_get_default":
                    default_val = match.group("default").strip()
                    if default_val in self.SAFE_DEFAULTS:
                        continue

                # Calculate line number
                line_number = code.count("\n", 0, match.start()) + 1
                context = (
                    match.group(0).strip().split("\n")[0]
                )  # Just the first line of match for context
                violations.append(
                    AxiomViolation(
                        axiom=self.AXIOM,
                        pattern_name=name,
                        message=message,
                        line_number=line_number,
                        context=context,
                    )
                )

        return violations


def detect_all_violations(code: str) -> list[AxiomViolation]:
    """Run all available axiom detectors on the code.

    Args:
        code: Source code to analyze.

    Returns:
        Aggregated list of violations.
    """
    detectors = [
        P8FallbackDetector(),
        # Add more detectors here (P12, P26, etc.)
    ]

    all_violations = []
    for detector in detectors:
        all_violations.extend(detector.detect(code))

    return all_violations
