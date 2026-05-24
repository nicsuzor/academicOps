---
title: Gates — runtime catalogue and forensic reference
type: state
category: state
permalink: state-gates
description: SSoT for every gate the framework runs at session time — what each one is, where it lives, how it's configured, how to verify it's firing, and how to debug it when it isn't.
---

# Gates — runtime catalogue and forensic reference

**Scope.** Single source of truth for the gates that fire at session time through the academicOps hook router. Each gate section opens with a TL;DR answer card, then expands into where it lives, how it's configured, how to verify firing, and how to debug.

**Doc category.** State, per [`specs/meta/doc-taxonomy.md`](../specs/meta/doc-taxonomy.md). Kept beside the other framework-wide state docs (`AXIOMS.md`, `SURFACES.md`, `HEURISTICS.md`, `CONSTRAINTS.md`).

**What is NOT here.**

- **Pyramid-position assignments, axiom mapping, escalation rules** — see [`.agents/ENFORCEMENT-MAP.md`](../.agents/ENFORCEMENT-MAP.md) (operative state SSoT for the L0–L7 regulatory pyramid; `rbg` blocks on it via P#65).
- **Hook router architecture, MCP wiring, hook I/O schemas, PATH bootstrap** — see [`aops-core/skills/aops/references/hooks.md`](skills/aops/references/hooks.md).
- **JSONL log schema, raw-file forensics procedures** — see [`aops-core/skills/aops/references/forensics-details.md`](skills/aops/references/forensics-details.md).
- **Design rationale (why the gate system is shaped this way)** — see [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md), [`specs/enforcement/hook-router.md`](../specs/enforcement/hook-router.md), [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md), [`specs/enforcement/enforcement-mechanisms.md`](../specs/enforcement/enforcement-mechanisms.md).

## At a glance

| Gate       | What it catches                                | Fires on               | Default | Stateful?   |
| ---------- | ---------------------------------------------- | ---------------------- | ------- | ----------- |
| `enforcer` | Periodic compliance / ultra-vires drift        | PreToolUse @ threshold | `warn`  | counter     |
| `qa`       | "Done" claimed without verification            | Stop while CLOSED      | `warn`  | open/closed |
| `handover` | Exit without commit / task update / reflection | Stop while CLOSED      | `warn`  | open/closed |
| `ida`      | Honesty / criterion-substitution at Stop       | Stop (once/turn)       | `warn`  | open/closed |

Schema lives in [`lib/polecat_config.py`](lib/polecat_config.py); each `GateConfig` is defined in [`lib/gates/definitions.py`](lib/gates/definitions.py); mode resolution happens in [`hooks/gate_config.py`](hooks/gate_config.py).

**Reserved name.** `hydration` is accepted in the `gates.*` config schema (`HYDRATION_GATE_MODE`) but **has no `GateConfig` today** — the visible hydration behaviour (skills-routing hint + context-map injection on UPS) runs unconditionally in the router. See [Reserved names](#reserved-names-hydration) at the bottom.

**Historical name.** `custodiet` was the previous name for the `enforcer` gate. Old references to `custodiet_*` env vars or the `custodiet` gate map one-to-one onto `enforcer`. See [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md) §rename-note.

---

## Config plumbing

Every gate above resolves its mode through the same path. Read this section once; the per-gate sections below only call out keys, not the resolution.

### Where polecat.yaml lives

- **Host**: `$AOPS_SESSIONS/polecat.yaml` (default), or `$AOPS_POLECAT_CONFIG` if set explicitly.
- **Polecat container**: staged in by polecat at launch; `$AOPS_POLECAT_CONFIG` points at the staged copy.
- **Example / schema**: `polecat/defaults/polecat.yaml.example`.
- **Loader**: [`lib/polecat_config.py:load_polecat_config()`](lib/polecat_config.py).

`polecat.yaml` is the **only** place gate-mode values are configured. Setting `*_GATE_MODE` env vars in `~/.claude/settings.json` is a no-op — see the "Removed" section at the bottom of `polecat.yaml.example`.

### Resolution path

```
polecat.yaml gates.{name}
  ↓ parsed by lib/polecat_config.py
PolecatConfig.session_defaults.gates
  ↓ .for_mode(POLECAT_SESSION_TYPE) overlay
hooks/gate_config.py:_resolve_gate_modes()   (lazy via PEP 562 __getattr__)
  ↓
ENFORCER_GATE_MODE, QA_GATE_MODE, HANDOVER_GATE_MODE, HYDRATION_GATE_MODE, IDA_GATE_MODE
  ↓
imported by lib/gates/definitions.py at module load
  ↓ embedded in GatePolicy.verdict for each GateConfig
runtime: lib/gates/engine.py:GenericGate._evaluate_policies
  ↓
GateResult.verdict ∈ {allow, warn, deny}
```

`gate_config.py` uses module-level `__getattr__` so config values are resolved lazily on first access — this is what lets tests monkeypatch the session env after the module is imported (call `_reset_gate_mode_cache()` to invalidate).

### Session-type overlays

`POLECAT_SESSION_TYPE` (set by `polecat/cli.py` at launch) selects the overlay:

| Value         | Overlay applied to defaults                                  | Surfaces                                                    |
| ------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| `crew`        | `polecat.yaml:crew_defaults` (today: `hooks_enabled: false`) | `polecat crew` interactive multi-agent sessions             |
| (unset/`run`) | `polecat.yaml:run_defaults` (today: `{}`)                    | `polecat run` workers, host-Claude sessions, fresh installs |

If unset the loader treats it as `run` — so host sessions get `run_defaults`.

### Plugin cache lifecycle

The aops-core plugin (and therefore the gates code) runs from a versioned cache directory at runtime, not directly from the source repo on the host:

- **Claude Code on host**: `~/.claude/plugins/cache/academicOps/aops-core/<ver>/` — Claude.app picks the most recent versioned dir; **does not garbage-collect older ones**. Stale dirs are a known trap (see [`SURFACES.md`](SURFACES.md) → "Claude Code CLI on host" → Known traps).
- **WSL crew container / polecat run**: `dist/aops-claude/` baked into the Docker image at build time. Pinned at image build until the image is rebuilt.
- **GHA runner**: agent prompt from `.github/agents/*.md`; no plugin runtime — gates do not fire.

To verify the cached copy matches source: `diff -ru ~/src/academicOps/aops-core/lib/gates/ ~/.claude/plugins/cache/academicOps/aops-core/<latest>/lib/gates/`.

### Hook env stripping (cross-cutting trap)

On Claude Code CLI on host (Mac, WSL host shell): `settings.json` `env` block does **not** propagate to hook subprocesses (`launchctl setenv` ignored; `.zshenv` partially sourced but `PATH` overridden). All gate-mode env vars in `settings.json` are dead by design — `gate_config.py` reads only from `polecat.yaml`. If `$AOPS_SESSIONS` is missing from the hook env, `gate_config.py` raises at import. See [`SURFACES.md`](SURFACES.md) → "Claude Code CLI on host" → Known traps for the full trace.

The WSL crew container surface receives env directly from the polecat launcher; no `launchctl`/`.zshenv` hop, so this trap does not apply there.

### Verifying the resolved mode at runtime

```bash
python -c '
import os, sys
sys.path.insert(0, "/path/to/aops-core")
from hooks.gate_config import (
    ENFORCER_GATE_MODE, QA_GATE_MODE, HANDOVER_GATE_MODE,
    HYDRATION_GATE_MODE, IDA_GATE_MODE, ENFORCER_TOOL_CALL_THRESHOLD,
)
print(f"enforcer={ENFORCER_GATE_MODE} threshold={ENFORCER_TOOL_CALL_THRESHOLD}")
print(f"qa={QA_GATE_MODE} handover={HANDOVER_GATE_MODE}")
print(f"ida={IDA_GATE_MODE} hydration={HYDRATION_GATE_MODE}")
'
```

If this fails, `polecat.yaml` is missing/unreadable or `$AOPS_SESSIONS` is unset — the same trap that causes gates to silently fail.

---

## `enforcer` gate

> **TL;DR.** Periodic compliance check. Counts write-tool calls since the last reset; when the count reaches `gates.enforcer_threshold` (default 50), the next non-infrastructure tool call fires a PreToolUse policy that dispatches the `enforcer` or `rbg` subagent. Defined in [`lib/gates/definitions.py`](lib/gates/definitions.py) (`GATE_CONFIGS[0]`). Mode key: `gates.enforcer`.

### What is it

The periodic-compliance gate. Counts write operations since the last enforcer/rbg check; when the count reaches `gates.enforcer_threshold` (default 50), the gate's PreToolUse policy fires on the next non-infrastructure tool call. The policy renders a compliance report from the session transcript into a temp file and instructs the agent to invoke the `enforcer` or `rbg` subagent. A successful dispatch resets the counter.

**Class of failure caught.** Ultra-vires drift, scope creep, unaudited long-running sessions, axiom violations the agent didn't self-catch. Enforces a periodic compliance check rather than blocking individual actions.

### Where it lives

| Concern                  | Path                                                                                                                  |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Gate definition (config) | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[0]`)                                                              |
| Threshold + mode lookup  | `aops-core/hooks/gate_config.py` (`ENFORCER_TOOL_CALL_THRESHOLD`, `ENFORCER_GATE_MODE`)                               |
| Audit-file builder       | `aops-core/lib/gates/custom_actions.py` (`prepare_compliance_report`)                                                 |
| Templates                | `aops-core/hooks/templates/enforcer-{audit,context,countdown,instruction,policy-context,policy-message,verified}.md`  |
| Compliance subagent      | `aops-core/agents/rbg.md` (only `rbg.md` is shipped; the regex also accepts a subagent named `enforcer` if installed) |

Subagent dispatches that look like `Agent(subagent_type="enforcer")` or `Agent(subagent_type="rbg")` reset the counter via the gate's trigger.

### How it's configured

- **Mode key**: `gates.enforcer` (see [Config plumbing](#config-plumbing) for resolution). `warn` | `block` | `off`.
- **Threshold** (write ops between checks): `gates.enforcer_threshold` (default 50).
- **Countdown window**: 7 ops before threshold (`start_before=7` in the `CountdownConfig` literal — not currently in YAML).
- **Plan-mode bypass**: `POLECAT_APPROVAL_MODE=plan` skips counter increments entirely (see `engine.py:on_tool_use`).
- **Tool-category exclusions**: `infrastructure`, `always_available`, `read_only` tools do not trip the policy (`TOOL_CATEGORIES` in `gate_config.py`).
- **Mid-edit deferral**: while a TodoWrite has an `in_progress` item, the block is deferred via the `not_mid_edit` custom check (`custom_conditions.py`).

### How to verify it's firing

```bash
# Live counter (since session start or last check)
jq -r 'select(.hook_event=="PostToolUse") | .output.system_message // empty' \
  ~/.claude/projects/*/$(ls -1t ~/.claude/projects/*/ | head -1)*-hooks.jsonl \
  | grep -E '◇|Compliance check' | tail -5

# Find PreToolUse blocks where the enforcer gate denied
grep '"hook_event":"PreToolUse"' <hooks.jsonl> \
  | jq -r 'select(.output.verdict=="deny") | "\(.logged_at) \(.tool_name): \(.output.system_message[:120])"'

# Count compliance dispatches (SubagentStart for enforcer or rbg)
grep '"hook_event":"SubagentStart"' <hooks.jsonl> \
  | jq -r 'select(.subagent_type|test("enforcer|rbg"))' | wc -l
```

**Healthy fire**: PreToolUse with `tool_name` ≠ infrastructure/read-only, `output.verdict="deny"` (mode `block`) or `"warn"`, system_message starting with `✕ Compliance check required` or carrying the `enforcer-policy-context` template. SubagentStart with `subagent_type` matching `enforcer|rbg` clears the counter.

**Visible icons** (`format_gate_status_icons` in `router.py`): `◇ N` during countdown window, `◇` when over threshold.

### How to debug when it isn't

| Failure mode                                                 | Diagnostic                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mode silently `off`                                          | `python -c "from hooks.gate_config import ENFORCER_GATE_MODE; print(ENFORCER_GATE_MODE)"` — if "off", check `polecat.yaml`.                                                                                                                                                                   |
| `polecat.yaml` unreadable / `$AOPS_SESSIONS` not in hook env | `gate_config.py` raises at import; check `~/.claude/projects/<workspace>/<base>-hooks.jsonl` for `CRITICAL: Failed to import`. Cross-ref the Mac-CLI hook env-stripping trap above.                                                                                                           |
| Gate never reaches threshold                                 | Read-only / infrastructure tools don't increment the counter by design. Confirm with `PostToolUse` entries where `tool_name` is `Edit`/`Write`/`Bash` — counter only ticks on these.                                                                                                          |
| Block deferred indefinitely                                  | Check `state.metrics.has_in_progress_todo` in the session state file — the `not_mid_edit` condition defers blocks while a TodoWrite item is `in_progress` (issue #319).                                                                                                                       |
| Subagent dispatch doesn't reset counter                      | Trigger regex: `^(aops[-_]core[:_])?(enforcer\|rbg)$` on `(PreToolUse\|SubagentStart\|SubagentStop)`. `aops-core:enforcer` and `enforcer` match; `aops_core_enforcer` does not. If dispatch was never emitted, check that the policy reached threshold (`not_mid_edit` may have deferred it). |

See [`forensics-details.md`](skills/aops/references/forensics-details.md#enforcer--rbg-gate) for the JSONL-level forensics procedure that complements these.

---

## `qa` gate

> **TL;DR.** Completion-quality gate — starts OPEN, closes when work begins (task bound to `in_progress` or any write-tool PostToolUse), reopens when a `qa`/`marsha`/`verify` subagent runs. Blocks Stop while CLOSED. Defined in [`lib/gates/definitions.py`](lib/gates/definitions.py) (`GATE_CONFIGS[1]`). Mode key: `gates.qa`.

### What is it

The completion-quality gate. Starts OPEN (short interactive chats don't require verification). Closes when work begins (task bound to `in_progress`, or any write-tool PostToolUse). Reopens when a `qa` / `verify` / `marsha` subagent runs to completion. On Stop, the policy blocks once per turn while the gate is CLOSED — the gate opens after the first block (fire-once trigger) and re-arms on UserPromptSubmit. Both warn and block modes inject the advisory into the agent's context (Claude Code's Stop schema has no non-blocking advisory channel).

**Class of failure caught.** "Done" claimed without verification: tests not run, acceptance criteria not checked, build broken on exit.

### Where it lives

| Concern           | Path                                                                               |
| ----------------- | ---------------------------------------------------------------------------------- |
| Gate definition   | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[1]`)                           |
| Custom action     | `aops-core/lib/gates/custom_actions.py` (`prepare_qa_review`)                      |
| Custom condition  | `aops-core/lib/gates/custom_conditions.py` (`is_write_tool`, shared with handover) |
| Templates         | `aops-core/hooks/templates/qa-{complete,context,policy-context,policy-message}.md` |
| Verifier subagent | `aops-core/agents/marsha.md` (the only verifier shipped today)                     |

