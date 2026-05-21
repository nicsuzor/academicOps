"""Smoke test: audit_agent_compliance generator must be byte-for-byte idempotent.

Running the generator twice in a row must produce identical output. Drift here would
make every regeneration produce noisy diffs against pre-commit's dprint-formatted
state, and (in the CI case) make it impossible to detect whether the matrix has
truly changed vs. just been re-stamped.

Also asserts that the committed artifact matches the generator's current output,
so the audit file in the repo can be trusted to reflect agent frontmatter state.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "audit_agent_compliance.py"
TOOL_MATRIX = REPO_ROOT / ".agents" / "AGENT-TOOLS.md"
COMPLIANCE_MATRIX = REPO_ROOT / ".agents" / "AGENT-COMPLIANCE-MATRIX.md"
REMEDIATION_BACKLOG = REPO_ROOT / ".agents" / "AGENT-REMEDIATION-BACKLOG.md"


def _run_generator() -> None:
    subprocess.run(
        ["uv", "run", "python", str(SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def preserve_audit_files():
    """Snapshot the audit files, restore them after the test so the working tree is unchanged."""
    files = (TOOL_MATRIX, COMPLIANCE_MATRIX, REMEDIATION_BACKLOG)
    snapshots = {p: p.read_bytes() for p in files if p.exists()}
    yield
    for p in files:
        if p in snapshots:
            p.write_bytes(snapshots[p])
        elif p.exists():
            p.unlink()


@pytest.mark.xdist_group("audit-agent-compliance")
@pytest.mark.skipif(shutil.which("dprint") is None, reason="dprint required for table alignment")
def test_generator_is_byte_idempotent(preserve_audit_files):
    """Running the generator twice must produce identical bytes."""
    _run_generator()
    first_tools = TOOL_MATRIX.read_bytes()
    first_compliance = COMPLIANCE_MATRIX.read_bytes()

    _run_generator()
    second_tools = TOOL_MATRIX.read_bytes()
    second_compliance = COMPLIANCE_MATRIX.read_bytes()

    assert first_tools == second_tools, "AGENT-TOOLS.md not byte-stable across re-runs"
    assert first_compliance == second_compliance, (
        "AGENT-COMPLIANCE-MATRIX.md not byte-stable across re-runs"
    )


@pytest.mark.xdist_group("audit-agent-compliance")
@pytest.mark.skipif(shutil.which("dprint") is None, reason="dprint required for table alignment")
def test_committed_artifact_matches_generator(preserve_audit_files):
    """The checked-in audit files must match what the generator currently emits.

    If this fails, regenerate with `uv run python scripts/audit_agent_compliance.py`
    and commit the updated artifacts.
    """
    committed_tools = TOOL_MATRIX.read_bytes()
    committed_compliance = COMPLIANCE_MATRIX.read_bytes()

    _run_generator()
    fresh_tools = TOOL_MATRIX.read_bytes()
    fresh_compliance = COMPLIANCE_MATRIX.read_bytes()

    assert fresh_tools == committed_tools, (
        "AGENT-TOOLS.md is stale; re-run scripts/audit_agent_compliance.py and commit."
    )
    assert fresh_compliance == committed_compliance, (
        "AGENT-COMPLIANCE-MATRIX.md is stale; re-run scripts/audit_agent_compliance.py and commit."
    )
