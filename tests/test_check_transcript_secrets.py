"""Tests for the pre-commit secret scanner (Layer 2 backstop — aops-00c0fa10).

Verifies that check_transcript_secrets.py exits 1 when given a file containing
a synthetic token-pattern and exits 0 for clean content / normal prose.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Import the scanner's main() directly so tests don't need subprocess overhead.
_SCANNER = (
    Path(__file__).resolve().parent.parent / "aops-core" / "scripts" / "check_transcript_secrets.py"
)
_spec = importlib.util.spec_from_file_location("check_transcript_secrets", _SCANNER)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
main = _mod.main


class TestScannerBlocksSecrets:
    def test_github_pat_blocked(self, tmp_path: Path):
        f = tmp_path / "transcript.md"
        f.write_text("# Session\n\nToken: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n")
        assert main([str(f)]) == 1

    def test_anthropic_key_blocked(self, tmp_path: Path):
        f = tmp_path / "summary.json"
        f.write_text('{"summary": "sk-ant-api03-abc123def456ghi789jkl012mno345"}')
        assert main([str(f)]) == 1

    def test_env_assignment_blocked(self, tmp_path: Path):
        f = tmp_path / "transcript.md"
        f.write_text("GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n")
        assert main([str(f)]) == 1

    def test_jwt_blocked(self, tmp_path: Path):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4"
        f = tmp_path / "transcript.md"
        f.write_text(f"Authorization: Bearer {jwt}\n")
        assert main([str(f)]) == 1


class TestScannerAllowsCleanContent:
    def test_clean_prose_passes(self, tmp_path: Path):
        f = tmp_path / "transcript.md"
        f.write_text(
            "# Session\n\nThe parser aggregates tokens by tool and skill. "
            "Task IDs like aops-00c0fa10 are fine.\n"
        )
        assert main([str(f)]) == 0

    def test_empty_file_passes(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert main([str(f)]) == 0

    def test_no_files_passes(self):
        assert main([]) == 0

    def test_code_with_variable_names_passes(self, tmp_path: Path):
        f = tmp_path / "summary.json"
        f.write_text('{"tools": ["Bash", "Read"], "count": 42, "api_key": "[REDACTED]"}')
        assert main([str(f)]) == 0

    def test_multiple_clean_files_passes(self, tmp_path: Path):
        files = []
        for i in range(3):
            f = tmp_path / f"session-{i}.md"
            f.write_text(f"# Session {i}\n\nSome content without secrets.\n")
            files.append(str(f))
        assert main(files) == 0

    def test_home_path_not_flagged(self, tmp_path: Path):
        f = tmp_path / "transcript.md"
        f.write_text("HOME=/Users/suzor\nEDITOR=vim\nPATH=/usr/bin:/bin\n")
        assert main([str(f)]) == 0


class TestScannerMixedFiles:
    def test_one_bad_file_among_clean_files_returns_1(self, tmp_path: Path):
        clean = tmp_path / "clean.md"
        clean.write_text("Normal session notes.\n")
        dirty = tmp_path / "dirty.md"
        dirty.write_text("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n")
        assert main([str(clean), str(dirty)]) == 1
