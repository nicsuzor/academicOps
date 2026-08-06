#!/usr/bin/env python3
"""Empirical stress test suite for Milestone R1.

Tests find_session_files() and _sanitize_path_component() under edge cases and adversarial inputs.
"""

import os
import shutil
import tempfile
import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, "/workspace/lib/py")
sys.path.insert(0, "/workspace/lib")

from transcripts.runner import find_session_files
from polecat.cli import _sanitize_path_component

def test_find_session_files_deep_nesting():
    print("=== Testing find_session_files() with Deep Nesting & Filters ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sessions_dir = tmp_path / "sessions"
        logs_dir = sessions_dir / "logs"

        expected_valid_files = set()
        excluded_files = set()

        # Depths 1 to 10
        for depth in range(1, 11):
            nested_path = logs_dir.joinpath(*[f"dir_level_{i}" for i in range(1, depth + 1)])
            nested_path.mkdir(parents=True, exist_ok=True)

            # Valid jsonl file
            f_valid = nested_path / f"valid_depth_{depth}.jsonl"
            f_valid.write_text('{"event": "test"}\n', encoding="utf-8")
            expected_valid_files.add(f_valid.resolve())

            # Valid transcript.jsonl file
            f_transcript = nested_path / "transcript.jsonl"
            f_transcript.write_text('{"event": "transcript"}\n', encoding="utf-8")
            expected_valid_files.add(f_transcript.resolve())

            # Excluded -hooks.jsonl file
            f_hook = nested_path / f"depth_{depth}-hooks.jsonl"
            f_hook.write_text('{"event": "hook"}\n', encoding="utf-8")
            excluded_files.add(f_hook.resolve())

            # Excluded subagents file in nested subagents directory
            subagent_dir = nested_path / "subagents"
            subagent_dir.mkdir(exist_ok=True)
            f_subagent = subagent_dir / f"subagent_depth_{depth}.jsonl"
            f_subagent.write_text('{"event": "subagent"}\n', encoding="utf-8")
            excluded_files.add(f_subagent.resolve())

            # Excluded deeply nested file inside subagents sub-subdirectories (subagents/foo/bar.jsonl)
            deep_subagent_dir = subagent_dir / "foo" / "bar"
            deep_subagent_dir.mkdir(parents=True, exist_ok=True)
            f_deep_subagent = deep_subagent_dir / f"deep_subagent_depth_{depth}.jsonl"
            f_deep_subagent.write_text('{"event": "deep_subagent"}\n', encoding="utf-8")
            excluded_files.add(f_deep_subagent.resolve())

        found_files = set(f.resolve() for f in find_session_files(sessions_dir))

        # Filter out any pre-existing files if running in environment with real logs
        found_files_tmp = set(f for f in found_files if tmpdir in str(f))

        missing_valid = expected_valid_files - found_files_tmp
        wrongly_included = excluded_files & found_files_tmp

        print(f"Total expected valid session files (depths 1-10): {len(expected_valid_files)}")
        print(f"Total found files in tmp: {len(found_files_tmp)}")
        print(f"Missing valid files count: {len(missing_valid)}")
        print(f"Wrongly included files count: {len(wrongly_included)}")

        if missing_valid:
            print("FAILED: missing valid files:", missing_valid)
        if wrongly_included:
            print("FAILED: wrongly included files:", wrongly_included)

        assert not missing_valid, f"Missing valid files: {missing_valid}"
        assert not wrongly_included, f"Wrongly included files: {wrongly_included}"
        print("-> find_session_files() deep nesting & filter test PASSED!\n")


def test_sanitize_path_component_stress():
    print("=== Testing _sanitize_path_component() Stress Cases ===")

    test_cases = [
        # (Input, Expected, Description)
        ("../../etc/passwd", "etc_passwd", "Path traversal"),
        ("foo/bar", "foo_bar", "Forward slashes"),
        ("foo\\bar", "foo_bar", "Backslashes"),
        ("session; rm -rf /", "session__rm_-rf", "Command injection with semicolon & rm"),
        ("foo && cat /etc/passwd", "foo____cat__etc_passwd", "Command injection with &&"),
        ("$(whoami)", "whoami", "Command substitution $()"),
        ("`id`", "id", "Backticks command substitution"),
        ("foo | bar", "foo___bar", "Pipe symbol"),
        ("session_测试_🔥", "session", "Unicode / non-ascii chars replaced"),
        ("   session name   ", "session_name", "Leading/trailing whitespace"),
        (" \t\n foo \r\n ", "foo", "Tabs and newlines"),
        ("--project-name--", "project-name", "Leading/trailing dashes"),
        ("..myproject..", "myproject", "Leading/trailing dots"),
        ("___project___", "project", "Leading/trailing underscores"),
        ("-leading-dash", "leading-dash", "Single leading dash"),
        ("._-test-_.", "test", "Mixed leading/trailing separators"),
        ("..", None, "Only double dot"),
        (".", None, "Only single dot"),
        ("../..", None, "Only path traversal slashes/dots"),
        ("   ", None, "Only whitespace"),
        ("", None, "Empty string"),
        (None, None, "None input"),
        ("...", None, "Only dots"),
        ("---", None, "Only dashes"),
        ("___", None, "Only underscores"),
        (" . _ - ", None, "Only separator chars & space"),
        ("\x00nullbyte", "nullbyte", "Null byte"),
        ("a" * 300, "a" * 300, "Long safe string"),
        ("../../a/b/c/../../etc/shadow", "a_b_c_.._.._etc_shadow", "Complex traversal"),
    ]

    failed_cases = []

    for val, expected, desc in test_cases:
        res = _sanitize_path_component(val)
        if res != expected:
            print(f"FAIL [{desc}]: input={val!r} -> got {res!r}, expected {expected!r}")
            failed_cases.append((val, res, expected, desc))
        else:
            print(f"PASS [{desc}]: input={val!r} -> {res!r}")

    assert not failed_cases, f"Sanitization stress tests failed: {failed_cases}"
    print("-> _sanitize_path_component() stress test PASSED!\n")


def test_path_traversal_safety():
    print("=== Testing Path Traversal Safety of Sanitized Components ===")
    base_dir = Path("/tmp/base_dir")
    malicious_inputs = [
        "../../etc/passwd",
        "../../../../",
        "../../../tmp/evil",
        "a/b/../../c",
        "/absolute/path",
        "C:\\Windows\\System32",
        "~/.ssh/id_rsa",
        "project/session/../../root",
    ]
    for inp in malicious_inputs:
        sanitized = _sanitize_path_component(inp)
        if sanitized is None:
            resolved = base_dir
        else:
            resolved = (base_dir / sanitized).resolve()
        
        # Verify that resolved path is ALWAYS inside base_dir or equal to base_dir
        try:
            resolved.relative_to(base_dir)
            print(f"PASS [Path Safety]: {inp!r} -> {sanitized!r} -> resolved to {resolved} (within {base_dir})")
        except ValueError:
            print(f"FAIL [Path Safety]: {inp!r} -> {sanitized!r} -> ESCAPED to {resolved}")
            sys.exit(1)
    print("-> Path traversal safety test PASSED!\n")


if __name__ == "__main__":
    test_find_session_files_deep_nesting()
    test_sanitize_path_component_stress()
    test_path_traversal_safety()
    print("ALL EMPIRICAL STRESS TESTS PASSED SUCCESSFULLY!")
