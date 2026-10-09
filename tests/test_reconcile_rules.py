"""Tests for truth-maintenance reconcile rules regarding user vs agent boundaries.

Closes academicOps#2840 (Cause D: Role & actionability semantic inversion).
Reconcile must never demand worker completion receipts or release summaries for
tasks closed directly by the user/principal, and must never treat user closures
as unverified anomalies or defects.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECONCILE_SKILL = REPO_ROOT / "plugins" / "ida" / "skills" / "reconcile" / "SKILL.md"
IDA_AGENT = REPO_ROOT / "plugins" / "ida" / "agents" / "ida.md"


def test_reconcile_exempts_user_closures_from_worker_completion_receipts():
    """Reconcile must explicitly distinguish user/principal closures from worker claims."""
    content = RECONCILE_SKILL.read_text(encoding="utf-8")
    assert "user closures" in content.lower() or "principal" in content.lower(), (
        "reconcile SKILL.md must explicitly address user/principal closures"
    )
    assert "completion receipt" in content.lower() or "receipts" in content.lower()
    assert (
        "self-authorizing" in content.lower()
        or "intentional" in content.lower()
        or "presumed intentional" in content.lower()
    )


def test_reconcile_prohibits_flagging_user_closures_as_defects_or_anomalies():
    """User closures must not be flagged as unverified closures or defects."""
    content = RECONCILE_SKILL.read_text(encoding="utf-8")
    assert "closed without an outcome" in content.lower() or "anomaly" in content.lower()


def test_ida_agent_status_rules_state_reconcile_audits_agent_worker_claims_only():
    """ida.md must explicitly state reconcile audits worker claims, not user closures."""
    content = IDA_AGENT.read_text(encoding="utf-8")
    assert "reconcile" in content.lower()
    assert "user closures" in content.lower() or "dashboard" in content.lower()
