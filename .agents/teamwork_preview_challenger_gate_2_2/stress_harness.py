"""
Adversarial Stress Harness for Gate Round 2 Verification.
Written by Challenger 2 in /workspace/.agents/teamwork_preview_challenger_gate_2_2/
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml

from lib.py.transcripts.domain.skills import (
    SkillStatus,
    diagnose_skill,
    diagnose_skill_status,
    is_deliberately_removed,
)
from lib.py.transcripts.domain.tasks import (
    create_task,
    list_tasks,
    update_task,
    validate_task_timestamps,
)
from lib.py.transcripts.domain.time import (
    bucket_tasks_by_due_date,
    get_brisbane_today,
    parse_due_date,
    parse_iso_utc,
)


def test_r1_wf_email_triage_adversarial() -> None:
    """R1: Test frontmatter, index alignment, and dist artifacts strictly."""
    wf_path = Path("plugins/pkb/workflows/wf-email-triage.md")
    assert wf_path.exists(), "wf-email-triage.md missing from plugins/pkb/workflows/"

    content = wf_path.read_text(encoding="utf-8")
    assert content.startswith("---"), "Workflow missing YAML frontmatter header"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Malformed YAML frontmatter delimiters"

    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter.get("id") == "wf-email-triage"
    assert frontmatter.get("kind") == "obligation"
    assert frontmatter.get("permalink") == "wf-email-triage"
    assert frontmatter.get("requires") == ["task-tracking"]

    # Verify INDEX.md
    index_path = Path("plugins/pkb/workflows/INDEX.md")
    assert index_path.exists()
    index_text = index_path.read_text(encoding="utf-8")
    assert "wf-email-triage" in index_text

    # Verify dist artifacts
    for target in ["dist/pkb-claude", "dist/pkb-agy"]:
        dist_wf = Path(target) / "workflows/wf-email-triage.md"
        assert dist_wf.exists(), f"Missing {dist_wf}"
        dist_text = dist_wf.read_text(encoding="utf-8")
        assert "id: wf-email-triage" in dist_text


def test_r2_dangling_plugin_refs_adversarial() -> None:
    """R2: Deep search for dangling /email references across plugins and dist."""
    from tests.test_dangling_plugin_refs import SLASH_EMAIL_REGEX

    # Test regex edge cases
    assert SLASH_EMAIL_REGEX.search("Execute /email now") is not None
    assert SLASH_EMAIL_REGEX.search("Use /email.") is not None
    assert SLASH_EMAIL_REGEX.search("/email") is not None

    assert SLASH_EMAIL_REGEX.search("See /email.md for docs") is None
    assert SLASH_EMAIL_REGEX.search("https://example.com/email") is None
    assert SLASH_EMAIL_REGEX.search("user@email.com") is None
    assert SLASH_EMAIL_REGEX.search("email_validator") is None

    # Scan source plugins & built dist artifacts
    scanned_extensions = {".md", ".json", ".py", ".yaml", ".toml", ".txt"}
    search_dirs = [Path("plugins"), Path("dist")]

    dangling_matches = []
    for sdir in search_dirs:
        for p in sdir.rglob("*"):
            if p.is_file() and p.suffix in scanned_extensions:
                try:
                    text = p.read_text(encoding="utf-8")
                    if SLASH_EMAIL_REGEX.search(text):
                        dangling_matches.append(str(p))
                except Exception:
                    pass

    assert len(dangling_matches) == 0, f"Found dangling /email references in: {dangling_matches}"


def test_r3_list_tasks_timestamps_adversarial() -> None:
    """R3: Test ISO-8601 UTC timestamps, task creation/update, and staleness filtering."""
    now_utc = datetime.now(UTC)
    t1 = create_task("Task 1", status="inbox")

    assert "created_at" in t1
    assert "updated_at" in t1
    assert t1["created_at"].endswith("+00:00") or t1["created_at"].endswith("Z")

    # Validate timestamp format parsing
    created_dt = parse_iso_utc(t1["created_at"])
    assert created_dt is not None
    assert created_dt.tzinfo == UTC

    # Update task
    t1_updated = update_task(t1, updates={"status": "completed"})
    assert t1_updated["updated_at"] >= t1["updated_at"]
    assert t1_updated["status"] == "completed"

    # Test validate_task_timestamps
    validated = validate_task_timestamps(t1_updated)
    assert validated["modified"] is not None
    assert validated["updated_at"] is not None

    # Test bad timestamp handling
    bad_task = dict(t1_updated)
    bad_task["modified"] = None
    bad_task["updated_at"] = "invalid-date"
    validated_bad = validate_task_timestamps(bad_task)
    assert validated_bad["modified"] is None
    assert validated_bad["updated_at"] is None

    # Test list_tasks filtering by since and before
    from datetime import timedelta

    past = (now_utc - timedelta(hours=1)).isoformat()
    future = (now_utc + timedelta(hours=1)).isoformat()

    tasks = [t1]
    res_since = list_tasks(tasks, since=past, include_done=True)
    assert isinstance(res_since, dict)
    assert len(res_since.get("tasks", [])) == 1

    res_future = list_tasks(tasks, since=future, include_done=True)
    assert isinstance(res_future, dict)
    assert len(res_future.get("tasks", [])) == 0


def test_r4_due_date_bucketing_adversarial() -> None:
    """R4: Test Brisbane local date calculation across the 10-hour UTC window."""
    # Test 10-hour boundary (UTC 14:00 - 23:59)
    # 2026-08-06 14:00:00 UTC -> 2026-08-07 00:00:00 Brisbane (+10:00)
    dt_utc_1400 = datetime(2026, 8, 6, 14, 0, 0, tzinfo=UTC)
    brisbane_date = get_brisbane_today(dt_utc_1400)
    assert brisbane_date == date(2026, 8, 7)

    # 2026-08-06 13:59:59 UTC -> 2026-08-06 23:59:59 Brisbane (+10:00)
    dt_utc_1359 = datetime(2026, 8, 6, 13, 59, 59, tzinfo=UTC)
    brisbane_date_prev = get_brisbane_today(dt_utc_1359)
    assert brisbane_date_prev == date(2026, 8, 6)

    # Test ISO string with microseconds + explicit offset
    iso_with_ms_and_tz = "2026-08-06T14:30:00.123456+10:00"
    dt_parsed = parse_due_date(iso_with_ms_and_tz)
    assert dt_parsed == date(2026, 8, 6)

    # Test bucket_tasks_by_due_date with reference Brisbane date
    ref_time = datetime(2026, 8, 6, 20, 0, 0, tzinfo=UTC)  # 06:00 AEST Aug 7
    tasks = [
        {"id": "overdue", "due_date": "2026-08-06"},
        {"id": "today", "due_date": "2026-08-07"},
        {"id": "tomorrow", "due_date": "2026-08-08"},
        {"id": "upcoming", "due_date": "2026-08-10"},
        {"id": "unscheduled", "due_date": None},
    ]
    buckets = bucket_tasks_by_due_date(tasks, reference_time=ref_time)
    assert len(buckets["overdue"]) == 1 and buckets["overdue"][0]["id"] == "overdue"
    assert len(buckets["today"]) == 1 and buckets["today"][0]["id"] == "today"
    assert len(buckets["tomorrow"]) == 1 and buckets["tomorrow"][0]["id"] == "tomorrow"
    assert len(buckets["upcoming"]) == 1 and buckets["upcoming"][0]["id"] == "upcoming"
    assert len(buckets["unscheduled"]) == 1 and buckets["unscheduled"][0]["id"] == "unscheduled"


def test_r5_daily_skill_status_adversarial(tmp_path: Path) -> None:
    """R5: Test skill diagnosis, retired /daily skill status, and corrupted install handling."""
    # Test /daily skill is deliberately removed
    status_daily = diagnose_skill_status("/daily")
    assert status_daily == SkillStatus.DELIBERATELY_REMOVED
    assert is_deliberately_removed("/daily") is True

    status_daily_variant = diagnose_skill_status("daily")
    assert status_daily_variant == SkillStatus.DELIBERATELY_REMOVED

    diag_daily = diagnose_skill("/daily")
    assert diag_daily["status"] == SkillStatus.DELIBERATELY_REMOVED.value
    assert diag_daily["is_deliberately_removed"] is True

    # Test corrupted skill directory (exists in plugins dir but no SKILL.md)
    corrupted_dir = tmp_path / "corrupted_skill"
    corrupted_dir.mkdir()
    diag_corrupted = diagnose_skill_status("corrupted_skill", plugins_dir=tmp_path)
    assert diag_corrupted == SkillStatus.INSTALL_FAILURE

    # Test missing skill
    diag_missing = diagnose_skill_status("nonexistent_skill_xyz", plugins_dir=tmp_path)
    assert diag_missing == SkillStatus.MISSING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
