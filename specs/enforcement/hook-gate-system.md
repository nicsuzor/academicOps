---
id: enforcement-hook-gate-system
title: Hook & Gate System — Function-per-Gate
type: spec
status: ready
tags: [enforcement, hooks, gates, framework-architecture]
---

# Hook & Gate System — Function-per-Gate

## What this replaces

v0.3's hook/gate subsystem was gutted on `dev` as too complicated (see [enforcement.md#retired](enforcement.md#retired)). A later plan to recover its "elegant kernel" wholesale failed review: the real dependency closure was measured at ~5,900 lines, welded to a `session_state ↔ definitions` import cycle, a template registry, per-client dialect modules, and env-var plumbing. That recovery plan is not carried forward.

This document describes the system actually shipped instead: a new, small implementation that keeps the one genuinely elegant idea — gate → single verdict merge → gate-as-unit — and throws out everything that made v0.3 heavy.

## The core idea: a gate is a function, not a data schema

v0.3's complexity tax came from a declarative condition DSL (`GateCondition`, ~15 matcher fields) plus `custom_check`/`custom_action` escape hatches needed because the DSL couldn't express everything. At two to five gates that indirection is pure overhead. A gate is a plain Python function:

```python
def require_subagent_model(e: Event, state: dict) -> Verdict | None:
    if e.event == "PreToolUse" and e.tool == "Agent":
        tool_input = e.raw.get("tool_input") or {}
        if tool_input.get("subagent_type") != "fork" and not tool_input.get("model"):
            return warn("Dispatching a subagent without an explicit model.")
    return None
```

The function IS the condition — reads top to bottom, full expressiveness, no escape hatch, trivially testable with a fake event. Every gate takes the same two arguments (`Event`, `state`); stateless gates simply ignore `state`.

## Components

Source: [`aops/hooks/gates/`](../../aops/hooks/gates/) and [`aops/hooks/gate_dispatch.py`](../../aops/hooks/gate_dispatch.py).

### Verdict (`gates/verdict.py`)

Three outcomes: **allow** (a gate returns `None`), **warn(message)** (non-blocking, injects context), **deny(reason)** (blocks). One merge rule, `deny > warn > allow`, applied across every gate's result for the event; ties at the same outcome keep the first verdict seen, so registry order is a stable tiebreak. ~30 lines, no class hierarchy.

### Event (`gates/event.py`)

The small, normalized shape every gate reads: `event` (the raw `hook_event_name`), `tool`, `command`, `session_id`, and `raw` (the untouched stdin JSON, for anything not worth promoting to a named field). `normalize(raw_json) -> Event` is the only translation step.

### The gate list (`gates/registry.py`)

```python
GATES = [
    require_subagent_model,
    exit_reflection_reminder,
]
```

The list **is** the registry. Registering a new gate means writing a function and appending it — no registry class, no discovery magic, no decorator plumbing.

### State (`gates/state.py`)

Most gates are stateless. For the "did the agent already do X this session" shape, one helper: `load(session_id) -> dict`, mutate the dict in place, `save(session_id, state)`. Storage is one JSON file per session under a temp directory (overridable via `AOPS_GATE_STATE_DIR`, mainly for test isolation). ~20 lines. No `SessionState` module, no naming/paths subsystem, no import cycle — the thing that sank v0.3's recovery. Stateful gates take `state` as an argument and mutate it; stateless gates take the same argument and ignore it.

### The dispatcher (`gate_dispatch.py`)

One script: read stdin JSON → `normalize()` into an `Event` → a structural self-loop guard (below) → `load()` session state → run every gate in `GATES`, each isolated in its own try/except → `merge()` the results → `save()` state → `emit()` the client's wire format. Printing nothing is a no-op.

**Exception isolation.** Each gate call is wrapped individually (`_run_gate`), not the whole loop in a bare list comprehension. Fail policy for a safety system: a gate that raises is fail-**safe** — its own verdict is skipped (the exception is reported to stderr, not swallowed silently) but every other gate still runs and still merges normally, including any legitimate `deny`. One gate blowing up must never crash the process or discard another gate's verdict.

**Self-loop guard.** For `Stop` and `SubagentStop`, the dispatcher checks the raw payload's `stop_hook_active` field _before_ running any gate. If true, it returns immediately: no gate runs, no state is touched, nothing is printed. This is a dispatcher-level guard, not a per-gate one, so every current and future `Stop`/`SubagentStop` gate is protected without having to remember to check it itself — this is the exact self-loop bug that hit `router.py` on 2026-07-13.

A raising gate no longer propagates and non-zero-exits the interpreter — `main()` catches it per-gate and returns `0` regardless. Blocking, where it happens, is expressed in the JSON payload per the wire contract below, not via a hook exit code.

### The emit adapter (`gates/emit.py`)

`emit(verdict, event, client) -> dict`. One small function with a branch per client — not a framework, not a translation DSL. Two clients are wired today:

