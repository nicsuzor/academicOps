"""Tests for session_naming module — single source of truth for session filenames."""

from datetime import UTC, datetime

import pytest
from lib.session_naming import (
    ARTIFACT_TYPES,
    derive_polecat_session_id,
    generate_base_name,
    generate_session_filename,
    get_artifact_subdir,
    get_machine_name,
    get_session_short_hash,
    get_session_shortform,
    parse_session_filename,
)

# Fixed timestamp for deterministic tests
TS = datetime(2026, 4, 11, 14, 30, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Strip host env that would leak into shortform generation."""
    for var in (
        "POLECAT_CREW_NAME",
        "AOPS_MACHINE",
        "GEMINI_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "AOPS_SESSION_STATE_DIR",
        "CLAUDE_PROJECT_DIR",
    ):
        monkeypatch.delenv(var, raising=False)


# --- get_session_short_hash ---


class TestGetSessionShortHash:
    def test_uuid_prefix(self):
        assert get_session_short_hash("a1b2c3d4-e5f6-7890-abcd-ef1234567890") == "a1b2c3d4"

    def test_long_alphanumeric(self):
        assert get_session_short_hash("abcdef1234567890") == "abcdef12"

    def test_short_id_uses_sha256(self):
        result = get_session_short_hash("abc")
        assert len(result) == 8
        assert result != "abc"

    def test_consistent(self):
        assert get_session_short_hash("test-id") == get_session_short_hash("test-id")

    def test_lowercase(self):
        assert get_session_short_hash("ABCDEF12") == "abcdef12"


# --- derive_polecat_session_id ---


class TestDerivePolecat:
    def test_standard_task_id(self):
        assert derive_polecat_session_id("aops-a1b2c3d4-fix-something") == "a1b2c3d4"

    def test_task_prefix(self):
        assert derive_polecat_session_id("task-bbd1b7e3-unified-session") == "bbd1b7e3"

    def test_academicops_prefix(self):
        assert derive_polecat_session_id("academicops-4f499738-fix-transcripts") == "4f499738"

    def test_no_hex_portion_uses_hash(self):
        result = derive_polecat_session_id("some-weird-id")
        assert len(result) == 8
        # Should be consistent
        assert result == derive_polecat_session_id("some-weird-id")

    def test_uppercase_hex_normalized(self):
        assert derive_polecat_session_id("aops-A1B2C3D4-fix") == "a1b2c3d4"


# --- get_machine_name ---


class TestGetMachineName:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("AOPS_MACHINE", "nuc")
        assert get_machine_name() == "nuc"

    def test_sanitizes_env(self, monkeypatch):
        monkeypatch.setenv("AOPS_MACHINE", "My Machine!")
        assert get_machine_name() == "my-machine"

    def test_fallback_to_hostname(self, monkeypatch):
        monkeypatch.delenv("AOPS_MACHINE", raising=False)
        result = get_machine_name()
        assert len(result) > 0
        assert " " not in result


# --- get_session_shortform ---


class TestGetSessionShortform:
    def test_manual_claude(self):
        result = get_session_shortform(
            crew_name=None, repo="academicops", machine="nuc", provider="claude"
        )
        assert result == "academicops-nuc-claude"

    def test_manual_gemini(self):
        result = get_session_shortform(
            crew_name=None, repo="writing", machine="mbp", provider="gemini"
        )
        assert result == "writing-mbp-gemini"

    def test_crew_claude(self):
        result = get_session_shortform(
            crew_name="gloria", repo="academicops", machine="nuc", provider="claude"
        )
        assert result == "gloria-academicops-nuc-claude"

    def test_crew_gemini(self):
        result = get_session_shortform(
            crew_name="banjo", repo="buttermilk", machine="nuc", provider="gemini"
        )
        assert result == "banjo-buttermilk-nuc-gemini"

    def test_sanitizes_components(self):
        result = get_session_shortform(
            crew_name="My Crew", repo="My.Repo", machine="DEV-01", provider="claude"
        )
        # Dashes are stripped from shortform components to keep the delimiter unambiguous
        assert result == "mycrew-myrepo-dev01-claude"

    def test_dashed_repo_name_no_crew(self):
        """Repo names with dashes must not break parsing — dashes are collapsed."""
        result = get_session_shortform(
            crew_name=None, repo="my-project", machine="nuc", provider="claude"
        )
        assert result == "myproject-nuc-claude"

    def test_dashed_repo_name_with_crew(self):
        result = get_session_shortform(
            crew_name="gloria", repo="my-project", machine="nuc", provider="claude"
        )
        assert result == "gloria-myproject-nuc-claude"


# --- generate_session_filename ---


class TestGenerateSessionFilename:
    def test_transcript_full(self):
        result = generate_session_filename(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-hook-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="transcript-full",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-full.md"

    def test_transcript_abridged(self):
        result = generate_session_filename(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-hook-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="transcript-abridged",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-abridged.md"

    def test_insights(self):
        result = generate_session_filename(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-hook-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="insights",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths.json"

    def test_hooks(self):
        result = generate_session_filename(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-hook-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="hooks",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-hooks.jsonl"

    def test_client(self):
        result = generate_session_filename(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-hook-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="client",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-client.jsonl"

    def test_with_crew(self):
        result = generate_session_filename(
            session_id="c3d4e5f6-a1b2-7890",
            timestamp=TS,
            slug="refactor-tests",
            crew_name="gloria",
            repo="academicops",
            machine="nuc",
            provider="claude",
            artifact_type="transcript-full",
        )
        assert (
            result == "20260411-1430-c3d4e5f6-gloria-academicops-nuc-claude-refactor-tests-full.md"
        )

    def test_invalid_artifact_type(self):
        with pytest.raises(ValueError, match="Unknown artifact_type"):
            generate_session_filename(
                session_id="abc12345",
                timestamp=TS,
                slug="test",
                repo="test",
                machine="test",
                provider="claude",
                artifact_type="invalid",
            )

    def test_slug_truncation(self):
        result = generate_session_filename(
            session_id="a1b2c3d4",
            timestamp=TS,
            slug="this-is-a-very-long-slug-with-too-many-words",
            repo="repo",
            machine="m",
            provider="claude",
            artifact_type="insights",
        )
        # Should truncate to 5 words
        assert "this-is-a-very-long" in result
        assert "slug-with-too-many-words" not in result

    def test_slug_special_chars(self):
        result = generate_session_filename(
            session_id="a1b2c3d4",
            timestamp=TS,
            slug="Fix: the bug! (urgent)",
            repo="repo",
            machine="m",
            provider="claude",
            artifact_type="insights",
        )
        # Should sanitize to kebab-case
        assert ":" not in result
        assert "!" not in result
        assert "(" not in result

    def test_empty_slug_defaults(self):
        result = generate_session_filename(
            session_id="a1b2c3d4",
            timestamp=TS,
            slug="",
            repo="repo",
            machine="m",
            provider="claude",
            artifact_type="insights",
        )
        assert "session" in result


# --- generate_base_name ---


class TestGenerateBaseName:
    def test_base_name(self):
        result = generate_base_name(
            session_id="a1b2c3d4-e5f6-7890",
            timestamp=TS,
            slug="fix-paths",
            repo="academicops",
            machine="nuc",
            provider="claude",
        )
        assert result == "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-paths"

    def test_all_artifacts_share_base(self):
        kwargs = {
            "session_id": "a1b2c3d4",
            "timestamp": TS,
            "slug": "test-slug",
            "repo": "repo",
            "machine": "m",
            "provider": "claude",
        }
        base = generate_base_name(**kwargs)
        for art_type in ARTIFACT_TYPES:
            filename = generate_session_filename(**kwargs, artifact_type=art_type)
            assert filename.startswith(base), f"{art_type}: {filename} doesn't start with {base}"


# --- parse_session_filename ---


class TestParseSessionFilename:
    def test_manual_claude_transcript(self):
        parsed = parse_session_filename(
            "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-full.md"
        )
        assert parsed is not None
        assert parsed.date == "20260411"
        assert parsed.time == "1430"
        assert parsed.session_id == "a1b2c3d4"
        assert parsed.crew is None
        assert parsed.repo == "academicops"
        assert parsed.machine == "nuc"
        assert parsed.provider == "claude"
        assert parsed.slug == "fix-hook-paths"
        assert parsed.variant == "-full"
        assert parsed.ext == ".md"

    def test_crew_gemini_hooks(self):
        parsed = parse_session_filename(
            "20260411-1445-d4e5f6a7-banjo-buttermilk-nuc-gemini-update-docs-hooks.jsonl"
        )
        assert parsed is not None
        assert parsed.crew == "banjo"
        assert parsed.repo == "buttermilk"
        assert parsed.machine == "nuc"
        assert parsed.provider == "gemini"
        assert parsed.slug == "update-docs"
        assert parsed.variant == "-hooks"
        assert parsed.ext == ".jsonl"

    def test_insights_no_variant(self):
        parsed = parse_session_filename(
            "20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-paths.json"
        )
        assert parsed is not None
        assert parsed.variant == ""
        assert parsed.ext == ".json"
        assert parsed.slug == "fix-paths"

    def test_client_log(self):
        parsed = parse_session_filename(
            "20260411-1500-e5f6a7b8-academicops-nuc-claude-fix-lint-client.jsonl"
        )
        assert parsed is not None
        assert parsed.variant == "-client"
        assert parsed.slug == "fix-lint"

    def test_with_directory_prefix(self):
        parsed = parse_session_filename(
            "transcripts/20260411-1430-a1b2c3d4-academicops-nuc-claude-test-full.md"
        )
        assert parsed is not None
        assert parsed.session_id == "a1b2c3d4"

    def test_dashed_repo_no_crew_roundtrips(self):
        """Repo names with dashes have dashes stripped, so parsing is unambiguous."""
        parsed = parse_session_filename(
            "20260411-1430-a1b2c3d4-myproject-nuc-claude-fix-bug-full.md"
        )
        assert parsed is not None
        assert parsed.crew is None
        assert parsed.repo == "myproject"
        assert parsed.machine == "nuc"
        assert parsed.provider == "claude"

    def test_invalid_returns_none(self):
        assert parse_session_filename("not-a-session-file.txt") is None
        assert parse_session_filename("README.md") is None
        assert parse_session_filename("") is None

    def test_old_format_returns_none(self):
        # Old format without minutes and shortform — should not parse
        assert parse_session_filename("20260411-14-academicops-a1b2c3d4-slug-full.md") is None


# --- Round-trip tests ---


class TestRoundTrip:
    """Generate -> parse -> generate must produce identical output."""

    @pytest.mark.parametrize(
        "crew_name,repo,machine,provider",
        [
            (None, "academicops", "nuc", "claude"),
            (None, "writing", "mbp", "gemini"),
            ("gloria", "academicops", "nuc", "claude"),
            ("banjo", "buttermilk", "nuc", "gemini"),
            (None, "mem", "dev01", "claude"),
            (None, "mem", "dev01", "gemini"),
        ],
        ids=[
            "manual-claude",
            "manual-gemini",
            "crew-claude",
            "crew-gemini",
            "polecat-claude",
            "polecat-gemini",
        ],
    )
    @pytest.mark.parametrize("artifact_type", ARTIFACT_TYPES.keys())
    def test_roundtrip(self, crew_name, repo, machine, provider, artifact_type):
        filename = generate_session_filename(
            session_id="a1b2c3d4",
            timestamp=TS,
            slug="test-slug",
            crew_name=crew_name,
            repo=repo,
            machine=machine,
            provider=provider,
            artifact_type=artifact_type,
        )

        parsed = parse_session_filename(filename)
        assert parsed is not None, f"Failed to parse: {filename}"

        # Re-generate from parsed components
        regenerated = generate_session_filename(
            session_id=parsed.session_id,
            timestamp=datetime(
                int(parsed.date[:4]),
                int(parsed.date[4:6]),
                int(parsed.date[6:8]),
                int(parsed.time[:2]),
                int(parsed.time[2:4]),
                tzinfo=UTC,
            ),
            slug=parsed.slug,
            crew_name=parsed.crew,
            repo=parsed.repo,
            machine=parsed.machine,
            provider=parsed.provider,
            artifact_type=artifact_type,
        )

        assert regenerated == filename, (
            f"Round-trip failed:\n  Original:    {filename}\n  Regenerated: {regenerated}"
        )


# --- get_artifact_subdir ---


class TestGetArtifactSubdir:
    def test_known_types(self):
        assert get_artifact_subdir("transcript-full") == "transcripts"
        assert get_artifact_subdir("transcript-abridged") == "transcripts"
        assert get_artifact_subdir("insights") == "summaries"
        assert get_artifact_subdir("hooks") == "hooks"
        assert get_artifact_subdir("client") == "client-logs"

    def test_unknown_type(self):
        with pytest.raises(ValueError):
            get_artifact_subdir("invalid")
