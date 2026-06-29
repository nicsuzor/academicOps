# Hook Client Translation — Spec & SSoT

> **State.** The single source of truth for how the Universal Hook Router translates
> between Claude Code, Gemini CLI, and Antigravity CLI (agy), and how the build keeps
> installed assets in sync with what the hooks expect. Per-gate forensic detail →
> [`specs/enforcement/GATES.md`](enforcement/GATES.md). Enforcement currency → [`specs/ENFORCEMENT-MAP.md`](ENFORCEMENT-MAP.md).

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

Contested cells are NOT guessed — they are filled from empirical measurement. Claude
USER-visibility cells are measured by the PTY harness (Test Layer C, `scripts/pty_hook_probe.py`
→ `tests/hooks/fixtures/pty_capabilities.json`). The agy cells were measured 2026-06-25 and
recorded in `tests/hooks/fixtures/client_capabilities.json`, which is now a **frozen record**:
its generating harness (`scripts/verify_hook_formats.py`) and the test that re-asserted it were
deleted 2026-06-26, so the agy values stand as recorded measurements, no longer test-guarded
(agy re-measurement is pending the Layer C agy port).

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

### Test layer C — PTY user-visibility harness (opt-in)

`scripts/pty_hook_probe.py` → `tests/hooks/fixtures/pty_capabilities.json`. Drives a REAL
INTERACTIVE `claude` inside a **tmux** pane (not `claude -p`), fires each candidate
hook-output shape with unique sentinels, and captures BOTH surfaces: the rendered pane
(`tmux capture-pane` = what the HUMAN sees) and the session transcript JSONL (what the
model received). Parameterized per `client` (Claude now; agy — which has its own
interactive TUI — added later via the same matrix shape, no schema change).

- **USER_SAW** (primary signal — the gap the old harness could not see) — sentinel rendered
  in the tmux pane = the HUMAN saw it. Measured for `SENTINELA` (advisory/reason channel)
  and `SENTINELB` (systemMessage/stopReason banner) independently, so a single probe proves
  whether the user sees ONE or BOTH payloads (e.g. warn mode renders BOTH `Stop says:` AND
  `Stop hook feedback:`).
- **AGENT_CTX** — sentinel injected into MODEL context: present in the `hookAdditionalContext`
  field (additionalContext channel) OR in a user/assistant message the model read (a blocking
  Stop `reason`). Authoritative for **Stop**. For **UPS/PreToolUse** additionalContext rides a
  `type:"attachment"` record — the SAME record that logs a user-only `systemMessage` — so it
  is structurally ambiguous there; for those events `AGENT_CTX` under-reports and the
  established C✓ comes from MODEL ECHO (invariant #14). The harness states this scope honestly
  rather than overclaiming.
- **IN_TRANSCRIPT** — sentinel anywhere in the transcript JSONL, INCLUDING raw
  hook-stdout `attachment`/`system` records (logged regardless of model visibility). "Shown in
  the agent transcript" literally — but NOT proof the model read it.

Output is committed as `pty_capabilities.json` — the empirical SSoT for user-visibility,
carrying per cell BOTH the measured signal AND each probe's CLAIMED audience. When Claude
changes its TTY rendering upstream, a signal flips. **This is what ends the guessing about
what the user sees.**

> **Coverage not yet re-added (after the headless Layer B deletion).** The PTY harness
> authoritatively measures USER-visibility (all events) and AGENT-context (Stop) for
> **Claude**. NOT yet ported from the deleted headless harness: (a) **agy** wire-acceptance +
> the `ephemeralMessage` real-plugin measurements (the agy rows below remain backed by the
> 2026-06-25 measurements recorded in prose, no longer by a live test); (b) `--resume`
> **persistence**; (c) PreToolUse **deny-blocks** verification; (d) a clean MODEL-ECHO
> agent-context lane for UPS/PreToolUse. Re-adding (a) and (d) to `pty_hook_probe.py` (agy has
> its own interactive TUI, driven identically) is the tracked follow-up — the matrix and
> fixture schema are already parameterized by `client` for it.
>
> **PreToolUse-deny user-visibility — capture gap, NOT U✗.** The `permissionDecisionReason`
> deny rows below are `U✓` on the basis of CLIENT DESIGN (Claude renders a denial toast) +
> `router.py` — they are NOT contradicted by the PTY fixture even though its
> `pretool-deny-reason` cell records `user_saw_a=false`. That `false` is a CAPTURE GAP: the
> denial toast is transient and scrolled out of the pane before the post-quiescence snapshot
> (the cell carries this in `measurement_caveats`; `agent_ctx_a=true` proves the hook fired
> and the reason reached the model). So PreToolUse-deny **U is design-asserted, not
> PTY-captured** — do not read it as PTY-proven, and do not downgrade it to U✗.

## Payload Routing Flowchart

```mermaid
flowchart TD
    A[Gate / Hook] -->|system_message| B{Target Client}
    A -->|context_injection| B

    B -->|Claude| C1(systemMessage / permissionDecisionReason)
    B -->|Claude| C2(additionalContext)

    B -->|Gemini| G1(reason / systemMessage)
    B -->|Gemini| G2(additionalContext)

    B -->|Agy| A1(denyReason / reason)
    B -->|Agy| A2(ephemeralMessage)

    C1 -.-> U1((User Terminal))
    G1 -.-> U1
    C2 -.-> A3((Agent Context))
    G2 -.-> A3
    A1 -.-> A3
    A2 -.-> A3
```

> **State Mapping.** The extensive mapping tables detailing exact payload routing have been consolidated into the unified macro matrix in [`../ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) to preserve Single Source of Truth. Please refer to that document for exact rule-to-mechanism routing logic.

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
