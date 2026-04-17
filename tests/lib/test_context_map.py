"""Tests for lib/context_map.py — context map loading and keyword matching."""

import json

import pytest
from lib.context_map import (
    format_context_hints,
    load_context_map,
    search_context_map,
)


@pytest.fixture
def sample_docs():
    """Minimal context map entries for testing."""
    return [
        {
            "topic": "taxonomy",
            "path": "aops-core/TAXONOMY.md",
            "description": "Canonical definitions for all framework concepts",
            "keywords": [
                "taxonomy",
                "epic",
                "task",
                "what is an epic",
                "what is a task",
                "definitions",
            ],
        },
        {
            "topic": "axioms",
            "path": "aops-core/AXIOMS.md",
            "description": "Inviolable principles and their logical derivations",
            "keywords": [
                "axiom",
                "principle",
                "rule",
                "fail-fast",
                "verify first",
            ],
        },
        {
            "topic": "prompt_hydration",
            "path": "specs/prompt-hydration.md",
            "description": "Prompt hydration specification — context injection and routing",
            "keywords": ["hydration", "context", "prompt", "injection", "hydrator"],
        },
        {
            "topic": "testing",
            "path": "tests/README.md",
            "description": "Test suite overview — how to run tests",
            "keywords": ["test", "testing", "pytest", "integration"],
        },
    ]


@pytest.fixture
def context_map_dir(tmp_path, sample_docs):
    """Create a temporary repo with .agents/context-map.json."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    map_file = agents_dir / "context-map.json"
    map_file.write_text(json.dumps({"docs": sample_docs}))
    return tmp_path


class TestLoadContextMap:
    def test_loads_valid_map(self, context_map_dir, sample_docs):
        docs = load_context_map(context_map_dir)
        assert len(docs) == len(sample_docs)
        assert docs[0]["topic"] == "taxonomy"

    def test_returns_empty_for_missing_file(self, tmp_path):
        docs = load_context_map(tmp_path)
        assert docs == []

    def test_raises_for_invalid_json(self, tmp_path):
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        (agents_dir / "context-map.json").write_text("not json{")
        with pytest.raises(json.JSONDecodeError):
            load_context_map(tmp_path)

    def test_returns_empty_for_missing_docs_key(self, tmp_path):
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        (agents_dir / "context-map.json").write_text('{"other": []}')
        docs = load_context_map(tmp_path)
        assert docs == []


class TestSearchContextMap:
    def test_finds_taxonomy_for_epic_question(self, sample_docs):
        matches = search_context_map(sample_docs, "what is an epic")
        assert len(matches) > 0
        assert matches[0]["topic"] == "taxonomy"

    def test_finds_axioms_for_principle_query(self, sample_docs):
        matches = search_context_map(sample_docs, "what are the axioms and principles")
        topics = [m["topic"] for m in matches]
        assert "axioms" in topics

    def test_finds_hydration_for_hydrator_query(self, sample_docs):
        matches = search_context_map(sample_docs, "how does prompt hydration work")
        topics = [m["topic"] for m in matches]
        assert "prompt_hydration" in topics

    def test_returns_empty_for_unrelated_query(self, sample_docs):
        matches = search_context_map(sample_docs, "kubernetes deployment yaml")
        assert matches == []

    def test_returns_empty_for_empty_prompt(self, sample_docs):
        assert search_context_map(sample_docs, "") == []

    def test_returns_empty_for_empty_docs(self):
        assert search_context_map([], "some query") == []

    def test_respects_max_results(self, sample_docs):
        matches = search_context_map(sample_docs, "test axiom hydration taxonomy", max_results=2)
        assert len(matches) <= 2

    def test_results_sorted_by_score(self, sample_docs):
        matches = search_context_map(sample_docs, "taxonomy epic task definitions", min_score=1)
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i]["_score"] >= matches[i + 1]["_score"]

    def test_higher_score_for_exact_keyword_match(self, sample_docs):
        """Entries with exact keyword matches should score higher."""
        matches = search_context_map(sample_docs, "taxonomy", min_score=1)
        assert len(matches) > 0
        assert matches[0]["topic"] == "taxonomy"


class TestFormatContextHints:
    def test_formats_matches(self, sample_docs):
        matches = [
            {**sample_docs[0], "_score": 5},
            {**sample_docs[1], "_score": 3},
        ]
        result = format_context_hints(matches)
        assert "context-map.json" in result
        assert "TAXONOMY.md" in result
        assert "AXIOMS.md" in result

    def test_returns_empty_for_no_matches(self):
        assert format_context_hints([]) == ""

    def test_includes_read_instruction(self, sample_docs):
        matches = [{**sample_docs[0], "_score": 5}]
        result = format_context_hints(matches)
        assert "Read these files" in result
