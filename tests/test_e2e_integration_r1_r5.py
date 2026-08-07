"""End-to-End Cross-Feature Integration Test Suite (R1 - R5).

Covers Tier 3 (Cross-Feature Integration) and Tier 4 (Real-World E2E Scenarios)
integrating workflow component validation, plugin reference cleanliness, task mutation
timestamp tracking, Brisbane timezone due-date bucketing, and skill status classification.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import yaml
from transcripts.domain.skills import get_all_skills_diagnostics
from transcripts.domain.tasks import (
    create_task,
    list_tasks,
    update_task,
)
from transcripts.domain.time import (
    bucket_due_date,
    bucket_tasks_by_due_date,
    get_brisbane_today,
)

from build.build import build_all

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_MARKETPLACE = PROJECT_ROOT / "build" / "marketplace.toml"


# ===========================================================================
# Tier 3: Cross-Feature Integration Tests
# ===========================================================================


def test_tier3_task_mutation_timestamp_and_brisbane_bucketing_integration():
    """Cross-Feature Test: Task creation, timestamp updates, staleness filtering, and Brisbane due-date bucketing."""
    # Reference time: 2026-08-06 18:00:00 UTC -> Brisbane date: 2026-08-07
    eval_time = datetime(2026, 8, 6, 18, 0, 0, tzinfo=UTC)
    brisbane_today = get_brisbane_today(eval_time)
    assert brisbane_today == date(2026, 8, 7)

    # 1. Create tasks with explicit timestamps and due dates
    t1 = create_task(
        "Triage incoming emails",
        created_at=datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC),
        due_date="2026-08-06",
        workflow="wf-email-triage",
    )
    t2 = create_task(
        "Process urgent response",
        created_at=datetime(2026, 8, 6, 8, 0, 0, tzinfo=UTC),
        due_date="2026-08-07",
        workflow="wf-email-triage",
    )
    t3 = create_task(
        "Archive weekly digest",
        created_at=datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC),
        due_date="2026-08-08",
        workflow="wf-email-triage",
    )

    raw_tasks = [t1, t2, t3]

    # 2. Mutate task t2
    t2_updated = update_task(
        t2,
        updates={"status": "in_progress"},
        modified_at=datetime(2026, 8, 6, 17, 30, 0, tzinfo=UTC),
    )
    raw_tasks[1] = t2_updated

    # 3. Perform staleness sweep (list_tasks since 2026-08-06)
    stale_sweep = list_tasks(raw_tasks, since="2026-08-06", include_done=True)
    assert isinstance(stale_sweep, dict)
    recent_tasks = stale_sweep["tasks"]
    assert len(recent_tasks) == 2
    assert [t["title"] for t in recent_tasks] == [
        "Process urgent response",
        "Archive weekly digest",
    ]

    # 4. Perform Brisbane due-date bucketing on recent tasks at 18:00 UTC
    bucketed = bucket_tasks_by_due_date(recent_tasks, reference_time=eval_time)

    # Aug 6 due date -> overdue in Brisbane (where today is Aug 7)
    # Aug 7 due date -> today in Brisbane
    # Aug 8 due date -> tomorrow in Brisbane
    assert len(bucketed["today"]) == 1
    assert bucketed["today"][0]["title"] == "Process urgent response"

    assert len(bucketed["tomorrow"]) == 1
    assert bucketed["tomorrow"][0]["title"] == "Archive weekly digest"


def test_tier3_workflow_contract_and_skill_diagnostics_alignment():
    """Cross-Feature Test: Verify workflow component obligations match skill diagnostics expectations."""
    # Workflow component wf-email-triage requires task-tracking
    wf_path = PROJECT_ROOT / "plugins" / "pkb" / "workflows" / "wf-email-triage.md"
    content = wf_path.read_text(encoding="utf-8")
    fm = yaml.safe_load(content.split("---", 2)[1])

    assert fm["id"] == "wf-email-triage"
    assert fm["kind"] == "obligation"
    assert "task-tracking" in fm["requires"]

    # Verify skill diagnostics correctly reports active brief skill and retired /daily skill
    diag = get_all_skills_diagnostics(["brief", "/daily"], plugins_dir=PROJECT_ROOT / "plugins")
    assert diag["brief"]["status"] == "installed"
    assert diag["/daily"]["status"] == "deliberately_removed"


# ===========================================================================
# Tier 4: Real-World E2E Scenarios
# ===========================================================================


def test_tier4_e2e_build_package_and_reference_cleanliness_pipeline(tmp_path):
    """Real-World E2E Scenario: Full build pipeline execution, dist artifact packaging, and reference audit."""
    dist_dir = tmp_path / "dist"

    # Build all plugin targets
    build_all(
        PROJECT_ROOT,
        dist_dir,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["pkb", "rbg", "ida"],
        version="1.0.0-e2e",
    )

    assert dist_dir.exists()
    assert (dist_dir / "pkb-claude").is_dir()
    assert (dist_dir / "pkb-agy").is_dir()

    # 1. Verify wf-email-triage presence in built dist artifacts
    built_claude_wf = dist_dir / "pkb-claude" / "workflows" / "wf-email-triage.md"
    built_agy_wf = dist_dir / "pkb-agy" / "workflows" / "wf-email-triage.md"

    assert built_claude_wf.is_file()
    assert built_agy_wf.is_file()

    claude_fm = yaml.safe_load(built_claude_wf.read_text().split("---", 2)[1])
    assert claude_fm["id"] == "wf-email-triage"
    assert claude_fm["permalink"] == "wf-email-triage"

    # 2. Audit generated dist artifacts for zero dangling `/email` slash command references
    from tests.test_dangling_plugin_refs import _scan_directory_for_dangling_slash_email

    dangling_refs = _scan_directory_for_dangling_slash_email(dist_dir)
    assert not dangling_refs, (
        f"Discovered dangling slash commands in built artifacts: {dangling_refs}"
    )


def test_tier4_e2e_full_task_lifecycle_across_brisbane_midnight():
    """Real-World E2E Scenario: Simulated task lifecycle created before UTC midnight, updated across Brisbane date shift."""
    # Step A: Created at 13:30 UTC on Aug 6 (23:30 AEST Aug 6)
    t_created = datetime(2026, 8, 6, 13, 30, 0, tzinfo=UTC)
    task = create_task("E2E Nightly Task", created_at=t_created, due_date="2026-08-06")

    # Evaluate bucket at 13:30 UTC (Brisbane date Aug 6) -> today
    assert bucket_due_date(task["due_date"], reference_time=t_created) == "today"

    # Step B: 45 minutes later at 14:15 UTC on Aug 6 (00:15 AEST Aug 7)
    # Brisbane date shifted to Aug 7!
    t_updated = datetime(2026, 8, 6, 14, 15, 0, tzinfo=UTC)
    task_updated = update_task(task, updates={"status": "ready"}, modified_at=t_updated)

    # Evaluate bucket at 14:15 UTC (Brisbane date Aug 7) -> task due 2026-08-06 is now OVERDUE
    assert bucket_due_date(task_updated["due_date"], reference_time=t_updated) == "overdue"

    # Verify task modification timestamp is recorded cleanly in ISO-8601 UTC
    assert task_updated["modified"] == "2026-08-06T14:15:00.000000+00:00"

    # Staleness sweep at 14:30 UTC selecting tasks modified since 14:00 UTC
    sweep_results = list_tasks([task_updated], since="2026-08-06T14:00:00Z", include_done=True)
    assert sweep_results["total"] == 1
    assert sweep_results["tasks"][0]["modified"] == "2026-08-06T14:15:00.000000+00:00"
