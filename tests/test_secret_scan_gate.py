"""Guards academicOps's own commit-time secret gate (Layer 2, aops_8c697102).

`lib/py/transcripts/domain/secret_redaction.py` (Layer 1) scrubs known
credential shapes at write time, inside this repo's transcript pipeline. This
module guards the commit-time backstop for the repo as a whole: a `gitleaks`
pre-commit hook, declared in `.pre-commit-config.yaml`. It is deliberately an
independently-maintained scanner rather than a hook that forks Layer 1's
pattern set — see the comment above the hook entry.

These tests are mutation-valid the way
`tests/transcripts/test_secret_redaction.py::TestWiringIntoArtifacts` is: they
assert on the hook actually blocking a staged commit, and prove the guard goes
red when the HOOK is removed — not merely when the pattern set is broken. A
test that only proves gitleaks recognises a pattern in isolation is the exact
mistake that let this layer disappear once already.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PRE_COMMIT_CONFIG = _REPO_ROOT / ".pre-commit-config.yaml"
_PRE_COMMIT_BIN = Path(sys.executable).parent / "pre-commit"

# Real GitHub PATs are base62 with real entropy; gitleaks' entropy threshold
# does not fire on degenerate strings (e.g. a repeated character), so the
# synthetic token below is deliberately varied rather than a placeholder run.
_SYNTHETIC_SECRET = "GH_TOKEN=ghp_wF9pQd3Xk7mNc2VbYt8LsAeR5oGjH1uZ0iEx\n"
_CLEAN_CONTENT = (
    "# Session\n\n"
    "The parser aggregates tokens by tool and skill. Task IDs like "
    "aops-00c0fa10 are fine.\n\n"
    "```python\n"
    "def redact_secrets(text: str) -> str: ...\n"
    "```\n"
)

pytestmark = pytest.mark.skipif(
    not _PRE_COMMIT_BIN.exists(), reason="pre-commit not installed in this venv"
)


def _gitleaks_hook_config() -> str:
    """The real gitleaks hook entry, read live from `.pre-commit-config.yaml`.

    Read rather than hand-copied so this test cannot silently drift from the
    hook actually shipped — the point is to guard *that* hook's presence.
    """
    doc = yaml.safe_load(_PRE_COMMIT_CONFIG.read_text())
    for repo in doc["repos"]:
        if repo.get("repo") == "https://github.com/gitleaks/gitleaks":
            return yaml.safe_dump({"repos": [repo]})
    raise AssertionError("gitleaks hook not found in .pre-commit-config.yaml")


def _init_repo(tmp_path: Path, *, config_yaml: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / ".pre-commit-config.yaml").write_text(config_yaml)
    subprocess.run(["git", "add", ".pre-commit-config.yaml"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def _stage(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)
    subprocess.run(["git", "add", name], cwd=repo, check=True)


def _run_gate(repo: Path, filename: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(_PRE_COMMIT_BIN), "run", "--files", filename],
        cwd=repo,
        capture_output=True,
        text=True,
    )


class TestSecretGateBlocksCommits:
    def test_staged_secret_is_blocked(self, tmp_path: Path):
        repo = _init_repo(tmp_path, config_yaml=_gitleaks_hook_config())
        _stage(repo, "transcript.md", _SYNTHETIC_SECRET)
        result = _run_gate(repo, "transcript.md")
        assert result.returncode != 0, result.stdout + result.stderr

    def test_clean_content_passes(self, tmp_path: Path):
        repo = _init_repo(tmp_path, config_yaml=_gitleaks_hook_config())
        _stage(repo, "transcript.md", _CLEAN_CONTENT)
        result = _run_gate(repo, "transcript.md")
        assert result.returncode == 0, result.stdout + result.stderr


class TestSecretGateMutationValid:
    """Proves the guard fails when the HOOK is removed, not the pattern.

    Mirrors the Layer 1 mutation evidence recorded on aops_8c697102: the same
    staged secret `test_staged_secret_is_blocked` proves is blocked, here
    proves is NOT blocked once the gitleaks hook entry is absent from the
    config — the exact failure mode (a control silently dropped by a
    refactor, with nothing left to notice) this task exists to close.
    """

    def test_removing_the_hook_unblocks_the_same_secret(self, tmp_path: Path):
        repo = _init_repo(tmp_path, config_yaml="repos: []\n")
        _stage(repo, "transcript.md", _SYNTHETIC_SECRET)
        result = _run_gate(repo, "transcript.md")
        assert result.returncode == 0, (
            "expected the mutated (hook-less) repo to let the secret through; "
            f"got exit {result.returncode}: {result.stdout + result.stderr}"
        )
