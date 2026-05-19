# ADR: Gate Config Env-Var Policy and Fresh-Install Defaults

**Status**: Accepted\
**Date**: 2026-05-19\
**Task**: aops-8259ab90

## Context

`hooks/gate_config.py` resolves gate modes lazily from `polecat.yaml` via
`lib/polecat_config.py`. The original comment read:

> "There are no environment-variable fallbacks: missing config hard-fails (A14, A16)."

Two problems surfaced:

1. **Stale env-var exports** — the sandbox shell had `HANDOVER_GATE_MODE`,
   `CUSTODIET_GATE_MODE`, `HYDRATION_GATE_MODE` set from an old bootstrap in
   `~/src/sessions/hooks/`. These contradicted the YAML truth and misled an
   agent that ran `env | grep GATE` expecting to see live config values. They are
   fiction: `gate_config.py` does **not** read them; it reads YAML.

2. **Fresh-install hard-fail** — a user installing the `aops-core` plugin on a
   machine without `$AOPS_SESSIONS/polecat.yaml` hit a Python `RuntimeError`
   traceback before any guidance was shown.

## Options considered

### Option 1 — Hard-fail with bootstrap guidance

Keep the hard-fail but emit an actionable error pointing at a `polecat init`
command that writes a baseline `polecat.yaml`; plugin install runs it
automatically.

**Rejected**: `polecat init` initialises bare repo mirrors, not config files.
Building a separate `polecat init --config` subcommand was out of scope and
would require validating that plugin install hooks it correctly — more moving
parts for the same onboarding outcome.

### Option 2 — Bake defaults into the code ✓ CHOSEN

`polecat_config.py` falls back to a hard-coded `BUILTIN_SESSION_DEFAULTS` when
no YAML is found (all gates `warn`, hydration `off`, threshold 50). YAML
overrides but isn't required.

### Option 3 — Env-var fallback

Wire the stale exports (`HANDOVER_GATE_MODE` etc.) through to actual gate
resolution.

**Rejected explicitly**: creates two config sources for the same value
(violates A16 DRY). The env vars are documented as "Removed" in
`polecat/defaults/polecat.yaml.example`. Keeping them would make `env | grep
GATE` look authoritative again.

## Decision

**Option 2** — baked defaults in code.

## Rationale

- A14 (fail-fast) applies to a config that is present but broken, not to a
  missing config on a fresh machine. A missing `polecat.yaml` on a fresh install
  is expected, not an error.
- A16 (DRY, no silent defaults) is satisfied: the fallback is documented,
  visible (stderr warning), and always overridden by explicit YAML — it is never
  silently preferred.
- The alternative (requiring a bootstrap command) defers the problem to a
  command that doesn't yet exist.

## What changes

### `aops-core/lib/polecat_config.py`

- `BUILTIN_GATES` and `BUILTIN_SESSION_DEFAULTS` constants document the fallback
  values explicitly.
- `load_polecat_config()` catches two "no config" cases and returns
  `_builtin_config()` with a stderr warning instead of raising:
  1. Neither `$AOPS_POLECAT_CONFIG` nor `$AOPS_SESSIONS` is set.
  2. The env-resolved path does not exist.
- Explicit-path callers (tests passing `path=...`) still hard-fail if the file
  is missing (programming error, not a fresh-install scenario).
- A file that **exists but is malformed** still hard-fails (A14 intact).

### `tests/hooks/conftest.py`

Removed stale `os.environ.setdefault("HANDOVER_GATE_MODE", ...)` calls. They
had no effect (gate_config.py ignores those env vars) and were misleading.
Updated comment to document the actual config mechanism.

### `tests/hooks/test_gate_context_injection.py`, `test_handover_gate_latch.py`, `test_handover_gate_regression.py`

Removed `monkeypatch.setenv("HANDOVER_GATE_MODE", ...)` calls in fixtures. Same
reason: gate_config.py does not read those env vars. The tests passed with or
without them because their assertions check `verdict != ALLOW`, which is true
for both `warn` and `block` modes.

## Fresh-install behaviour after this change

A user who installs `aops-core` on a machine without `$AOPS_SESSIONS` or
`polecat.yaml`:

- Gets working gates (all `warn`) — no traceback.
- Sees a stderr warning explaining what's missing and where to find the example
  file.
- Can configure their setup by copying `polecat/defaults/polecat.yaml.example`
  to `$AOPS_SESSIONS/polecat.yaml`.

## Stale env-var exports

The stale `HANDOVER_GATE_MODE` / `CUSTODIET_GATE_MODE` / `HYDRATION_GATE_MODE`
exports in `~/src/sessions/hooks/` (the user's sessions repo, not this repo) are
**fiction**: gate_config.py has never read them since the YAML migration. They
should be deleted from the sessions repo's bootstrap hooks. The canonical
reference for which env vars are still live vs removed is the inventory table at
the bottom of `polecat/defaults/polecat.yaml.example`.

`AOPS_HOOK_LOG_PATH` and `AOPS_GATE_FILE_<NAME>` are session-scoped env vars set
by the SessionStart hook — they are real and correct. Only the gate-mode vars are
stale.
