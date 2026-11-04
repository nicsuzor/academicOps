---
id: develop-specification
type: template
description: Collaboratively develop a complete task/feature specification before implementation begins
---

# Process: Develop Specification

**When**: automating a manual process, or a good automation/build candidate has
been identified. Purpose: a complete spec before implementation starts —
implementation without this template first is scope-creep waiting to happen.

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Steps

1. **Identify the target** — confirm a manual process worth automating, or a
   feature worth specifying.
2. **Create the spec document** from the standard template.
3. **Problem statement and user stories** -- collaborative: what, why, and for which human user. User stories must always be written from the perspective of a human person whom the system serves, never an agent, persona, worker, or internal component (`As an agent, I want...`); agents do not want anything and are given capabilities only to fulfil human user requirements.
4. **Acceptance criteria** -- defined from the human principal's perspective, including a persona paragraph and any
   qualitative dimensions, not just mechanical checks.
5. **Scope** — propose initial scope, explicitly define boundaries (what's out).
6. **Dependencies** — required infrastructure/data; document error handling.
7. **Test and verification design** — for code that executes, an integration
   test that validates each criterion it serves and detects each failure mode;
   for any other criterion, how it is verified.
8. **Implementation approach** — components, data flow, risk assessment.
9. **Effort and risk** — estimates, mitigation plans.
10. **Rule-compliance review** — obtain an independent agent review of the draft
    specification against framework axioms and rules (proportionality, single
    source of truth, closure). Resolve any required changes before advancing.
11. **Review** — record the independent agent review verdicts on the PKB task or note.
12. **Finalize and submit** — for a Stage 1 design or spec task preceding a build, record the drafted spec change and the independent agent review verdicts in a PKB note the Stage 2 task points to, open no PR, and release the task as `done` once independent agent review passes (or release as `partial` where an explicit user decision on competing design alternatives is required), never releasing as `review` and never putting a spec to the user for approval on its own. Implementation proceeds on the build task (or a bounded single-task change updating spec and code together), which carries the build and spec change onto the feature branch and opens the single draft PR into `dev`, with the spec still editable; mark the draft PR ready for review (`gh pr ready`) once the feature is written and proportionate review by independent agents is posted to the PR thread, without waiting for approval; spec and feature reach the user on that single PR and merge together after full review.

## Verification before proceeding to implementation

Acceptance criteria section complete; each criterion maps to its test where
code executes, or to its verification otherwise; criteria confirmed on the record to define "done".
