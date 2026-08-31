---
id: temp_f4a9cb82
title: "wf-agentic-e2e-certification"
type: template
created: 2026-07-28T03:02:03.400645342+00:00
modified: 2026-07-28T03:02:03.400645342+00:00
last_modified: 2026-07-28T03:02:03.400675899+00:00
alias:
  - "temp_f4a9cb82-wf-agentic-e2e-certification"
  - "temp_f4a9cb82"
permalink: temp_f4a9cb82
tags:
  - wf-template
  - workflow
  - framework
  - testing
  - certification
  - hooks
---

## What this step does

Verify the framework's plugins actually work — hooks, MCP, skills, subagent tool binding — on every surface they ship to. Judgment is non-delegable here: the driving agent reads the evidence and issues verdicts; a script's exit code or a single string match never substitutes for that.

**Quiescence rule (applies throughout).** Never evaluate a loading screen. If a pane shows a spinner or a "working" indicator, wait and re-capture until the final response and a clean prompt are visible. Passing a check without observing its final state is a failure of judgment, not a pass.

A **persistently blank pane** — no spinner, no text at all — is a different failure signature from a busy spinner, not just a slower version of the same thing: it can mean an unrendered confirmation dialog (a trust prompt, an onboarding wizard) is sitting there waiting for input nobody sent, which looks identical to a dead hang from process state alone (alive, idle, zero CPU). Before concluding a worker is truly stuck, check for exactly this — one blind keypress is a cheap, non-destructive way to find out.

**Computed ≠ Delivered ≠ Seen.** A hook-log record proves a gate _computed_ output; a clean exit code plus the client's wire payload proves it was _delivered_; only the rendered transcript or pane proves the agent or user actually _saw_ it. State which layer each piece of evidence proves — see [[wf-session-hook-forensics]] for the full treatment of this distinction.

## 1. The surface matrix

The same plugins typically ship through several different install channels (terminal CLI, GUI app, various forms of cloud/remote session, worker containers per supported client), and the same backend tools can appear under **different name-prefixes per surface**. A wrong-prefix tool call fails with a not-found error — that is a _binding_ finding, not a server-health finding, and the two must not be conflated when triaging a failure.

Build the actual current surface × prefix matrix at test time (which surfaces exist and what each expects) rather than assuming a fixed list — surfaces and prefixes are exactly the kind of thing that drifts as install channels change. Container-based surfaces (one per supported client) additionally warrant the deep-dive in §3; the rest are quick probes (§2). Run every client's container variant with the same prompt so results are comparable — asymmetric breakage between clients is itself a finding worth reporting, not noise to average away.

## 2. Per-surface probe (run on every surface)

Five checks, in order. Each verdict needs its own receipt — a command and its output, a pane capture, or a file:line citation.

1. **Plugins present.** Check the surface's own plugin-listing mechanism (or, where none exists, the install directory structure directly). Expect exactly the intended set for that surface; for worker containers, also positively confirm that surfaces-only plugins are _absent_, not just that the expected ones are present.
2. **Hooks fire.** Start a session; expect the startup banner and the first-prompt hydration reminder. Hooks present in a terminal session but silently absent from a GUI-launched one is a specific, recurring failure class (a `PATH` issue — hook commands need to bootstrap their own environment on surfaces that don't inherit a shell profile).
3. **MCP alive.** Ask the session to call the surface's expected-prefix status tool. Expect a version/build identifier back. Record both the prefix that worked and the version returned — version skew across surfaces is itself a finding.
4. **Subagent binding.** Delegate the same status call to a subagent. This is the check that catches allowlist/namespace mismatches: the subagent's own tool-access configuration must carry a pattern matching _this_ surface's prefix. A subagent reporting every prefix variant as unavailable is a binding gap — file it.
5. **Negative check.** Confirm the _wrong_ prefix genuinely fails on this surface. If a name that should be absent instead resolves, a duplicate registration exists somewhere — a distinct class of defect from anything §1–4 catches.

Before filing anything new, check whether the specific failure shape already has a known cause on record — unset connection config silently overridden by stale shell state, an install channel that gets wiped on a routine restart, an agent allowlist pattern not matching the surface's actual prefix, a config-upload validator rejecting something the source file itself considers valid, and stale plugin names left in a setup script are all recurring shapes worth checking against before treating a failure as novel.

## 3. Container deep-dive (per-client worker surfaces)

Run when infrastructure, gate definitions, the plugin allowlist, or the container entrypoint changed — or as a periodic audit. Reuse the boot sequence and plugin pre-check from [[wf-self-test]] §2; forensics mechanics from [[wf-session-hook-forensics]]. Dispatch through the real production dispatch mechanism — never a hand-rolled interactive session, which bypasses exactly the container/config/credential-scoping machinery under test.

State these axes up front, then judge each independently with its own evidence (pass / fail / inconclusive — don't force a binary where the evidence doesn't support one):

1. **Hooks** fire for the events that actually occurred (computed layer), deliver cleanly (clean exit, no stderr), and the expected user-facing text actually appears in the pane (seen layer).
2. **Responses** are appropriate to the prompt and to any gate constraint in effect — the agent waits or complies rather than routing around a block. Test the full cycle: trigger the gate, satisfy it, confirm the original task resumes rather than stalling.
3. **Execution** — at least one real tool or shell call returns genuine success inside the container. "Blocked by a gate as designed" is a separate axis from this one, not a failure of it.
4. **Gates** — the gates that actually fire match what the tools invoked should trigger, produce the right state transition at the right point, and run in the mode the current dispatch configuration specifies. A gate that's supposed to block something but never visibly does is _inconclusive_, not a pass — don't round that up.
5. **Plugins** — exactly the allow-listed set, diffed against the container's own default config, with positive-absence checks for everything that should be excluded.
6. **Credentials** — confirm bot/service identity only: git identity, relevant env vars, no personal auth reachable, no ambient credential leakage. If the observed identity doesn't match the requirement, halt and file a task — do not silently pass, and do not patch the entrypoint inline during a verification run.

## 4. Closing pipeline

1. **Render the transcript yourself** before delegating any part of the write-up — pin the exact artifact so a later reviewer isn't left hunting for "a session matching this description" among stale same-named sessions.
2. **Independent evidence extraction** — a separate pass pulls verbatim proof from the raw logs (hook exit codes, context actually reaching the prompt, per-axis evidence for container runs), scoped to exactly the artefacts already pinned.
3. **Independent compliance ruling** — a separate pass rules on the pinned transcript plus the extracted evidence against the framework's own rules (data boundaries, honest epistemics, halt-on-failure). A ruling that cites an artefact not actually handed to it is invalid — re-pin and re-invoke rather than accept it.
4. **Certification report** — the §1 matrix as a verdict table (surface × five probes × verdict × receipt), the container axes if run, and every failure filed as one task per root cause (never per symptom). Clean up whatever the session left running.

## When to include

After any change touching hooks, MCP wiring, the plugin manifest, worker/container packaging, or dispatch mechanics — or as a periodic cross-surface audit. This is the outermost verification layer: it composes [[wf-self-test]] (single-surface infrastructure validation) and [[wf-session-hook-forensics]] (the forensic method for diagnosing anything either the matrix or the deep-dive turns up) rather than duplicating either.

## Source

Recovered verbatim (condensed formatting only, and platform/tool-specific proper nouns generalised since some named a client or mechanism since retired) from `.agents/skills/aops/workflows/12-agentic-e2e-certification.md`, deleted in the v0.6 plugin reorganisation (PR #2340) with no successor found anywhere in the rebuilt `plugins/` tree.
