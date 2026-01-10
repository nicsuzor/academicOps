Analyze this Claude Code session transcript. Extract the following information.

SESSION METADATA (include these EXACTLY in your response):

- session_id: {session_id}
- date: {date}
- project: {project}

EXTRACTION TASKS:

1. SUMMARY - One sentence describing what was worked on
2. ACCOMPLISHMENTS - List of completed items
3. SKILL EFFECTIVENESS - Look for '**Skill(s)**: X' (suggested) and '🔧 Skill invoked: `Y`' (used)
4. CONTEXT TIMING - Was context injected at the right time?
5. USER CORRECTIONS - with heuristic mapping (H2=Skill-First, H3=Verification, H4=Explicit Instructions, H22=Indices First)
6. FAILURES - mistakes requiring intervention
7. SUCCESSES - tasks completed well
8. USER MOOD/SATISFACTION - Subjective assessment: -1.0 (frustrated) to 1.0 (satisfied), 0.0 neutral
9. CONVERSATION FLOW - List of [timestamp, role, content] tuples showing dialogue (user prompts verbatim, agent responses summarized)
10. VERBATIM USER PROMPTS WITH CONTEXT - All user prompts with preceding agent message (format: [timestamp, role, content] tuples)

Return JSON with this EXACT structure:
{
"session_id": "{session_id}",
"date": "{date}",
"project": "{project}",
"summary": "one sentence description",
"accomplishments": ["item1", "item2"],
"learning_observations": [{"category": "...", "evidence": "...", "context": "...", "heuristic": "H[n] or null", "suggested_evidence": "..."}],
"skill_compliance": {"suggested": [...], "invoked": [...], "compliance_rate": 0.0-1.0},
"context_gaps": ["gap1", "gap2"],
"user_mood": 0.3,
"conversation_flow": [["timestamp", "user", "prompt text"], ["timestamp", "agent", "response summary"]],
"user_prompts": [["timestamp", "agent", "preceding message"], ["timestamp", "user", "verbatim prompt"]]
}
