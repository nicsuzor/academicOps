# Hook Client Translation — Spec & SSoT

> **State.** The single source of truth for how the Universal Hook Router translates
> between Claude Code, Gemini CLI, and Antigravity CLI (agy), and how the build keeps
> installed assets in sync with what the hooks expect. Per-gate forensic detail →
> [`specs/GATES.md`](../GATES.md). Enforcement currency → [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).

## Problem this solves

Per-client hook knowledge (event names, output-channel rules, field names, tool names,
config shapes) was duplicated across `router.py`, `scripts/build.py`,
`scripts/transforms/*`, and `lib/tool_categories.py` as inline prose with **no single
source of truth and no cross-client conformance test**. Each client's hook API is new,
sparsely documented, and changes upstream. Result: ~20 regressions in three weeks —
wrong wire fields, silent verdict drops, tool calls unrecognised on one surface, gate
advisories delivered to the user instead of the agent.

## Design: two SSoT tables + thin renderers + two test layers

### Table 1 — Client/event channel spec (`aops-core/hooks/client_spec.py`)

Pure-python (no heavy deps so the build can import it). One record per
`(client, internal_event)`:

| field              | meaning                                                                           |
| ------------------ | --------------------------------------------------------------------------------- |
| `wire_event`       | event name on the wire (e.g. internal `UserPromptSubmit` → agy `PreInvocation`)   |
| `config_shape`     | `wrapper` (matcher/hooks[]) · `flat` (bare handler list) · `claude`               |
| `can_block`        | does this event express a deny/block?                                             |
| `agent_channel`    | how `context_injection` reaches the AGENT (field path / injectStep kind / `None`) |
| `user_channel`     | how `system_message` reaches the USER (field / `None`)                            |
| `block`            | wire expression of deny/ask                                                       |
| `timeout_floor_ms` | per-(client,event) cold-start floor (agy PreToolUse = 15000)                      |

Drives BOTH the runtime renderers AND the build's `hooks.json` generation. The
event-name map (both directions) lives here ONCE — replacing the three divergent copies
(`router.GEMINI_EVENT_MAP`, `build.CLAUDE_TO_GEMINI_EVENTS`, `transforms/hooks.py`).

Contested cells are NOT guessed — they are filled from the **live conformance harness**
(below) and pinned in `tests/hooks/fixtures/client_capabilities.json`.

### Table 2 — Tool registry (`lib/tool_registry.py`, extends `lib/tool_categories.py`)

One record per ABSTRACT tool: `canonical`, `category`
(read/write/spawn/destructive/skill), and the per-client concrete name. Drives BOTH the
build's text/frontmatter rewriting (replacing `tool_translation.py` and the agent maps)
AND runtime recognition (`extract_subagent_type`, `SPAWN_TOOLS`, sentinel, enforcer).
Fixes the agy gap: agy's vocabulary (`view_file`, `run_command`, `invoke_subagent`, …)
is currently unknown at runtime, so sentinel/enforcer/spawn matching silently fails on agy.

### Renderers (thin, structural only)

`render_claude` / `render_gemini` / `render_agy` read Table 1 and map
`CanonicalHookOutput(verdict, system_message, context_injection)` → the wire dict. Policy
(which channel, can-block, field names) is DATA; only the structural nesting is code.

### Test layer A — unit matrix (fast, CI, deterministic)

`run_router(client, event, payload)` unified fixture + per-client **interpreter**
`interpret(client, event, output) -> Delivered(agent_sees, user_sees, blocked, accepted)`
mirroring how each real client consumes output (the agy accept-contract is the agy
interpreter). ONE parametrized `(client × event × scenario)` matrix asserts the router
conforms to Table 1 and that the core invariants hold. **No per-client test bodies.**

Core invariants:

- **A. accepted** — output validates against the client's schema / protojson accept-contract.
- **B. injection reaches agent** — `context_injection` present ⇒ `agent_sees` contains it,
  OR Table 1 says no agent channel ⇒ router blocked-to-deliver (if `can_block`) or
  dropped-with-logged-warning. _This is the property that keeps regressing._
- **C. verdict fidelity** — deny ⇒ blocked; allow ⇒ not blocked (agy: allow ≠ `{}`).
- **D. no leak** — `system_message` only on user channels; advisory never on a user-only field.

