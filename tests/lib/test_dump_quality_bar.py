"""Quality-bar tests for /dump (task-5a54f813).

Covers the new structured-extraction fields:
  - `## Output` parsing (links + explicit none)
  - `## Tasks worked` parsing (id / precis / action)
  - identifier+precis pair extraction
  - quality warnings (missing blocks, bare ids, feature-suggestion smell)

End-to-end fixture also asserts these fields propagate into the dict
returned by `parse_framework_reflection`.
"""

from __future__ import annotations

from lib.transcript_parser import (
    assess_reflection_quality,
    parse_framework_reflection,
    parse_identifier_precis_pairs,
    parse_output_section,
    parse_tasks_worked_section,
)

# ---------------------------------------------------------------------------
# Output section
# ---------------------------------------------------------------------------


class TestOutputSection:
    def test_pr_link(self):
        text = """\
## Output

- PR https://github.com/nicsuzor/academicOps/pull/847 (transcript.py)
"""
        result = parse_output_section(text)
        assert result is not None
        assert result["explicit_none"] is False
        assert result["outputs"] == [
            {
                "kind": "pr",
                "url": "https://github.com/nicsuzor/academicOps/pull/847",
            }
        ]

    def test_explicit_none_in_section(self):
        text = """\
## Output

none — pure planning session, no artefact produced.
"""
        result = parse_output_section(text)
        assert result is not None
        assert result["explicit_none"] is True
        assert "pure planning session" in (result["none_reason"] or "")

    def test_bare_none_line_no_heading(self):
        text = "Some prose.\nOutput: none — blocked on user input.\nMore prose."
        result = parse_output_section(text)
        assert result is not None
        assert result["explicit_none"] is True
        assert "blocked on user input" in (result["none_reason"] or "")

    def test_missing_section_returns_none(self):
        text = "## Some Other Heading\n\nNo output here."
        assert parse_output_section(text) is None

    def test_classifies_issue_and_commit(self):
        text = """\
## Output

- https://github.com/x/y/issues/12 (an issue)
- https://github.com/x/y/commit/abcdef1234 (a commit)
- https://example.com/doc (a doc)
"""
        result = parse_output_section(text)
        assert result is not None
        kinds = [o["kind"] for o in result["outputs"]]
        assert kinds == ["issue", "commit", "doc"]


# ---------------------------------------------------------------------------
# Tasks worked
# ---------------------------------------------------------------------------


class TestTasksWorked:
    def test_full_block(self):
        text = """\
## Tasks worked

- task-5a54f813 (/dump quality bar) — updated, added schema doc
- task-d4932f32 (audit early-returns) — created
- task-acd9af54 (inspect tool) — cancelled per user
"""
        items = parse_tasks_worked_section(text)
        assert items is not None
        assert len(items) == 3
        assert items[0]["id"] == "task-5a54f813"
        assert items[0]["precis"] == "/dump quality bar"
        assert items[0]["action"] == "updated"
        assert items[1]["action"] == "created"
        assert items[2]["action"] == "cancelled"

    def test_missing_section(self):
        assert parse_tasks_worked_section("nothing here") is None


# ---------------------------------------------------------------------------
# Identifier+precis pairs
# ---------------------------------------------------------------------------


class TestIdentifierPrecisPairs:
    def test_mixed_ids_with_and_without_precis(self):
        text = (
            "Filed task-acba1234 (some precis) and also task-deadbeef. "
            "See PR #847 (the metadata extractor) and commit cf83b1f."
        )
        refs = parse_identifier_precis_pairs(text)
        ids = {(r["type"], r["id"].lower()) for r in refs}
        assert ("task", "task-acba1234") in ids
        assert ("task", "task-deadbeef") in ids
        # bare task should appear with precis=None
        bare = next(r for r in refs if r["id"].lower() == "task-deadbeef")
        assert bare["precis"] is None
        with_precis = next(r for r in refs if r["id"].lower() == "task-acba1234")
        assert with_precis["precis"] == "some precis"


