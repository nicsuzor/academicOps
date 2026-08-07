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

Read [`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md) — it is authoritative for
the layout, the plugin boundaries, and the constraints on both. Then
[`.agents/CORE.md`](.agents/CORE.md) for the rules that bind agents and people
working in this repository.

## Checks

```bash
make test     # uv run pytest tests/
make lint     # ruff check
make format   # ruff format + dprint fmt
make build    # must assemble every plugin for both clients without error
make docker   # build the crew worker image
```

Run `make format` before committing. Pre-commit runs `dprint fmt` over markdown,
JSON, and TOML files; and `uv run ruff format` / `uv run ruff check --fix` for Python files.

## Pull requests

Open against `dev`. Structure the body as a reviewer-decision aid — the sections
are pre-filled from
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Releases are cut by release-please on `dev`; `CHANGELOG.md` is generated, never
hand-edited.
