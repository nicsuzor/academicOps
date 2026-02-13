---
title: Framework Observability Architecture
type: spec
category: architecture
status: active
created: 2026-01-24
related: [[workflow-system-spec]], [[enforcement]], [[session-insights-prompt]]
---

# Framework Observability Architecture

## Giving Effect

- [[skills/session-insights/SKILL.md]] - Skill for generating session insights from transcripts
- [[specs/session-insights-prompt.md]] - Prompt template for session analysis
- [[specs/session-insights-metrics-schema.md]] - Schema for metrics extraction
- [[hooks/unified_logger.py]] - Centralized logging for observability
- [[polecat/observability.py]] - Polecat-specific observability
- [[commands/log.md]] - `/log` command for logging observations

## Overview

The framework is **self-reflexive**: it observes its own execution, extracts patterns, and feeds those observations back into improvement processes. This document describes the observability pipeline that makes self-improvement possible.

## Core Principle: Observe, Don't Assume

The framework cannot directly observe agent behavior (agents are probabilistic). Instead, it observes:

1. **Session artifacts** - JSONL transcripts, tool invocations, timestamps
2. **Structured outputs** - Framework Reflections, insights JSON, task updates
3. **Enforcement events** - Hook triggers, custodiet blocks, policy violations

These observables create an audit trail that humans and agents can analyze.

