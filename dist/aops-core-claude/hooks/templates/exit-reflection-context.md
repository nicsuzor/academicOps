---
name: exit-reflection-context
title: Exit-Reflection Context Template
category: template
description: |
  Template written to temp file for the FULL-tier exit-reflection checklist
  (self-audit or a dispatched auditor). Consolidates the former rbg-context.md
  (compliance audit) and qa-context.md (verification) framings into one
  session record (aops_4c2949d9).
  Variables: {session_context} (chronological session record),
             {tool_name} (tool that triggered the check),
             {active_skill} (current active skill if any; "none" if no skill),
             {skill_scope} (authorized scope description for the active skill, empty if none)
  Ordering (cache-prefix rule): all static instruction is emitted FIRST as a
  stable prefix; the variable payload ({active_skill}, {skill_scope},
  {session_context}) is appended LAST. {session_context} ends with the
  audit-complete sentinel, which must remain the final line of the file so a
  truncated read is detectable (aops-e4e90f31).
---

# Exit-Reflection Record

This is the full session record for the exit-reflection checklist — self-audit or a dispatched auditor. Ground every judgment in what actually happened, not what was claimed.

## How to read this file

- The **Active Skill Context** section names the skill (if any) the agent is operating under. If a skill is shown (not "none"), the agent has implicit authority for actions that skill requires — evaluate against that skill's authorized scope; actions within scope are NOT violations.
- The **Session Narrative** section is a chronological record of the entire session (windowed to the most recent turns). Use it to detect workflow anti-patterns and to judge whether delivered work is real, complete, correct, and high quality.

## What to check

1. **RBG-lens self-audit** — review the session against the framework axioms. Any violations?
2. **Verification** — is the work real, complete, correct, and high quality? Does it meet every requirement, and does it actually serve the user? Trace evidence: run it, read the diff, check imports resolve and call sites line up.
3. **Durable capture** — is everything load-bearing already saved to the PKB/task, or only in this transcript (which is ephemeral)?
4. **Substance vs form** — a claim of compliance is not compliance. Reject a self-graded ritual that recites this checklist's headings without showing the underlying evidence (command + observed output, file:line, or a resolving link) for each load-bearing claim.

## Active Skill Context

**Active skill**: {active_skill}

{skill_scope}

## Session Narrative

{session_context}
