# Session Insights Generation Prompt

## Giving Effect

- [[skills/session-insights/SKILL.md]] - Session insights skill that uses this prompt
- [[mcp__gemini__*]] - Gemini MCP tools for transcript analysis
- [[specs/session-insights-metrics-schema.md]] - Schema for extracted metrics
- [[specs/framework-observability.md]] - Observability architecture this feeds into

---

Analyze this session and extract structured insights. Output ONLY valid JSON (no markdown code fences, no commentary).

## Session Metadata

Use these values EXACTLY in your response:

- **session_id**: {session_id}
- **date**: {date}
- **project**: {project}

## Required Analysis

### 1. High-Level Summary (Required by all generators)

- **summary**: One sentence describing what was worked on
- **outcome**: Must be exactly one of: `"success"`, `"partial"`, or `"failure"`
  - `success`: All goals accomplished, no blocking issues
  - `partial`: Some goals accomplished, some incomplete or with issues
  - `failure`: Major blockers prevented goal completion
- **accomplishments**: Array of completed items (concrete deliverables, e.g., "Created 5 bd issues", "Fixed authentication bug")
- **friction_points**: Array of what was harder than expected (empty array if none, e.g., "LLM timeout required fallback", "Test framework setup confusion")
- **proposed_changes**: Array of framework improvements identified (empty array if none, e.g., "Add timeout handling to insights generator", "Improve skill discovery docs")

### 2. Operational Metrics (if available from session state)

These fields are typically provided by Claude at session end from session state. If analyzing a transcript post-hoc, extract what you can:

- **current_bead_id**: String issue ID of the bd issue being worked on at session end (e.g., `"aops-kdl0"`). Enables exact checkpoint recovery for session resumption. Use `null` if no bead was active.
- **worker_name**: String identifier for the agent or human completing the work (e.g., `"Claude Opus 4.5"`, `"nic"`). Used for attribution and resumption context. Use `null` if unknown.
- **workflows_used**: Array of workflow names (e.g., `["tdd"]`, `["plan-mode"]`, or `[]` if unknown)
- **subagents_invoked**: Array of subagent names (e.g., `["prompt-hydrator", "critic", "qa"]`)
- **subagent_count**: Integer count of subagents invoked
- **custodiet_blocks**: Integer count of custodiet blocks (0 if none)
- **stop_reason**: String describing how session ended (e.g., `"end_turn"`, `"user_stopped"`, `"unknown"`)
- **critic_verdict**: One of `"PROCEED"`, `"REVISE"`, `"HALT"`, or `null` if critic not invoked
- **acceptance_criteria_count**: Integer count of acceptance criteria, or `null` if not applicable

### 3. Learning Observations (Rich analysis)

For each correction, mistake, learning moment, or process violation, provide an object with:

```json
{
  "category": "Process Adherence|Verification|Context Gap|Axiom Violation|Skill Usage|Error Handling|...",
  "evidence": "What was observed (quote from transcript if possible)",
  "context": "When/where this occurred in the session (e.g., 'During PR creation', 'When implementing tests')",
  "heuristic": "H2|H3|H4|H22|null (map to known heuristics if applicable: H2=Skill-First, H3=Verification, H4=Explicit Instructions, H22=Indices First)",
  "suggested_evidence": "What should have happened instead"
}
```

Examples:

- User corrected agent for skipping a skill → Category: "Skill Usage", Heuristic: "H2"
- Agent forgot to run tests → Category: "Verification", Heuristic: "H3"
- Missing context caused wrong assumption → Category: "Context Gap", Heuristic: null

### 4. Skill Compliance

Track skill invocation effectiveness:

- **suggested**: Array of skills that SHOULD have been invoked
  - Look for hydrator suggestions: `**Skill(s)**: X`
  - Look for router suggestions in system messages
  - Look for explicit user requests: `/skillname`
- **invoked**: Array of skills that WERE actually invoked
  - Look for: `🔧 Skill invoked: \`X\``
  - Look for: `Launching skill: X`
  - Look for: Skill tool calls in transcript
- **compliance_rate**: Float 0.0-1.0
  - Formula: `len(invoked) / len(suggested)` if suggestions exist
  - `1.0` if no skills were suggested (perfect compliance)
  - `0.0` if skills were suggested but none invoked

