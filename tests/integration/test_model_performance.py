#!/usr/bin/env python3
"""
Performance comparison tests for different Claude models.

Tests the same simple question against Haiku and Sonnet to measure
execution time differences.

Run with: uv run pytest tests/integration/test_model_performance.py -v -s
"""

import time

import pytest


def test_haiku_performance(claude_headless):
    """Test execution time with Haiku model."""
    start = time.time()
    result = claude_headless(
        "Without using any tools, whose repository is this?", model="haiku"
    )
    execution_time = time.time() - start

    assert result["success"], f"Failed: {result['error']}"

    # Print timing info
    print("\n=== Haiku Performance ===")
    print(f"Total execution time: {execution_time:.2f}s")
    print(f"API duration: {result['duration_ms'] / 1000:.2f}s")
    print(f"Overhead: {execution_time - result['duration_ms'] / 1000:.2f}s")
    print(f"Result: {result['result'][:100]}...")


def test_sonnet_performance(claude_headless):
    """Test execution time with Sonnet model (default)."""
    start = time.time()
    result = claude_headless(
        "Without using any tools, whose repository is this?",
        # No model specified = uses default (Sonnet 4.5)
    )
    execution_time = time.time() - start

    assert result["success"], f"Failed: {result['error']}"

    # Print timing info
    print("\n=== Sonnet Performance ===")
    print(f"Total execution time: {execution_time:.2f}s")
    print(f"API duration: {result['duration_ms'] / 1000:.2f}s")
    print(f"Overhead: {execution_time - result['duration_ms'] / 1000:.2f}s")
    print(f"Result: {result['result'][:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
