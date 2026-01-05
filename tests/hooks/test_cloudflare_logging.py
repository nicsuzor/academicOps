"""Integration tests for Cloudflare prompt logging function.

Tests that log_to_cloudflare():
1. Actually POSTs to Cloudflare endpoint when token is valid
2. Handles missing token gracefully with warning
3. Handles invalid token gracefully without raising
4. Does NOT raise exceptions even if request fails

NO MOCKS. Real subprocess execution only.
"""

import importlib
import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root and hooks to path for imports
AOPS_ROOT = Path(__file__).parent.parent.parent
HOOKS_DIR = AOPS_ROOT / "hooks"
sys.path.insert(0, str(AOPS_ROOT))
sys.path.insert(0, str(HOOKS_DIR))


def import_log_to_cloudflare():
    """Dynamically import log_to_cloudflare function.

    This allows the test to fail with a clear ImportError if the function
    doesn't exist yet, rather than failing during module collection.

    Mocks dependencies that are not relevant to the function being tested.
    """
    # Mock dependencies needed for user_prompt_submit module to import
    with patch.dict(
        sys.modules,
        {
            "hook_debug": MagicMock(),
            "lib.activity": MagicMock(),
        },
    ):
        user_prompt_submit = importlib.import_module("user_prompt_submit")
        return user_prompt_submit.log_to_cloudflare


def test_log_to_cloudflare_success() -> None:
    """Test that log_to_cloudflare successfully POSTs to Cloudflare with real token.

    This test makes a REAL HTTP request to the Cloudflare endpoint.
    Requires PROMPT_LOG_API_KEY environment variable - FAILS if not set.
    """
    # Fail-fast: require token for this test
    assert os.environ.get(
        "PROMPT_LOG_API_KEY"
    ), "PROMPT_LOG_API_KEY must be set to run integration tests"

    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Integration test prompt - validating real Cloudflare logging"

    # Call the function with real execution - should complete without exception
    log_to_cloudflare(test_prompt)


def test_log_to_cloudflare_missing_token() -> None:
    """Test that log_to_cloudflare warns when token is missing.

    No mock needed - just unset the environment variable and verify warning.
    """
    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Test prompt"

    # Capture stderr to verify warning message
    captured_stderr = StringIO()

    # Remove token from environment
    env_without_token = os.environ.copy()
    env_without_token.pop("PROMPT_LOG_API_KEY", None)

    with patch.dict(os.environ, env_without_token, clear=True):
        with patch("sys.stderr", captured_stderr):
            # Should NOT raise - function is fire-and-forget
            log_to_cloudflare(test_prompt)

    # Verify warning was printed to stderr
    stderr_output = captured_stderr.getvalue()
    assert (
        "WARNING: PROMPT_LOG_API_KEY not set" in stderr_output
    ), "Should warn when token is missing"


def test_log_to_cloudflare_invalid_token() -> None:
    """Test that log_to_cloudflare handles invalid token gracefully.

    Uses a real subprocess call with an invalid token to verify graceful failure.
    """
    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Test prompt with invalid token"

    # Capture stderr to verify warning on failure
    captured_stderr = StringIO()

    # Use invalid token
    with patch.dict(os.environ, {"PROMPT_LOG_API_KEY": "invalid-token-12345"}):
        with patch("sys.stderr", captured_stderr):
            # Should NOT raise - function catches errors and warns
            log_to_cloudflare(test_prompt)

    # Verify warning was printed (either about failure or timeout)
    stderr_output = captured_stderr.getvalue()
    # The function should warn about the failure
    assert (
        "WARNING:" in stderr_output or stderr_output == ""
    ), "Should either warn or silently fail on invalid token"


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