### How it's configured

- **Mode**: `polecat.yaml` → `session_defaults.gates.qa` (`warn` | `block` | `off`).
- **Close triggers**: `update_task` PostToolUse with input matching `in_progress`, OR any PostToolUse where `is_write_tool` matches (Edit, Write, Bash/`run_shell_command`/`shell`/`execute_code`, etc.). Shares `is_write_tool` with handover; the bash-as-read carve-out keyed on `handover_skill_invoked` also applies, so `git status` after `/end-session` doesn't re-close the gate.
- **Reopen triggers**: (1) any subagent matching `^(aops-core:)?(qa|verify|marsha)$` on `SubagentStart|SubagentStop|PostToolUse`; (2) Stop while CLOSED (fire-once — gate opens after first block so retried Stops pass).
- **Re-arm trigger**: `UserPromptSubmit` → CLOSED.
- **Policy fires**: only on `hook_event="Stop"` while `current_status=CLOSED`. `prepare_qa_review` writes a qa-context audit file into the session dir; the policy message points the agent at it.

### How to verify it's firing

```bash
# Stop events that the qa gate blocked
grep '"hook_event":"Stop"' <hooks.jsonl> \
  | jq -r 'select(.output.verdict=="deny" and (.output.system_message|test("QA|qa|marsha"))) | .logged_at'

# Verifier completions that touched the gate
grep '"hook_event":"SubagentStop"' <hooks.jsonl> \
  | jq -r 'select(.subagent_type|test("qa|verify|marsha")) | "\(.logged_at) opened: \(.subagent_type)"'
```

