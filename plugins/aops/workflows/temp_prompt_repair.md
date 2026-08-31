---
alias:
- temp_prompt_repair-prompt-repair
- temp_prompt_repair
category: process
created: 2026-08-28T03:50:17.175107811+00:00
description: 'Select when a reusable prompt or instruction set produced output that fails its readers: dispatch independent blind critiques, synthesise a causal diagnosis tracing each failure to the prompt, draft and validate replacement instructions via an independent evaluator, and deliver them in place. Not for one-off revision of a single artifact.'
id: temp_prompt_repair
last_modified: 2026-08-28T04:32:53.967202453+00:00
modified: 2026-08-28T04:32:53.967199337+00:00
permalink: temp_prompt_repair
tags:
- template
- process
- instruction-quality
- critique
- prompt-engineering
title: prompt-repair
type: template
---

# prompt-repair — repair the instructions that produced a failing output

**Covers:** a reusable prompt or instruction set whose output failed its readers, where the fix
belongs in the instructions, not the artifact. Do not select it to revise one artifact once — only
when the instructions will run again.

**Inputs:** the original instructions, at their actual location; one or more failing outputs;
optionally the artifact's purpose and audience.

**This template composes into tasks, not inline steps.** The composing agent creates the nodes
below, wires the dependencies, and performs none of them. Brief every executor with purpose,
audience, and strategic context — never method: each executor is at least as capable as its
dispatcher, and method prescribed from outside the work is on average worse than what the executor
would choose itself.

## Tasks

1. **Independent critiques — two or more, parallel, blind to each other.** Each critic receives
   only the failing output(s), the original instructions, and the purpose and audience — stated
   first as testable assumptions if not supplied. Deliverable per critic: what the reader needed
   and what they got instead, with each failure traced to the instruction line that caused it or
   the omission that permitted it.
2. **Synthesis — depends on all critiques.** Reconcile them: independent convergence is strong
   evidence; divergence is traced to its cause, never averaged. Deliverables: (a) one causal
   diagnosis per failure; (b) replacement instructions that prevent each failure _class_, not just
   its instance; (c) a checklist a reviewer can score — one check per substantive difference
   between old and new instructions, on substance and level of abstraction, never expression or
   style.
3. **Validation — depends on synthesis; the evaluator wrote none of it.** Regenerate an output
   under the replacement or test it adversarially, and score the checklist: every diagnosed
   failure excluded, no new failure mode introduced. One failed validation returns to synthesis; a
   second is a finding about the diagnosis.
4. **Delivery — depends on validation.** The replacement lands as a drop-in at the original
   instructions' actual location. A proposal beside the original is not delivery.

## Exit

Purpose and audience on the record; every failure has a traced cause; the checklist is scored by
validation; the original location holds the replacement — which obeys every rule it imposes.
