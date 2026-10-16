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
            if any(
                str(s.get("uses", "")).startswith("anthropics/claude-code-action") for s in steps
            ):
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
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    assert ids.index("otel") < first_agent


@pytest.mark.parametrize(("workflow", "job", "steps"), AGENT_JOBS)
def test_every_agent_step_takes_the_otel_settings(workflow, job, steps):
    for step in steps:
        if str(step.get("uses", "")).startswith("anthropics/claude-code-action"):
            assert str(step["with"].get("settings", "")).startswith(
                "${{ steps.otel.outputs.settings"
            ), f"{workflow}:{job}:{step.get('name')}"


@pytest.mark.parametrize(("workflow", "job", "steps"), AGENT_JOBS)
def test_agent_job_checks_tracer_status_after_the_agent(workflow, job, steps):
    last_agent = max(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    status_steps = [
        s
        for i, s in enumerate(steps)
        if i > last_agent and "tracer_error" in str(s.get("run", ""))
    ]
    assert status_steps, f"{workflow}:{job} has no step checking tracer_error after the agent"
    for s in status_steps:
        assert s.get("if") == "always()", f"{workflow}:{job} tracer status check step must run if: always()"
        assert "::warning::" in s.get("run", ""), f"{workflow}:{job} tracer status check step must emit a ::warning::"
