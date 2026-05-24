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

## Verification approach

This self-test verifies that gates **already configured** behave correctly in production. For each hook event:

1. **Check what's live**: read `hooks.json` and the corresponding gate implementation to identify which gates are active for the event.
2. **Check it's configured right**: verify the gate's intended output channels (`system_message`, `context_injection`, or both) match the expected-channel matrix in the table above.
3. **Check it routes correctly**: trigger the hook in a real session (walk-through below) or inspect completed session artifacts (post-hoc evaluation below), and confirm the gate's output landed on the correct channel(s) — and did not leak to unintended channels.

Pick a distinctive substring from a live gate's output as the identifier for tracing through transcripts. For example, if the `Stop` hook's RBG advisory contains `"response-readiness"`, use that string to verify which channels it appeared on. Each hook event should have a recognisable payload that can be traced through the hooks JSONL and transcript JSONL.

**Caution on Stop-event verdicts**: a warn verdict on Stop events triggers a legacy fallback (router.py:838, see issue #1042) that leaks `context_injection` to the user surface, producing a false positive. When interpreting results for Stop hooks, check the verdict type and account for this known interaction.

## Walk-through

Run interactively in a fresh Claude session (`polecat crew` or local); one human watching the terminal, one agent ready to answer. Repeat for Gemini if the v0.4 pass includes both clients.

For each row in the table, in order:

1. **Identify live gate payloads**: before starting, read `hooks.json` and the active gate implementations to know what each hook emits into `system_message` and `context_injection`. These are the payloads you will trace through the session.
2. **Trigger the hook** — actions per event:
   - `SessionStart` — start the session; the first agent turn captures this.
   - `UserPromptSubmit` — type any prompt (the act of submitting fires the hook).
   - `PreToolUse` / `PostToolUse` — ask the agent to invoke a trivially cheap tool (e.g. `Read` on a small file).
   - `Stop` — let the agent finish a turn (don't interrupt; Stop fires as the agent returns).
   - `SubagentStart` / `SubagentStop` — dispatch a subagent (e.g. `/aops-core:junior` with a trivial task).
   - `PreCompact` — trigger compaction (typically `/compact`).
   - `Notification` — take any action that fires the notification hook (permission prompt, idle alert — context-dependent).
   - `SessionEnd` — `/exit` or kill the session cleanly.
3. **Observe the user surface.** Scroll the terminal (or review the transcript file) for `system_message` content from the gate — i.e., the payload the gate is configured to emit. Check whether the gate's `context_injection` content also appeared user-side — its presence would indicate a channel leak. Record: **system_message visible to user? Yes / No; context_injection content visible to user? (must be No for agent-only hooks)**.
4. **Ask the agent explicitly** on the next turn (or, for `SessionEnd`, on the next session start that reads handover state):

   > Did you receive the [hook name]'s context_injection payload in your context (system-reminder, additionalContext, or any hook-injected block) on this turn? Yes or no — do not infer from the user message; check your actual context.

   The agent must answer from its actual context, not from the user's question text — the "do not infer" guard is load-bearing. Record: **context_injection visible to agent? Yes / No**.
5. **Compare against the expected channel** in the table.

## Pass / fail criterion

| Expected     | Pass condition                                                                                                                                 |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `user-only`  | `system_message` content user-side: Yes. `context_injection` content user-side: **No**. `context_injection` agent-side: No.                    |
| `agent-only` | `system_message` content user-side: Yes. `context_injection` content user-side: **No** (inversion guard). `context_injection` agent-side: Yes. |
| `both`       | `system_message` content user-side: Yes. `context_injection` content user-side: **No**. `context_injection` agent-side: Yes.                   |
| `TBD`        | Record all observed content and surfaces; do not pass or fail — escalate.                                                                      |

_Note: the framework unconditionally routes `system_message` to the user surface; the diagnostic signal is whether `context_injection` content leaks to the user surface (must never) and whether it reaches agent context (required for `agent-only` / `both`)._

Any mismatch (e.g. `Stop` expected `agent-only` but `context_injection` appears user-side and not agent-side — the [[aops-d10e7db6]] inversion) is a **routing bug**, not a self-test failure. Halt the section and file a `bug` issue under [[epic-9fa15948]]: title `<EVENT>-hook output routed to <observed> channel, expected <intended>`; body must include the session id, the transcript excerpt, and the agent's verbatim answer. Do **not** attempt to fix routing in this session — that's a separate task in the same shape as [[aops-d10e7db6]].

## Post-hoc transcript evaluation

The standard verification method: always verify from completed session artifacts. First confirm the plugin version matches the version under test (check SessionStart log entry or plugin manifest) — a stale cached plugin invalidates the run. The agent performing this evaluation must **read and evaluate** the hooks JSONL and transcript JSONL content directly — there are no markers, status lines, or grep-friendly output to search for. Read the actual payload content from each hook event and judge whether it appeared on the correct channel(s).

1. **Hooks JSONL** (`~/.claude/projects/-workspace/*-session-hooks.jsonl`): each line records one hook event with `event`, `verdict`, `system_message` (user surface), and `context_injection` (agent context). Read each event and evaluate the populated channels against the expected-channel matrix above — non-empty `system_message` for an `agent-only` hook, or missing `context_injection` for `agent-only`/`both`, is a routing bug.
2. **Transcript JSONL** (`~/.claude/projects/-workspace/*-transcript.jsonl`): read assistant turns and evaluate whether `system-reminder` blocks contain the `context_injection` content from step 1. Presence confirms the agent-side channel is working.
3. **Cross-reference**: for each hook event, evaluate (a) `context_injection` content appears in transcript system-reminders (agent context confirmed), (b) `system_message` content appears in user-visible output (user surface confirmed), (c) `context_injection` content does NOT appear in user-visible output (leakage — the [[aops-d10e7db6]] inversion pattern).
4. Record results per the pass/fail criterion above. File routing bugs the same way.

Use transcript evaluation for auditing past sessions and batch regression checks. Use the interactive walk-through for first-time hook verification and release gates.

## Anti-pattern: synthetic testing

**No synthetic testing in this workflow.** This self-test exists to verify live, runtime behavior — the gap between "Python code produces correct JSON" and "the runtime delivers it to the correct surface." That gap lives in the CLI's hook protocol and channel-dispatch code, and no synthetic approach exercises it: not stdin piping, not unit-test harnesses, not mock hook events, not injected test payloads. If you want synthetic tests, run the pytest suite — that is a different workflow with a different purpose. An agent that substitutes any form of synthetic testing for the live verification defined here commits a methodology-substitution failure: the result would not have caught [[aops-d10e7db6]]. This workflow tests real production behavior only.

## Notes for the agent running the section

- You are the test instrument for half of each row. When asked whether you received a hook's `context_injection` payload, answer from your **actual context**, not from your model of what should have happened. Inferring "the Stop hook is configured so I must have seen it" is exactly the failure mode this test exists to catch.
- If your context for a turn does not include the expected payload, say "No, I did not receive that content in my context on this turn" — full stop. Do not soften with "but it may have been processed elsewhere".
- Cross-reference: the working channel-routing reference is `UserPromptSubmit`'s skills-routing-table injection (you reliably do see that). If your `UserPromptSubmit` answer pattern doesn't match the expected row, the test rig itself is broken — halt and report.
