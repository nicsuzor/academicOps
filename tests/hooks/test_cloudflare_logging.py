"""Unit test for Cloudflare prompt logging function.

Tests that log_to_cloudflare():
1. Constructs correct JSON payload with prompt, hostname, cwd, project, timestamp
2. Makes HTTP POST to correct endpoint with Authorization header
3. Does NOT raise exceptions even if request fails (warns to stderr)
4. Completes successfully when token present and request succeeds
"""

import importlib
import json
import os
import sys
from datetime import datetime, timezone
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
    with patch.dict(sys.modules, {
        "hook_debug": MagicMock(),
        "lib.activity": MagicMock(),
    }):
        user_prompt_submit = importlib.import_module("user_prompt_submit")
        return user_prompt_submit.log_to_cloudflare


def test_log_to_cloudflare_constructs_correct_curl_command() -> None:
    """Test that log_to_cloudflare constructs correct curl command with all required fields."""
    # Import the function (will raise ImportError if it doesn't exist)
    log_to_cloudflare = import_log_to_cloudflare()

    # Setup test data
    test_prompt = "Test user prompt for logging"
    test_hostname = "test-machine"
    test_cwd = "/opt/nic/writing/academicOps"
    test_project = "academicOps"

    # Mock subprocess.run to capture the curl command
    with patch("subprocess.run") as mock_run:
        # Configure mock to simulate successful execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Mock environment variables and paths
        with patch.dict(os.environ, {"PROMPT_LOG_API_KEY": "test-token-12345"}):
            with patch("socket.gethostname", return_value=test_hostname):
                with patch("os.getcwd", return_value=test_cwd):
                    with patch("pathlib.Path.name", test_project):
                        # Call the function
                        log_to_cloudflare(test_prompt)

        # Verify subprocess.run was called
        assert mock_run.called, "subprocess.run should be called"

        # Get the command that was passed to subprocess.run
        call_args = mock_run.call_args
        curl_command = call_args[0][0]  # First positional argument

        # Verify it's a curl command
        assert curl_command[0] == "curl", "Command should start with curl"

        # Verify URL is correct
        assert "https://prompt-logs.nicsuzor.workers.dev/write" in curl_command, "URL should be correct"

        # Verify Authorization header is present
        auth_header = None
        for i, arg in enumerate(curl_command):
            if arg == "-H" and i + 1 < len(curl_command):
                next_arg = curl_command[i + 1]
                if next_arg.startswith("Authorization:"):
                    auth_header = next_arg
                    break

        assert auth_header is not None, "Authorization header should be present"
        assert "Bearer test-token-12345" in auth_header, "Authorization should contain Bearer token"

        # Verify Content-Type header is present
        content_type_header = None
        for i, arg in enumerate(curl_command):
            if arg == "-H" and i + 1 < len(curl_command):
                next_arg = curl_command[i + 1]
                if next_arg.startswith("Content-Type:"):
                    content_type_header = next_arg
                    break

        assert content_type_header is not None, "Content-Type header should be present"
        assert "application/json" in content_type_header, "Content-Type should be application/json"

        # Find and verify the JSON payload
        data_arg_index = None
        for i, arg in enumerate(curl_command):
            if arg == "-d":
                data_arg_index = i + 1
                break

        assert data_arg_index is not None, "Should have -d flag for data"
        json_payload_str = curl_command[data_arg_index]
        json_payload = json.loads(json_payload_str)

        # Verify payload contains all required fields
        assert "prompt" in json_payload, "Payload should contain prompt"
        assert json_payload["prompt"] == test_prompt, "Prompt should match input"

        assert "hostname" in json_payload, "Payload should contain hostname"
        assert json_payload["hostname"] == test_hostname, "Hostname should match"

        assert "cwd" in json_payload, "Payload should contain cwd"
        assert json_payload["cwd"] == test_cwd, "CWD should match"

        assert "project" in json_payload, "Payload should contain project"
        assert json_payload["project"] == test_project, "Project should match"

        assert "timestamp" in json_payload, "Payload should contain timestamp"
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(json_payload["timestamp"].replace("Z", "+00:00"))
        assert timestamp.tzinfo is not None, "Timestamp should have timezone"


def test_log_to_cloudflare_does_not_raise_on_failure() -> None:
    """Test that log_to_cloudflare does NOT raise exceptions on failure."""
    # Import the function (will raise ImportError if it doesn't exist)
    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Test prompt"

    # Mock subprocess.run to raise an exception
    with patch("subprocess.run", side_effect=Exception("Network error")):
        with patch.dict(os.environ, {"PROMPT_LOG_API_KEY": "test-token"}):
            # Should NOT raise - function catches exceptions
            log_to_cloudflare(test_prompt)  # Should complete without exception


def test_log_to_cloudflare_handles_missing_token() -> None:
    """Test that log_to_cloudflare handles missing token gracefully (fire-and-forget)."""
    # Import the function (will raise ImportError if it doesn't exist)
    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Test prompt"

    # Remove token from environment
    with patch.dict(os.environ, {}, clear=True):
        # Should NOT raise - function is fire-and-forget
        log_to_cloudflare(test_prompt)  # Should complete without exception


def test_log_to_cloudflare_success_path() -> None:
    """Test that log_to_cloudflare executes successfully when token is present and subprocess succeeds."""
    # Import the function (will raise ImportError if it doesn't exist)
    log_to_cloudflare = import_log_to_cloudflare()

    test_prompt = "Test prompt for success path"

    # Mock subprocess.run to verify it was called successfully
    with patch("subprocess.run") as mock_run:
        # Configure mock to simulate successful execution (returncode 0)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Mock environment variables
        with patch.dict(os.environ, {"PROMPT_LOG_API_KEY": "test-token-12345"}):
            # Call the function - should return None without raising
            result = log_to_cloudflare(test_prompt)

        # Verify subprocess.run was called exactly once
        assert mock_run.call_count == 1, "subprocess.run should be called exactly once"

        # Verify the function returned None (implicit success)
        assert result is None, "Function should return None"

        # Verify subprocess was spawned with capture_output=True for fire-and-forget
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("capture_output") is True, "capture_output should be True"
        assert call_kwargs.get("check") is False, "check should be False (we handle errors manually)"
        assert call_kwargs.get("timeout") == 5, "timeout should be 5 seconds"


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
