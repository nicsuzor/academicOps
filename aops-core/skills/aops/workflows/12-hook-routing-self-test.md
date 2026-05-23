# Hook Output Channel Routing Self-Test

Regression cover for [[aops-d10e7db6]] — the Stop-hook RBG advisory was leaking into the user-visible chat surface instead of being injected into the agent's next-turn context. User suspects ("stop hooks (maybe others?)") that the same inversion may exist for other hook types. This workflow verifies, **for every hook the framework configures**, that the output channel matches design intent. Companion to [[11-self-test]]; included in the v0.4 release self-test pass.

## Channel model

The router (`aops-core/hooks/router.py`) produces a `CanonicalHookOutput` with two payload slots:

- `system_message` → **user-visible** surface (Claude: `systemMessage` / `stopReason`; Gemini: `systemMessage` / `reason`).
- `context_injection` → **agent's next-turn context** (Claude: `hookSpecificOutput.additionalContext`, or `reason` on a blocked `Stop`; Gemini: `hookSpecificOutput.additionalContext`).

A hook can legitimately emit to one channel or both. The test asserts the observed channels match the intended channels per hook. Any mismatch is a routing bug.

## Hooks under test

Authoritative source for active hooks is `aops-core/hooks/hooks.json`; channel dispatch lives in `HookRouter.output_for_claude` / `output_for_gemini`. Re-verify the row set before each run — if `hooks.json` adds an event, this table is silently incomplete.

| Hook               | Expected   | Why                                                                                                                           |
| ------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `SessionStart`     | agent-only | Boot-time principles / session env load into agent context. (See [[11-self-test]] §1.)                                        |
| `UserPromptSubmit` | agent-only | Hydrator skills-routing table + `context-map.json` matches go to `context_injection`. **Canonical working reference.**        |
| `PreToolUse`       | both       | Blocking gates need `system_message` (user sees _why_ denied) **and** `additionalContext` (agent gets recovery instructions). |
| `PostToolUse`      | agent-only | Post-hoc observations / status icons feed the next agent turn; user already saw the tool output.                              |
| `Stop`             | agent-only | RBG pre-response advisory belongs in `additionalContext` (or `reason` when blocking). [[aops-d10e7db6]] is the inversion bug. |
| `SubagentStart`    | agent-only | Subagent receives its dispatch context; main user surface stays quiet.                                                        |
| `SubagentStop`     | agent-only | Subagent-completion summary feeds the parent agent's next turn, not the user's chat.                                          |
| `PreCompact`       | TBD        | No active gate currently emits on `PreCompact`; intent undocumented. If a payload appears, flag and ask before classifying.   |
| `Notification`     | user-only  | Notifications are by definition a user-surface event (desktop / `ntfy`); no agent action expected.                            |
| `SessionEnd`       | agent-only | Same dispatch shape as `Stop` (`router.py:807`); cleanup advisory belongs in the next session's handover read, not on exit.   |

## Marker convention

Pick a fresh run id per session (timestamp or short uuid). Use **distinct** markers per channel so each can be verified independently and cross-talk or inversion is immediately visible:

```
[SELFTEST-HOOK-<EVENT>-SYS-<RUN_ID>]   # emitted into system_message  → user surface
[SELFTEST-HOOK-<EVENT>-CTX-<RUN_ID>]   # emitted into context_injection → agent context
```

Examples: `[SELFTEST-HOOK-Stop-SYS-20260522a]`, `[SELFTEST-HOOK-Stop-CTX-20260522a]`.

**Emission options:**

1. **Add a one-shot debug gate** that emits the SYS marker into `system_message` and the CTX marker into `context_injection` for the target event, then remove it after the run. Distinct markers let you independently verify each channel and detect inversion (e.g. SYS landing in agent context, or CTX leaking to user surface). Use an **`allow` verdict** — a `warn` verdict on Stop events triggers a legacy fallback (router.py:825) that leaks `context_injection` to the user surface, producing a false positive for channel leakage. **Preferred for v0.4.**
2. **Read an existing gate's payload** if one is live for the event (e.g. hydrator hint on `UserPromptSubmit`, RBG advisory on `Stop`); pick a distinctive substring from its output as the marker. No code change but coverage is limited to whatever the live gate emits.

