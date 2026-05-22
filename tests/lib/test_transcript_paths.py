"""Tests for the date-rotated transcript path helper (aops-b975b185)."""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest
from lib.transcript_paths import (
    ensure_rotated_dir,
    extract_date_from_filename,
    find_artifact,
    is_rotated_dir,
    iter_rotated_files,
    rotated_path,
    rotated_subdir,
)


class TestRotatedSubdir:
    def test_basic_utc(self):
        dt = datetime(2026, 5, 22, 14, 30, tzinfo=UTC)
        assert rotated_subdir(dt) == "2026-05"

    def test_naive_datetime_treated_as_utc(self):
        dt = datetime(2026, 1, 1, 0, 0)
        assert rotated_subdir(dt) == "2026-01"

    def test_timezone_aware_normalised_to_utc(self):
        # 23:30 local on 2026-05-31 in UTC+10 = 13:30 UTC on 2026-05-31.
        from datetime import timedelta

        tz_plus10 = timezone(timedelta(hours=10))
        dt = datetime(2026, 5, 31, 23, 30, tzinfo=tz_plus10)
        assert rotated_subdir(dt) == "2026-05"

    def test_timezone_aware_crosses_month_boundary(self):
        # 02:30 UTC+10 on June 1 = 16:30 UTC on May 31. Sorts into May.
        from datetime import timedelta

        tz_plus10 = timezone(timedelta(hours=10))
        dt = datetime(2026, 6, 1, 2, 30, tzinfo=tz_plus10)
        assert rotated_subdir(dt) == "2026-05"


class TestExtractDateFromFilename:
    @pytest.mark.parametrize(
        "name,expected_ym",
        [
            ("20260522-1430-abcd1234-foo-bar-full.md", (2026, 5)),
            ("20260101-0000-deadbeef-x-y.json", (2026, 1)),
            ("20251231-2359-abc12345-gemini-q.md", (2025, 12)),
        ],
    )
    def test_parses_leading_date(self, name, expected_ym):
        dt = extract_date_from_filename(name)
        assert dt is not None
        assert (dt.year, dt.month) == expected_ym
        assert dt.tzinfo is not None

    @pytest.mark.parametrize(
        "name",
        [
            "not-a-date-file.md",
            "abcd1234-no-date.md",
            "2026-not-compact-date.md",
            "",
        ],
    )
    def test_returns_none_for_no_date(self, name):
        assert extract_date_from_filename(name) is None


class TestRotatedPath:
    def test_returns_dir_when_no_filename(self, tmp_path: Path):
        dt = datetime(2026, 3, 5, tzinfo=UTC)
        result = rotated_path(tmp_path, dt)
        assert result == tmp_path / "2026-03"

    def test_returns_file_path(self, tmp_path: Path):
        dt = datetime(2026, 3, 5, tzinfo=UTC)
        result = rotated_path(tmp_path, dt, "x.md")
        assert result == tmp_path / "2026-03" / "x.md"

    def test_ensure_creates_dir(self, tmp_path: Path):
        dt = datetime(2026, 3, 5, tzinfo=UTC)
        result = ensure_rotated_dir(tmp_path, dt)
        assert result == tmp_path / "2026-03"
        assert result.exists()


class TestIsRotatedDir:
    def test_recognises_yyyy_mm(self, tmp_path: Path):
        d = tmp_path / "2026-05"
        d.mkdir()
        assert is_rotated_dir(d)

    def test_rejects_other_dirs(self, tmp_path: Path):
        d = tmp_path / "polecats"
        d.mkdir()
        assert not is_rotated_dir(d)

    def test_rejects_yyyy_only(self, tmp_path: Path):
        d = tmp_path / "2026"
        d.mkdir()
        assert not is_rotated_dir(d)


class TestIterRotatedFiles:
    def test_yields_nothing_for_missing_dir(self, tmp_path: Path):
        assert list(iter_rotated_files(tmp_path / "ghost")) == []

    def test_walks_flat_and_rotated_layouts(self, tmp_path: Path):
        # Flat (legacy) file
        flat = tmp_path / "20260101-0000-abcd1234-foo-session-full.md"
        flat.write_text("flat")
        # Rotated file
        sub = tmp_path / "2026-05"
        sub.mkdir()
        rotated = sub / "20260522-1430-deadbeef-foo-bar-full.md"
        rotated.write_text("rotated")
        # Noise (subdir that is not a rotation bucket)
        other = tmp_path / "polecats"
        other.mkdir()
        (other / "ignored.md").write_text("nope")

        found = set(iter_rotated_files(tmp_path, "*-full.md"))
        assert flat in found
        assert rotated in found
        assert (other / "ignored.md") not in found

    def test_find_artifact_returns_list(self, tmp_path: Path):
        (tmp_path / "20260101-0000-abcd1234-x-y-full.md").write_text("")
        assert len(find_artifact(tmp_path, "*-full.md")) == 1


class TestWriterRotatesTranscript:
    """End-to-end: transcript.py writes session artefacts under YYYY-MM/."""

    def test_transcript_lands_in_rotated_subdir(self, tmp_path: Path, monkeypatch):
        """A session whose first event is in May 2026 must land at
        ``transcripts/2026-05/...`` regardless of write time."""
        import json
        import subprocess
        import sys

        sessions = tmp_path / "sessions"
        for sub in ("transcripts", "summaries"):
            (sessions / sub).mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
        monkeypatch.setenv("AOPS_MACHINE", "testmachine")
        # Avoid the script's git-sync touching anything real.
        monkeypatch.delenv("AOPS_TASK_ID", raising=False)

        session_uuid = "a63851ba-1234-5678-9abc-def012345678"
        jsonl = tmp_path / f"{session_uuid}.jsonl"

        def _entry(role: str, uuid: str, parent: str, text: str, off_min: int) -> dict:
            from datetime import timedelta

            ts = datetime(2026, 5, 12, 9, 0, tzinfo=UTC) + timedelta(minutes=off_min)
            return {
                "type": role,
                "uuid": uuid,
                "parentUuid": parent,
                "sessionId": session_uuid,
                "timestamp": ts.isoformat(),
                "message": {
                    "role": role,
                    "content": [{"type": "text", "text": text}],
                    **(
                        {
                            "model": "claude-opus-4-5",
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 10,
                                "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 0,
                            },
                        }
                        if role == "assistant"
                        else {}
                    ),
                },
                "cwd": "/home/test/proj",
            }

        with open(jsonl, "w") as f:
            for e in [
                _entry("user", "u1", "", "hello there", 0),
                _entry("assistant", "a1", "u1", "hi back", 1),
                _entry("user", "u2", "a1", "another", 2),
                _entry("assistant", "a2", "u2", "ok", 3),
            ]:
                f.write(json.dumps(e) + "\n")

        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "aops-core" / "scripts" / "transcript.py"),
                str(jsonl),
                "--no-sync",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"transcript.py failed:\n{result.stdout}\n{result.stderr}"

        # Transcripts must be under transcripts/2026-05/, not flat.
        rotated = list((sessions / "transcripts" / "2026-05").glob("*-full.md"))
        assert rotated, (
            f"no rotated transcript produced. stdout={result.stdout!r}\n"
            f"flat files: {list((sessions / 'transcripts').glob('*-full.md'))}"
        )
        # Filename's leading date matches the rotation bucket.
        assert rotated[0].name.startswith("20260512-"), rotated[0].name

        # Summaries follow the same rotation.
        summaries = list((sessions / "summaries" / "2026-05").glob("*.json"))
        assert summaries, "expected rotated summary JSON"
