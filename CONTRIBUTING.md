# Contributing

For people developing academicOps itself. Installing it for your own work starts
at [`README.md`](README.md).

## Setup

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync
make install-dev   # build, install the local marketplace, activate pre-commit
```

## Before you change anything

Read [`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md) -- it is authoritative for
the layout, the plugin boundaries, and the constraints on both. Then
[`.agents/CORE.md`](.agents/CORE.md) for the rules that bind agents and people
working in this repository.

## Checks

```bash
make test     # uv run pytest tests/
make lint     # ruff check
make format   # ruff format + dprint fmt
make build    # must assemble every plugin for both clients without error
```

Run `make format` before committing. Pre-commit runs `dprint fmt` over markdown,
JSON, and TOML files; and `uv run ruff format` / `uv run ruff check --fix` for Python files.

## Branch, merge and release rules (v1 feature freeze)

academicOps v1 is under **feature freeze** (see announcement [#3206](https://github.com/nicsuzor/academicOps/issues/3206)).

- **Target branch**: until `release/v1.0-rc0` is merged, all academicOps work, hotfix releases included, targets `release/v1.0-rc0`.
- **New features and big changes**: the freeze blocks new features and big changes. Develop new features on a dedicated feature branch and open a pull request targeting `release/v1.0-rc0`. Merging new features or large changes into `release/v1.0-rc0` requires the user's explicit approval.
- **Hotfixes**: merge straight to `release/v1.0-rc0` once all CI checks are green, after an initial review check confirms the change is genuinely a hotfix. Hotfixes must be clearly labelled (`hotfix`) so that release-please bumps only the patch version and automatically publishes a new release build with no approval required.
- **Everything else**: waits for the user's approval before merging and releasing. Non-hotfix changes yield no automatic release.

## Pull requests

During the v1 feature freeze, open pull requests against `release/v1.0-rc0` (superseding `dev` until `release/v1.0-rc0` merges). Structure the body as a reviewer-decision aid -- the sections
are pre-filled from
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Releases are cut by release-please on `release/v1.0-rc0`; `CHANGELOG.md` is generated, never
hand-edited.
