"""Tests for lib/context_map.py — context map loading and formatting."""

import json
from pathlib import Path

import pytest
from lib.context_map import (
    audit_context_map_coverage,
    format_context_hints,
    load_context_map,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


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
            "path": ".agents/rules/AXIOMS.md",
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


def _write_map(repo: Path, data: dict) -> None:
    agents = repo / ".agents"
    agents.mkdir(exist_ok=True)
    (agents / "context-map.json").write_text(json.dumps(data))


class TestAuditContextMapCoverage:
    """Coverage audit: specs must be indexed (docs[]) or excluded (exclude[]) — #1364."""

    def _repo_with_specs(self, tmp_path: Path, spec_rel_paths: list[str]) -> Path:
        for rel in spec_rel_paths:
            spec = tmp_path / rel
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text("# spec\n")
        return tmp_path

    def test_no_issues_when_map_missing(self, tmp_path):
        assert audit_context_map_coverage(tmp_path) == []

    def test_no_issues_when_no_spec_dirs(self, tmp_path):
        _write_map(tmp_path, {"docs": [], "spec_dirs": []})
        assert audit_context_map_coverage(tmp_path) == []

    def test_clean_when_all_specs_indexed_or_excluded(self, tmp_path):
        self._repo_with_specs(tmp_path, ["specs/a.md", "specs/b.md"])
        _write_map(
            tmp_path,
            {
                "spec_dirs": ["specs/"],
                "docs": [{"topic": "a", "path": "specs/a.md", "description": "d"}],
                "exclude": ["specs/b.md"],
            },
        )
        assert audit_context_map_coverage(tmp_path) == []

    def test_flags_uncovered_spec(self, tmp_path):
        self._repo_with_specs(tmp_path, ["specs/a.md", "specs/new.md"])
        _write_map(
            tmp_path,
            {
                "spec_dirs": ["specs/"],
                "docs": [{"topic": "a", "path": "specs/a.md", "description": "d"}],
                "exclude": [],
            },
        )
        issues = audit_context_map_coverage(tmp_path)
        assert len(issues) == 1
        assert "specs/new.md" in issues[0]

    def test_flags_nested_uncovered_spec(self, tmp_path):
        self._repo_with_specs(tmp_path, ["specs/sub/deep.md"])
        _write_map(tmp_path, {"spec_dirs": ["specs/"], "docs": [], "exclude": []})
        issues = audit_context_map_coverage(tmp_path)
        assert any("specs/sub/deep.md" in i for i in issues)

    def test_flags_dangling_docs_entry(self, tmp_path):
        self._repo_with_specs(tmp_path, ["specs/a.md"])
        _write_map(
            tmp_path,
            {
                "spec_dirs": ["specs/"],
                "docs": [
                    {"topic": "a", "path": "specs/a.md", "description": "d"},
                    {"topic": "gone", "path": "specs/removed.md", "description": "d"},
                ],
                "exclude": [],
            },
        )
        issues = audit_context_map_coverage(tmp_path)
        assert any("specs/removed.md" in i and "does not exist" in i for i in issues)

    def test_flags_stale_exclude_entry(self, tmp_path):
        self._repo_with_specs(tmp_path, ["specs/a.md"])
        _write_map(
            tmp_path,
            {
                "spec_dirs": ["specs/"],
                "docs": [{"topic": "a", "path": "specs/a.md", "description": "d"}],
                "exclude": ["specs/deleted.md"],
            },
        )
        issues = audit_context_map_coverage(tmp_path)
        assert any("specs/deleted.md" in i and "does not exist" in i for i in issues)


class TestRealRepoContextMapIsFresh:
    """Regression guard (CI enforcement surface for #1364).

    Fails the moment a spec is added/removed without the context map being
    updated — the gap that let doc-taxonomy.md merge invisibly (PR #1185).
    """

    def test_real_context_map_has_no_coverage_gaps(self):
        issues = audit_context_map_coverage(REPO_ROOT)
        assert issues == [], (
            "Context map is stale. Every spec under spec_dirs must be indexed in "
            "docs[] or listed in exclude[]. Run the context-map-audit workflow.\n"
            + "\n".join(f"  - {i}" for i in issues)
        )
