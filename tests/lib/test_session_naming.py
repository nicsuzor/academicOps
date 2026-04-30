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


if __name__ == "__main__":
    unittest.main()
