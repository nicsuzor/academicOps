# Self-Test Workflow

## 1. Hook Gates Verification

Testing the four layers of session infrastructure. For each layer, verify it fires AND that output lands on the correct channel (see §3 for channel-routing matrix):

- SessionStart: principles loaded, session env file written (agent-only channel)
- MCP & PKB: semantic search, task metadata indexed, Rust server responsive
- PreToolUse: hydration gate blocks write operations; user sees why (both channels)
- PKB write: task creation unblocks gates
- RBG enforcer: invoke periodic compliance enforcer per instructions
- Skills: invoke /plan, /aops, /remember
- Subagents: dispatch junior or marsha; verify context passing
- Polecats: dispatch remote workers (gemini and claude) over SSH
- Stop Gates: stop prevented before handover; permitted after
- Handover: /dump provides useful instructions; execute them all

IMPORTANT: All required information should be in context at startup, within hooks, and in referred files. If insufficient, HALT and report FAILURE to provide adequate instruction. Do NOT guess or seek out information that should have been provided.

## Step 0: Verify hooks are operational in THIS session

Before testing any specific hook behavior, verify that hooks are actually running. Read your own session transcript JSONL (for background jobs: `$CLAUDE_JOB_DIR/../<session-id>.jsonl`; for interactive sessions: `~/.claude/projects/<project-dir>/<session-id>.jsonl`).

**Do NOT grep for a single marker string. Read `stderr` on EVERY hook attachment.** Hooks degrade in two distinct ways, and a keyword grep for `hook_non_blocking_error` catches only the first:

