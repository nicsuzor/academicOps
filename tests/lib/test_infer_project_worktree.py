#!/usr/bin/env python3
"""Tests for ``infer_project_from_working_dir`` worktree handling.

Covers the four acceptance cases from task-ea880699:
(a) Claude Code worktree path -> main repo
(b) Polecat worktree path -> still works (regression guard)
(c) Hex-only basename -> walks up or returns None
(d) Regular project path -> unchanged
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from lib.transcript_parser import (
    _is_worktree_basename,
    _walk_up_for_project,
    infer_project_from_working_dir,
)


class TestIsWorktreeBasename:
    """Pattern matching for worktree-style directory basenames."""

    @pytest.mark.parametrize(
        "name",
        [
            "79257c",  # hex-only, 6 chars
            "008c345f",  # hex-only, 8 chars
            "1202c6",  # hex-only, 6 chars
            "aops-008c345f",  # polecat-style: word-hex
            "gallant-albattani-79257c",  # claude code: adj-noun-hex
            "modest-jemison-1202c6",  # claude code: adj-noun-hex
            "foo-bar-baz-deadbeef",  # multi-word-hex
        ],
    )
    def test_matches_worktree_basenames(self, name: str) -> None:
        assert _is_worktree_basename(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "brain",
            "academicOps",
            "client-work",  # word-word, no hex
            "myproject",
            "abc",  # too short for hex pattern
            "AOPS-008c345f",  # uppercase first segment
            "aops_008c345f",  # underscore separator
            "aops-008c345g",  # 'g' is not hex
        ],
    )
    def test_rejects_non_worktree_basenames(self, name: str) -> None:
        assert _is_worktree_basename(name) is False


class TestWalkUpForProject:
    """The path-walk fallback when git is unavailable."""

    def test_walks_past_generic_containers(self) -> None:
        # /Users/suzor/.aops/brain/gallant-albattani-79257c
        parts = ("/", "Users", "suzor", ".aops", "brain", "gallant-albattani-79257c")
        assert _walk_up_for_project(parts) == "brain"

    def test_walks_past_claude_worktrees_dir(self) -> None:
        # /home/x/src/academicOps/.claude/worktrees/modest-jemison-1202c6
        parts = (
            "/",
            "home",
            "x",
            "src",
            "academicOps",
            ".claude",
            "worktrees",
            "modest-jemison-1202c6",
        )
        assert _walk_up_for_project(parts) == "academicOps"

    def test_returns_none_when_only_generic_ancestors(self) -> None:
        # /worktrees/79257c -> no project ancestor
        parts = ("/", "worktrees", "79257c")
        assert _walk_up_for_project(parts) is None

    def test_returns_none_for_root_only(self) -> None:
        parts = ("/", "79257c")
        assert _walk_up_for_project(parts) is None

    def test_skips_nested_worktree_basenames(self) -> None:
        # Hypothetical chain of worktrees — keep walking until non-worktree.
        parts = ("/", "home", "x", "brain", "aops-deadbeef", "gallant-albattani-79257c")
        assert _walk_up_for_project(parts) == "brain"


class TestInferProjectFromWorkingDir:
    """End-to-end behavior of ``infer_project_from_working_dir``."""

    # ----- Acceptance (a): Claude Code worktree -> main repo -----

    def test_claude_worktree_under_aops_brain_resolves_to_brain(self) -> None:
        """Bug evidence: /Users/suzor/.aops/brain/gallant-albattani-79257c
        previously returned '79257c' / 'gallant-albattani-79257c'. Must
        resolve to 'brain'.

        Patches the git resolver to None so the path-walking fallback is
        exercised in pure-string mode (CI has no filesystem at this path).
        """
        with patch("lib.transcript_parser._resolve_worktree_via_git", return_value=None):
            result = infer_project_from_working_dir(
                "/Users/suzor/.aops/brain/gallant-albattani-79257c"
            )
        assert result == "brain"

    def test_claude_worktree_under_dot_claude_worktrees_resolves_to_repo(self) -> None:
        """A worktree at <repo>/.claude/worktrees/<slug>-<hex> should
        resolve to <repo>."""
        with patch("lib.transcript_parser._resolve_worktree_via_git", return_value=None):
            result = infer_project_from_working_dir(
                "/home/nic/src/academicOps/.claude/worktrees/modest-jemison-1202c6"
            )
        assert result == "academicOps"

    def test_git_resolution_takes_precedence(self) -> None:
        """When the git resolver returns a name, it wins over path walking."""
        with patch(
            "lib.transcript_parser._resolve_worktree_via_git",
            return_value="brain",
        ):
            result = infer_project_from_working_dir(
                "/Users/suzor/.aops/brain/gallant-albattani-79257c"
            )
        assert result == "brain"

    # ----- Acceptance (b): Polecat worktree still works -----

    def test_polecat_worktree_resolves_to_project(self) -> None:
        """Existing polecat handling: $POLECAT_HOME/polecat/{project}-{hash}."""
        # No git patch needed — polecat branch returns before git is called.
        result = infer_project_from_working_dir("/home/nic/.aops/polecat/aops-008c345f")
        assert result == "aops"

    def test_polecat_worktree_dotpolecat_variant(self) -> None:
        result = infer_project_from_working_dir("/home/x/.polecat/polecat/brain-12345678")
        assert result == "brain"

    def test_polecat_short_name_returns_as_is(self) -> None:
        # Names that don't match the {name}-{8hex} pattern under polecat
        # are returned as-is (existing behavior).
        result = infer_project_from_working_dir("/home/x/.aops/polecat/aops")
        assert result == "aops"

    # ----- Acceptance (c): hex-only basename -----

    def test_hex_only_basename_walks_up(self) -> None:
        """A bare hex basename with a non-generic parent walks up to it."""
        with patch("lib.transcript_parser._resolve_worktree_via_git", return_value=None):
            result = infer_project_from_working_dir("/Users/suzor/.aops/brain/79257c")
        assert result == "brain"

    def test_hex_only_basename_with_no_real_ancestor_returns_none(self) -> None:
        """Hex with only generic ancestors returns None — never the hex
        slug itself."""
        with patch("lib.transcript_parser._resolve_worktree_via_git", return_value=None):
            result = infer_project_from_working_dir("/worktrees/79257c")
        assert result is None

    def test_hex_only_basename_at_filesystem_root_returns_none(self) -> None:
        with patch("lib.transcript_parser._resolve_worktree_via_git", return_value=None):
            result = infer_project_from_working_dir("/79257c")
        assert result is None

    # ----- Acceptance (d): regular project path unchanged -----

    def test_regular_project_path_unchanged(self) -> None:
        assert infer_project_from_working_dir("/home/user/src/myproject") == "myproject"

    def test_regular_hyphenated_project_unchanged(self) -> None:
        assert infer_project_from_working_dir("/home/user/projects/client-work") == "client-work"

    def test_generic_basename_walks_up_one(self) -> None:
        # Existing behavior: trailing 'src' walks up to its parent.
        assert infer_project_from_working_dir("/opt/user/code") == "user"

    # ----- Edge cases -----

    def test_empty_input_returns_none(self) -> None:
        assert infer_project_from_working_dir("") is None

    def test_none_input_returns_none(self) -> None:
        assert infer_project_from_working_dir(None) is None

    def test_single_segment_returns_none(self) -> None:
        assert infer_project_from_working_dir("/") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
