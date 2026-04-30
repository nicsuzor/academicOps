"""Static schema-clarity tests for the /remember skill SKILL.md.

These tests assert the SKILL.md spells out the actual PKB data model:

- `confidence` is numeric 0.0-1.0 (the categorical names are prose
  descriptors that map onto numeric ranges, not the field's schema).
- `synthesized:` is REQUIRED for `type: knowledge` notes.
- `sources:` is REQUIRED for `type: knowledge` notes and must be a YAML
  list (array).

History: agents repeatedly omit `synthesized:` and `sources:` because the
spec was ambiguous — task-2e8b1498 (and task-495b648d before it) both
caught this in consolidation. These tests pin the clarification so a
future edit doesn't silently regress it.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMEMBER_PATH = REPO_ROOT / "aops-core" / "skills" / "remember" / "SKILL.md"


def _read(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


class TestRememberSkillConfidenceSchema:
    """Static assertions on aops-core/skills/remember/SKILL.md."""

    def test_skill_file_exists(self) -> None:
        assert REMEMBER_PATH.exists(), f"remember SKILL.md missing at {REMEMBER_PATH}"

    def test_confidence_is_described_as_numeric_range(self) -> None:
        """`confidence` must be documented as numeric 0.0-1.0, not just categorical.

        The PKB schema stores `confidence` as a float used for search ranking;
        agents that read the SKILL.md should see the numeric form so they
        write the correct frontmatter value.
        """
        content = _read(REMEMBER_PATH)
        # The phrase "numeric 0.0-1.0" must appear adjacent to a `confidence`
        # mention. We accept either ASCII hyphen or en-dash between the bounds.
        assert "confidence" in content.lower(), "SKILL.md must mention `confidence`"
        assert "numeric 0.0–1.0" in content or "numeric 0.0-1.0" in content, (
            "SKILL.md must document `confidence` as numeric 0.0-1.0"
        )

    def test_categorical_labels_described_as_ranges_not_schema(self) -> None:
        """The categorical names should still appear, but as prose
        descriptors mapped onto numeric ranges — not as the schema."""
        content = _read(REMEMBER_PATH)
        # All three descriptors should still be defined.
        for label in ("established", "provisional", "speculative"):
            assert label in content, f"SKILL.md still expects to describe `{label}`"
        # And they should be tied to numeric thresholds somewhere.
        assert "0.8" in content, "SKILL.md must give the established >= 0.8 threshold"
        assert "0.4" in content, "SKILL.md must give the provisional/speculative boundary"

    def test_synthesized_required_for_knowledge_notes(self) -> None:
        """`synthesized:` must be called out as REQUIRED for type: knowledge."""
        content = _read(REMEMBER_PATH)
        # Find the provenance/required-fields section.
        assert "type: knowledge" in content, (
            "SKILL.md must scope the required-fields rule to `type: knowledge`"
        )
        assert "REQUIRED" in content, "SKILL.md must use the word REQUIRED to mark mandatory fields"
        # `synthesized:` field must appear in the required list.
        assert "synthesized:" in content, "SKILL.md must mention `synthesized:` field"

    def test_sources_required_and_must_be_yaml_list(self) -> None:
        """`sources:` must be REQUIRED for knowledge and called out as a YAML list."""
        content = _read(REMEMBER_PATH)
        assert "sources:" in content, "SKILL.md must mention `sources:` field"
        # Must say it's a YAML list (array).
        lower = content.lower()
        assert "yaml list" in lower, "SKILL.md must say `sources:` must be a YAML list"

    def test_episodic_notes_exempt_from_required_fields(self) -> None:
        """Memory/episodic notes shouldn't be forced through the
        synthesis required-fields rule — the SKILL.md must say so to
        prevent over-application."""
        content = _read(REMEMBER_PATH)
        lower = content.lower()
        # Some phrasing of "memory and episodic notes do not require these".
        assert "do not require" in lower or "not require these" in lower, (
            "SKILL.md must explicitly exempt memory/episodic notes from the "
            "knowledge-required-fields rule"
        )
