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
        filename = session_naming.get_gate_filename("custodiet", session_id, date=date, hour=hour)
        self.assertEqual(filename, "20260411-10-550e8400-custodiet.md")

    def test_iso_date_extraction(self):
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        date = "2026-01-24T17:30:00+10:00"
        filename = session_naming.get_session_filename(session_id, date=date)
        self.assertEqual(filename, "20260124-17-550e8400.json")


if __name__ == "__main__":
    unittest.main()