### 5. Context Gaps

Array of knowledge/context that was needed but not surfaced at the right time.

Examples:

- `"Agent didn't know about existing test helper functions"`
- `"Hydrator didn't mention project's commit message convention"`
- `"Missing information about PR review process"`

Empty array if no gaps identified.

### 6. User Tone Evaluation (Proxy for Satisfaction)

Float from **-1.0** to **1.0** measuring user satisfaction via tone analysis.

**Anchor Points:**

- **1.0** = Effusively positive ("Great work!", "Perfect!", "Love it!", exclamation marks)
- **0.5** = Satisfied ("Thanks", "Looks good", task completed without friction)
- **0.0** = Neutral (default - no feedback, straightforward task execution)
- **-0.5** = Disappointed ("Not quite what I wanted", corrections needed, mild frustration)
- **-1.0** = Furious (explicit frustration, "This is completely wrong", repeated failures)

**Indicators:**

- **Positive (>0)**: Explicit thanks, praise, collaborative tone, smooth completion
- **Neutral (0)**: Minimal feedback, task-focused exchanges only
- **Negative (<0)**: Corrections, repeat requests, explicit frustration, sarcasm

### 7. Conversation Flow (if transcript available)

Array of `[timestamp_iso8601, role, content]` tuples showing dialogue progression:

- **User prompts**: Include verbatim
- **Agent responses**: Summarize in 1-2 sentences
- **Timestamps**: Use ISO 8601 format with timezone (e.g., `"2026-01-13T10:00:00+00:00"`)

If transcript unavailable, provide empty array `[]`.

Example:

```json
[
  ["2026-01-13T10:00:00+00:00", "user", "Create session insights architecture"],
  [
    "2026-01-13T10:00:30+00:00",
    "agent",
    "Spawned prompt-hydrator and entered plan mode"
  ],
  ["2026-01-13T10:15:00+00:00", "user", "Approved plan"],
  ["2026-01-13T10:15:05+00:00", "agent", "Implemented Phase 1 and Phase 2"]
]
```

### 8. User Prompts with Context (if transcript available)

Array of `[timestamp_iso8601, role, content]` tuples capturing:

- The agent message immediately preceding each user prompt
- Then the user prompt itself (verbatim)

This provides context for understanding what prompted each user response.

If transcript unavailable, provide empty array `[]`.

Example:

```json
[
  [
    "2026-01-13T09:59:50+00:00",
    "agent",
    "I've completed the analysis. Ready to proceed?"
  ],
  ["2026-01-13T10:00:00+00:00", "user", "Yes, but also add error handling"],
  ["2026-01-13T10:14:55+00:00", "agent", "Here's the implementation plan."],
  ["2026-01-13T10:15:00+00:00", "user", "Approved"]
]
```

### 9. Agent Self-Reflection (Performance & Workflow Improvements)

Reflect on your performance this session. Identify changes to make workflows easier for similar tasks in the future.

Array of specific, actionable workflow improvements:

Examples:

- `"Add pre-flight checklist for PR creation to avoid missing test runs"`
- `"Create a skill for common test fixture setup pattern"`
- `"Should have run linter earlier in the workflow"`
- `"Skill documentation unclear - needed to read source code"`

Empty array `[]` if no workflow improvements identified.

### 10. JIT Context Optimization (Missing Context)

Identify information that would have saved time if provided earlier. This helps optimize Just-In-Time instruction delivery.

Array of specific context that was missing at session start but needed later:

Examples:

- `"Project uses pytest, not unittest - discovered after writing wrong tests"`
- `"Auth tokens stored in .env.local not .env - caused 10 min debugging"`
- `"Existing helper function already handled this case - duplicated effort"`
- `"Commit message convention not in CLAUDE.md - had to look up in git log"`

Empty array `[]` if no missing context identified.

### 11. Context Distractions (Irrelevant Information)

Identify information that was provided but was irrelevant or distracting. This helps reduce token cost and improve efficiency.

Array of specific context that added noise without value:

Examples:

