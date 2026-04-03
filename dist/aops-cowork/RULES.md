---
name: rules
title: Rules Quick Reference
type: index
category: framework
description: |
  Quick-reference index of axioms, contextual rules, and heuristics.
  Organized by tier. See enforcement-map.md for the full manifest.
permalink: rules
tags: [framework, index, governance, principles]
---

# Rules Quick Reference

Quick lookup for framework principles. See [[enforcement-map.md]] for the full tiered architecture and enforcement details.

## Tier 1: Universal Axioms (always active)

**File**: [[AXIOMS.md]] | **Agent**: Integrity enforcer

| P#   | Name                            | One-liner                                  |
| ---- | ------------------------------- | ------------------------------------------ |
| P#3  | Don't Make Shit Up              | If you don't know, say so - no guesses     |
| P#5  | Do One Thing                    | Complete requested task, then STOP         |
| P#6  | Data Boundaries                 | Never expose private data in public places |
| P#9  | Fail-Fast (Agents)              | When instructions fail, STOP immediately   |
| P#26 | Verify First                    | Check actual state, never assume           |
| P#27 | No Excuses                      | Never claim success without confirmation   |
| P#30 | Nothing Is Someone Else's       | If you can't fix it, HALT                  |
| P#31 | Acceptance Criteria Own Success | Only user criteria determine completion    |
| P#48 | Human Tasks Are Not Agent Tasks | External comms route to user               |
| P#50 | Explicit Approval               | Get approval before expensive operations   |
| P#99 | Delegated Authority Only        | Act within delegated authority only        |

## Tier 2: Contextual Rules (activated by project context)

### Academic Context

**File**: [[skills/research/axioms.md]] | **Agent**: Academic standards enforcer

| P#    | Name                              | One-liner                                 |
| ----- | --------------------------------- | ----------------------------------------- |
| P#4   | Always Cite Sources               | No plagiarism, ever                       |
| P#42  | Research Data Immutable           | Source data is SACRED                     |
| P#53  | Academic Output Quality           | Triple-check before public release        |
| P#84  | Methodology Belongs to Researcher | HALT on methodological choices            |
| P#111 | User Sign-Off Required            | Deliverables need explicit approval       |
| P#112 | Receipts on QA                    | Show what was checked and results         |
| P#113 | Over-Verify Externally Visible    | Prefer over-verification for public work  |
| P#114 | No Silent Release                 | User reviews final version before release |

### Development Context

**File**: [[agents/dev-standards.md]] | **Agent**: Engineering standards enforcer

| P#   | Name                         | One-liner                                     |
| ---- | ---------------------------- | --------------------------------------------- |
| P#8  | Fail-Fast (Code)             | No defaults, no fallbacks, no silent failures |
| P#10 | Self-Documenting             | Documentation-as-code first                   |
| P#12 | DRY, Modular, Explicit       | One golden path, no guessing                  |
| P#24 | Trust Version Control        | Git is backup - no .bak files                 |
| P#41 | Plan-First Development       | No coding without approved plan               |
| P#51 | Credential Isolation         | Use bot tokens, not user credentials          |
| P#82 | Mandatory Reproduction Tests | Bug fix needs failing test first              |
| P#97 | Never Edit Generated Files   | Find and update the source instead            |

### Framework Context

**File**: [[agents/framework-ops.md]] | **Agent**: Framework operations enforcer

| P#   | Name                      | One-liner                                                                    |
| ---- | ------------------------- | ---------------------------------------------------------------------------- |
| P#22 | Always Dogfooding         | Use real projects as test cases; discover quality criteria before automating |
| P#23 | Skills Are Read-Only      | No dynamic data in skills                                                    |
| P#25 | No Workarounds            | If tools fail, halt - don't bypass                                           |
| P#29 | Relational Integrity      | Atomic markdown files that link                                              |
| P#43 | Just-In-Time Context      | Missing context = framework bug                                              |
| P#46 | Memory Model              | $ACA_DATA = semantic + episodic with provenance                              |
| P#47 | Agents Execute Workflows  | Agents select workflows, don't contain them                                  |
| P#49 | No Shitty NLP             | Use LLMs for semantic decisions; agentic-first                               |
| P#55 | Non-interactive Execution | No commands requiring interactive input                                      |

## Tier 3: Heuristics (advisory)

**File**: [[HEURISTICS.md]] | Inform but don't block.

Includes demoted former axioms (P#7, P#11, P#28, P#44, P#45, P#52) plus operational guidelines. See HEURISTICS.md for the full list.

## Enforcement Levels

| Level                 | Mechanism                   | Example            |
| --------------------- | --------------------------- | ------------------ |
| **Hard block**        | Hook returns `block`        | Hydration gate     |
| **Soft warning**      | Hook returns `warn`         | Missing reflection |
| **Context injection** | Principle in tier files     | Agent sees rule    |
| **Behavioral**        | Agent instruction-following | Most principles    |

See [[enforcement-map.md]] for full enforcement details.
