"""Every claude-code-action step in this repo's workflows is traced to Phoenix.

The tracing contract (scripts/ci_otel_hooks.py): a step with id ``otel`` runs
the script before the agent, never fails the job, and the agent step takes its
``settings`` output.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


def _agent_jobs():
    for path in WORKFLOWS:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_name, job in (doc.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any(str(s.get("uses", "")).startswith("anthropics/claude-code-action") for s in steps):
                yield pytest.param(path.name, job_name, steps, id=f"{path.name}:{job_name}")


AGENT_JOBS = list(_agent_jobs())


def test_agent_jobs_found():
    assert len(AGENT_JOBS) >= 8


@pytest.mark.parametrize(("workflow", "job", "steps"), AGENT_JOBS)
def test_agent_job_configures_otel_before_the_agent(workflow, job, steps):
    ids = [s.get("id") for s in steps]
    assert "otel" in ids, f"{workflow}:{job} has no otel step"
    otel = steps[ids.index("otel")]
    assert "ci_otel_hooks.py" in otel["run"]
    assert otel.get("continue-on-error") is True
    first_agent = next(
        i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    assert ids.index("otel") < first_agent
    assert otel["env"]["GENAI_ENGINE_API_KEY"] == "${{ secrets.GENAI_ENGINE_API_KEY }}"
    assert otel["env"]["GENAI_ENGINE_TRACE_ENDPOINT"] == "${{ vars.GENAI_ENGINE_TRACE_ENDPOINT }}"


@pytest.mark.parametrize(("workflow", "job", "steps"), AGENT_JOBS)
def test_every_agent_step_takes_the_otel_settings(workflow, job, steps):
    for step in steps:
        if str(step.get("uses", "")).startswith("anthropics/claude-code-action"):
            assert step["with"].get("settings") == "${{ steps.otel.outputs.settings }}", (
                f"{workflow}:{job}:{step.get('name')}"
            )


def _reusable(path: Path) -> dict | None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on = doc.get(True) or doc.get("on") or {}
    return on.get("workflow_call") if isinstance(on, dict) else None


@pytest.mark.parametrize("workflow", sorted({p.values[0] for p in AGENT_JOBS}))
def test_reusable_agent_workflows_accept_the_otel_secret(workflow):
    call = _reusable(REPO_ROOT / ".github" / "workflows" / workflow)
    if call is None:
        pytest.skip("not a reusable workflow")
    secret = (call.get("secrets") or {}).get("GENAI_ENGINE_API_KEY")
    assert secret is not None
    assert secret.get("required") is False