### Test layer B — live conformance harness (opt-in / scheduled)

`scripts/verify_hook_formats.py` + `tests/hooks/test_live_conformance.py`
(`@live @slow`, skip-if-client-unavailable). Parametrized over
`(client × event × candidate_shape × scenario)`. Per cell: install a probe hook emitting
the candidate shape with a unique sentinel in the agent channel; run the client headless;
ask the model to echo any system/context instruction it received. Records three signals:
**ACCEPTED** (no client error), **AGENT_SAW** (model echoed the sentinel — delivery proven
by MODEL ECHO, never transcript grep), **BLOCKED** (deny actually blocked / stop re-entered).
Output is committed as `client_capabilities.json` — the empirical SSoT. When a client
changes upstream, a signal flips and this test goes red. **This is what ends the guessing.**

## Authoritative channel matrix (live docs + to be confirmed by harness, 2026-06-25)

See `client_spec.py` for the machine-readable form. Key facts:

- **agy has NO hidden agent-only channel** — injected steps are user-visible; only knob is
  `userMessage` (persistent) vs `ephemeralMessage` (transient) + `<details>` collapse.
- **agy PreToolUse** docs = `decision`/`reason`/`permissionOverrides`; verified-live =
  top-level `allowTool`/`denyReason`. Binary descriptor has BOTH. Harness decides; until
  then emit both consistent (belt-and-suspenders) — `{}` is NEVER allow (omitted bool=false).
- **agy Stop** = `{decision:"continue", reason}`; **PostInvocation** =
  `{injectSteps, terminationBehavior:"force_continue"|"terminate"}`. Enables the agy hard
  stop-block (handover) that is a silent no-op today.
- **Claude Stop** (2.1.191) docs = accepts `hookSpecificOutput.additionalContext` without
  blocking. If the harness confirms, the qa/handover/ida force-block-on-first workaround
  retires by flipping ONE table cell.

## Regression-avoidance invariants (24) — encoded as permanent test anchors

The hard-won invariants from three weeks of agy fixes. Full list with WHY in the PR / git
history; the load-bearing ones:

1. agy rejects unknown protojson fields → only documented fields; never `metadata`.
2. agy PreToolUse allow = explicit `{"allowTool":true}`; `{}` = deny.
3. `allowTool`/`denyReason` top-level, never nested in `permissionOverrides` (repeated list).
4. agy PostToolUse / unmapped event = `{}` only.
5. injectSteps `userMessage`/`ephemeralMessage` are SCALAR strings; prefer `ephemeralMessage`.
6. PreInvocation/PostInvocation tolerate `short_reason` — never raise.
7. Claude `hookSpecificOutput` only for {PreToolUse, UserPromptSubmit, PostToolUse, PostToolBatch} (+Stop iff harness-verified).
8. agy `toolCall`/`error` at ROOT of stdin; root-first extraction.
9. agy flat handler list for PreInvocation/PostInvocation/Stop; wrapper only for Pre/PostToolUse.
10. agy PreToolUse timeout floor ≥ 15000ms.
11. substitute `${CLAUDE_PLUGIN_ROOT}` for agy; agy agent bodies use Claude tool names.
12. never `--dangerously-skip-permissions` on agy; `AOPS_AGY_CLIENT` worker posture; Stop never worker-skipped.
13. plugin dir FRONT of sys.path; provider from `--client`; prebake venv (staging + runtime registry).
14. verify agy injection by MODEL ECHO not transcript grep; test SEMANTIC verdict not literal dict.
15. cowork ships NO hooks.

## Phasing (regression-safe)

- **P0** unit-matrix safety net (router vs table, current behavior) + live conformance harness.
- **P1** SSoT tables (`client_spec.py`, `tool_registry.py`); router reads them; output byte-identical.
- **P2** renderers become thin table-driven functions.
- **P3** build imports the SSoT; delete orphaned `transforms/` duplicates; regen dist.
- **P4** corrections (each = one table-cell flip, harness-driven): agy PreToolUse format,
  agy hard stop-block, Claude Stop inject retirement.
- **P5** ENFORCEMENT-MAP row; update `specs/GATES.md` + `aops-core/skills/aops/references/hooks.md`; cleanup; PR.
