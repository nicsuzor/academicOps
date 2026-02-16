"""Minimal test for polecat swarm functionality."""

import sys
from pathlib import Path

# Add repo root to path so we can import polecat
REPO_ROOT = Path(__file__).parents[2].resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from polecat.swarm import DEFAULT_GEMINI_STAGGER_S


def test_default_stagger_constant():
    """Test that the default stagger constant is defined."""
    assert DEFAULT_GEMINI_STAGGER_S == 15.0
