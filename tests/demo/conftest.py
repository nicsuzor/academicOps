"""Demo test configuration.

Demo tests run with special settings:
- No parallelization (-n 0) - demos must run sequentially for readable output
- Verbose output (-v) - show test names
- No output capture (-s) - print statements visible immediately
- Log to console (--log-cli-level=INFO) - see logging output
"""

import pytest

# Re-export fixtures from integration tests
from tests.integration.conftest import (
    claude_headless,
    claude_headless_tracked,
    extract_response_text,
)

__all__ = ["claude_headless", "claude_headless_tracked", "extract_response_text"]


def pytest_configure(config: pytest.Config) -> None:
    """Force demo-friendly settings when running tests in this directory.

    Overrides -n (parallelization) and enables output capture bypass.
    """
    # Check if we're running from this directory or with demo marker
    # The workercount check prevents this from running on worker processes
    if hasattr(config, "workerinput"):
        return  # Skip on xdist worker processes

    # Disable xdist parallelization for demo tests
    # This ensures sequential execution with readable output
    if hasattr(config.option, "numprocesses"):
        config.option.numprocesses = 0

    # Enable live logging to console
    if hasattr(config.option, "log_cli_level"):
        config.option.log_cli_level = "INFO"


@pytest.fixture(autouse=True)
def demo_test_banner(request: pytest.FixtureRequest) -> None:
    """Print separator before each demo test for readability."""
    if request.node.get_closest_marker("demo"):
        print(f"\n{'='*80}")
        print(f"DEMO: {request.node.name}")
        print(f"{'='*80}")