## The Observability Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SESSION EXECUTION                              │
│                                                                         │
│  User Prompt → Hydrator → Agent → Tools → Hooks → Completion            │
│       │           │         │       │       │          │                │
│       ▼           ▼         ▼       ▼       ▼          ▼                │
│  [intent]    [workflow] [actions] [results] [gates] [reflection]        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAW OBSERVABLES                                 │
│                                                                         │
│  session.jsonl          Entry-level records with:                       │
│  ├── type               user | assistant | tool_use | tool_result       │
│  ├── timestamp          ISO 8601 with timezone                          │
│  ├── content            Message/tool content                            │
│  └── message.usage      Token counts: input, output, cache_*            │
│                                                                         │
│  subagents/agent-*.jsonl  Per-subagent transcripts                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRANSCRIPT PROCESSING                            │
│                                                                         │
│  scripts/transcript.py parses JSONL into structured data:               │
│                                                                         │
│  SessionProcessor.parse_session_file()                                  │
│  ├── Entry.from_dict()           Extract per-entry data                 │
│  │   ├── timestamp               Parse to datetime                      │
│  │   ├── input_tokens            From message.usage                     │
│  │   ├── output_tokens           From message.usage                     │
│  │   ├── cache_read_input_tokens From message.usage                     │
│  │   └── model                   Model identifier                       │
│  │                                                                      │
│  ├── extract_reflection_from_entries()                                  │
│  │   └── Parse "## Framework Reflection" blocks                         │
│  │                                                                      │
│  └── _aggregate_session_usage()                                         │
│      └── UsageStats with by_model, by_agent, by_tool breakdowns         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         INSIGHTS GENERATION                              │
│                                                                         │
│  _process_reflection() orchestrates:                                    │
│                                                                         │
│  1. Extract reflections from session entries                            │
│  2. Compute usage_stats via _aggregate_session_usage()                  │
│  3. Compute session_duration via _compute_session_duration()            │
│  4. Call reflection_to_insights() with all data                         │
│  5. Validate against insights schema                                    │
│  6. Write to sessions/insights/<date>-<project>-<session_id>.json       │
│                                                                         │
│  reflection_to_insights() produces:                                     │
│  {                                                                      │
│    session_id, date, project, summary, outcome,                         │
│    accomplishments, friction_points, proposed_changes,                  │
│    learning_observations, skill_compliance, context_gaps,               │
│    workflow_improvements, jit_context_needed, context_distractions,     │
│    token_metrics: {                                                     │
│      totals: { input_tokens, output_tokens, cache_* },                  │
│      by_model: { "claude-opus-4-5": { input, output } },                │
│      by_agent: { "main": {...}, "prompt-hydrator": {...} },             │
│      efficiency: { cache_hit_rate, tokens_per_minute, duration }        │
│    }                                                                    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         HUMAN REVIEW & ANALYSIS                          │
│                                                                         │
│  Insights JSON files are designed for human consumption:                │
│                                                                         │
│  - Identify patterns across sessions                                    │
│  - Spot skill compliance gaps                                           │
│  - Analyze token efficiency trends                                      │
│  - Review proposed framework changes                                    │
│  - Feed observations into /learn workflow                               │
│                                                                         │
│  Note: Insights are NOT automatically consumed by agents.               │
│  Humans analyze and decide what changes to make.                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Observable Types

### 1. Framework Reflections

Agents emit structured reflections at session end (via Stop hook):

```markdown
## Framework Reflection

**Prompts**: [What user asked for]
**Guidance received**: [Hydrator/workflow guidance]
**Followed**: Yes | Partial | No
**Outcome**: success | partial | failure
**Accomplishments**: [What was delivered]
**Friction points**: [What was harder than expected]
**Root cause**: [If not success - which component failed]
**Proposed changes**: [Framework improvements identified]
```

These are parsed by `extract_reflection_from_entries()` and converted to insights JSON.

### 2. Token Metrics

Per-entry token data is extracted from `message.usage`:

| Field                         | Source                                    | Purpose                  |
| ----------------------------- | ----------------------------------------- | ------------------------ |
| `input_tokens`                | message.usage.input_tokens                | Track input consumption  |
| `output_tokens`               | message.usage.output_tokens               | Track output generation  |
| `cache_read_input_tokens`     | message.usage.cache_read_input_tokens     | Measure cache efficiency |
| `cache_creation_input_tokens` | message.usage.cache_creation_input_tokens | Track cache population   |
| `model`                       | message.model                             | Attribution by model     |

Aggregated by `UsageStats.add_entry()` into:

- **Totals**: Session-wide token counts
- **By model**: Breakdown per model (opus, haiku, etc.)
- **By agent**: Breakdown per agent (main, subagents)
- **By tool**: Breakdown per tool invoked

### 3. Skill Compliance

Track whether suggested skills were actually invoked:

```json
{
  "skill_compliance": {
    "suggested": ["framework", "audit"],
    "invoked": ["framework"],
    "compliance_rate": 0.5
  }
}
```

Low compliance rates indicate:

- Skill discovery problems (agent didn't know skill existed)
- Context gaps (agent didn't understand when to use skill)
- Instruction clarity issues (skill trigger conditions unclear)

### 4. Learning Observations

Structured capture of agent mistakes and corrections:

```json
{
  "category": "Process Adherence",
  "evidence": "Agent skipped skill invocation",
  "context": "During initial request",
  "heuristic": "H2",
  "suggested_evidence": "Should have invoked framework skill"
}
```

These feed into the [[/learn|learn]] workflow for root cause analysis.

## Integration Points

### Hooks That Generate Observables

| Hook                          | Event        | Observable Generated            |
| ----------------------------- | ------------ | ------------------------------- |
| `sessionstart_load_axioms.py` | SessionStart | Session initialization logged   |
| `custodiet_gate.py`           | PostToolUse  | Block events, drift detection   |
| `session_reflect.py`          | Stop         | Framework Reflection extraction |
| `autocommit_state.py`         | PostToolUse  | State file updates              |

### Workflows That Consume Observables

| Workflow   | Consumes                             | Produces                                  |
| ---------- | ------------------------------------ | ----------------------------------------- |
| [[/learn]] | Insights JSON, learning_observations | Heuristic/axiom updates, tasks            |
| [[audit]]  | Insights JSON, skill_compliance      | Compliance reports, enforcement proposals |
| [[qa]]     | Insights JSON, friction_points       | Root cause analysis, fix proposals        |

## Adding New Observables

To add a new observable pattern:

1. **Identify the source** - Where does this data originate? (JSONL, hook, tool result)

2. **Add extraction** - Update `lib/transcript_parser.py`:
   - Add field to `Entry` dataclass if per-entry
   - Add aggregation to `UsageStats` if session-wide
   - Update `Entry.from_dict()` to extract the data

3. **Add to insights schema** - Update `specs/session-insights-prompt.md`:
   - Add field definition
   - Add to example JSON output
   - Document when to use null/empty

4. **Wire into pipeline** - Update `scripts/transcript.py`:
   - Pass new data through `_process_reflection()`
   - Update `reflection_to_insights()` to include it

5. **Update enforcement-map** - If observable enables new enforcement:
   - Add entry to [[enforcement-map|indices/enforcement-map.md]]
   - Document the enforcement point

## Design Principles

### Observability is for Humans

The framework does NOT automatically act on insights. Humans review insights JSON and decide what changes to make. This prevents:

- Runaway self-modification
- Overfitting to single sessions
- Loss of human oversight

### Observable, Not Interpretable

Observables capture WHAT happened, not WHY. Interpretation requires:

- Pattern recognition across multiple sessions
- Root cause analysis (via [[/learn]])
- Human judgment on appropriate response

### Structured for Analysis

Insights JSON uses consistent schemas so tooling can:

- Aggregate across sessions
- Trend over time
- Filter by project/outcome/compliance
- Feed into dashboards or reports

## Related Documents

- [[workflow-system-spec]] - How workflows are selected and composed
- [[enforcement]] - How rules are enforced via hooks
- [[session-insights-prompt]] - Full schema for insights JSON
- [[feedback-loops]] - How observations become improvements
