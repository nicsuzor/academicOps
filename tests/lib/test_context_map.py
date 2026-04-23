"""Tests for lib/context_map.py — context map loading and formatting."""

import json

import pytest
from lib.context_map import (
    format_context_hints,
    load_context_map,
)


@pytest.fixture
def sample_docs():
    """Minimal context map entries for testing."""
    return [
        {
            "topic": "taxonomy",
            "path": "aops-core/skills/remember/references/TAXONOMY.md",
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


class TestFormatContextHints:
    def test_formats_all_docs(self, sample_docs):
        result = format_context_hints(sample_docs)
        assert "context-map.json" in result
        assert "TAXONOMY.md" in result
        assert "AXIOMS.md" in result
        assert "prompt-hydration.md" in result
        assert "README.md" in result

    def test_returns_empty_for_no_docs(self):
        assert format_context_hints([]) == ""

    def test_includes_read_instruction(self, sample_docs):
        result = format_context_hints(sample_docs)
        assert "Read relevant files" in result

    def test_includes_all_descriptions(self, sample_docs):
        result = format_context_hints(sample_docs)
        for doc in sample_docs:
            assert doc["description"] in result
