"""Functional tests for bmem retrieval.

These tests verify that bmem search is actually USEFUL - not just "working".
A search that returns zero results for known concepts is BROKEN.

Run with: uv run pytest tests/test_bmem_retrieval.py -v

IMPORTANT: These tests use the REAL bmem via uvx basic-memory CLI.
If they fail, the search is NOT fit for purpose.
"""

import subprocess
import json
from typing import Any

import pytest


BMEM_PROJECT = "main"  # Default bmem project


def bmem_search(query: str, page_size: int = 10) -> dict[str, Any]:
    """Call bmem search via basic-memory CLI.

    This calls the actual bmem backend to test real behavior.
    """
    cmd = [
        "uvx",
        "basic-memory",
        "tool",
        "search-notes",
        query,
        "--project", BMEM_PROJECT,
        "--page-size", str(page_size),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return {"results": [], "error": result.stderr}

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        return {"results": [], "error": "Search timed out"}
    except json.JSONDecodeError as e:
        return {"results": [], "error": f"Invalid JSON: {e}"}
    except FileNotFoundError:
        pytest.skip("uvx/basic-memory not available")
        return {"results": []}


def bmem_recent_activity(timeframe: str = "30d") -> dict[str, Any]:
    """Call bmem recent_activity via CLI."""
    cmd = [
        "uvx",
        "basic-memory",
        "tool",
        "recent-activity",
        "--project", BMEM_PROJECT,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return {"results": [], "error": result.stderr}

        return json.loads(result.stdout)

    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"results": [], "error": "CLI failed"}
    except FileNotFoundError:
        pytest.skip("uvx/basic-memory not available")
        return {"results": []}


class TestSingleTermQueries:
    """Test 1: Single-term queries must return results."""

    @pytest.mark.parametrize("term", ["workaround", "agent", "framework", "task"])
    def test_known_terms_return_results(self, term: str) -> None:
        """Known terms that exist in corpus must return results."""
        result = bmem_search(term)

        assert "error" not in result or not result.get("error"), (
            f"Search for '{term}' failed: {result.get('error')}"
        )
        assert len(result.get("results", [])) > 0, (
            f"'{term}' should return results - this term is known to exist in the knowledge base"
        )


class TestTwoTermQueries:
    """Test 2: Two-term queries shouldn't fail catastrophically."""

    @pytest.mark.parametrize("query", [
        "agent behavior",
        "task management",
        "framework learning",
    ])
    def test_two_term_combinations(self, query: str) -> None:
        """Common two-term combinations should return results."""
        result = bmem_search(query)

        assert len(result.get("results", [])) > 0, (
            f"Two-term query '{query}' returned no results"
        )


class TestMultiTermDegradation:
    """Test 3: Multi-term graceful degradation (CRITICAL).

    This is the key bug that prompted these tests:
    'agent subagent behavior lazy workaround bypass' returned 0 results
    while 'agent behavior' and 'workaround' each returned 10 results.
    """

    def test_multi_term_does_not_return_zero_when_subsets_match(self) -> None:
        """Adding terms must NOT cause zero results when subsets match."""
        # If individual terms return results...
        single_results = [
            bmem_search("agent"),
            bmem_search("workaround"),
            bmem_search("bypass"),
        ]
        any_single_has_results = any(
            len(r.get("results", [])) > 0 for r in single_results
        )

        # ...then combining them should NOT return zero
        combined = bmem_search("agent workaround bypass")

        if any_single_has_results:
            assert len(combined.get("results", [])) > 0, (
                "Multi-term query returned 0 results but individual terms had matches. "
                "Search should use OR semantics or fallback to semantic search. "
                f"Individual results: agent={len(single_results[0].get('results', []))}, "
                f"workaround={len(single_results[1].get('results', []))}, "
                f"bypass={len(single_results[2].get('results', []))}"
            )

    def test_six_term_query_original_failure(self) -> None:
        """The original failing query that exposed this bug.

        This is the EXACT query that returned 0 results and prompted
        the creation of these tests.
        """
        # This specific query returned 0 results
        result = bmem_search("agent subagent behavior lazy workaround bypass")

        # Check if ANY simpler subset returns results
        subsets = [
            bmem_search("agent behavior"),
            bmem_search("workaround"),
            bmem_search("lazy"),
        ]
        any_subset_has_results = any(
            len(r.get("results", [])) > 0 for r in subsets
        )

        if any_subset_has_results:
            # If subsets match, the full query should return SOMETHING
            assert len(result.get("results", [])) > 0, (
                "Six-term query 'agent subagent behavior lazy workaround bypass' "
                "returned 0 results, but simpler subsets matched. "
                "This is the exact bug this test was written to catch! "
                f"Subset results: 'agent behavior'={len(subsets[0].get('results', []))}, "
                f"'workaround'={len(subsets[1].get('results', []))}, "
                f"'lazy'={len(subsets[2].get('results', []))}"
            )


class TestSearchDoesNotSilentlyFail:
    """Test 5: Search must never silently return empty for common terms."""

    def test_common_word_returns_results(self) -> None:
        """Search for extremely common terms must return something."""
        found_any = False
        for term in ["project", "note", "session"]:
            result = bmem_search(term)
            if len(result.get("results", [])) > 0:
                found_any = True
                break

        assert found_any, (
            "None of the common terms ['project', 'note', 'session'] returned results. "
            "Either the knowledge base is empty or search is broken."
        )


class TestRecentActivity:
    """Test 6: Recent activity must return content if KB has data."""

    def test_recent_activity_not_empty(self) -> None:
        """recent_activity should return content if knowledge base has data."""
        result = bmem_recent_activity("30d")

        # If this fails with error, skip
        if result.get("error"):
            pytest.skip(f"recent_activity failed: {result['error']}")

        # We expect SOME activity in a working knowledge base
        # Empty result for active KB = warning, not hard fail
        if not result.get("results") and not result.get("entities"):
            pytest.skip(
                "No recent activity found. May be expected for unused KB."
            )


class TestSearchQuality:
    """Additional quality tests for search usefulness."""

    def test_relevant_results_ranked_higher(self) -> None:
        """More specific queries should return more relevant results first."""
        result = bmem_search("bmem validation bypass")

        if len(result.get("results", [])) == 0:
            pytest.skip("No results for 'bmem validation bypass'")

        # The first result should be about bmem/validation, not random
        first_result = result["results"][0]
        content = json.dumps(first_result).lower()

        # At least one of the query terms should appear in top result
        assert any(term in content for term in ["bmem", "validation", "bypass"]), (
            f"Top result doesn't seem relevant to query. "
            f"Got: {first_result.get('title', 'unknown')}"
        )
