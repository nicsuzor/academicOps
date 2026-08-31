---
alias:
- kb_831042d0-wf-self-test
- kb_831042d0
created: 2026-07-28T02:39:39.475916318+00:00
id: kb_831042d0
last_modified: 2026-07-28T03:01:21.927917772+00:00
modified: 2026-07-28T03:01:21.927916009+00:00
permalink: kb_831042d0
tags:
- wf-template
- workflow
- framework
- testing
- hooks
- certification
title: wf-self-test
type: template
---

## What this step does

End-to-end self-test of the session infrastructure itself — hook gates, MCP/PKB connectivity, subagent dispatch, and hook-output channel routing. Distinguishes "the infrastructure files are present" from "the infrastructure actually fires and delivers to the right place."

## 1. Hook gates verification

Test the layers of session infrastructure in order, and for each layer verify it fires **and** that its output lands on the correct channel (agent-only vs. user-visible vs. both — see §3):

- SessionStart — principles loaded, session state written (agent-only channel).
- MCP/PKB — semantic search and task metadata answer, the server is responsive.
- PreToolUse — a hydration/gate check blocks the operation it's meant to block, and the user can see why.
- A PKB write — confirm it actually unblocks whatever gate was waiting on it.
- Any periodic compliance check — confirm it fires per its own instructions.
- Skills — invoke a representative sample and confirm they run.
- Subagents — dispatch at least one and verify context passes through correctly.
- Workers/containers — dispatch a local worker and confirm it completes.
- Stop gates — confirm a stop is prevented before a required handover step, and permitted after.
- Handover — confirm the handover mechanism produces genuinely useful next-step instructions, and that they get executed.

**Everything needed should already be in context at startup** — from hooks, from referred files. If it isn't, halt and report the gap rather than guessing or hunting for information that should have been supplied.

## Step 0 — verify hooks are actually running, before testing specific behaviour

Read the session's own transcript JSONL directly (not a derived summary).

**Do not grep for a single marker string. Read `stderr` on every hook attachment.** Hooks degrade in two different ways, and a keyword grep for one crash signature only catches the first:

1. **Hard crash** — the attachment type itself signals a non-blocking error, or the exit code is non-zero. The crash traceback is in `stderr`. No downstream hook-log file gets written for that event at all.
2. **Silent degradation** — the attachment reports success (exit 0) but `stderr` is non-empty. The hook "succeeded" in the sense of not blocking the turn, while some substep inside it actually failed (e.g. a per-event logger throwing, so no log line gets written even though the hook ran). A grep for the hard-crash signature is blind to this; only reading `stderr` on success attachments finds it.

**The correct check**: iterate every record with an attachment, inspect `attachment.stderr` on each. Any non-empty `stderr`, regardless of exit code or attachment type, is a finding. Group by hook name and first stderr line — a config-load failure typically repeats on every event. Halt before proceeding if anything turns up: a degraded-but-exit-0 hook is not a pass. The absence of a downstream log file does not by itself mean the hook is unhealthy — the logger may have thrown on an otherwise-successful hook — so check stderr before concluding either way.

## 2. Worker/container session validation

Run after any change to worker default settings, entrypoint, plugin packaging, or CLI version. Discriminates "infrastructure files present" from "infrastructure actually fires." Run every supported client — asymmetric breakage across clients is common and easy to miss if only one is tested.

Walk these layers in order; stop at the first failure:

**§0 Image freshness** — compare the container image's build timestamp against the last commit touching its Dockerfile or bundled files. If stale, do a clean verification build (not an incremental one — an incremental build with cached layers can produce a false-green result on exactly the files that changed).

**§0.5 Plugin pre-check** — before any boot-signal checks, verify inside the container that exactly the intended plugin set is installed (check the client's own plugin-listing mechanism where one exists; where it doesn't, confirm the install structurally by listing the plugin directory). A marketplace cache-miss or install failure is silent at startup and only shows up later as a confusing hook or tool failure — catching it here takes seconds and saves a much longer misdiagnosis.

**§1 Boot signals** — drive the session with the same permission/auto-approval flags production dispatch actually uses (not an interactive/plan-mode flag), capture the pane output, and look for the expected startup banner with no onboarding or trust prompts blocking it. Do not use incidental footer text as a boot signal — it's not a reliable indicator.

> **Permission mode matters for validity.** A smoke test run in plan/interactive-approval mode does not reflect actual autonomous-dispatch behaviour and will not catch permission-related failures. Use plan/interactive mode only when the thing under test genuinely is the human-in-the-loop path.

