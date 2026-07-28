# aops-jr

Head-persona package (`jr`/`ida`).

As of `epic_725fd517` (v0.5 topology relocation), **the live `polecat` dispatch CLI and the `/dispatch` skill have moved into `aops` core** (`aops/polecat/` and `aops/skills/dispatch/`). The `polecat` dispatch CLI no longer lives in this package.

`aops-jr` is rescoped to hold the head persona definitions (`agents/ida.md`, `agents/junior.md`), face-discipline hook router (`hooks/router.py`), and process gates (`hooks/gates/`).

## Installation & Quickstart

`aops-jr` is an optional plugin providing face discipline and interactive reminders for the head personas (`ida` / `junior`).

### Claude Code

Install from the `academicOps` marketplace:

```bash
claude plugin install aops-jr@academicOps
```

### Antigravity (`agy`)

Install from local build:

```bash
agy plugin install ./dist/aops-jr-antigravity
```

## Contents

- [`agents/`](agents/) — persona charters for Ida and Junior.
- [`templates/`](templates/) — head-persona templates (`honesty.md`, `verify.md`).
- [`hooks/`](hooks/) — face-discipline hook router and gate dispatch.

`debug` (`.agents/skills/debug/SKILL.md`) intentionally stays a framework-dev-only tool in `.agents/skills/` — maintainer tooling, not a coordinator operation.
