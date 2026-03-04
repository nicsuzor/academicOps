"""Tests for Framework Reflection parsing in transcript_parser.py.

Covers standard heading format, bold-text drift (Claude agents),
unstructured fallback, outcome inference, and edge cases.
"""

from __future__ import annotations

from lib.transcript_parser import parse_framework_reflection


class TestStandardHeadingFormat:
    """Tests for ## Framework Reflection (spec format)."""

    def test_full_structured_reflection(self):
        text = """\
## Framework Reflection

**Prompts**: Fix the repo-sync cron script
**Guidance received**: N/A
**Followed**: Yes
**Outcome**: success
**Accomplishments**: Fixed cron timing, added error handling
**Friction points**: None
**Root cause**: N/A
**Proposed changes**: None
**Next step**: None — PR merged, task complete
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        assert result["prompts"] == "Fix the repo-sync cron script"
        assert result["accomplishments"] == ["Fixed cron timing, added error handling"]
        assert result["next_step"] == "None — PR merged, task complete"

    def test_minimal_three_field_reflection(self):
        text = """\
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        assert result["accomplishments"] == ["Fixed the repo-sync cron script"]
        assert result["next_step"] == "None — PR merged, task complete"

    def test_h3_heading_variant(self):
        text = """\
### Framework Reflection

**Outcome**: partial
**Accomplishments**: Started implementation
**Next step**: Continue tomorrow
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "partial"

    def test_h4_heading_variant(self):
        text = """\
#### Framework Reflection

**Outcome**: success
**Accomplishments**: Diagnosed issue, added heuristic
**Next step**: Task complete
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"

    def test_reflection_with_list_accomplishments(self):
        text = """\
## Framework Reflection

**Outcome**: success
**Accomplishments**:
- Fixed the cron script
- Added error handling
- Updated documentation
**Next step**: None
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert len(result["accomplishments"]) == 3
        assert "Fixed the cron script" in result["accomplishments"]

    def test_reflection_stops_at_next_heading(self):
        text = """\
## Framework Reflection

**Outcome**: success
**Accomplishments**: Done

## Next Section

Some other content here.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        # Should not include content from "Next Section"
        assert "other content" not in str(result)


class TestBoldTextDrift:
    """Tests for **Framework Reflection**: format (common Claude drift)."""

    def test_bold_with_colon(self):
        text = """\
**Framework Reflection:**

**Outcome**: success
**Accomplishments**: Fixed repo-sync
**Next step**: Done
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        assert result["accomplishments"] == ["Fixed repo-sync"]

    def test_bold_without_colon(self):
        text = """\
**Framework Reflection**

**Outcome**: partial
**Accomplishments**: Started work on the parser
**Next step**: Continue in next session
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "partial"

    def test_bold_with_space_before_colon(self):
        text = """\
**Framework Reflection** :

**Outcome**: success
**Accomplishments**: Completed all tasks
**Next step**: None
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"

    def test_bare_text_with_colon(self):
        """Framework Reflection: preceded by newline (bare text variant)."""
        text = """\
Some previous content.

Framework Reflection:

**Outcome**: success
**Accomplishments**: Fixed the issue
**Next step**: None
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"


class TestUnstructuredFallback:
    """Tests for unstructured reflections without **Field**: value lines."""

    def test_prose_only(self):
        """Single-line prose reflection (real Claude drift pattern)."""
        text = """\
**Framework Reflection:**

Simple diagnostic + fix session. Hydration was invoked twice; overhead was disproportionate.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result.get("inferred") is True
        assert result["outcome"] == "partial"  # no success keywords
        assert len(result["accomplishments"]) == 1
        assert "diagnostic" in result["accomplishments"][0]

    def test_bullet_list_as_accomplishments(self):
        text = """\
**Framework Reflection:**

- Fixed the cron script timing
- Added error handling for edge cases
- Updated the README
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result.get("inferred") is True
        assert len(result["accomplishments"]) == 3
        assert "Fixed the cron script timing" in result["accomplishments"]

    def test_mixed_bullets_and_prose(self):
        text = """\
**Framework Reflection:**

Straightforward session. Changes made:
- Fixed repo-sync script
- Merged PR #42
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result.get("inferred") is True
        assert len(result["accomplishments"]) == 2
        assert result["outcome"] == "success"  # "merged" keyword

    def test_success_keyword_inference(self):
        text = """\
## Framework Reflection

Successfully completed the migration. All tests pass and PR merged.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"

    def test_failure_keyword_inference(self):
        text = """\
## Framework Reflection

Failed to complete the task. Build is broken and couldn't fix it.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "failure"

    def test_partial_keyword_inference(self):
        text = """\
## Framework Reflection

Work in progress. Started the refactor but ran out of context.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        # "partial" is default when no strong keyword matches
        assert result["outcome"] == "partial"

    def test_done_keyword_maps_to_success(self):
        text = """\
**Framework Reflection:**

Done. Reindexed all documents, added progress bar.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"


class TestEdgeCases:
    """Edge cases and regression tests."""

    def test_no_reflection_returns_none(self):
        text = "Just some regular markdown content.\n\n## Other Section\n\nStuff."
        result = parse_framework_reflection(text)
        assert result is None

    def test_empty_reflection_body(self):
        text = """\
## Framework Reflection

## Next Section
"""
        result = parse_framework_reflection(text)
        assert result is None

    def test_quick_exit_still_works(self):
        text = """\
## Framework Reflection

Answered user's question: "How do I configure SSH keys?"
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result.get("quick_exit") is True
        assert result["outcome"] == "success"

    def test_aops_status_still_works(self):
        text = """\
## Framework Reflection

AOPS status: done
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"
        assert result.get("brief_status") is True

    def test_reflection_embedded_in_larger_document(self):
        text = """\
# Session Summary

Some intro text about the session.

## Work Done

Lots of work was done.

## Framework Reflection

**Outcome**: success
**Accomplishments**: Everything
**Next step**: Nothing

## Appendix

Extra info here.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"

    def test_case_insensitive_heading(self):
        text = """\
## framework reflection

**Outcome**: success
**Accomplishments**: Done
**Next step**: None
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["outcome"] == "success"

    def test_next_steps_plural_accepted(self):
        """Parser should accept both 'Next step' and 'Next steps'."""
        text = """\
## Framework Reflection

**Outcome**: partial
**Accomplishments**: Started work
**Next steps**: Continue with task aops-abc123
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result["next_step"] == "Continue with task aops-abc123"

    def test_real_claude_drift_inline_prose(self):
        """Real-world pattern: bold heading followed by inline prose (no fields)."""
        text = """\
**Framework Reflection**: Straightforward single-feature session. The existing indicatif dependency and progress bar scaffolding made this a minimal diff. No new dependencies needed.

Handover complete.
"""
        result = parse_framework_reflection(text)
        assert result is not None
        assert result.get("inferred") is True
        assert "single-feature session" in result["summary"]
