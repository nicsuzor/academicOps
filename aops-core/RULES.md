---
name: rules
title: Rules Quick Reference
type: index
category: framework
description: |
  Quick-reference index of AXIOMS (inviolable) and HEURISTICS (guidelines).
  For full content, see AXIOMS.md and HEURISTICS.md.
permalink: rules
tags: [framework, index, governance, principles]
---

# Rules Quick Reference

Quick lookup for framework principles. Full definitions in [[AXIOMS.md]] and [[HEURISTICS.md]].

## AXIOMS (Inviolable)

Violation = system failure. No exceptions.

| P#   | Name                            | One-liner                                        |
| ---- | ------------------------------- | ------------------------------------------------ |
| P#1  | No Other Truths                 | Only derive from axioms, no external assumptions |
| P#2  | Categorical Imperative          | Actions must be justifiable as universal rules   |
| P#3  | Don't Make Shit Up              | If you don't know, say so - no guesses           |
| P#4  | Always Cite Sources             | No plagiarism, ever                              |
| P#5  | Do One Thing                    | Complete requested task, then STOP               |
| P#6  | Data Boundaries                 | Never expose private data in public places       |
| P#7  | Project Independence            | Projects work independently, no cross-deps       |
| P#8  | Fail-Fast (Code)                | No defaults, no fallbacks, no silent failures    |
| P#9  | Fail-Fast (Agents)              | When instructions fail, STOP immediately         |
| P#10 | Self-Documenting                | Documentation-as-code first                      |
| P#11 | Single-Purpose Files            | One audience, one purpose per file               |
| P#12 | DRY, Modular, Explicit          | One golden path, no guessing                     |
| P#22 | Always Dogfooding               | Use real projects as test cases                  |
| P#23 | Skills Are Read-Only            | No dynamic data in skills                        |
| P#24 | Trust Version Control           | Git is backup - no .bak files                    |
| P#25 | No Workarounds                  | If tools fail, halt - don't bypass               |
| P#26 | Verify First                    | Check actual state, never assume                 |
| P#27 | No Excuses                      | Never claim success without confirmation         |
| P#28 | Write For Long Term             | No single-use scripts                            |
| P#29 | Relational Integrity            | Atomic markdown files that link                  |
| P#30 | Nothing Is Someone Else's       | If you can't fix it, HALT                        |
| P#31 | Acceptance Criteria Own Success | Only user criteria determine completion          |
| P#41 | Plan-First Development          | No coding without approved plan                  |
| P#42 | Research Data Immutable         | Source data is SACRED                            |
| P#43 | Just-In-Time Context            | Missing context = framework bug                  |
| P#44 | Minimal Instructions            | No more detail than required                     |
| P#45 | Feedback Loops                  | Unknown solution = set up experiment             |
| P#46 | Current State Machine           | $ACA_DATA = semantic memory only                 |
| P#47 | Agents Execute Workflows        | Agents select workflows, don't contain them      |
| P#48 | Human Tasks ≠ Agent Tasks       | External comms route to user                     |
| P#49 | No Shitty NLP                   | Use LLMs for semantic decisions                  |

## HEURISTICS (Guidelines)

Violation = friction, not failure. Evidence-based working hypotheses.

| P#   | Name                                 | One-liner                            |
| ---- | ------------------------------------ | ------------------------------------ |
| P#19 | Skills No Dynamic Content            | Current state in $ACA_DATA           |
| P#54 | Semantic Link Density                | Related files MUST link              |
| P#56 | File Category Classification         | Every file has one category          |
| P#57 | Never Bypass Locks                   | HALT on locks, ask user              |
| P#58 | Indices Before Exploration           | Prefer indices over grep             |
| P#59 | Action Over Clarification            | Pick and start, don't ask preference |
| P#60 | Local AGENTS.md                      | Instructions where agents work       |
| P#61 | Internal Records First               | Search bd/memory before APIs         |
| P#62 | Tasks Inherit Context                | Apply session context to new tasks   |
| P#63 | Task Output Includes IDs             | Always show task IDs                 |
| P#64 | Planning to Daily Note               | Write guidance, don't execute        |
| P#65 | Enforcement Map Updates              | Document new enforcement             |
| P#66 | Just-In-Time Information             | Only present necessary info          |
| P#67 | Extract Implies Persist              | "Extract" → remember workflow        |
| P#68 | Background Agent Visibility          | Tell user about spawned agents       |
| P#69 | Large Data Handoff                   | >10KB → provide file path            |
| P#70 | Trust Version Control                | Delete outright, trust git           |
| P#71 | Decomposed = Complete                | Parent done when decomposed          |
| P#72 | Decompose Only When Adding Value     | Empty child = premature              |
| P#73 | Task Sequencing on Insert            | Connect to hierarchy                 |
| P#74 | User Expertise > Hypotheses          | Trust user assertions                |
| P#75 | Tasks Have Single Objectives         | One objective per task               |
| P#76 | Commands Dispatch, Workflows Execute | Separation of concerns               |
| P#77 | CLI-MCP Parity                       | Same defaults across interfaces      |
| P#78 | Deterministic in Code                | Use Python for counting              |
| P#79 | Prefer fd Over ls                    | Better file finding                  |
| P#80 | Fixes Preserve Spec                  | Don't remove required behavior       |
| P#81 | Spike Output to Graph                | Findings in task body                |
| P#82 | Mandatory Reproduction Tests         | Bug fix needs failing test           |
| P#83 | Explicit Cross-Project Deps          | Document infrastructure use          |
| P#84 | Methodology to Researcher            | HALT on methodological choices       |
| P#85 | Error Recovery to Reference          | Re-read reference on failure         |
| P#86 | Background Notifications Unreliable  | Never block on TaskOutput            |
| P#87 | Preserve Pre-Existing Content        | Don't delete without instruction     |

## Enforcement Levels

| Level                 | Mechanism                      | Example                   |
| --------------------- | ------------------------------ | ------------------------- |
| **Hard block**        | Hook returns `block`           | Hydration gate |
| **Soft warning**      | Hook returns `warn`            | Missing reflection        |
| **Context injection** | Principle in AXIOMS/HEURISTICS | Agent sees rule           |
| **Behavioral**        | Agent instruction-following    | Most principles           |

See [[framework/enforcement-map.md]] for full enforcement details.