- `"Detailed plugin architecture docs loaded for simple bug fix"`
- `"Full PR template instructions when task was just code review"`
- `"Legacy migration notes for greenfield development"`
- `"Extensive API documentation when only using one endpoint"`

Empty array `[]` if no distractions identified.

### 12. Framework Reflections (Agent Self-Assessment)

Extract ALL Framework Reflection sections found in the transcript. These structured reflections are output by agents at session end (via `/dump`, `/handover`, or `/learn` skills) and contain valuable session metadata.

**Where to find them:**

- Look for `## Framework Reflection` markdown headers in assistant messages
- May appear multiple times in a session (all should be captured)
- May appear in both main agent and subagent entries

**Framework Reflection format:**

```markdown
## Framework Reflection

**Prompts**: [The user request that triggered the session]
**Guidance received**: [Guidance from hydrator/system]
**Followed**: Yes|No
**Outcome**: success|partial|failure
**Accomplishments**: [List of completed items]
**Friction points**: [Issues encountered]
**Root cause** (if not success): [Category that failed]
**Proposed changes**: [Framework improvements identified]
**Next step**: [Follow-up work needed]
```

**Output structure:**

```json
{
  "framework_reflections": [
    {
      "prompts": "User request that triggered session",
      "guidance_received": "Hydrator/system guidance text",
      "followed": true,
      "outcome": "success",
      "accomplishments": ["Item 1", "Item 2"],
      "friction_points": ["Issue 1"],
      "root_cause": null,
      "proposed_changes": ["Change 1"],
      "next_step": "Follow-up action or null"
    }
  ]
}
```

**Field mappings:**

- `prompts`: String - the user request
- `guidance_received`: String or null - guidance from hydrator
- `followed`: Boolean - whether guidance was followed (true for "Yes", false for "No")
- `outcome`: String - must be "success", "partial", or "failure"
- `accomplishments`: Array of strings - completed items
- `friction_points`: Array of strings - issues encountered (empty array if none)
- `root_cause`: String or null - failure category (only if outcome != success)
- `proposed_changes`: Array of strings - suggested improvements (empty array if none)
- `next_step`: String or null - follow-up action

**Quick Exit format:**
If a reflection shows `Answered user's question: "<summary>"`, parse as:

```json
{
  "prompts": "<summary>",
  "outcome": "success",
  "quick_exit": true
}
```

If no Framework Reflections are found in the transcript, return empty array `[]`.

### 13. Token Metrics (Usage Tracking)

Object containing token usage statistics for observability. This data helps humans analyze patterns and tune JIT hydrator behavior.

Structure:

```json
{
  "token_metrics": {
    "totals": {
      "input_tokens": 45000,
      "output_tokens": 12000,
      "cache_read_tokens": 30000,
      "cache_create_tokens": 5000
    },
    "by_model": {
      "claude-opus-4-5-20251101": { "input": 40000, "output": 10000 },
      "claude-3-5-haiku-20241022": { "input": 5000, "output": 2000 }
    },
    "by_agent": {
      "main": { "input": 35000, "output": 8000 },
      "prompt-hydrator": { "input": 3000, "output": 1000 },
      "custodiet": { "input": 2000, "output": 500 }
    },
    "efficiency": {
      "cache_hit_rate": 0.67,
      "tokens_per_minute": 2500,
      "session_duration_minutes": 23
    }
  }
}
```

**Field descriptions:**

- **totals**: Aggregate token counts across the session
  - `input_tokens`: Total input tokens consumed
  - `output_tokens`: Total output tokens generated
  - `cache_read_tokens`: Tokens read from cache (cost savings)
  - `cache_create_tokens`: Tokens written to cache
- **by_model**: Token breakdown by model used (keys are model IDs)
  - Each model has `input` and `output` counts
- **by_agent**: Token breakdown by agent/subagent
  - `main`: Primary agent tokens
  - Other keys: Subagent names (e.g., `prompt-hydrator`, `custodiet`, `critic`)
- **efficiency**: Derived metrics for analysis
  - `cache_hit_rate`: Float 0.0-1.0, ratio of cache reads to total input
  - `tokens_per_minute`: Average token throughput
  - `session_duration_minutes`: Total session length

Use `null` for the entire object if token data is unavailable.

## Output Format

