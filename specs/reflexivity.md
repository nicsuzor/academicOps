---
title: Framework Reflexivity
type: spec
category: spec
status: implemented
permalink: reflexivity
tags:
  - spec
  - framework
  - meta-learning
  - dogfooding
  - episodic
---

# Framework Reflexivity

**Status**: Implemented

## Definition

Reflexivity is the framework's capacity to improve itself through use. Every agent interaction serves dual objectives:

1. **Task**: Complete what the user asked
2. **Meta-task**: Improve the system that completes tasks

This is mandatory. The framework develops itself through use (per [[AXIOMS]] #13: Dogfooding).

## Data Architecture

Per [[AXIOMS]] #28 (Current State Machine), reflexivity data has two types:

| Type         | Definition                      | Storage                  | Example                  |
| ------------ | ------------------------------- | ------------------------ | ------------------------ |
| **Episodic** | Observations at a point in time | bd issues                | "Agent bypassed skill X" |
| **Semantic** | Timeless truths, always current | `$ACA_DATA/` or `$AOPS/` | HEURISTICS.md entry      |

**Episodic observations → bd issues** (`.beads/issues.jsonl`, git-tracked)

**Synthesized patterns → HEURISTICS.md**

### Issue Labels

| Label        | Use For                                    |
| ------------ | ------------------------------------------ |
| `learning`   | Agent behavior patterns (default)          |
| `bug`        | Component-level bugs                       |
| `experiment` | Systemic investigations with interventions |
| `devlog`     | Development observations                   |
| `decision`   | Architectural choices                      |

## Workflows

### Observing (What Happened)

**Entry point**: `/log [observation]` or `Skill(skill="learning-log")`

**Flow**:

1. Search existing Issues for match
2. If match → add comment; if not → create Issue
3. Link to ROADMAP.md user stories if applicable

**When to use**: Noticing agent behavior, friction, missing context, guardrail failures.

See [[specs/learning-log-skill]] for full workflow.

### Intervening (Fixing It)

**Entry point**: `/learn [issue]` or framework skill

**Flow**:

1. Understand issue category (missing fact, ignored instruction, poor behavior, etc.)
2. Search for prior occurrences (bd issues with same pattern)
3. Choose minimal intervention per [[RULES]]
4. Make change, document in Issue
5. Track success criteria in Issue comments

**When to use**: Making framework changes in response to observations.

**Note**: Interventions are tracked as Issue comments or linked PRs, not separate experiment files.

### Synthesizing (Pattern → Heuristic)

**Trigger**: 3+ Issues with same root cause

**Flow**:

1. Identify pattern across Issues
2. Draft heuristic per HEURISTICS.md format
3. Add to HEURISTICS.md with Issue references
4. Close Issues: "Synthesized to HEURISTICS.md H[n]"

Closed Issues remain searchable via GitHub.

## Session Reflection

During work, notice:

- **Routing**: How did you know which process to use?
- **Friction**: What's harder than it should be?
- **Missing process**: What skill/workflow should exist?
- **Missing context**: What knowledge didn't surface?
- **Guardrails**: What constraint would have prevented a mistake?

At session end:

1. If observations worth logging → `/log [observation]`
2. If pattern emerged → check synthesis triggers
3. If actionable change → `/learn [issue]`

## Integration Points

| Component            | Role                                      |
| -------------------- | ----------------------------------------- |
| `/log` command       | Routes observations to bd issues          |
| `/learn` command     | Makes tracked interventions               |
| `learning-log` skill | Implements Issue search/create workflow   |
| `framework` skill    | Governance for interventions              |
| [[HEURISTICS]]       | Synthesis destination                     |
| Memory server        | Semantic search (supplements `bd search`) |

## HEURISTICS.md Format

HEURISTICS.md is kept minimal for token efficiency. Each heuristic entry contains:

```
## H[n]: Title
**Statement**: [actionable rule - 1-2 sentences max]
**Confidence**: [High/Medium/Low] | **Implements**: [axiom numbers] | **Evidence**: #[issue]
```

**What lives WHERE:**

| Content              | Location                  |
| -------------------- | ------------------------- |
| Actionable rule      | HEURISTICS.md (Statement) |
| Rationale/context    | GitHub Issue (body)       |
| Dated observations   | GitHub Issue (comments)   |
| Application examples | GitHub Issue (body)       |

**Token budget**: HEURISTICS.md should stay under 2,000 tokens (~200 lines). If approaching limit, evidence sections move to Issues.

## Validation Criteria

1. New episodic observations → bd issues (not local files)
2. Search-before-create prevents duplicates
3. Patterns synthesize to HEURISTICS.md when 3+ Issues share root cause
4. `/log` and `/learn` both route through this architecture
5. HEURISTICS.md stays under 2,000 tokens

## Design Rationale

**Why bd issues?**

Per [[AXIOMS]] #28: bd issues provide structured storage with timelines, labels, and search. They're git-tracked and local-first, enabling offline work and version control integration. Searchable via `bd search` and `bd list`.

**Why not local experiment files?**

Experiments are tracked as bd issues (label: `experiment`) with intervention history in the description. This keeps all episodic content in one searchable place and avoids file proliferation.

**Why synthesize to HEURISTICS.md?**

Individual observations have limited value. Patterns that recur 3+ times indicate systematic issues worth encoding as permanent guidance. Synthesis converts noisy observations into actionable heuristics.