- **`claude`** — fully implemented, confirmed against current Claude Code hook documentation (see [Wire contract](#wire-contract) below).
- **`agy`** (Antigravity) — the non-blocking context-injection shape is confirmed (it matches the existing pattern already in [`aops/hooks/router.py`](../../aops/hooks/router.py)'s `PreInvocation`/`PostInvocation` handling: `{"injectSteps": [{"ephemeralMessage": ...}]}`). agy has no confirmed equivalent of Claude's `permissionDecision: "deny"` block. Until that's resolved, a `deny` verdict on the agy branch degrades to the same context-injection shape as `warn`, marked with a `TODO(agy-deny-format)` comment, rather than guessing at an unconfirmed schema. Tracked as a follow-up.

Adding a third client means adding one more branch to `emit()`, not a new subsystem.

## Wire contract

Confirmed against current Claude Code hook documentation. The mapping is **per event**, not per client:

- **`PreToolUse` deny** → `hookSpecificOutput.permissionDecision: "deny"` + `hookSpecificOutput.permissionDecisionReason`.
- **Any other event, deny** (`Stop`, `PostToolUse`, …) → top-level `decision: "block"` + `reason`.
- **`warn`, any event** → `hookSpecificOutput.additionalContext` (non-blocking; the agent sees the message but is not stopped).
- **`allow`** (verdict is `None`) → no stdout output at all.

`exit 2` is a separate, coarser blocking path Claude Code also supports (stderr becomes the agent's feedback) — this system does not use it; every decision is expressed as structured JSON on stdout.

## Registration

Registered in the plugin's hook manifest source, [`aops/templates/hooks.template.json`](../../aops/templates/hooks.template.json) (compiled to `hooks/hooks.json` per-client at build time by `scripts/build.py`), using exec form — `command` and `args` as separate fields, not a `bash -c '...'` string — so `${CLAUDE_PLUGIN_ROOT}` path substitution needs no manual quoting:

```json
{
  "type": "command",
  "command": "uv",
  "args": [
    "run",
    "python",
    "${CLAUDE_PLUGIN_ROOT}/hooks/gate_dispatch.py",
    "claude"
  ]
}
```

`gate_dispatch.py` is registered once per Claude Code event it needs to see (`PreToolUse`, `Stop`) — it is the same script and the same `GATES` list both times; only the client argument (`claude`) is fixed at registration, since the dispatcher itself doesn't need to know which event fired ahead of time — `hook_event_name` arrives on stdin and each gate self-filters on `e.event`. It is the only `Stop`-time hook: `router.py`'s former Stop reminder branch was consolidated into the `exit_reflection_reminder` gate (2026-07-23, task `aops_cace51f9`), so `router.py` no longer registers on `Stop` at all.

## The two shipped gates

Exactly two, chosen to prove the stateless and stateful shapes end-to-end — not a target catalogue size:

1. **`require_subagent_model`** (`gates/require_subagent_model.py`, stateless) — warns (non-blocking `additionalContext`) on `PreToolUse` when `tool_name == "Agent"` and the structured `tool_input.model` field is absent (forked agents, `subagent_type == "fork"`, are exempt — they always inherit the parent's model). Keyed purely off structural fields already present on every hook payload (event type, tool name, a structured input field's presence) — no command-string or content sniffing, no destructive-verb matching. Enforces a documented framework practice (dispatch subagents with an explicit cheap model for routine work) the same way `router.py`'s real handlers key off structured fields like `tool_name` and `background_tasks` length rather than parsing free text.
2. **`exit_reflection_reminder`** (`gates/exit_reflection.py`, stateful) — the single Stop-time handover reminder. On the first clean `Stop` event of a session, warns (non-blocking `additionalContext`) with the full `templates/handover.md` reminder plus a short user-visible `systemMessage` line; marks session state so it doesn't repeat for the rest of the session, and skips (without marking state) while `background_tasks` are pending so the reminder lands on the next clean Stop. This absorbed `router.py`'s former Stop branch — one mechanism, once per session, never blocks.

Grow the catalogue against real need, not speculatively.

## Deliberately not built (anti-bloat)

- **No multi-client translation DSL** — `emit()` is two `if` branches, not a template/schema layer.
- **No template registry** — gate messages are string literals in the gate function.
- **No tool-category dialect module** — gates match tool names inline (`e.tool == "Bash"`).
- **No condition DSL** — gates are Python; the function body is the condition.
- **No forensic logging in the hot path** — nothing is logged by default; a logging sink, if ever wanted, is a one-line addition at the dispatcher, off by default.
- **No registry class, no gate discovery, no plugin-loading magic** — the registry is a literal Python list.

## Tests

[`tests/hooks/test_gate_verdict.py`](../../tests/hooks/test_gate_verdict.py) (merge rule), [`test_gate_emit.py`](../../tests/hooks/test_gate_emit.py) (wire mapping per event/client), [`test_gates_examples.py`](../../tests/hooks/test_gates_examples.py) (the two shipped gates), [`test_gate_state.py`](../../tests/hooks/test_gate_state.py) (state load/save/isolation), and [`test_gate_dispatch.py`](../../tests/hooks/test_gate_dispatch.py) (end-to-end: stdin JSON in, wire JSON out, via a real subprocess run of `gate_dispatch.py`).