1. **Hard crash** — attachment `type` is `hook_non_blocking_error` (or `exitCode != 0`). The `stderr` field carries the crash traceback. The router never wrote a `*-session-hooks.jsonl`.
2. **Silent degradation** — attachment `type` is `hook_success` with `exitCode: 0` **but a non-empty `stderr`**. The hook "succeeded" (didn't block the turn) while a substep failed — e.g. `WARNING: Failed to log hook event: ...`, which means the per-event logger threw and **no `*-session-hooks.jsonl` was written even though hooks ran**. A grep for `hook_non_blocking_error` is blind to this; only reading stderr on success attachments finds it.

**The correct check:** iterate all records with an `attachment` field; for each, inspect `attachment.stderr`. **Any non-empty `stderr`, regardless of `exitCode` or attachment `type`, is a finding.** Group by `hookName` + first stderr line; report the distinct warnings and how many events each affects (a config-load failure typically repeats on every event). HALT before proceeding — a degraded-but-exit-0 hook is NOT a pass. The `*-session-hooks.jsonl` is written only after successful processing; its absence does NOT mean healthy (the logger may have thrown on an exit-0 hook), so read success-attachment stderr before concluding.

## 2. Polecat session validation

Run after changes to `polecat/defaults/*-settings.json`, entrypoint, plugin packaging, or CLI upgrades. Discriminates "infrastructure files present" from "infrastructure actually fires." Run both clients (Claude and Gemini) — asymmetric breakage is common. Mechanics in [[tests/harness/README.md]].

Walk layers in order; stop at first failure:

**§0 Image freshness** — `docker images aops-crew --format '{{.CreatedAt}}'` vs last commit touching Dockerfile or bundled files. Stale → `make verify-docker` (**not** `make build-docker` — verification requires a clean build; `--no-cache` prevents stale cached layers from producing a false-green result; issue #1452).

**§0.5 Plugin pre-check** — Before any boot signal checks, run `claude plugin list` inside the container (and `gemini extensions list` for Gemini sessions) to verify plugins and extensions loaded correctly. A marketplace cache-miss or install failure is silent at startup and only manifests later as hook failures or missing tools; this step catches it in seconds. If either command returns no plugins / no extensions, halt and diagnose before proceeding.

**§1 Boot signals** — spin via tmux using the **same permission flags that `polecat run` uses** (auto-approval / `--dangerously-skip-permissions`, not plan mode), then `capture-pane -p -S -2000`. Look for router banner, no onboarding/trust prompts. Do NOT use footer text as a boot signal (#1197).

> **Permission mode:** Crew smoke tests for autonomous-worker validation must match the production permission model — use the same flags as `polecat run` (bypass-permissions / auto-approval). **Do not start crew containers in plan mode for these tests**: plan mode does not reflect actual polecat dispatch behavior and will not catch permission-related failures. Plan mode is acceptable only when explicitly testing interactive crew workflows where human-in-the-loop approval is the intended behavior.

**§2 First UserPromptSubmit** — send a trivial prompt. Hook-blocked error = hook fired and errored. Treat error text as primary evidence.

**§3 Environment sanity** (if §2 failed) — UID resolution, fast-path artifacts, plugin install path vs. expected path.

**§4 Skill + subagent exercise** — `/aops-core:aops` + `Agent(subagent_type='aops-core:junior')`. Verify visible output, not just return.

**§5 Observability** — hooks JSONL populated; PKB MCP answers 406 (not refused/timeout); `mcp__plugin_aops-core_pkb__*` tool answered in §4. If hooks JSONL is missing or empty, diagnose per **Step 0's stderr-on-every-attachment method** (not a `hook_non_blocking_error` grep): absence does not distinguish a misconfigured log path from an import-time crash from a logger that threw on an exit-0 hook.

**§6 Cleanup** — `/exit` → `tmux kill-session` → `polecat nuke <crew>`. Repeat for other client.

On failure: file one issue per root cause, not per symptom. Append to existing PR/task when one exists. Refs: [[aops-7c45802b]], GH #1237.

## 3. Hook output channel routing

Regression cover for [[aops-d10e7db6]] — Stop-hook RBG advisory leaked to user surface. Verifies every configured hook routes output to its intended channel. Run as part of the v0.4 release self-test pass.

**Channel model:** `system_message` → user-visible surface; `context_injection` → agent's next-turn context.

Authoritative source for active hooks: `hooks.json`. Channel dispatch: `HookRouter.output_for_claude` / `output_for_gemini`. Re-verify rows before each run — new events in `hooks.json` make this table silently incomplete.

| Hook               | Expected   | Why                                                                      |
| ------------------ | ---------- | ------------------------------------------------------------------------ |
| `SessionStart`     | agent-only | Boot-time principles into agent context (see §1)                         |
| `UserPromptSubmit` | agent-only | Hydrator injection. **Canonical working reference.**                     |
| `PreToolUse`       | both       | User sees why denied; agent gets recovery instructions                   |
| `PostToolUse`      | agent-only | Post-hoc observations feed next agent turn                               |
| `Stop`             | agent-only | RBG advisory in `additionalContext`. [[aops-d10e7db6]] is the inversion. |
| `SubagentStart`    | agent-only | Dispatch context to subagent; user surface quiet                         |
| `SubagentStop`     | agent-only | Completion summary to parent agent, not user                             |
| `PreCompact`       | TBD        | No active gate; flag any payload and escalate                            |
| `Notification`     | user-only  | By definition a user-surface event                                       |
| `SessionEnd`       | agent-only | Cleanup advisory for next session; same dispatch as Stop (router.py:807) |

**Pre-flight: confirm hooks are executing** (per Step 0 — total hook failure reads as "no findings" here, the wrong answer). Confirm at least one hook event processed successfully before judging routing.

**Verification approach:** (1) read `hooks.json` + gate implementation to identify active payloads; (2) verify intended channels match matrix; (3) trigger in real session or evaluate post-hoc from artifacts. Caution: warn verdict on Stop triggers legacy fallback (router.py:838, #1042) leaking `context_injection` to user — false positive; check verdict type.

**Pass / fail:**

| Expected     | Pass condition                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------------------- |
| `user-only`  | `system_message` user-side: Yes. `context_injection` user-side: **No**. Agent-side: No.                    |
| `agent-only` | `system_message` user-side: Yes. `context_injection` user-side: **No** (inversion guard). Agent-side: Yes. |
| `both`       | `system_message` user-side: Yes. `context_injection` user-side: **No**. Agent-side: Yes.                   |
| `TBD`        | Record all; do not pass/fail — escalate.                                                                   |

Any mismatch is a **routing bug** — halt and file under [[epic-9fa15948]] with session id, transcript excerpt, and agent's verbatim answer. Do not attempt to fix routing in this session.

**Walk-through** (interactive, fresh Claude session; repeat for Gemini): trigger each hook — SessionStart: start session; UserPromptSubmit: any prompt; PreToolUse/PostToolUse: trivial Read; Stop: finish a turn; SubagentStart/Stop: dispatch subagent; PreCompact: /compact; Notification: any notification action; SessionEnd: /exit. After each, ask the agent explicitly whether it received the `context_injection` payload in its context. The "do not infer" guard is load-bearing — the agent answers from actual context, not from its model of expected behavior.

**Post-hoc transcript evaluation** (auditing past sessions): confirm plugin version matches version under test. Read hooks JSONL and transcript JSONL directly — no grep shortcuts. Cross-reference: (a) `context_injection` appears in transcript system-reminders; (b) `system_message` appears in user output; (c) `context_injection` does NOT appear in user output (leakage = inversion bug). Record per pass/fail criterion; file routing bugs the same way.

**No synthetic testing.** This verifies live runtime behavior — the gap between "Python produces correct JSON" and "runtime delivers to correct surface." Stdin piping, unit harnesses, mock events, and injected payloads cannot catch [[aops-d10e7db6]]. Methodology-substitution is a failure.

**Notes for agent running §3:** answer "did you receive X payload" from your **actual context**, not from your model of what should have happened. If you didn't receive it, say "No, I did not receive that content in my context on this turn" — full stop. The `UserPromptSubmit` injection is the working reference; if that row doesn't match expected, the test rig is broken — halt and report.
