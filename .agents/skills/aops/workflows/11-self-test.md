# Self-Test Workflow

## 1. Hook Gates Verification

Testing the four layers of session infrastructure. For each layer, verify it fires AND that output lands on the correct channel (see §3 for channel-routing matrix):

- SessionStart: principles loaded, session env file written (agent-only channel)
- MCP & PKB: semantic search, task metadata indexed, Rust server responsive
- PreToolUse: hydration gate blocks write operations; user sees why (both channels)
- PKB write: task creation unblocks gates
- RBG rbg: invoke periodic compliance rbg per instructions
- Skills: invoke /plan, /aops, /remember
- Subagents: dispatch ida or marsha; verify context passing
- Polecats: dispatch local workers (gemini and claude) via uv run
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

**§2 First UserPromptSubmit** — send a trivial prompt. Hook-blocked error = hook fired and errored. Treat error text as primary evidence. **Liveness check before polling**: before writing a poll loop here, check whether the callee already surfaces liveness or completion — the hook-blocked error IS the liveness signal; do not build a poll loop if the callee already exposes one.

**§3 Environment sanity** (if §2 failed) — UID resolution, fast-path artifacts, plugin install path vs. expected path.

**§4 Skill + subagent exercise** — `/aops-core:aops` + `Agent(subagent_type='aops-core:ida')`. Verify visible output, not just return.

**§5 Observability** — hooks JSONL populated; PKB MCP answers 406 (not refused/timeout); `mcp__plugin_aops_pkb__*` tool answered in §4. If hooks JSONL is missing or empty, diagnose per **Step 0's stderr-on-every-attachment method** (not a `hook_non_blocking_error` grep): absence does not distinguish a misconfigured log path from an import-time crash from a logger that threw on an exit-0 hook.

**§6 Cleanup** — `/exit` → `tmux kill-session` → `polecat nuke <crew>`. Repeat for other client.

On failure: file one issue per root cause, not per symptom. Append to existing PR/task when one exists. Refs: [[aops-7c45802b]], GH #1237.

## 3. Hook output channel routing

Regression cover for [[aops-d10e7db6]] — Stop-hook RBG advisory leaked to user surface. Verifies every configured hook routes output to its intended channel. Run as part of the v0.4 release self-test pass.

**Channel model:** `system_message` → user-visible surface; `context_injection` → agent's next-turn context.

Authoritative source for active hooks: `hooks.json`. Channel dispatch: `HookRouter.output_for_claude` / `output_for_gemini`.

**Expected disposition is not restated here.** Derive it at test time from the SSoT, not a local copy that can silently drift as gates are added, retired, or reclassified: the **Gate user-visibility** table in [`specs/adhd/surface-contract.md`](../../../../specs/adhd/surface-contract.md#gate-user-visibility) (per-gate `silent` / `same` / `keep`) plus the per-(client, event) capability matrix in [`specs/CLIENT-TRANSLATION.md`](../../../../specs/CLIENT-TRANSLATION.md#authoritative-channel-matrix-per-client) (what a channel can even deliver). For each hook event under test (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, SubagentStart, SubagentStop, PreCompact, Notification, SessionEnd — see the Walk-through below), look up every gate that fires on it in the surface-contract table before judging pass/fail.

**Pre-flight: confirm hooks are executing** (per Step 0 — total hook failure reads as "no findings" here, the wrong answer). Confirm at least one hook event processed successfully before judging routing.

**Verification approach:** (1) read `hooks.json` + gate implementation to identify active payloads; (2) verify intended channels match matrix; (3) trigger in real session or evaluate post-hoc from artifacts. Caution: warn verdict on Stop triggers legacy fallback (router.py:838, #1042) leaking `context_injection` to user — false positive; check verdict type.

**Channel vocabulary — derive, do not restate.** The disposition for a given (client, event) is not a fixed named category memorised here — it is computed from `channel_spec(client, event)` in [`aops-core/hooks/client_spec.py`](../../../../aops-core/hooks/client_spec.py) (the same table CLIENT-TRANSLATION.md's authoritative channel matrix renders). Look up the spec for the hook under test and read off its fields:

- `user_message` — does ANY message reach the user on this channel?
- agent receives context — `agent_context_without_block` (non-blocking delivery) OR `can_block` (block-to-inject; a block's `reason` is the agent's only channel, and on Claude/Gemini that `reason` is ALSO user-visible — there is no agent-only block channel).
- `agent_full_user_summary` — the quiet-split disposition: agent gets the FULL body, user sees only a short summary of it (never the body). **Currently `False` for every (client, event) in the table.** The mechanism that would set it True — Claude's `asyncRewake` (Stop, exit 2) — was retired 2026-07-08 (GH #2181, fixed by PR #2189) after it was found to silently discard `decision:block` output from co-located block-mode gates sharing the same Stop entry. See `ChannelSpec.agent_full_user_summary`'s docstring and `tests/hooks/test_client_spec.py::TestChannelTable::test_claude_stop_asyncrewake_quiet_split_retired` / `test_no_client_event_has_the_retired_quiet_split`. Do not assume this disposition is exercised anywhere live; if a probe shows it True and the code disagrees, that is itself a finding (channel_spec has drifted from the client) — file it, don't force a pass.

**Pass / fail — computed from the fields above, not a restated table:**

| `agent_full_user_summary` | `user_message` | agent gets context | Disposition                 | Pass condition                                                                                                                                                                                                                        |
| ------------------------- | -------------- | ------------------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `True`                    | —              | —                  | `agent-full / user-summary` | Agent transcript contains the FULL body. User pane shows ONLY a short summary line — the full body must never render to the user. (Not currently reachable — see note above; a live hit here is a drift finding, not a routine pass.) |
| `False`                   | `False`        | `True`             | `agent-only`                | `system_message` user-side: **No**. `context_injection`/agent-side: Yes.                                                                                                                                                              |
| `False`                   | `True`         | `False`            | `user-only`                 | `system_message` user-side: Yes. Agent-side: No.                                                                                                                                                                                      |
| `False`                   | `True`         | `True`             | `both`                      | `system_message` user-side: Yes. `context_injection`/agent-side: Yes — and (Claude/Gemini Stop/block) it is the SAME text on both sides, since `reason` is the only agent channel and it is also user-visible.                        |
| —                         | `False`        | `False`            | _(unmapped/inert)_          | No live channel — the event is log-only or the client drops it. Record and move on; not a routing bug.                                                                                                                                |

Any mismatch between the computed expectation and the observed pane/transcript is a **routing bug** — halt and file under [[epic-9fa15948]] with session id, transcript excerpt, agent's verbatim answer, and which `channel_spec()` cell it contradicts. Do not attempt to fix routing in this session.

**Automated Live Verification (`pty_hook_probe.py`)**

The manual walkthrough has been replaced by the PTY host testing system (`scripts/pty_hook_probe.py`), which automates end-to-end verification. This script drives live interactive `claude` and `agy` clients in a headless `tmux` pane.

**Run the probe:**

```bash
uv run python scripts/pty_hook_probe.py --client all
```

The script explicitly verifies BOTH surfaces:

1. **User Surface:** Uses `tmux capture-pane` with early and late snapshots to verify that transient toasts, feedback banners, and notifications are actually rendered to the user, and that agent-only context never leaks into the UI.
2. **Agent Surface:** Checks the transcript JSONL (for Claude) or model echo (for agy) to confirm the agent successfully received `context_injection`.

This maintains the "no synthetic testing" rule by verifying real runtime behavior in a real terminal context, closing the structural blindness gap of previous synthetic JSON harnesses without requiring manual walkthroughs.
