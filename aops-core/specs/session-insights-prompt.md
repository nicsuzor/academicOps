# Session Insights Generation Prompt

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

- **workflows_used**: Array of workflow names (e.g., `["tdd"]`, `["plan-mode"]`, or `[]` if unknown)
- **subagents_invoked**: Array of subagent names (e.g., `["prompt-hydrator", "critic", "qa-verifier"]`)
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

### 6. User Mood/Satisfaction

Float from **-1.0** (frustrated) to **1.0** (satisfied), **0.0** neutral.

Indicators:
- **Positive**: Explicit thanks, collaborative tone, task completed smoothly
- **Neutral**: Straightforward task execution, minimal corrections
- **Negative**: Corrections, repeat requests, explicit frustration, sarcasm

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
  ["2026-01-13T10:00:30+00:00", "agent", "Spawned prompt-hydrator and entered plan mode"],
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
  ["2026-01-13T09:59:50+00:00", "agent", "I've completed the analysis. Ready to proceed?"],
  ["2026-01-13T10:00:00+00:00", "user", "Yes, but also add error handling"],
  ["2026-01-13T10:14:55+00:00", "agent", "Here's the implementation plan."],
  ["2026-01-13T10:15:00+00:00", "user", "Approved"]
]
```

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
  ]
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

4. **JSON Only**: Do NOT wrap JSON in markdown code fences (` ``` `). Do NOT include commentary before or after the JSON. Output should be pure JSON that can be directly parsed.

5. **Outcome Guidelines**:
   - If user explicitly said "done", "complete", "working" → likely `"success"`
   - If user had to make corrections, work incomplete → likely `"partial"`
   - If major blockers prevented completion → `"failure"`

6. **Timestamp Format**: Always use ISO 8601 with timezone (e.g., `"2026-01-13T10:00:00+00:00"`)