Document the temporary gate in the PR; revert before merging.

## Walk-through

Run interactively in a fresh Claude session (`polecat crew` or local); one human watching the terminal, one agent ready to answer. Repeat for Gemini if the v0.4 pass includes both clients.

For each row in the table, in order:

1. **Pick the run id** for the session (one id covers all hooks in this run).
2. **Trigger the hook** — actions per event:
   - `SessionStart` — start the session; the first agent turn captures this.
   - `UserPromptSubmit` — type any prompt (the act of submitting fires the hook).
   - `PreToolUse` / `PostToolUse` — ask the agent to invoke a trivially cheap tool (e.g. `Read` on a small file).
   - `Stop` — let the agent finish a turn (don't interrupt; Stop fires as the agent returns).
   - `SubagentStart` / `SubagentStop` — dispatch a subagent (e.g. `/aops-core:junior` with a trivial task).
   - `PreCompact` — trigger compaction (typically `/compact`).
   - `Notification` — take any action that fires the notification hook (permission prompt, idle alert — context-dependent).
   - `SessionEnd` — `/exit` or kill the session cleanly.
3. **Observe the user surface.** Grep the transcript file (or scroll the terminal) for the **SYS** marker (`[SELFTEST-HOOK-<EVENT>-SYS-<RUN_ID>]`). Also check that the **CTX** marker does _not_ appear user-side — its presence would indicate `context_injection` leaking to the user surface. Record: **SYS marker visible to user? Yes / No; CTX marker visible to user? (must be No)**.
4. **Ask the agent explicitly** on the next turn (or, for `SessionEnd`, on the next session start that reads handover state):

   > Did you receive `[SELFTEST-HOOK-<EVENT>-CTX-<RUN_ID>]` in your context (system-reminder, additionalContext, or any hook-injected block) on this turn? Yes or no — do not infer from the user message; check your actual context.

   The agent must answer from its actual context, not from the user's question text — the "do not infer" guard is load-bearing. Record: **CTX marker visible to agent? Yes / No**.
5. **Compare against the expected channel** in the table.

## Pass / fail criterion

| Expected     | Pass condition (Option 1 — distinct markers)                                      |
| ------------ | --------------------------------------------------------------------------------- |
| `user-only`  | SYS user-side: Yes. CTX user-side: **No**. CTX agent-side: No.                    |
| `agent-only` | SYS user-side: Yes. CTX user-side: **No** (inversion guard). CTX agent-side: Yes. |
| `both`       | SYS user-side: Yes. CTX user-side: **No**. CTX agent-side: Yes.                   |
| `TBD`        | Record all observed markers and surfaces; do not pass or fail — escalate.         |

_Note: with Option 1 the SYS marker always appears user-side (the framework unconditionally routes `system_message` there); the diagnostic signal is whether the **CTX** marker leaks to the user surface (must never) and whether it reaches agent context (required for `agent-only` / `both`)._

Any mismatch (e.g. `Stop` expected `agent-only` but marker appears user-side and not agent-side — the [[aops-d10e7db6]] inversion) is a **routing bug**, not a self-test failure. Halt the section and file a `bug` issue under [[epic-9fa15948]]: title `<EVENT>-hook output routed to <observed> channel, expected <intended>`; body must include the marker run id, the transcript excerpt, and the agent's verbatim answer. Do **not** attempt to fix routing in this session — that's a separate task in the same shape as [[aops-d10e7db6]].

## Notes for the agent running the section

- You are the test instrument for half of each row. When the human asks "did you see `[SELFTEST-HOOK-X-CTX-Y]`?", answer from your **actual context**, not from your model of what should have happened. Inferring "the Stop hook is configured so I must have seen it" is exactly the failure mode this test exists to catch.
- If your context for a turn does not include the CTX marker, say "No, I did not receive that marker in my context on this turn" — full stop. Do not soften with "but it may have been processed elsewhere".
- Cross-reference: the working channel-routing reference is `UserPromptSubmit`'s skills-routing-table injection (you reliably do see that). If your `UserPromptSubmit` answer pattern doesn't match the expected row, the test rig itself is broken — halt and report.