Output ONLY this JSON structure (no markdown code fences, no explanatory text before or after):

```json
{
  "session_id": "{session_id}",
  "date": "{date}",
  "project": "{project}",
  "summary": "One sentence describing what was worked on",
  "outcome": "success",
  "accomplishments": ["Item 1", "Item 2"],
  "friction_points": ["Issue 1", "Issue 2"],
  "proposed_changes": ["Change 1", "Change 2"],
  "current_bead_id": "aops-kdl0",
  "worker_name": "Claude Opus 4.5",
  "workflows_used": ["workflow1"],
  "subagents_invoked": ["agent1", "agent2"],
  "subagent_count": 2,
  "custodiet_blocks": 0,
  "stop_reason": "end_turn",
  "critic_verdict": "PROCEED",
  "acceptance_criteria_count": 3,
  "learning_observations": [
    {
      "category": "Process Adherence",
      "evidence": "Agent skipped skill invocation",
      "context": "During initial request",
      "heuristic": "H2",
      "suggested_evidence": "Should have invoked framework skill"
    }
  ],
  "skill_compliance": {
    "suggested": ["framework", "audit"],
    "invoked": ["framework"],
    "compliance_rate": 0.5
  },
  "context_gaps": ["Gap 1", "Gap 2"],
  "user_mood": 0.5,
  "conversation_flow": [
    ["2026-01-13T10:00:00+00:00", "user", "Prompt text"],
    ["2026-01-13T10:00:30+00:00", "agent", "Response summary"]
  ],
  "user_prompts": [
    ["2026-01-13T09:59:50+00:00", "agent", "Preceding message"],
    ["2026-01-13T10:00:00+00:00", "user", "User prompt"]
  ],
  "workflow_improvements": [
    "Should have run linter earlier",
    "Skill docs unclear"
  ],
  "jit_context_needed": ["Project uses pytest not unittest"],
  "context_distractions": ["Plugin architecture docs not needed for bug fix"],
  "framework_reflections": [
    {
      "prompts": "User request that triggered the session",
      "guidance_received": "Hydrator guidance text",
      "followed": true,
      "outcome": "success",
      "accomplishments": ["Completed task 1", "Fixed bug 2"],
      "friction_points": [],
      "root_cause": null,
      "proposed_changes": ["Add validation step"],
      "next_step": null
    }
  ],
  "token_metrics": {
    "totals": {
      "input_tokens": 45000,
      "output_tokens": 12000,
      "cache_read_tokens": 30000,
      "cache_create_tokens": 5000
    },
    "by_model": {
      "claude-opus-4-5-20251101": { "input": 40000, "output": 10000 },
      "claude-3-5-haiku-20241022": { "input": 5000, "output": 2000 }
    },
    "by_agent": {
      "main": { "input": 35000, "output": 8000 },
      "prompt-hydrator": { "input": 3000, "output": 1000 },
      "custodiet": { "input": 2000, "output": 500 }
    },
    "efficiency": {
      "cache_hit_rate": 0.67,
      "tokens_per_minute": 2500,
      "session_duration_minutes": 23
    }
  }
}
```

## Important Notes

1. **Variable Substitution**: `{session_id}`, `{date}`, and `{project}` will be replaced before this prompt is sent to you. Use the substituted values EXACTLY.

2. **Required Fields**: At minimum, must include: `session_id`, `date`, `project`, `summary`, `outcome`, `accomplishments`

3. **Optional Fields**: If information is unavailable:
   - Arrays: Use empty array `[]`
   - Objects: Use `null`
   - Strings: Use `null` or empty string `""`
   - Numbers: Use `null` or `0` as appropriate

4. **JSON Only**: Do NOT wrap JSON in markdown code fences (`` ``` ``). Do NOT include commentary before or after the JSON. Output should be pure JSON that can be directly parsed.

5. **Outcome Guidelines**:
   - If user explicitly said "done", "complete", "working" → likely `"success"`
   - If user had to make corrections, work incomplete → likely `"partial"`
   - If major blockers prevented completion → `"failure"`

6. **Timestamp Format**: Always use ISO 8601 with timezone (e.g., `"2026-01-13T10:00:00+00:00"`)
