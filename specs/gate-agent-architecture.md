---
title: Gate Agent Architecture
type: spec
category: spec
status: draft
permalink: gate-agent-architecture
tags: [framework, hooks, agents, architecture]
---

# Gate Agent Architecture

Unified architecture for gate agents that control session flow.

## Gate Functions

Gate agents perform six distinct functions, organized into two execution phases:

### Pre-Action Gates (UserPromptSubmit, PreToolUse)

| Function               | Purpose                                                 | Current Owner   |
| ---------------------- | ------------------------------------------------------- | --------------- |
| **Hydration**          | Enrich prompts with context (memory, codebase, session) | prompt-hydrator |
| **Planning**           | Select workflow dimensions (gate/pre-work/approach)     | prompt-hydrator |
| **Workflow Selection** | Match skills, apply guardrails                          | prompt-hydrator |

### Post-Action Gates (PostToolUse, Stop, SubagentStop)

| Function                 | Purpose                                      | Current Owner      |
| ------------------------ | -------------------------------------------- | ------------------ |
| **Enforcement**          | Detect ultra vires actions, drift from scope | custodiet          |
| **Guardrails**           | Block mechanical violations (patterns)       | policy_enforcer.py |
| **Knowledge Extraction** | Capture decisions/learnings to PKG           | (new)              |

## Design Principle: Internal Modules, Not Separate Agents

Gate functions are **conceptually separate** but **executed together** within a single agent invocation per hook. Rationale:

1. **Latency**: Separate agents add sequential overhead
2. **Dependencies**: Workflow selection depends on context; guardrails depend on workflow
3. **Token efficiency**: Single agent call with temp file is cheaper than multiple

Each gate agent internally runs modules in order, but the user sees one agent per hook.

## Unified Session State

All hooks share a single session state file for cross-gate coordination.

### Location

`/tmp/claude-session/state-{project_hash}.json`

Project hash is SHA256 of cwd (same as current custodiet approach).

### Schema

```json
{
  "last_hydration_ts": 1736234567.89,
  "last_compliance_ts": 1736234890.12,
  "tool_calls_since_compliance": 4,
  "prompts_since_hydration": 1,
  "declared_workflow": {
    "gate": "none",
    "pre_work": "verify-first",
    "approach": "direct"
  },
  "active_skill": "framework",
  "intent_envelope": "fix the type error in parser.py"
}
```

### Field Definitions

| Field                         | Updated By                  | Used By                             |
| ----------------------------- | --------------------------- | ----------------------------------- |
| `last_hydration_ts`           | UserPromptSubmit            | PreToolUse (overdue check)          |
| `last_compliance_ts`          | PostToolUse (on check)      | PreToolUse (overdue check)          |
| `tool_calls_since_compliance` | PostToolUse                 | PreToolUse (threshold check)        |
| `prompts_since_hydration`     | UserPromptSubmit            | (reserved)                          |
| `declared_workflow`           | UserPromptSubmit (hydrator) | PostToolUse (custodiet drift check) |
| `active_skill`                | UserPromptSubmit            | PostToolUse (skill compliance)      |
| `intent_envelope`             | UserPromptSubmit            | PostToolUse (scope drift)           |

### Atomic Updates

Hooks use write-then-rename for atomic updates:

```python
temp_path = state_path.with_suffix('.tmp')
temp_path.write_text(json.dumps(state))
temp_path.rename(state_path)
```

## Overdue Enforcement

### Thresholds

| Metric                        | Threshold | Enforcement                   |
| ----------------------------- | --------- | ----------------------------- |
| `tool_calls_since_compliance` | 7         | Hard block on Edit/Write/Bash |

### Enforcement Levels

| Tool Category                | If Gate Overdue                |
| ---------------------------- | ------------------------------ |
| Mutating (Edit, Write, Bash) | Block until gate runs          |
| Read-only (Read, Glob, Grep) | Soft reminder only             |
| MCP tools                    | Block if writes, soft if reads |

### Implementation

PreToolUse hook checks session state before allowing mutating tools:

