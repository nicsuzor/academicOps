#!/usr/bin/env python3
"""Shared fixtures and constants for polecat e2e tests."""

from pathlib import Path

import yaml

# Known-stable fallback parent under the aops project: an active "Framework
# maintenance and tooling improvements" epic with mixed scratch children.
# Can be overridden via POLECAT_E2E_PARENT.
_DEFAULT_AOPS_SCRATCH_PARENT = "task-0d77545a"


def write_polecat_test_config(
    tmp_path: Path,
    *,
    home_dir: Path,
    project_paths: dict[str, Path],
    crew_names: list[str] | None = None,
    extra_registry_keys: dict | None = None,
    project_extras: dict[str, dict] | None = None,
) -> Path:
    """Write a portable polecat.yaml + machine-local local.yaml for tests.

    The unified polecat.yaml carries both the project registry (consumed by
    polecat/manager.py) and the operational session config (consumed by
    aops-core/lib/polecat_config.py).

    Returns the sessions_dir; callers must set AOPS_SESSIONS=<sessions_dir> in env.
    """
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    projects_block = {}
    for slug in project_paths:
        entry = {"default_branch": "main"}
        if project_extras and slug in project_extras:
            entry.update(project_extras[slug])
        projects_block[slug] = entry

    registry: dict = {
        "session_defaults": {
            "hooks_enabled": True,
            "model": "claude-sonnet-4-6",
            "debug": False,
            "gates": {
                "handover": "warn",
                "qa": "warn",
                "enforcer": "warn",
                "commit": "warn",
                "hydration": "off",
                "enforcer_threshold": 50,
            },
        },
        "crew_defaults": {},
        "run_defaults": {},
        "docker": {"image": "aops-crew"},
        "external_agents": {},
        "projects": projects_block,
    }
    if crew_names:
        registry["crew_names"] = crew_names
    if extra_registry_keys:
        registry.update(extra_registry_keys)

    (sessions_dir / "polecat.yaml").write_text(yaml.dump(registry))

    home_dir.mkdir(parents=True, exist_ok=True)
    overlay = {"paths": {slug: str(path) for slug, path in project_paths.items()}}
    (home_dir / "local.yaml").write_text(yaml.dump(overlay))

    return sessions_dir
