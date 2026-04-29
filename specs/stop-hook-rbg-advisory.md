# Stop-hook RBG advisory — design

**Status:** design (epic-9fa15948 / task-6e1e4e5c)
**Scope:** v1 advisory only, no binding enforcement.

## Resolution of open questions

### 1. Hook point — `Stop`, via existing gate infrastructure

Use the existing `Stop` event already wired in `aops-core/hooks/hooks.json`. The
advisory check is added as a new entry in `aops-core/lib/gates/definitions.py`
alongside the `enforcer`, `qa`, and `handover` gates. **No new hook event, no
new dispatcher, no new code path.**

The pattern is identical to the existing `qa` gate (Stop-triggered, instructs
the main agent to invoke a compliance subagent before allowing the turn to end).

### 2. Latency — N/A; hook does not call an LLM

The hook injects an instruction template (`rbg-advisory-policy-context.md`)
telling the **main agent** to invoke `Agent(subagent_type='aops-core:rbg', ...)`
itself. RBG then runs in the agent's own context and emits its verdict into
the normal message stream.

This is the same pattern as `enforcer-policy-context.md` →
`enforcer-instruction.md`. The hook itself returns in the same milliseconds as
the existing enforcer gate evaluation. Stop's current 5000ms timeout is
unchanged and unstressed.

### 3. Loop avoidance — `subagent_type_pattern` exclusion

The gate's reopen trigger excludes the compliance agent family using the same
regex shape `enforcer` already uses:

```
subagent_type_pattern="^(aops[-_]core[:_])?(rbg|enforcer|qa|marsha|pauli)$"
```

The advisory does not fire on stops of compliance/QA agents (RBG, enforcer,
QA, marsha, pauli). It only checks regular agents' final responses.

### 4. Verdict surface + logging — use existing pipeline

Verdict surface to user: **whatever RBG normally emits.** RBG runs as a
subagent invoked by the main agent; its output is part of the main thread's
visible response, exactly as today when nic invokes RBG manually. No new
rendering surface.

Logging: **automatic via `unified_logger`** — every Stop event, the
`Agent(rbg)` PreToolUse, and the `SubagentStop` with RBG's verdict are already
captured in the per-session JSONL hook log (`get_hook_log_path(...)`). Querying
verdicts means grepping JSONL, no new store. This satisfies the "verdicts
captured queryably" acceptance criterion using the existing observation pipe
documented by the per-session JSONL hook log pattern used across all gates.

## Gate semantics

```
GateConfig(
    name="rbg_advisory",
    description="Advisory inference-vs-fact check on agent stops.",
    initial_status=OPEN,
    triggers=[
        # New user prompt resets per-turn flag.
        GateTrigger(
            condition=GateCondition(hook_event="UserPromptSubmit"),
            transition=GateTransition(target_status=OPEN),
        ),
        # RBG (or any compliance agent) returning satisfies the advisory.
        GateTrigger(
            condition=GateCondition(
                hook_event="^(SubagentStart|SubagentStop)$",
                subagent_type_pattern="^(aops[-_]core[:_])?(rbg|enforcer|qa|marsha|pauli)$",
            ),
            transition=GateTransition(
                target_status=CLOSED,
                system_message_key="rbg_advisory.verified",
            ),
        ),
    ],
    policies=[
        # On Stop while OPEN: instruct main agent to invoke RBG.
        GatePolicy(
            condition=GateCondition(
                current_status=OPEN,
                hook_event="Stop",
                # Don't fire when the running agent itself is a compliance agent.
                subagent_type_pattern_exclude="^(aops[-_]core[:_])?(rbg|enforcer|qa|marsha|pauli)$",
            ),
            verdict=RBG_ADVISORY_GATE_MODE,  # default "warn"; off|warn|deny
            message_key="rbg_advisory.policy_message",
            context_key="rbg_advisory.policy_context",
        ),
    ],
)
```

Per-turn cycle:

1. Agent finishes turn → `Stop` fires; gate is OPEN → policy emits instruction:
   _"Invoke `Agent(subagent_type='aops-core:rbg', prompt='<focused prompt>')`
   to verify your previous response did not present inference as fact."_
2. Main agent invokes RBG → `SubagentStop(rbg)` → trigger transitions gate to
   CLOSED; verified message rendered.
3. Agent's next `Stop` is unblocked; turn ends.
4. User submits next prompt → `UserPromptSubmit` resets gate to OPEN.

## RBG invocation prompt skeleton

Stored as `aops-core/hooks/templates/rbg-advisory-instruction.md`:

```
Read the previous assistant message in this conversation. Apply ONE check from
CORE.md: "inference is not evidence."

For each factual claim in the response, classify:
- VERIFIED — supported by tool output, file content, or test result earlier in
  the transcript
- INFERENCE — derived from documentation, naming, prose, or pattern-matching;
  not directly verified
- UNCLEAR

Flag any INFERENCE claim presented without hedging ("likely", "appears to",
"based on the docstring"). Pass cleanly if all claims are VERIFIED or
appropriately hedged.

Output:
- VERDICT: pass | flag
- If flag: list each flagged claim with a one-line explanation of the
  inference→fact slip.

Do NOT block. Do NOT rewrite the response. This is advisory.
```

## Configuration

| Var                      | Values                  | Default | Effect                                                                                                                                                            |
| ------------------------ | ----------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RBG_ADVISORY_GATE_MODE` | `off` / `warn` / `deny` | `warn`  | `off` disables; `warn` injects the advisory instruction without blocking; `deny` would force the agent to actually run RBG before stopping. v1 ships `warn` only. |

Mirrors `QA_GATE_MODE`, `ENFORCER_GATE_MODE` conventions in
`hooks/gate_config.py`.

## Implementation deliverables (for task-0295c0ff)

1. `aops-core/lib/gates/definitions.py` — append `rbg_advisory` GateConfig
   (above).
2. `aops-core/hooks/gate_config.py` — add `RBG_ADVISORY_GATE_MODE = _gate_mode("RBG_ADVISORY_GATE_MODE")`.
3. Templates in `aops-core/hooks/templates/`:
   - `rbg-advisory-instruction.md`
   - `rbg-advisory-policy-context.md`
   - `rbg-advisory-policy-message.md`
   - `rbg-advisory-verified.md`
4. Tests in `tests/hooks/`:
   - Verdict fixture: regular agent Stop with gate OPEN → policy_context
     injected.
   - Verdict fixture: rbg Stop → no advisory (subagent_type_pattern_exclude).
   - Verdict fixture: `RBG_ADVISORY_GATE_MODE=off` → no advisory.
   - Loop test: Agent(rbg) PreToolUse → SubagentStop → Stop → no second advisory.

## Out of scope

- Binding enforcement (deferred per epic; toggled later via
  `RBG_ADVISORY_GATE_MODE=deny`).
- Other compliance lenses (pauli, marsha) — RBG only.
- New rendering surface — uses RBG's existing main-thread output.
- New logging store — uses existing `unified_logger` JSONL.

## Open follow-ups (not blocking implementation)

- After 2 weeks of dogfood, evaluate whether RBG output is too verbose for an
  every-turn check. If so, either narrow the prompt further or downgrade
  default mode to require an explicit opt-in.
