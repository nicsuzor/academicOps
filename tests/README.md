---
title: Framework Testing
type: spec
permalink: framework-testing
description: Comprehensive test suite for the academicOps framework
tags:
  - testing
  - framework
  - automation
---

# Framework Testing

Test suite for the academicOps (aOps) core package (`aops/`). Sibling plugins
(`aops-jr/`, `reflexes-cope/`) carry their own `tests/` directories, listed
alongside this one in `testpaths` (see [Test Configuration](#test-configuration)).

## Test Organization

```
tests/
├── conftest.py                          # Shared fixtures (paths, headless-exec helpers)
├── paths.py                             # Path resolution utilities
├── test_plugin_manifests.py             # Built-plugin validation: manifest schema,
│                                         #   hooks.json script paths, Dockerfile COPY
│                                         #   sources vs .dockerignore
├── test_router.py                       # aops/hooks/router.py (SessionStart credential
│                                         #   isolation, PreToolUse gate dispatch)
├── hooks/
│   ├── conftest.py                      # Puts aops/hooks on sys.path (`import gates`)
│   └── test_require_aops_bot_gh_token.py # Fail-closed git/gh push gate
├── polecat/                             # Regression tests for aops/polecat/cli.py
│   ├── test_cli_seed_verification.py    #   -t <task> seed-verification fail-fast path
│   ├── test_delivery_guard.py           #   uncommitted/unpushed-work delivery guard
│   ├── test_setup_staging.py            #   Gemini settings staging
│   └── test_workspace_isolation.py      #   worktree/workspace isolation
├── transcripts/                         # aops/lib/transcripts/* adapter + domain tests
│   ├── test_agy_adapter.py
│   ├── test_claude_adapter.py
│   ├── test_domain.py
│   ├── test_regressions.py
│   └── test_sync.py
└── harness/                             # Artifact dropbox for agent-driven `polecat run`
    └── README.md                        #   probes; no test files. See its own README.
```

Some built-artifact-dependent tests (e.g. in `test_plugin_manifests.py`) skip
when `dist/` hasn't been built yet — run `make build-dev` first to exercise them.

## Running Tests

```bash
uv run pytest tests/
```

Runs the full default set per [Test Configuration](#test-configuration) below
(parallelized, `slow`/`integration`/`demo` deselected by default).

### Specific files or directories

```bash
uv run pytest tests/test_plugin_manifests.py -v
uv run pytest tests/polecat/ -v
uv run pytest tests/hooks/test_require_aops_bot_gh_token.py -v
```

### By marker

```bash
uv run pytest tests/ -m slow           # slow tests only
uv run pytest tests/ -m integration    # integration tests only
uv run pytest tests/ -m metrics -s -n 0  # observability/metrics tests, unparallelized
uv run pytest tests/ -m live           # drives a real headless client; skips if unavailable
uv run pytest tests/ -m e2e            # requires POLECAT_E2E=1 and live infra
```

## Test Configuration

Configured in `pyproject.toml` (`[tool.pytest.ini_options]`):

- `testpaths`: `tests`, `aops/tests`, `aops-jr/tests`, `reflexes-cope/tests` — this
  directory is one of several test roots pytest collects in a single run.
- `pythonpath`: includes `aops/hooks` (so `hooks/` tests can `import gates`
  directly, the same way the plugin hook scripts do at runtime) and the other
  plugin roots' `hooks/`/`lib/` dirs.
- `addopts`: `-n 16 --dist loadgroup -m 'not slow and not integration and not demo'`
  — parallelized by default, with `slow`/`integration`/`demo` deselected unless
  explicitly requested via `-m`.
- `markers`: `slow`, `integration`, `metrics`, `demo`, `e2e` (requires
  `POLECAT_E2E=1`), `live` (drives a real headless client, skips if unavailable).

Check `pyproject.toml` directly for the current values — this section
summarizes it, and pytest config is the source of truth if the two disagree.

## Philosophy

Following the framework's fail-fast axioms:

1. Tests fail immediately with clear error messages — no silent failures or
   workarounds.
2. A test produces a definitive pass/fail. If infrastructure is missing, the
   test should fail, not silently skip (built-artifact-dependent tests are the
   sanctioned exception — see [Test Organization](#test-organization)).
3. Regression tests document the defect they close in their docstring
   (see `tests/polecat/*.py`, `tests/transcripts/test_regressions.py`,
   `test_plugin_manifests.py`'s hooks.json and Dockerfile guard tests) so a
   later reader knows why the test exists, not just what it asserts.
