# Meta Improvement and Skill Piloting Details

Detailed procedures for auditing tool effectiveness and piloting new framework skills.

## Tool Effectiveness Audit

Reflect on each tool used during the session:

| Tool Category    | Questions                                    |
| ---------------- | -------------------------------------------- |
| Search tools     | Did queries find what I described?           |
| Memory/retrieval | Was content relevant? Fresh?                 |
| Task manager     | Did structured queries beat semantic search? |
| Graph traversal  | Could I find relationships?                  |

### Knowledge Base Hygiene

- **Task titles**: Use natural language alongside technical terms.
- **Memory freshness**: Periodically check if recent work is represented.
- **Graph completeness**: Relationships in your head → relationships in graph.

## Section: Skill Piloting

Build new skills when decomposition reveals capability gaps.

### When to Pilot

- Decomposition reaches task with no matching skill.
- Recurring pattern without standardized approach.
- First-time task worth capturing.

### Piloting Steps

1. **Articulate gap**: What? Why no existing skill?
2. **Pilot with user**: Interactive, supervised learning.
3. **Reflect**: Essential vs incidental steps.
4. **Draft SKILL.md**: when-to-use, steps, quality gates.
5. **Test**: Apply to similar task without guidance.
6. **Index**: Add to plugin.json.

### Anti-Patterns

| Anti-Pattern          | Problem                      |
| --------------------- | ---------------------------- |
| Premature abstraction | Skill after one use.         |
| Kitchen sink          | Too much in one skill.       |
| Orphan skill          | Not indexed = doesn't exist. |