**§2 First prompt round-trip** — send a trivial prompt. A hook-blocked error here is itself useful evidence (it means the hook fired and errored) — treat that error text as primary evidence, not noise to route around. Before adding a polling loop to wait for a response, check whether the failure mode already gives you a liveness signal for free.

**§3 Environment sanity** (if §2 failed) — check ID/permission resolution, expected startup artifacts, and whether the plugin install path matches what the config expects.

**§4 Skill + subagent exercise** — invoke a representative skill and dispatch a representative subagent; verify actual visible output, not just that the call returned without erroring.

**§5 Observability** — hook JSONL is actually being populated; the PKB/MCP connection answers a trivial status call (not refused, not timed out). If the hook JSONL is missing or empty, diagnose with Step 0's stderr-on-every-attachment method — absence alone doesn't distinguish a misconfigured log path from an import-time crash from a logger that silently threw on an otherwise-successful hook.

**§6 Cleanup** — exit the session and tear down the container/session cleanly; confirm no manual cleanup step is actually required (a self-removing container should self-remove). Repeat for every other client.

On any failure: file one issue per root cause, not per symptom, and append to an existing tracking task/PR where one already exists rather than opening a duplicate.

## 3. Hook output channel routing

Verifies every configured hook routes its output to the channel it's meant to reach — this is a regression class in its own right (a gate meant to log silently that instead leaks a wall of text to the user, or a gate meant to inform the user that instead only reaches agent context, are both real failure modes that have shipped before).

**Channel model**: one channel is user-visible surface; the other is the agent's own next-turn context. A hook's disposition — which channel(s) it's meant to reach — is a property of that specific (client, event, gate) combination and should be looked up from the live authoritative source at test time, never assumed from memory or a stale local note, since gates get added, retired, and reclassified.

**Pre-flight**: confirm hooks are executing at all before judging routing (Step 0) — total hook failure reads as "no findings" here, which is the wrong conclusion; confirm at least one hook processed successfully first.

**Verification approach**: read the live hook configuration and gate implementation to identify active payloads; look up the intended channel for each; then either trigger it in a real session or evaluate post-hoc from session artefacts. One known false-positive shape to watch for: a "warn" verdict on a stop-type hook can trigger a legacy fallback path that leaks agent-only content to the user channel — check the verdict type before concluding a routing bug.

**Compute the expected disposition, don't restate a memorised table.** For the (client, event) pair under test, derive from the live channel specification: does any message reach the user at all; does the agent receive context, and via which mechanism (non-blocking delivery, or block-to-inject — noting that on at least one client family a block's "reason" text is the agent's only channel and is _also_ user-visible, so there is no such thing as a pure agent-only block channel on that client); and is there a "agent gets the full body, user gets only a short summary" split disposition available on this client/event at all (this disposition has historically been retired on at least one client after being found to silently discard blocking output from co-located gates sharing the same hook entry — don't assume it's live without checking the current mechanism).

**Pass/fail is computed from those fields, not read off a fixed table**: agent-full/user-summary → the agent transcript must contain the full body and the user pane only a short summary, never the full body (flag as a drift finding if you find equipment for this disposition present but the code disagrees that it's reachable); agent-only → no user-visible message, but the agent gets the content; user-only → the reverse; both → same text reaches both sides; unmapped/inert → no live channel at all, the event is log-only or dropped by the client — record and move on, not a bug.

Any mismatch between the computed expectation and what you actually observe in the pane/transcript is a routing bug — file it with the session id, the transcript excerpt, the agent's verbatim answer, and which specific expectation it contradicts. Don't attempt to fix routing inside a self-test session.

**No automated probe assumed.** Absent a maintained automated harness for this specific check, drive the client directly (tmux or equivalent), capture the pane at two points — right after the triggering action and again after a short settle — to distinguish a transient toast from steady-state UI, and cross-check the raw transcript JSONL (via Step 0's stderr-on-every-attachment method) for what actually reached agent-side context.

## When to include

After any change to hook configuration, gate definitions, the plugin allowlist, worker/container packaging, or client dispatch mechanics. Feeds into [[wf-agentic-e2e-certification]] as the infrastructure-level validation layer beneath that template's cross-surface matrix.

## Source

Recovered verbatim (condensed formatting only) from `.agents/skills/aops/workflows/11-self-test.md`, deleted in the v0.6 plugin reorganisation (PR #2340) with no successor found anywhere in the rebuilt `plugins/` tree. Its own internal references depended on two specs (`specs/adhd/surface-contract.md`, `specs/CLIENT-TRANSLATION.md`) that are themselves no longer present on `v0.6` as of this recovery — the channel-routing section above has been generalised away from those specific pointers rather than left citing files that no longer resolve; re-derive the live channel specification from whatever the current hook/channel implementation actually is before relying on §3.
