---
title: Gates — runtime catalogue and forensic reference
type: state
category: state
permalink: state-gates
description: SSoT for every gate the framework runs at session time — what each one is, where it lives, how it's configured, how to verify it's firing, and how to debug it when it isn't.
---

# Gates — runtime catalogue and forensic reference

**Scope.** Single source of truth for the gates that fire at session time through the academicOps hook router. For each gate this doc answers five questions in a uniform shape: **what**, **where**, **how configured**, **how to verify firing**, **how to debug**.

**This file is "state" in the [doc taxonomy](../specs/meta/doc-taxonomy.md) sense** — the current truth about which gates exist and how they behave at runtime, kept beside the other framework-wide state docs (`AXIOMS.md`, `SURFACES.md`, `HEURISTICS.md`, `CONSTRAINTS.md`).

**What is NOT here.**

- **Cost-ladder rank, axiom mapping, tier escalation rules** — see `.agents/ENFORCEMENT-MAP.md` (operative state SSoT for the L0–L7 cost ladder; `rbg` blocks on it via P#65).
- **Hook router architecture, MCP wiring, hook I/O schemas, PATH bootstrap** — see [`aops-core/skills/aops/references/hooks.md`](skills/aops/references/hooks.md).
- **JSONL log schema, raw-file forensics procedures** — see [`aops-core/skills/aops/references/forensics-details.md`](skills/aops/references/forensics-details.md).
- **Design rationale (why the gate system is shaped this way)** — see [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md), [`specs/enforcement/hook-router.md`](../specs/enforcement/hook-router.md), [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md), [`specs/enforcement/enforcement-mechanisms.md`](../specs/enforcement/enforcement-mechanisms.md).

## At a glance

| Gate        | Hook event(s)           | Default mode | Blocks on closed status?       | Definition                           |
| ----------- | ----------------------- | ------------ | ------------------------------ | ------------------------------------ |
| `enforcer`  | PreToolUse, Post, Sub*  | `warn`       | Yes — write tools at threshold | `aops-core/lib/gates/definitions.py` |
| `qa`        | Stop, Post, Sub*        | `warn`       | Yes — Stop                     | `aops-core/lib/gates/definitions.py` |
| `handover`  | Stop, Post, UPS, Pre    | `warn`       | Yes — Stop                     | `aops-core/lib/gates/definitions.py` |
| `ida`       | Stop                    | `warn`       | No (reminder only)             | `aops-core/lib/gates/definitions.py` |
| `hydration` | (config knob; reserved) | `off`        | n/a — disabled by default      | `aops-core/lib/polecat_config.py`    |

All five names are validated against `warn | block | off` in [`lib/polecat_config.py`](lib/polecat_config.py); the `GateConfig` objects that actually drive runtime behaviour live in [`lib/gates/definitions.py`](lib/gates/definitions.py).

**Historical name.** `custodiet` was the previous name for the `enforcer` gate and agent. The rename is in progress — old references to `custodiet_*` env vars, `aops-core:custodiet`, or the `custodiet` gate row in older audits map one-to-one onto `enforcer`. See [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md) §rename-note.

---

## `enforcer` gate

### What is it

The periodic-compliance gate. Counts write operations since the last enforcer/rbg check; when the count reaches `gates.enforcer_threshold` (default 50), the gate's PreToolUse policy fires on the next non-infrastructure tool call. The policy renders a compliance report from the session transcript into a temp file and instructs the agent to invoke the `enforcer` (Haiku) or `rbg` (Sonnet) subagent. A successful dispatch resets the counter.

**Class of failure caught.** Ultra-vires drift, scope creep, unaudited long-running sessions, axiom violations the agent didn't self-catch. Enforces a periodic compliance check rather than blocking individual actions.

### Where it lives

| Concern                  | Path                                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Gate definition (config) | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[0]`)                                                                              |
| Threshold + mode lookup  | `aops-core/hooks/gate_config.py` (`ENFORCER_TOOL_CALL_THRESHOLD`, `ENFORCER_GATE_MODE`)                                               |
| Audit-file builder       | `aops-core/lib/gates/custom_actions.py` (`prepare_compliance_report`)                                                                 |
| Templates                | `aops-core/hooks/templates/enforcer-{audit,context,countdown,instruction,policy-context,policy-message,verified}.md`                  |
| Subagent (Haiku)         | `aops-core/agents/enforcer.md`                                                                                                        |
| Subagent (Sonnet ad-hoc) | `aops-core/agents/rbg.md`                                                                                                             |
| Plugin cache at runtime  | `~/.claude/plugins/cache/academicOps/aops-core/<ver>/lib/gates/definitions.py` (Claude Code on host) — most recent versioned dir wins |

The gate is loaded by the aops-core plugin's hook router at every hook event; nothing else loads it. Subagent dispatches that look like `Agent(subagent_type="enforcer")` reset the counter via the gate's trigger.

### How it's configured

- **Mode** (`warn` | `block` | `off`): `polecat.yaml` → `session_defaults.gates.enforcer`. Per-mode overrides in `crew_defaults.gates.enforcer` / `run_defaults.gates.enforcer`. Mode is resolved lazily via `_resolve_gate_modes()` in `gate_config.py`, keyed by `POLECAT_SESSION_TYPE` (`crew` or `run`).
- **Threshold** (write ops between checks): `polecat.yaml` → `session_defaults.gates.enforcer_threshold` (default 50). Also overridable per session type.
- **Countdown window**: 7 ops before threshold (`start_before=7` in the `CountdownConfig` literal — not currently in YAML).
- **Plan-mode bypass**: `POLECAT_APPROVAL_MODE=plan` skips counter increments entirely (see `engine.py:on_tool_use`).
- **Tool-category exclusions**: `infrastructure`, `always_available`, `read_only` tools do not trip the policy (see `TOOL_CATEGORIES` in `gate_config.py`).
- **Mid-edit deferral**: while a TodoWrite has an `in_progress` item, the block is deferred via the `not_mid_edit` custom check (`custom_conditions.py`).

There are **no environment-variable fallbacks**. Setting `ENFORCER_GATE_MODE=warn` in `settings.json` does nothing; configuration values live in `polecat.yaml` only. See `polecat/defaults/polecat.yaml.example` and the "Removed" section at its bottom for the full list of dead env vars.

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

**Healthy fire**: PreToolUse with `tool_name` ≠ infrastructure/read-only, `output.verdict="deny"` (mode `block`) or `output.verdict="warn"`, system_message starts with `✕ Compliance check required` or carries the `enforcer-policy-context` template. SubagentStart with `subagent_type` matching `enforcer|rbg` clears the counter.

**Visible icons** (set by `format_gate_status_icons` in `router.py`): `◇ N` during countdown window, `◇` when over threshold.

### How to debug when it isn't

| Failure mode                                                 | Diagnostic                                                                                                                                                                                     |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mode silently `off`                                          | `python -c "from hooks.gate_config import ENFORCER_GATE_MODE; print(ENFORCER_GATE_MODE)"` — if "off", check `polecat.yaml`.                                                                    |
| `polecat.yaml` unreadable / `$AOPS_SESSIONS` not in hook env | `gate_config.py` raises at import; check `~/.claude/projects/<workspace>/<base>-hooks.jsonl` for `CRITICAL: Failed to import`. Cross-ref the Mac-CLI hook env-stripping trap in `SURFACES.md`. |
| Gate never reaches threshold                                 | Read-only / infrastructure tools don't increment the counter by design. Confirm with `PostToolUse` entries where `tool_name` is `Edit`/`Write`/`Bash` — counter only ticks on these.           |
| Block deferred indefinitely                                  | Check `state.metrics.has_in_progress_todo` in the session state file — the `not_mid_edit` condition defers blocks while a TodoWrite item is `in_progress` (issue #319).                        |
| `enforcer` subagent dispatch doesn't reset counter           | Trigger fires on `(PreToolUse                                                                                                                                                                  |

See [`forensics-details.md`](skills/aops/references/forensics-details.md#enforcer--rbg-gate) for the JSONL-level forensics procedure that complements these.

---

## `qa` gate

### What is it

The completion-quality gate. Closes when work begins (today: opens at SessionStart and stays open unless a custom action sets it CLOSED — verify in `definitions.py`); reopens when a `qa`/`marsha`/`verify` subagent runs to completion. The Stop-event policy blocks (or warns) when the gate is CLOSED, requiring verification before the session can end.

**Class of failure caught.** "Done" claimed without verification: tests not run, acceptance criteria not checked, build broken on exit. Forces a verifier subagent to inspect the work before Stop is permitted.

### Where it lives

| Concern            | Path                                                                               |
| ------------------ | ---------------------------------------------------------------------------------- |
| Gate definition    | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[1]`)                           |
| Templates          | `aops-core/hooks/templates/qa-{complete,context,policy-context,policy-message}.md` |
| Verifier subagents | `aops-core/agents/marsha.md`, `aops-core/agents/qa.md` (verify present)            |

### How it's configured

- **Mode**: `polecat.yaml` → `session_defaults.gates.qa` (`warn` | `block` | `off`).
- **Triggers**: matched on `subagent_type_pattern="^(aops-core:)?(qa|verify|marsha)$"` — any matching subagent completion opens the gate.
- **Policy fires**: only on `hook_event="Stop"` while `current_status=CLOSED`.

### How to verify it's firing

```bash
# Stop events that the qa gate blocked
grep '"hook_event":"Stop"' <hooks.jsonl> \
  | jq -r 'select(.output.verdict=="deny" and (.output.system_message|test("QA|qa|marsha"))) | .logged_at'

# Verifier completions that opened the gate
grep '"hook_event":"SubagentStop"' <hooks.jsonl> \
  | jq -r 'select(.subagent_type|test("qa|verify|marsha")) | "\(.logged_at) opened: \(.subagent_type)"'
```

### How to debug when it isn't

- Gate stays OPEN unexpectedly: the qa gate **starts** OPEN. A custom action is required to close it (today there is no `set_status` trigger landed for qa-CLOSED; if you expect blocking on Stop, verify the trigger that closes the gate is present in `definitions.py`).
- Subagent didn't reset: check the spelled `subagent_type` against the trigger regex — `aops-core:qa` and `qa` both match, `aops_core_qa` does not (regex uses `:`, not `_`).
- Mode `off`: confirm with `gate_config.QA_GATE_MODE` import.

---

## `handover` gate

### What is it

The exit-discipline gate. Starts OPEN (short interactive chats don't require handover). Closes when work begins (task bound to `in_progress`, or any write-tool PostToolUse). Reopens when the `/end-session` (canonical) or `/dump` (emergency) skill completes. On Stop, the policy blocks (or warns) while the gate is CLOSED.

**Class of failure caught.** Uncommitted changes lost at exit, task left without a status update, no framework reflection captured. Forces commit + task update + reflection before Stop is permitted.

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

- **Mode**: `polecat.yaml` → `session_defaults.gates.handover`.
- **Close triggers**: `update_task` PostToolUse with input matching `in_progress`, OR any PostToolUse where `is_write_tool` matches (Edit, Write, Bash/`run_shell_command`/`shell`/`execute_code`, etc. per `TOOL_CATEGORIES["write"]`).
- **Reopen triggers**: `Skill`/`activate_skill` PostToolUse with `subagent_type_pattern="^(aops-core:)?(handover|dump|end_session)$"`, OR a Gemini slash-command UPS prompt matching `^\s*#\s*/(dump|end_session)`.
- **Safety override**: after **5** consecutive Stop denies within 2 minutes (`router.py:execute_hooks`), the gate auto-approves to prevent deadlock. The forensics doc still references "4 denies" — verify against current `router.py` (line ~580) before quoting.
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

### What is it

The pre-Stop honesty reminder. Named for Ida B. Wells — investigative journalist whose work rested on documented evidence. On every Stop, injects a non-blocking reminder that asks the agent to cite proof for assertions (file:line or command output, not reasoning) and to flag claims that were substituted, skipped, or laundered from a subagent without verification.

**Class of failure caught.** Criterion substitution, narrative-as-proof, fabricated diagnostics, skipped verification, positive-framing bias, unverified keystone assumptions, subagent-output laundering. Targets the issues catalogued in the gate definition's docstring (#621, #563, #380, #430, #359, #798, #549, #624, #317, #100, #376, #437, #391, #416, #335, #932, #822, #714).

**Why warn-only by design.** A block-tier version would force the agent to discharge the gate by writing a disclosure block, which is itself the criterion-substitution failure mode the gate is trying to prevent. If reminder-only fails to shift behaviour, the next intervention is structural (forced disclosure / mandatory review subagent), not a stricter prose gate.

### Where it lives

| Concern         | Path                                                     |
| --------------- | -------------------------------------------------------- |
| Gate definition | `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[3]`) |
| Template        | `aops-core/hooks/templates/ida-reminder.md`              |
| Mode lookup     | `aops-core/hooks/gate_config.py` (`IDA_GATE_MODE`)       |

The gate is loaded by the aops-core plugin's `GateRegistry.initialize()` (called from `router.execute_hooks`). It fires on **every Stop event** in main-agent context — there is no subagent-skip or threshold.

### How it's configured

- **Mode**: `polecat.yaml` → `session_defaults.gates.ida` (`warn` | `block` | `off`). Per-mode overrides in `crew_defaults`/`run_defaults`.
- **No triggers**, only one policy: `hook_event="Stop"`, verdict `warn` by default. There is no state machine.
- **Default-everywhere**. `polecat.yaml.example` ships `ida: warn`. `BUILTIN_GATES` (used when no polecat.yaml is found) also sets `ida: warn`.

### How to verify it's firing

```bash
# Stop events with the ida context injection
grep '"hook_event":"Stop"' <hooks.jsonl> \
  | jq -r 'select(.output.context_injection|test("Before stopping|Ida")) | .logged_at'

# Verdict-warn rate on Stop (ida is the only Stop policy that warns without state)
grep '"hook_event":"Stop"' <hooks.jsonl> | jq -r '.output.verdict' | sort | uniq -c
```

**Healthy fire** (mode `warn`): every Stop produces an `output.verdict="warn"` (unless overridden by a stricter deny from another gate) with `output.context_injection` containing the ida-reminder template text ("Before stopping: for each claim..."). On the Claude side, `output_for_claude` copies the context_injection to `systemMessage`/`stopReason` when the verdict is `warn` and no other gate has set a system_message (router.py:on_stop / output_for_claude).

### How to debug when it isn't

| Failure mode                                          | Diagnostic                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Mode silently `off`                                   | `python -c "from hooks.gate_config import IDA_GATE_MODE; print(IDA_GATE_MODE)"` — confirm the resolved value.                                                                                                                                                                                    |
| Visible at SessionEnd but not at Stop (or vice versa) | Policy is keyed on `hook_event="Stop"`. Router maps `Stop` → `on_stop` and `SessionEnd` → `on_stop` (see `_call_gate_method`). Both should fire. If only one does, check `is_subagent` — gates are skipped in subagent context.                                                                  |
| Suppressed when another gate blocks                   | The router merges with DENY > WARN > ALLOW. A `handover` or `qa` DENY swallows the `ida` WARN's context_injection. Read the raw hook JSONL; the gate **did** evaluate, but its output was merged out.                                                                                            |
| Mode `warn` but no visible reminder in agent context  | Cross-check `output_for_claude` behaviour: when verdict is `warn` and no other gate set a system_message, the reminder is copied into `stopReason` + `systemMessage` (router.py near "WARN inertia #338"). If neither field is set in the JSONL output, the merge logic dropped it — file a bug. |

**The 2026-05-18 motivating question** ("what is the `ida` gate and is it firing in this session?") resolves here:

1. `ida` is the pre-Stop honesty reminder defined in `aops-core/lib/gates/definitions.py` (`GATE_CONFIGS[3]`), loaded by the aops-core hook router, fires on every Stop event.
2. To check if it's firing in _this_ session: read `~/.claude/projects/<workspace>/<base>-hooks.jsonl`, find Stop events, look for `output.context_injection` containing the ida-reminder template. If `IDA_GATE_MODE` resolves to `off`, it won't fire at all.

---

## `hydration` gate

### What is it

**Reserved name in the gate-mode config schema; not currently implemented as a `GateConfig`.** `polecat.yaml` accepts `gates.hydration: warn|block|off` and the value is exposed via `HYDRATION_GATE_MODE`, but `lib/gates/definitions.py` does not define a `hydration` `GateConfig` today.

What **does** run under the "hydration" name is a non-blocking hint injection in the hook router itself — `router.py:_run_lightweight_hydrator` adds a skills-routing hint (template `hydration.warn`) and `_inject_context_map_hints` injects `.agents/context-map.json` entries on every UserPromptSubmit in main-agent context. These run regardless of `gates.hydration` mode because they are not gated by it.

**Class of failure caught.** Tool calls made without skills routing being surfaced; missing context that the repo's `.agents/context-map.json` would have provided.

### Where it lives

| Concern               | Path                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------- |
| Mode placeholder      | `aops-core/lib/polecat_config.py` (`GatesConfig.hydration`)                            |
| Mode lookup           | `aops-core/hooks/gate_config.py` (`HYDRATION_GATE_MODE`)                               |
| Active hint injector  | `aops-core/hooks/router.py` (`_run_lightweight_hydrator`, `_inject_context_map_hints`) |
| Routing-hint template | `aops-core/hooks/templates/hydration-gate-warn.md`                                     |
| Context-map loader    | `aops-core/lib/context_map.py`                                                         |

### How it's configured

- **Mode**: `polecat.yaml` → `session_defaults.gates.hydration` (`warn` | `block` | `off`). Default `off`. **Currently the mode is read but has no `GateConfig` to gate.** The active routing-hint injection runs unconditionally on UPS in main-agent context.
- **Routing-table content**: `hydration-gate-warn.md` (today a placeholder: "No active routing rules").
- **Context-map**: `<cwd>/.agents/context-map.json` (per-repo). Absence is a no-op.

### How to verify it's firing

```bash
# Look for UserPromptSubmit events with the hydration / context-map injection
grep '"hook_event":"UserPromptSubmit"' <hooks.jsonl> \
  | jq -r 'select(.output.context_injection!=null) | "\(.logged_at) \(.output.context_injection[:120])"'
```

The injection lands in the agent's context, not as a verdict.

### How to debug when it isn't

- **No injection at all on UPS**: confirm `is_subagent=False` for the event (gates / hint injectors skip in subagent context). Confirm `_is_task_notification` returned False — task-notification prompts are filtered as internal plumbing.
- **No context-map hints**: confirm `<cwd>/.agents/context-map.json` exists in the worker's CWD; the loader checks `ctx.cwd / .agents / context-map.json`.
- **Expected a gate verdict, got nothing**: there is no policy; the "hydration gate" is mode-config without a `GateConfig`. This is by design today — see `polecat.yaml.example` which ships `hydration: off`.

---

## Config plumbing

This section explains how a value typed in `polecat.yaml` becomes a runtime decision at hook time. Every gate above reads its mode through this same path.

### Where polecat.yaml lives

- **Host**: `$AOPS_SESSIONS/polecat.yaml` (default), or `$AOPS_POLECAT_CONFIG` if set explicitly.
- **Polecat container**: staged in by polecat at launch; `$AOPS_POLECAT_CONFIG` points at the staged copy.
- **Example / schema**: `polecat/defaults/polecat.yaml.example`.
- **Loader**: `aops-core/lib/polecat_config.py:load_polecat_config()`.

`polecat.yaml` is the **only** place gate-mode values are configured. Setting `*_GATE_MODE` env vars in `~/.claude/settings.json` is a no-op — see the "Removed" section at the bottom of `polecat.yaml.example`.

### Resolution path: `polecat.yaml` → runtime

```
polecat.yaml gates.{name}
  ↓ (parsed by lib/polecat_config.py)
PolecatConfig.session_defaults.gates
  ↓ (overlay applied by .for_mode(POLECAT_SESSION_TYPE))
gate_config.py:_resolve_gate_modes() (cached, lazy via PEP 562 __getattr__)
  ↓
ENFORCER_GATE_MODE, QA_GATE_MODE, HANDOVER_GATE_MODE, HYDRATION_GATE_MODE, IDA_GATE_MODE
  ↓
imported by lib/gates/definitions.py at module load
  ↓
embedded in GatePolicy.verdict for each GateConfig
  ↓
runtime: lib/gates/engine.py:GenericGate._evaluate_policies
  ↓
GateResult.verdict ∈ {allow, warn, deny}
```

`gate_config.py` uses PEP 562 module-level `__getattr__` so config values are resolved lazily on first access — this is what lets tests monkeypatch the session env _after_ the module is imported (call `_reset_gate_mode_cache()` to invalidate).

### Session-type overlays

`POLECAT_SESSION_TYPE` (set by `polecat/cli.py` at launch) is read by `_resolve_gate_modes`:

| Value         | Overlay applied to defaults                                  | Surfaces                                                    |
| ------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| `crew`        | `polecat.yaml:crew_defaults` (today: `hooks_enabled: false`) | `polecat crew` interactive multi-agent sessions             |
| (unset/`run`) | `polecat.yaml:run_defaults` (today: `{}`)                    | `polecat run` workers, host-Claude sessions, fresh installs |

If `POLECAT_SESSION_TYPE` is unset the loader treats it as `run` — so host sessions get `run_defaults`.

### Plugin cache lifecycle

The aops-core plugin (and therefore the gates code) runs from a versioned cache directory at runtime, not directly from the source repo on the host:

- **WSL crew container**: `dist/aops-claude/` baked into the Docker image at build time. Plugin version is pinned at image build until the image is rebuilt.
- **Claude Code on host**: `~/.claude/plugins/cache/academicOps/aops-core/<ver>/` — Claude.app picks the most recent versioned dir; **does not garbage-collect older ones**. Stale dirs are a known trap (see `SURFACES.md` → "Claude Code CLI on host" → Known traps).
- **Polecat run/crew container**: `dist/aops-claude/` from the image — same as the WSL crew row.
- **GHA runner**: agent prompt from `.github/agents/*.md`; no plugin runtime — gates do not fire.

**Invalidating the cache**: rebuild the plugin (or reinstall in Claude.app). To verify the cached copy matches source: `diff -ru ~/src/academicOps/aops-core/lib/gates/ ~/.claude/plugins/cache/academicOps/aops-core/<latest>/lib/gates/`. If versions diverge, regen `dist/` and reinstall.

### Hook env stripping (cross-cutting trap)

On Claude Code CLI on host (Mac, WSL host shell): `settings.json` `env` block does **not** propagate to hook subprocesses (`launchctl setenv` ignored; `.zshenv` partially sourced but `PATH` overridden). All gate-mode env vars in `settings.json` are dead by design — `gate_config.py` reads only from `polecat.yaml`. Failure mode: `gate_config.py` imports raise if `$AOPS_SESSIONS` is missing from the hook env. See `SURFACES.md` → "Claude Code CLI on host" → Known traps for the full trace.

The WSL crew container surface receives env directly from the polecat launcher; no `launchctl`/`.zshenv` hop, so this trap does not apply there.

### Verifying the resolved mode at runtime

```bash
# Print resolved gate modes for the current session env
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

If this import fails, `polecat.yaml` is missing, unreadable, or `$AOPS_SESSIONS` is unset in the hook env — the same trap that causes gates to silently fail.

---

## Cross-references

### Authoritative on adjacent slices

- [`.agents/ENFORCEMENT-MAP.md`](../.agents/ENFORCEMENT-MAP.md) — operative cost-ladder catalogue (L0–L7), axiom × mechanism cross-reference, PR-pipeline agents. `rbg` blocks on it via P#65.
- [`aops-core/skills/aops/references/hooks.md`](skills/aops/references/hooks.md) — hook router architecture, PATH bootstrap, MCP wiring, hook I/O schemas, Gemini differences.
- [`aops-core/skills/aops/references/forensics-details.md`](skills/aops/references/forensics-details.md) — JSONL log schema, per-gate forensics procedures, polecat-session identification.
- [`polecat/defaults/polecat.yaml.example`](../polecat/defaults/polecat.yaml.example) — config schema + master environment-variable inventory.

### Design rationale (specs)

- [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md) — design statement: why enforcement is shaped this way, pipeline and pyramid views, evidence loop.
- [`specs/enforcement/enforcement-mechanisms.md`](../specs/enforcement/enforcement-mechanisms.md) — per-mechanism reference catalogue keyed to the L0–L11 pipeline view.
- [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md) — design rationale for the enforcer agent + gate.
- [`specs/enforcement/hook-router.md`](../specs/enforcement/hook-router.md) — design rationale for the hook router.
- [`specs/meta/doc-taxonomy.md`](../specs/meta/doc-taxonomy.md) — categories (state / spec / instructions / audit-artifact / docs) this file fits into.

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

---

## SSoT pattern: how this file is shaped (for Phase C reuse)

This file is the Phase B pilot of the framework SSoT-consolidation pattern (epic `aops-2b8dd7a7`). Phase C re-uses this pattern across 8 more subsystems; the structure is intentional and worth lifting verbatim.

**Location.** State-category SSoTs live at `aops-core/<NAME>.md` (framework-wide) or `.agents/<NAME>.md` (repo-local), per [`specs/meta/doc-taxonomy.md`](../specs/meta/doc-taxonomy.md). Existing examples: `AXIOMS.md`, `SURFACES.md`, `HEURISTICS.md`, `CONSTRAINTS.md`, `.agents/ENFORCEMENT-MAP.md`. **Do not** place state docs inside a skill's `references/` directory — that's the instructions category.

**Five-question template** for each runtime subsystem element:

1. **What is it** — one-sentence definition + the class of failure it catches.
2. **Where does it live** — file path(s) in source; plugin-cache location at runtime; which agent/skill loads it.
3. **How is it configured** — config keys, env vars, plugin cache invalidation cadence.
4. **How do I verify it's firing** — exact commands / log paths / artefact paths; expected output on healthy fire vs silent failure.
5. **How do I debug it when it isn't** — top failure modes + diagnostic for each.

**Cross-reference shape.** For each adjacent doc that retains relevant content, add a header note framing its role and pointing back to this canonical. Anchor links into specific sections (e.g. `forensics-details.md#enforcer--rbg-gate`) preserve discoverability without duplicating content.

**Redirect-stub shape.** Where a former definition is wholly subsumed by the canonical, replace the body with a short redirect (frontmatter `status: superseded`, `supersedes_target: <path>`, one paragraph naming the canonical). See `specs/enforcement/enforcement-map.md` for the Phase A example.

**Anti-pattern guard.** No silent removals: every demoted file either (a) becomes a redirect stub or (b) keeps non-overlapping content with an explicit cross-reference. The canonical doc is the **only** file that claims to be the single source for its slice; adjacent files explicitly cite it.
