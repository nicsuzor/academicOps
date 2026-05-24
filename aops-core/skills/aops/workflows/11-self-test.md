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

Before testing any specific hook behavior, verify that hooks are actually running. Read your own session transcript JSONL (for background jobs: `$CLAUDE_JOB_DIR/../<session-id>.jsonl`; for interactive sessions: `~/.claude/projects/<project-dir>/<session-id>.jsonl`). Search for records containing `"hook_non_blocking_error"`. If any exist, hooks are broken — the attachment's `stderr` field contains the crash traceback. **HALT and report the hook failure before proceeding.**

The hooks JSONL (`*-session-hooks.jsonl`) is written by the router AFTER successful hook processing. When hooks crash at import time (e.g., `NameError`, `ImportError` in the router or its dependencies), this file is never created. The session transcript JSONL is the ground-truth artifact for hook crash detection — it records `hook_non_blocking_error` attachments written by the CLI itself, not by the router.

---

## 2. Polecat session validation

Run after changes to `polecat/defaults/*-settings.json`, entrypoint, plugin packaging, or CLI upgrades. Discriminates "infrastructure files present" from "infrastructure actually fires." Run both clients (Claude and Gemini) — asymmetric breakage is common. Mechanics in [[tests/harness/README.md]].

Walk layers in order; stop at first failure:

**§0 Image freshness** — `docker images aops-crew --format '{{.CreatedAt}}'` vs last commit touching Dockerfile or bundled files. Stale → `make build-docker`.

**§1 Boot signals** — spin via tmux, `capture-pane -p -S -2000`. Look for router banner, plan mode, no onboarding/trust prompts. Do NOT use footer text as a boot signal (#1197).

**§2 First UserPromptSubmit** — send a trivial prompt. Hook-blocked error = hook fired and errored. Treat error text as primary evidence.

**§3 Environment sanity** (if §2 failed) — UID resolution, fast-path artifacts, plugin install path vs. expected path.

**§4 Skill + subagent exercise** — `/aops-core:aops` + `Agent(subagent_type='aops-core:junior')`. Verify visible output, not just return.

**§5 Observability** — hooks JSONL populated; PKB MCP answers 406 (not refused/timeout); `mcp__plugin_aops-core_pkb__*` tool answered in §4. **Absence of hooks JSONL does not distinguish "log path misconfigured" from "hooks crashing at import time."** If missing or empty, also check the session transcript JSONL for `hook_non_blocking_error` attachment records — these are written by the CLI (not the router) when a hook process exits non-zero, and the `stderr` field contains the crash traceback.

**§6 Cleanup** — `/exit` → `tmux kill-session` → `polecat nuke <crew>`. Repeat for other client.

On failure: file one issue per root cause, not per symptom. Append to existing PR/task when one exists. Refs: [[aops-7c45802b]], GH #1237.

---

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

**Pre-flight: confirm hooks are executing.** Before verifying channel routing, confirm that at least one hook event has been processed successfully. Check the hooks JSONL for any entry with a successful verdict. If no such entry exists, or if the hooks JSONL is absent, check the session transcript JSONL for `hook_non_blocking_error` records. If hooks are not running at all, this workflow cannot produce valid routing results — halt and diagnose per Step 0 above. Total hook failure reads as "no findings" in this section, which is the wrong answer.

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