```python
state = load_session_state()
if state["tool_calls_since_compliance"] >= THRESHOLD:
    return {
        "decision": "block",
        "reason": "Compliance check overdue. Spawn custodiet first."
    }
```

## Transcript Processor

Single implementation for extracting gate-relevant information from session transcripts.

### API

```python
def extract_gate_context(
    transcript_path: Path,
    include: set[str],
    max_turns: int = 5,
) -> dict[str, Any]:
    """Extract configurable context for gate agents.

    Args:
        transcript_path: Path to session JSONL
        include: Set of extraction types
        max_turns: Lookback limit for prompts/tools

    Returns:
        Dict with requested context sections
    """
```

### Extraction Types

| Type        | Contents                                      | Used By             |
| ----------- | --------------------------------------------- | ------------------- |
| `prompts`   | Last N user prompts (cleaned)                 | hydrator            |
| `skill`     | Most recent Skill invocation                  | hydrator, custodiet |
| `todos`     | TodoWrite state (counts, in_progress)         | hydrator, custodiet |
| `intent`    | First non-meta user prompt (original request) | custodiet           |
| `errors`    | Recent tool errors                            | custodiet           |
| `tools`     | Recent tool calls with args                   | custodiet           |
| `files`     | Files modified in session                     | PKG extraction      |
| `decisions` | User statements indicating decisions          | PKG extraction      |

### Location

`lib/session_reader.py` - extends existing `extract_router_context()`.

## Template System

### When to Use Jinja2

Convert to Jinja2 (`.j2` extension) when template needs:

- Conditional sections based on context
- Loops over variable-length data
- Includes of shared fragments

Keep as markdown with `{var}` substitution when:

- Simple variable replacement only
- No conditional logic needed

### Current Templates

| Template                          | Format     | Reason                                |
| --------------------------------- | ---------- | ------------------------------------- |
| `prompt-hydrator-context.md`      | Markdown   | Simple substitution                   |
| `prompt-hydration-instruction.md` | Markdown   | Simple substitution                   |
| `custodiet-context.md`            | **Jinja2** | Conditional axiom/heuristic injection |
| `custodiet-instruction.md`        | Markdown   | Simple substitution                   |

### Jinja2 Environment

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

## Knowledge Extraction (PKG)

### Trigger Points

| Hook         | Condition               | Extraction Type        |
| ------------ | ----------------------- | ---------------------- |
| Stop         | Session ending          | Full session decisions |
| SubagentStop | Subagent completed work | Subagent outcomes      |
| PostToolUse  | (reserved)              | (not implemented)      |

### What Gets Extracted

Per [[skills/remember/SKILL.md]]:

| Content Type                | Destination                  |
| --------------------------- | ---------------------------- |
| User preferences discovered | `$ACA_DATA/context/`         |
| Project decisions           | `$ACA_DATA/projects/<name>/` |
| Tool usage patterns         | Memory server only           |
| Workflow observations       | GitHub Issues (episodic)     |

### Implementation

Background subagent using remember skill:

```python
Task(
    subagent_type="general-purpose",
    model="haiku",
    run_in_background=True,
    description="PKG extraction",
    prompt="Extract and persist key decisions from this session..."
)
```

## Relationship to Other Specs

| Spec                            | Relationship                    |
| ------------------------------- | ------------------------------- |
| [[specs/prompt-hydration]]      | Pre-action gate implementation  |
| [[specs/ultra-vires-custodiet]] | Post-action gate implementation |
| [[specs/execution-flow-spec]]   | Shows where gates fit in flow   |
| [[RULES.md]]                    | Guardrail definitions           |

## Files

| File                          | Purpose                                         |
| ----------------------------- | ----------------------------------------------- |
| `lib/session_reader.py`       | Transcript processor (`extract_gate_context()`) |
| `lib/session_state.py`        | Session state management (new)                  |
| `hooks/user_prompt_submit.py` | Pre-action gate hook                            |
| `hooks/custodiet.py`          | Post-action gate hook                           |
| `hooks/templates/*.j2`        | Jinja2 templates                                |
| `hooks/templates/*.md`        | Simple markdown templates                       |
