# aops-jr

Head-persona package (`jr`/`ida`).

As of `epic_725fd517` (v0.5 topology relocation), **the live `polecat` dispatch CLI and the `/dispatch` skill have moved into `aops` core** (`aops/polecat/` and `aops/skills/dispatch/`). The `polecat` dispatch CLI no longer lives in this package.

`aops-jr` is rescoped to hold the head persona definitions (`agents/ida.md`, `agents/junior.md`) and templates awaiting the standalone face-plugin extraction (`epic_be1e4465`).

## Contents

- [`agents/`](agents/) — persona charters for Ida and Junior.
- [`templates/`](templates/) — head-persona templates (`honesty.md`, `verify.md`).

`debug` (`.agents/skills/debug/SKILL.md`) intentionally stays a framework-dev-only tool in `.agents/skills/` — maintainer tooling, not a coordinator operation.
