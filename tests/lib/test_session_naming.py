import os
import unittest

from lib import session_naming


class TestSessionNaming(unittest.TestCase):
    def test_get_session_short_hash_uuid(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        self.assertEqual(session_naming.get_session_short_hash(session_id), "550e8400")

    def test_get_session_short_hash_short(self):
        session_id = "abc"
        # Should use SHA256 fallback
        self.assertEqual(len(session_naming.get_session_short_hash(session_id)), 8)

    def test_get_session_short_hash_empty_raises(self):
        with self.assertRaises(ValueError):
            session_naming.get_session_short_hash("")

    def test_get_session_short_hash_unknown_raises(self):
        with self.assertRaises(ValueError):
            session_naming.get_session_short_hash("unknown")

    def test_get_session_filename_basic(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-04-11"
        hour = "10"
        filename = session_naming.get_session_filename(session_id, date=date, hour=hour)
        self.assertEqual(filename, "20260411-10-550e8400.json")

    def test_get_session_filename_full(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-04-11"
        hour = "10"
        project = "my-project"
        slug = "refactor"
        filename = session_naming.get_session_filename(
            session_id, date=date, hour=hour, project=project, slug=slug
        )
        self.assertEqual(filename, "20260411-10-my-project-550e8400-refactor.json")

    def test_get_hook_log_filename(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-04-11"
        hour = "10"
        filename = session_naming.get_hook_log_filename(session_id, date=date, hour=hour)
        self.assertEqual(filename, "20260411-10-550e8400-hooks.jsonl")

    def test_get_gate_filename(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-04-11"
        hour = "10"
        filename = session_naming.get_gate_filename("enforcer", session_id, date=date, hour=hour)
        self.assertEqual(filename, "20260411-10-550e8400-enforcer.md")

    def test_iso_date_extraction(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-01-24T17:30:00+10:00"
        filename = session_naming.get_session_filename(session_id, date=date)
        self.assertEqual(filename, "20260124-17-550e8400.json")


class TestTaskIdAlignment(unittest.TestCase):
    """Task-c36a6b0c: task_id embedded in slug for grep-friendly artefact discovery."""

    SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"

    def _ts(self):
        from datetime import datetime

        return datetime(2026, 4, 30, 12, 34).astimezone()

    def test_no_task_id_preserves_existing_filename(self):
        """task_id=None must produce the exact filename as before this change."""
        without = session_naming.generate_session_filename(
            self.SESSION_ID, timestamp=self._ts(), repo="academicops", slug="session"
        )
        explicit_none = session_naming.generate_session_filename(
            self.SESSION_ID,
            timestamp=self._ts(),
            repo="academicops",
            slug="session",
            task_id=None,
        )
        self.assertEqual(without, explicit_none)
        self.assertNotIn("task-", without)

    def test_task_id_embedded_in_slug(self):
        filename = session_naming.generate_session_filename(
            self.SESSION_ID,
            timestamp=self._ts(),
            repo="academicops",
            slug="session",
            task_id="task-c36a6b0c-something",
        )
        # Grep-friendly: full task hash appears literally in filename.
        self.assertIn("task-c36a6b0c", filename)
        # Slug position preserved (between shortform and variant).
        self.assertTrue(filename.endswith("-task-c36a6b0c-session-full.md"))

    def test_task_id_in_base_name(self):
        base = session_naming.generate_base_name(
            self.SESSION_ID,
            timestamp=self._ts(),
            repo="academicops",
            slug="session",
            task_id="task-c36a6b0c",
        )
        self.assertIn("task-c36a6b0c", base)

    def test_filename_with_task_id_still_parseable(self):
        filename = session_naming.generate_session_filename(
            self.SESSION_ID,
            timestamp=self._ts(),
            repo="academicops",
            slug="session",
            task_id="task-c36a6b0c",
        )
        parsed = session_naming.parse_session_filename(filename)
        self.assertIsNotNone(parsed)
        # Structurally unambiguous fields must round-trip.
        self.assertEqual(parsed.session_id, "550e8400")
        self.assertEqual(parsed.date, "20260430")
        self.assertEqual(parsed.variant, "-full")
        self.assertEqual(parsed.ext, ".md")
        # Task hash appears literally in the filename — this is what enables
        # grep-based artefact discovery. Crew/repo/slug heuristics are
        # documented as low-confidence (frontmatter is authoritative).
        self.assertIn("c36a6b0c", filename)

    def test_non_hex_task_id_falls_back_to_hash(self):
        filename = session_naming.generate_session_filename(
            self.SESSION_ID,
            timestamp=self._ts(),
            repo="academicops",
            slug="session",
            task_id="my-arbitrary-task-name",
        )
        # Non-hex task IDs still get an 8-char shortform via SHA-256.
        self.assertRegex(filename, r"-task-[0-9a-f]{8}-")


class TestSurfaceClientDetection(unittest.TestCase):
    """aops-eaf402f5: surface/client/crew tagging on session summaries.

    Each test scrubs the relevant env vars so host env doesn't leak in.
    """

    SCRUBBED = (
        "GITHUB_ACTIONS",
        "AOPS_POLECAT_CONTAINER",
        "POLECAT_CREW_NAME",
        "GEMINI_SESSION_ID",
        "AOPS_SESSION_ID",
        "AOPS_SESSION_STATE_DIR",
        "AOPS_MACHINE",
    )

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in self.SCRUBBED}
        for k in self.SCRUBBED:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_github_actions_surface(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        self.assertEqual(session_naming.get_surface(), "github-actions")
        self.assertEqual(session_naming.get_client(), "github-actions")

    def test_polecat_run_surface(self):
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        self.assertEqual(session_naming.get_surface(), "claude-polecat")
        self.assertEqual(session_naming.get_client(), "polecat")

    def test_polecat_crew_surface(self):
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        os.environ["POLECAT_CREW_NAME"] = "barbara"
        self.assertEqual(session_naming.get_surface(), "claude-crew")
        self.assertEqual(session_naming.get_client(), "crew")
        self.assertEqual(session_naming.resolve_crew_name(), "barbara")

    def test_plain_cli_surface(self):
        # No polecat, no GHA — default claude CLI.
        self.assertEqual(session_naming.get_surface(), "claude-code-cli")
        self.assertEqual(session_naming.get_client(), "claude-code")

    def test_gemini_cli_surface(self):
        os.environ["GEMINI_SESSION_ID"] = "gemini-test"
        self.assertEqual(session_naming.get_surface(), "gemini-cli")
        self.assertEqual(session_naming.get_client(), "gemini-cli")

    def test_gemini_polecat_surface(self):
        os.environ["GEMINI_SESSION_ID"] = "gemini-test"
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        self.assertEqual(session_naming.get_surface(), "gemini-polecat")
        self.assertEqual(session_naming.get_client(), "polecat")

    def test_gha_takes_precedence_over_polecat(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        # CI is the dominant surface — polecat-on-GHA is still "github-actions".
        self.assertEqual(session_naming.get_surface(), "github-actions")

    def test_metadata_dict_has_all_fields(self):
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        os.environ["POLECAT_CREW_NAME"] = "barbara"
        meta = session_naming.get_session_metadata()
        self.assertEqual(
            set(meta.keys()),
            {"machine", "hostname", "provider", "surface", "client", "crew"},
        )
        self.assertEqual(meta["surface"], "claude-crew")
        self.assertEqual(meta["client"], "crew")
        self.assertEqual(meta["crew"], "barbara")
        self.assertEqual(meta["provider"], "claude")

    def test_provider_override_propagates_to_surface_and_client(self):
        """Path-detected provider must override env-detected provider.

        The offline transcript-to-summary converter reads `.gemini/` files from
        a Claude shell; without override the JSON would mis-stamp provider.
        """
        os.environ["AOPS_POLECAT_CONTAINER"] = "1"
        meta = session_naming.get_session_metadata(provider="gemini")
        self.assertEqual(meta["provider"], "gemini")
        self.assertEqual(meta["surface"], "gemini-polecat")
        self.assertEqual(meta["client"], "polecat")


class TestInferSessionOriginFromPath(unittest.TestCase):
    """Path-based surface/client/crew inference for the offline converter.

    The transcript.py batch job runs long after the original runtime env has
    been torn down (GHA jobs ended, polecat containers exited). It must infer
    the surface trio from where the session file lives, not from the
    converter shell's live env. See infer_session_origin_from_path docstring.
    """

    def test_github_actions_path(self):
        from pathlib import Path

        p = Path(
            "/home/nic/src/sessions/github/academicops/25594329521/1/"
            "-home-runner-work-academicOps-academicOps/27cbbac8.jsonl"
        )
        origin = session_naming.infer_session_origin_from_path(p)
        self.assertEqual(origin["surface"], "github-actions")
        self.assertEqual(origin["client"], "github-actions")
        self.assertIsNone(origin["crew"])

    def test_crew_path(self):
        from pathlib import Path

        p = Path(
            "/home/nic/src/sessions/crew/gloria/aops/-workspace/"
            "20260504-1534-6bcb0403-gloria-workspace-session.json"
        )
        origin = session_naming.infer_session_origin_from_path(p)
        self.assertEqual(origin["surface"], "claude-crew")
        self.assertEqual(origin["client"], "crew")
        self.assertEqual(origin["crew"], "gloria")

    def test_crew_path_with_gemini_provider(self):
        from pathlib import Path

        p = Path("/home/nic/src/sessions/crew/bayard/mem/-workspace/x.json")
        origin = session_naming.infer_session_origin_from_path(p, provider="gemini")
        self.assertEqual(origin["surface"], "gemini-crew")
        self.assertEqual(origin["client"], "crew")
        self.assertEqual(origin["crew"], "bayard")

    def test_polecat_path(self):
        from pathlib import Path

        p = Path("/home/nic/src/sessions/polecats/task-4747a704/aops/-workspace/x.json")
        origin = session_naming.infer_session_origin_from_path(p)
        self.assertEqual(origin["surface"], "claude-polecat")
        self.assertEqual(origin["client"], "polecat")
        self.assertIsNone(origin["crew"])

    def test_gemini_cli_path(self):
        from pathlib import Path

        p = Path("/home/nic/.gemini/tmp/abc123/chats/session-2026-05-11T10-58-a5234d3e.json")
        origin = session_naming.infer_session_origin_from_path(p)
        self.assertEqual(origin["surface"], "gemini-cli")
        self.assertEqual(origin["client"], "gemini-cli")
        self.assertIsNone(origin["crew"])

    def test_claude_cli_default(self):
        from pathlib import Path

        p = Path("/home/nic/.claude/projects/-home-nic-src-academicOps/abc.jsonl")
        origin = session_naming.infer_session_origin_from_path(p)
        self.assertEqual(origin["surface"], "claude-code-cli")
        self.assertEqual(origin["client"], "claude-code")
        self.assertIsNone(origin["crew"])

    def test_metadata_accepts_path_overrides(self):
        """get_session_metadata forwards explicit surface/client/crew overrides."""
        meta = session_naming.get_session_metadata(
            provider="claude",
            surface="github-actions",
            client="github-actions",
            crew=None,
        )
        self.assertEqual(meta["surface"], "github-actions")
        self.assertEqual(meta["client"], "github-actions")
        self.assertEqual(meta["provider"], "claude")


class TestInferSessionOriginFromEntries(unittest.TestCase):
    """Content-based surface upgrade for Claude Desktop LAM sessions.

    Claude Code launched from inside the desktop GUI's Local Agent Mode writes
    JSONL to the same path as a terminal launch (~/.claude/projects/...), so
    path inference can't distinguish them. The entry-content scan looks for
    the desktop GUI's plugin cache path leaking into early entries.
    """

    class _StubEntry:
        def __init__(self, content=None, cwd=None):
            self.message = {"content": content} if content is not None else {}
            self.cwd = cwd

    _LAM_SKILL_REMINDER = (
        "<system-reminder>\n"
        "Invoked: /supervisor (skill)\n\n"
        "Base directory for this skill: "
        "/Users/x/Library/Application Support/Claude/local-agent-mode-sessions/"
        "abc/def/skills/supervisor\n"
        "</system-reminder>"
    )

    def test_plain_cli_stays_cli(self):
        entries = [self._StubEntry("hello world"), self._StubEntry("no marker here")]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base)
        self.assertEqual(origin["surface"], "claude-code-cli")
        self.assertEqual(origin["client"], "claude-code")

    def test_conversational_mention_does_not_trigger(self):
        """Users typing the LAM path in chat must not be classified as LAM.

        Regression: this very session discussed local-agent-mode-sessions while
        being a regular terminal launch — without the narrow signal it would
        misclassify itself.
        """
        entries = [
            self._StubEntry(
                "Today I'm working on detecting "
                "Library/Application Support/Claude/local-agent-mode-sessions paths "
                "in transcript.py — see the plan."
            )
        ]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base)
        self.assertEqual(origin["surface"], "claude-code-cli")

    def test_skill_reminder_string_content_upgrades(self):
        entries = [self._StubEntry(self._LAM_SKILL_REMINDER)]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base)
        self.assertEqual(origin["surface"], "claude-code-desktop")
        self.assertEqual(origin["client"], "claude-desktop")

    def test_skill_reminder_block_list_content_upgrades(self):
        entries = [self._StubEntry([{"type": "text", "text": self._LAM_SKILL_REMINDER}])]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base)
        self.assertEqual(origin["surface"], "claude-code-desktop")

    def test_lam_cwd_upgrades(self):
        entries = [
            self._StubEntry(
                "ok",
                cwd="/Users/x/Library/Application Support/Claude/local-agent-mode-sessions/abc",
            )
        ]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base)
        self.assertEqual(origin["surface"], "claude-code-desktop")

    def test_path_origin_wins_over_content(self):
        """GHA/crew/polecat detection should not be downgraded by content."""
        entries = [self._StubEntry(self._LAM_SKILL_REMINDER)]
        for base in (
            {"surface": "github-actions", "client": "github-actions", "crew": None},
            {"surface": "claude-crew", "client": "crew", "crew": "gloria"},
            {"surface": "claude-polecat", "client": "polecat", "crew": None},
        ):
            with self.subTest(surface=base["surface"]):
                origin = session_naming.infer_session_origin_from_entries(entries, dict(base))
                self.assertEqual(origin["surface"], base["surface"])
                self.assertEqual(origin["client"], base["client"])

    def test_scan_window_respects_max_scan(self):
        """Entries beyond max_scan must not be inspected."""
        entries = [self._StubEntry("clean") for _ in range(20)] + [
            self._StubEntry(self._LAM_SKILL_REMINDER)
        ]
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(entries, base, max_scan=10)
        self.assertEqual(origin["surface"], "claude-code-cli")

    def test_none_entries_returns_base_unchanged(self):
        base = {"surface": "claude-code-cli", "client": "claude-code", "crew": None}
        origin = session_naming.infer_session_origin_from_entries(None, base)
        self.assertEqual(origin, base)


if __name__ == "__main__":
    unittest.main()
