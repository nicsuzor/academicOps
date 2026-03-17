---
title: The Curia
type: note
category: spec
permalink: aops-curia
tags:
  - framework
  - agents
  - architecture
---

# The Curia

The Curia is the academicOps agent team -- a small group of named agents that operate across local sessions, GitHub PRs, and other surfaces. Each agent has a clear charter and shows up in multiple places (skill, GitHub Action, hook) under consistent identity.

The roster is iterative. Agents are added as they prove useful, not designed upfront.

## Roster

| Agent        | Charter                                                               | Local Skill | GitHub Agent                                                             | Mechanical (Hook/Gate)                  |
| ------------ | --------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------ | --------------------------------------- |
| **Hydrator** | Context enrichment: transform terse prompts into rich execution plans | `hydrator`  | --                                                                       | hydration gate, `user_prompt_submit.py` |
| **Auditor**  | Rule enforcement: check compliance with axioms and heuristics         | `custodiet` | `auditor.agent.md`                                                       | `policy_enforcer.py`                    |
| **Critic**   | Strategic review: evaluate plans, assumptions, and VISION alignment   | `critic`    | `critic.agent.md` (file: `assessor.agent.md`†), `summary-brief.agent.md` | --                                      |
| **QA**       | Acceptance testing: prove things work, don't just review on paper     | `qa`        | `qa.agent.md`                                                            | QA gate                                 |
| **Advocate** | Voice matching: ensure external-facing text sounds like the user      | -- (future) | -- (future)                                                              | --                                      |

Workers (polecats) execute bounded tasks. They use `worker` skill locally and `worker.agent.md` / `merge-prep.agent.md` on GitHub. They are not Curia governance agents.

† `assessor.agent.md` is the current filename; rename to `critic.agent.md` when the corresponding workflow is updated. The local Auditor skill remains named `custodiet` for historical reasons — rename is tracked separately.

## Privacy Boundaries

| Agent    | Reads private data?                | Outputs publicly?                     | Constraint                                                  |
| -------- | ---------------------------------- | ------------------------------------- | ----------------------------------------------------------- |
| Hydrator | Yes (full PKB, email, memory)      | No (session-internal only)            | Strips private content before any public surface            |
| Auditor  | Yes (session transcripts)          | Yes (PR violation reports)            | References axiom numbers, never quotes private content      |
| Critic   | Limited (agent output, PR diff)    | Yes (PR reviews)                      | Analysis of diff and plan only, no external context         |
| QA       | Limited (test outputs)             | Locally: no. GitHub: yes (PR reviews) | Verification evidence only                                  |
| Advocate | Yes (writing samples, past emails) | Yes (polished drafts)                 | Voice profiles never quoted; output is original composition |

## Design Principles

- **The mechanism is a deployment detail, not an identity.** `custodiet/SKILL.md` and `auditor.agent.md` are the same agent (the Auditor) on different surfaces.
- **Domain skills are tools, not agents.** Skills like `python-dev`, `analyst`, `garden` are tools any Curia agent can use. They don't have Curia identities.
- **Infrastructure is mechanical, not agentic.** Hooks (`router.py`, `gate_config.py`) and gates are infrastructure that triggers agents. They are not agents themselves.
- **Hooks implement mechanical subsets.** `policy_enforcer.py` implements the Auditor's deterministic rules (protected paths, destructive git) without LLM judgment. The full Auditor adds scope drift detection and axiom compliance that require judgment.

## Cross-Reference Convention

Each skill and GitHub agent file includes a short cross-reference identifying its Curia role and listing related implementations. Look for `> **Curia**:` lines in those files.
