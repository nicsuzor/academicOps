---
id: wf-agentic-e2e-certification
title: "wf-agentic-e2e-certification"
type: template
created: 2026-07-28T03:02:03.400645342+00:00
modified: 2026-10-26T00:00:00.000000000+00:00
last_modified: 2026-10-26T00:00:00.000000000+00:00
permalink: wf-agentic-e2e-certification
tags:
  - wf-template
  - workflow
  - framework
  - testing
  - certification
  - hooks
---

## What this step does

Verify framework plugins, hooks, services, subagent bindings, and runtime constraints end-to-end across target surfaces and release candidates. Judgment is non-delegable: the certifying agent inspects primary evidence and issues qualitative verdicts; exit codes or string matches never substitute for qualitative evaluation.

## Core Evidentiary Principles

1. **Quiescence rule.** Never evaluate an in-flight, transitional, or loading screen. Wait until the final response and a clean prompt are visible before capturing evidence or issuing a verdict.
2. **Computed ≠ Delivered ≠ Seen.** A hook log proves a gate or instruction was _computed_; wire logs prove it was _delivered_; only the rendered transcript or pane proves the agent _saw_ and operated under it. State explicitly which layer each piece of evidence proves (see [[wf-session-hook-forensics]]).
3. **Live trace data preferred.** When evaluating agent behavior and retrieval quality, using existing live data from OpenTelemetry (OTel) traces is STRONGLY preferred over generating synthetic test data. Assemble genuine samples of call-and-response pairs from actual sessions. Only generate new test interactions if recorded responses do not exist for a required prompt class.
4. **Class-based comparison.** Prompts across evaluation buckets (baseline vs. candidate) do not need to be identical string matches. They need only represent roughly similar classes of queries or tasks (conceptual queries, explicit lookups, constraint edges) to compare qualitative performance and drift without treating evaluation as a brittle unit test.

## Certification Phases

The certification campaign composes three modular test workflows across target deployment surfaces:

### Phase 1: Surface & Environment Integrity

Execute [[wf-surface-probe]] on each target surface (CLI, GUI, background workers, remote sessions). Verify:

- Plugins and extensions match the expected allowlist for that surface.
- Session lifecycle hooks trigger cleanly on startup and initial prompt hydration.
- Core backend services respond and return results (for example, test that the Personal Knowledge Base returns results).
- Subagent delegation binds tools and executes without namespace rejections.
- Unauthorized tools or out-of-scope boundaries fail closed (negative security check).

### Phase 2: Runtime Gates & Constraint Compliance

Execute [[wf-gate-compliance]] inside target execution and container environments (leveraging boot validation from [[wf-self-test]]). Verify:

- Hook delivery is verified across computed, delivered, and seen layers.
- Under policy gates and blocks, the agent complies rather than evading or routing around constraints.
- The complete block-satisfy-resume cycle functions cleanly without stalls or lost context.
- Tool operations execute successfully within sandboxed runtime boundaries.
- Ambient credentials remain strictly isolated to authorized service/bot identities with zero private credential leakage.

### Phase 3: Live Trace Comparative Evaluation

Execute [[wf-trace-sample-eval]] comparing candidate performance against baseline behavior. Verify:

- Samples are drawn primarily from historical OTel traces, pairing before-and-after call and response interactions.
- New test data is generated only for prompt classes lacking existing trace responses.
- Qualitative judging evaluates retrieval relevance, task completion, and constraint adherence across representative prompt classes.
- Behavioral drift and regression metrics are documented with pinpoint citations.

## Closing Pipeline

1. **Render and pin artifacts.** Pin specific session IDs, transcript captures, and trace spans before delegating write-up to prevent evaluation drift.
2. **Independent evidence extraction.** Extract verbatim receipts (hook exit logs, context payloads, pane outputs) for every tested axis.
3. **Independent compliance review.** Rule on pinned evidence against framework axioms (data boundaries, honest epistemics, halt-on-failure).
4. **Certification report.** Produce a unified certification matrix (surfaces × test phases × verdicts × receipts). File any defect as one task per root cause (never per symptom).

## When to include

After any change touching hooks, core service wiring, plugin manifests, container packaging, or dispatch mechanics, and prior to tagging release candidates.