### How to debug when it isn't

- **Gate stays OPEN despite write activity**: confirm a task is bound (`state.main_agent.current_task` non-empty) — the `is_write_tool` carve-out treats shell tools as read-only when no task is bound. With a bound task, any write should close the gate.
- **Subagent didn't reset**: check the spelled `subagent_type` against `^(aops-core:)?(qa|verify|marsha)$` — `aops-core:marsha` and `marsha` both match; `aops_core_marsha` does not.
- **Mode `off`**: confirm with `from hooks.gate_config import QA_GATE_MODE`.

---

## `handover` gate

> **TL;DR.** Exit-discipline gate. Starts OPEN, CLOSES when work begins (task bound to `in_progress` or any write-tool PostToolUse), reopens when `/end-session` or `/dump` completes. Blocks once per turn on Stop while CLOSED (fire-once, re-arms on UPS). Both warn and block modes inject advisory into agent context. Safety override: 5+ Stop denies in 2 minutes auto-approves to prevent deadlock. Defined in [`lib/gates/definitions.py`](lib/gates/definitions.py) (`GATE_CONFIGS[2]`). Mode key: `gates.handover`.

### What is it

The exit-discipline gate. Starts OPEN (short interactive chats don't require handover). Closes when work begins (task bound to `in_progress`, or any write-tool PostToolUse). Reopens when the `/end-session` (canonical) or `/dump` (emergency) skill completes. On Stop, the policy blocks once per turn while the gate is CLOSED — the gate opens after the first block (fire-once trigger) and re-arms on UserPromptSubmit. Both warn and block modes inject the advisory into the agent's context.

**Class of failure caught.** Uncommitted changes lost at exit, task left without a status update, no framework reflection captured.

### Where it lives

| Concern               | Path                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Gate definition       | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[2]`)                                               |
| Custom actions        | `aops-core/lib/gates/custom_actions.py` (`set_handover_invoked`, `reset_handover_invoked`)             |
| Custom condition      | `aops-core/lib/gates/custom_conditions.py` (`is_write_tool`)                                           |
| Templates             | `aops-core/hooks/templates/handover-{bound,complete,policy-message}.md`, `stop-gate-handover-block.md` |
| Skills that reopen it | `aops-core/skills/end_session/SKILL.md`, `aops-core/skills/dump/SKILL.md`                              |
| Safety override       | `aops-core/hooks/router.py` (`execute_hooks` — `stop_block_timestamps`)                                |

### How it's configured

- **Mode key**: `gates.handover` (`warn` | `block` | `off`).
- **Close triggers**: `update_task` PostToolUse with input matching `in_progress`, OR any PostToolUse where `is_write_tool` matches (Edit, Write, Bash/`run_shell_command`/`shell`/`execute_code`, etc. per `TOOL_CATEGORIES["write"]`).
- **Reopen triggers**: `Skill`/`activate_skill` PostToolUse with `subagent_type_pattern="^(aops-core:)?(handover|dump|end_session)$"`, OR a Gemini slash-command UPS prompt matching `^\s*#\s*/(dump|end_session)`.
- **Safety override**: after **5** consecutive Stop denies within 2 minutes (`router.py:execute_hooks`, set by aops-c67313ef), the gate auto-approves to prevent deadlock.
- **Bash-as-read carve-out**: once `handover_skill_invoked=True` or no task is bound, shell tools are treated as read-only by `is_write_tool` so the gate doesn't re-close on `git status` / `echo` after a /dump (issue aops-2283a8b0).

### How to verify it's firing

```bash
# Stop denies caused by handover
grep '"hook_event":"Stop"' <hooks.jsonl> \
  | jq -r 'select(.output.verdict=="deny" and (.output.system_message|test("Handover|handover"))) | .logged_at'

# Pattern: N denies followed by an allow → safety override fired
grep '"hook_event":"Stop"' <hooks.jsonl> | jq -r '.output.verdict' | uniq -c
```

**Visible icon**: `≡` appears in the icon strip only when the gate is OPEN **and** `handover_skill_invoked=True` (set by `set_handover_invoked` in `custom_actions.py`).

### How to debug when it isn't

| Failure mode                                 | Diagnostic                                                                                                                                                                                                          |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stop blocked despite running `/end-session`  | Re-check the subagent_type extraction — the trigger requires the router to have populated `ctx.subagent_type` from `tool_input.skill`. Look for the PostToolUse event in the JSONL and inspect its `subagent_type`. |
| `≡` never shows after handover               | Either the skill name didn't match the trigger regex, or `handover_skill_invoked` wasn't set. Inspect the session state file (`~/.claude/projects/<workspace>/*-session.json`) for `state.handover_skill_invoked`.  |
| 4–5 denies pattern (safety override)         | Normal once. Repeated across sessions = agent isn't completing handover before retrying Stop. Read the CC session JSONL between denies to see what the agent did.                                                   |
| Gate closed on a `git status` after handover | The Bash-as-read carve-out depends on `handover_skill_invoked` OR no bound task. If both are false the carve-out is off — that's by design while work is in progress.                                               |

See [`forensics-details.md`](skills/aops/references/forensics-details.md#stop--handover-gate) for the JSONL-level forensics procedure.

---

## `ida` gate

> **TL;DR.** Pre-Stop honesty reminder, named for Ida B. Wells. Fires on **every** Stop event in main-agent context (no state machine, no triggers, one policy). Default `warn` — injects a context_injection asking the agent to cite proof, not reasoning. To check if it fired this session: `grep '"hook_event":"Stop"' <hooks.jsonl> | jq 'select(.output.context_injection|test("Before stopping|Ida"))'`. Defined in [`lib/gates/definitions.py`](lib/gates/definitions.py) (`GATE_CONFIGS[3]`). Mode key: `gates.ida`.

### What is it

The pre-Stop honesty reminder. On every Stop, injects a non-blocking reminder that asks the agent to cite proof for assertions (file:line or command output, not reasoning) and to flag claims that were substituted, skipped, or laundered from a subagent without verification.

**Class of failure caught.** Criterion substitution, narrative-as-proof, fabricated diagnostics, skipped verification, positive-framing bias, unverified keystone assumptions, subagent-output laundering. Targets the issues catalogued in the gate definition's docstring (#621, #563, #380, #430, #359, #798, #549, #624, #317, #100, #376, #437, #391, #416, #335, #932, #822, #714).

**Why warn-only by design.** A block-tier version would force the agent to discharge the gate by writing a disclosure block, which is itself the criterion-substitution failure mode the gate is trying to prevent. If reminder-only fails to shift behaviour, the next intervention is structural (forced disclosure / mandatory review subagent), not a stricter prose gate.

### Where it lives

| Concern         | Path                                                     |
| --------------- | -------------------------------------------------------- |
| Gate definition | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[3]`) |
| Template        | `aops-core/hooks/templates/ida-reminder.md`              |
| Mode lookup     | `aops-core/hooks/gate_config.py` (`IDA_GATE_MODE`)       |

Loaded by the aops-core plugin's `GateRegistry.initialize()` (called from `router.execute_hooks`). Fires on **every Stop event** in main-agent context — no subagent-skip, no threshold.

### How it's configured

- **Mode key**: `gates.ida` (`warn` | `block` | `off`).
- **No triggers**, one policy: `hook_event="Stop"`, verdict `warn` by default.
- **Default-everywhere**: `polecat.yaml.example` ships `ida: warn`. `BUILTIN_GATES` (used when no polecat.yaml is found) also sets `ida: warn`.

### How to verify it's firing

```bash
# Stop events with the ida context injection
grep '"hook_event":"Stop"' <hooks.jsonl> \
  | jq -r 'select(.output.context_injection|test("Before stopping|Ida")) | .logged_at'

# Verdict-warn rate on Stop (ida is the only Stop policy that warns without state)
grep '"hook_event":"Stop"' <hooks.jsonl> | jq -r '.output.verdict' | sort | uniq -c
```

**Healthy fire** (mode `warn`): every Stop produces `output.verdict="warn"` (unless overridden by a stricter deny from another gate) with `output.context_injection` containing the ida-reminder template text ("Before stopping: for each claim..."). On the Claude side, `output_for_claude` copies the context_injection to `systemMessage`/`stopReason` when the verdict is `warn` and no other gate has set a system_message (`router.py:on_stop` / `output_for_claude`).

### How to debug when it isn't

| Failure mode                                          | Diagnostic                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Mode silently `off`                                   | `python -c "from hooks.gate_config import IDA_GATE_MODE; print(IDA_GATE_MODE)"` — confirm the resolved value.                                                                                                                                                                                    |
| Visible at SessionEnd but not at Stop (or vice versa) | Policy is keyed on `hook_event="Stop"`. Router maps `Stop` → `on_stop` and `SessionEnd` → `on_stop` (see `_call_gate_method`). Both should fire. If only one does, check `is_subagent` — gates are skipped in subagent context.                                                                  |
| Suppressed when another gate blocks                   | The router merges with DENY > WARN > ALLOW. A `handover` or `qa` DENY swallows the `ida` WARN's context_injection. Read the raw hook JSONL; the gate **did** evaluate, but its output was merged out.                                                                                            |
| Mode `warn` but no visible reminder in agent context  | Cross-check `output_for_claude` behaviour: when verdict is `warn` and no other gate set a system_message, the reminder is copied into `stopReason` + `systemMessage` (router.py near "WARN inertia #338"). If neither field is set in the JSONL output, the merge logic dropped it — file a bug. |

---

## Reserved names: `hydration`

`hydration` is accepted in the `gates.*` schema and exposed via `HYDRATION_GATE_MODE`, but `lib/gates/definitions.py` does not define a `hydration` `GateConfig`. The visible "hydration" behaviour is two non-blocking injections in the router:

- **Skills-routing hint** — `router.py:_run_lightweight_hydrator` adds template `hydration.warn` on every UserPromptSubmit in main-agent context.
- **Context-map hint** — `_inject_context_map_hints` injects `.agents/context-map.json` entries on the same event.

Both run unconditionally (not gated by `gates.hydration`). Mode is a placeholder for a future `GateConfig`.

| Concern               | Path                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------- |
| Mode placeholder      | `aops-core/lib/polecat_config.py` (`GatesConfig.hydration`)                            |
| Mode lookup           | `aops-core/hooks/gate_config.py` (`HYDRATION_GATE_MODE`)                               |
| Active hint injector  | `aops-core/hooks/router.py` (`_run_lightweight_hydrator`, `_inject_context_map_hints`) |
| Routing-hint template | `aops-core/hooks/templates/hydration-gate-warn.md`                                     |
| Context-map loader    | `aops-core/lib/context_map.py`                                                         |

**Verify the injection landed**:

```bash
grep '"hook_event":"UserPromptSubmit"' <hooks.jsonl> \
  | jq -r 'select(.output.context_injection!=null) | "\(.logged_at) \(.output.context_injection[:120])"'
```

**Common failures**: no injection at all → confirm `is_subagent=False` and `_is_task_notification` returned False. No context-map hints → confirm `<cwd>/.agents/context-map.json` exists. Expected a verdict and got none → there is no policy; this is by design.

---

## Cross-references

### Authoritative on adjacent slices

- [`.agents/ENFORCEMENT-MAP.md`](../.agents/ENFORCEMENT-MAP.md) — operative register: L0–L7 regulatory pyramid (Ayres & Braithwaite 1992), axiom × mechanism cross-reference, PR-pipeline agents. `rbg` blocks on it via P#65.
- [`aops-core/skills/aops/references/hooks.md`](skills/aops/references/hooks.md) — hook router architecture, PATH bootstrap, MCP wiring, hook I/O schemas, Gemini differences.
- [`aops-core/skills/aops/references/forensics-details.md`](skills/aops/references/forensics-details.md) — JSONL log schema, per-gate forensics procedures, polecat-session identification.
- [`polecat/defaults/polecat.yaml.example`](../polecat/defaults/polecat.yaml.example) — config schema + master environment-variable inventory.

### Design rationale (specs)

- [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md) — design statement: why enforcement is shaped this way, pipeline and pyramid views, evidence loop.
- [`specs/enforcement/enforcement-mechanisms.md`](../specs/enforcement/enforcement-mechanisms.md) — per-mechanism reference catalogue keyed to the L0–L11 pipeline view.
- [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md) — design rationale for the enforcer agent + gate.
- [`specs/enforcement/hook-router.md`](../specs/enforcement/hook-router.md) — design rationale for the hook router.

### Source

- `aops-core/lib/gates/definitions.py` — gate config literals
- `aops-core/lib/gates/engine.py` — `GenericGate` evaluation
- `aops-core/lib/gates/{custom_actions,custom_conditions}.py` — gate-specific side effects and predicates
- `aops-core/lib/gate_types.py` — pydantic models (`GateConfig`, `GateTrigger`, `GatePolicy`, `GateState`)
- `aops-core/lib/gate_model.py` — `GateResult`, `GateVerdict`
- `aops-core/lib/polecat_config.py` — `polecat.yaml` loader; schema validator
- `aops-core/hooks/gate_config.py` — mode resolution, tool categories, subagent extraction
- `aops-core/hooks/router.py` — event dispatch, gate registry, safety override, hint injection
- `aops-core/hooks/templates/*.md` — message/context templates rendered by gates

### Doc shape

This file is a state-category SSoT per [`specs/meta/doc-taxonomy.md`](../specs/meta/doc-taxonomy.md). The per-gate "TL;DR → where → config → verify → debug" shape is reusable for the Phase C subsystem consolidations (epic `aops-2b8dd7a7`).
