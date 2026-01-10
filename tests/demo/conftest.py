"""Demo test configuration - imports fixtures from integration tests."""

# Re-export fixtures from integration tests
from tests.integration.conftest import (
    claude_headless,
    claude_headless_tracked,
    extract_response_text,
)

__all__ = ["claude_headless", "claude_headless_tracked", "extract_response_text"]