# ---------------------------------------------------------------------------
# Quality warnings
# ---------------------------------------------------------------------------


class TestQualityWarnings:
    def test_missing_blocks_emit_warnings(self):
        warnings = assess_reflection_quality(
            reflection_text="some text",
            outputs=None,
            tasks_worked=None,
            references=[],
        )
        assert any(w.startswith("missing-output-section") for w in warnings)
        assert any(w.startswith("missing-tasks-worked") for w in warnings)

    def test_empty_output_emits_warning(self):
        warnings = assess_reflection_quality(
            reflection_text="x",
            outputs={"outputs": [], "explicit_none": False, "none_reason": None},
            tasks_worked=[{"id": "task-1", "precis": "p", "action": "created"}],
            references=[],
        )
        assert any(w.startswith("empty-output-section") for w in warnings)

    def test_bare_identifier_warning(self):
        warnings = assess_reflection_quality(
            reflection_text="ref",
            outputs={
                "outputs": [{"kind": "pr", "url": "u"}],
                "explicit_none": False,
                "none_reason": None,
            },
            tasks_worked=[{"id": "task-1", "precis": "p", "action": "created"}],
            references=[{"type": "task", "id": "task-deadbeef", "precis": None}],
        )
        assert any("bare-identifier" in w for w in warnings)

    def test_feature_suggestion_smell(self):
        warnings = assess_reflection_quality(
            reflection_text="We should build a new tool that pulls sessions by id.",
            outputs={
                "outputs": [{"kind": "pr", "url": "u"}],
                "explicit_none": False,
                "none_reason": None,
            },
            tasks_worked=[{"id": "task-1", "precis": "p", "action": "created"}],
            references=[],
        )
        assert any(w.startswith("feature-suggestion") for w in warnings)

    def test_clean_reflection_has_no_warnings(self):
        warnings = assess_reflection_quality(
            reflection_text="Hit friction in transcript_parser.py around early-return.",
            outputs={
                "outputs": [{"kind": "pr", "url": "u"}],
                "explicit_none": False,
                "none_reason": None,
            },
            tasks_worked=[{"id": "task-1", "precis": "p", "action": "created"}],
            references=[{"type": "task", "id": "task-1", "precis": "p"}],
        )
        assert warnings == []


# ---------------------------------------------------------------------------
# Integration through parse_framework_reflection
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_reflection_propagates_new_fields(self):
        text = """\
## Framework Reflection

**Outcome**: success
**Accomplishments**: Wired metadata extraction
**Friction points**: $AOPS_SESSIONS env var unreachable on worker container
**Next step**: Land PR

Mentioned task-5a54f813 (/dump quality bar) and PR #847 (metadata extractor).

## Output

- https://github.com/nicsuzor/academicOps/pull/847 (this PR)

## Tasks worked

- task-5a54f813 (/dump quality bar) — updated
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        # Output extracted
        assert result["outputs"] == [
            {"kind": "pr", "url": "https://github.com/nicsuzor/academicOps/pull/847"}
        ]
        assert result["output_explicit_none"] is False
        # Tasks worked extracted
        assert len(result["tasks_worked"]) == 1
        assert result["tasks_worked"][0]["id"] == "task-5a54f813"
        assert result["tasks_worked"][0]["action"] == "updated"
        # References extracted (task + PR)
        ref_types = {r["type"] for r in result["references"]}
        assert "task" in ref_types
        assert "pr" in ref_types
        # No quality warnings on a clean reflection
        assert "quality_warnings" not in result or not result["quality_warnings"]

    def test_reflection_without_output_block_warns(self):
        text = """\
## Framework Reflection

**Outcome**: partial
**Accomplishments**: Investigated only
**Next step**: Continue tomorrow
"""
        result = parse_framework_reflection(text)
        assert result is not None
        warnings = result.get("quality_warnings") or []
        assert any(w.startswith("missing-output-section") for w in warnings)
        assert any(w.startswith("missing-tasks-worked") for w in warnings)
