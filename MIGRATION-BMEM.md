# bmem → memory Migration Instructions

**Branch**: `remove-bmem`
**Goal**: Replace all bmem references with memory server equivalents

## Replacement Rules

| Old | New |
|-----|-----|
| `mcp__bmem__search_notes(...)` | `mcp__memory__retrieve_memory(query="...")` |
| `mcp__bmem__write_note(...)` | `Skill(skill="remember")` |
| `mcp__bmem__read_note(...)` | `mcp__memory__retrieve_memory(query="...")` |
| `mcp__bmem__build_context(...)` | `mcp__memory__retrieve_memory(query="...")` |
| `Skill(skill="bmem")` | `Skill(skill="remember")` |
| `bmem` (prose) | `memory` or `memory server` (context-dependent) |
| `bmem-formatted` | `properly formatted markdown` |
| `project="main"` parameter | DELETE (memory server doesn't use projects) |

## Important Context

- The `remember` skill writes markdown AND syncs to memory server
- Agents should invoke `Skill(skill="remember")` to persist knowledge, NOT write markdown directly
- For searching: use `mcp__memory__retrieve_memory(query="...")`

---

## TIER 1: Haiku (Simple text replacements)

These files just need prose updates - no logic changes:

```
commands/diag.md
commands/email.md
commands/meta.md
commands/pull.md
commands/strategy.md
commands/ttd.md
agents/intent-router.md
skills/session-insights/SKILL.md
skills/osb-drafting/SKILL.md
skills/link-audit/SKILL.md
skills/learning-log/SKILL.md
README.md
RULES.md
INDEX.md
GEMINI.md
tests/README.md
tests/HOOK_TEST_PROTOCOL.md
scripts/transcribe_recording.sh
```

**Instructions for Haiku agents**:
1. Read the file
2. Replace bmem references per the table above
3. Keep the meaning intact, just update terminology
4. Commit with message: `chore: update [filename] for memory migration`

---

## TIER 2: Sonnet (Need careful review)

These have tool invocations or test assertions:

```
commands/qa.md
commands/task-viz.md
commands/parallel-batch.md
hooks/request_scribe.py
hooks/autocommit_state.py
lib/session_analyzer.py
scripts/migrate_log_entries.py
setup.sh
skills/dashboard/SKILL.md
skills/extractor/SKILL.md
skills/extractor/extractor.md
tests/conftest.py
tests/tools/conftest.py
tests/integration/conftest.py
tests/test_request_scribe_hook.py
tests/test_session_analyzer_dashboard.py
tests/test_task_server_integration.py
tests/integration/test_autocommit_data.py
tests/integration/test_prompt_router_haiku_flow.py
tests/integration/test_skill_delegation_pattern.py
tests/integration/test_skill_invocation_e2e.py
tests/integration/test_subagent_skill_invocation.py
```

**Instructions for Sonnet agents**:
1. Read the file carefully
2. Understand what bmem operations are being performed
3. Replace with memory equivalents per table
4. For tests: update assertions to check for new tool names
5. If a test is fundamentally testing bmem-specific behavior, DELETE it
6. Commit with message: `refactor: migrate [filename] from bmem to memory`

---

## TIER 3: Opus (Complex rewrites needed)

These are core workflows that need careful thought:

```
skills/tasks/SKILL.md
skills/tasks/tasks.md
skills/tasks/task_ops.py
skills/tasks/scripts/task_add.py
skills/tasks/workflows/email-capture.md
skills/framework/SKILL.md
skills/framework/references/strategic-partner-mode.md
skills/framework/references/e2e-test-harness.md
skills/framework/references/script-design-guide.md
skills/framework/tests/test_email_workflow_tools.py
skills/dashboard/dashboard.py
skills/extractor/tests/test_archive_integration.sh
.github/workflows/ios-note-capture.yml
```

**Instructions for Opus agents**:
1. Read the ENTIRE file to understand the workflow
2. The key change: knowledge persistence now goes through `Skill(skill="remember")`
3. Update workflows to:
   - Use `mcp__memory__retrieve_memory` for searching
   - Use `Skill(skill="remember")` for persisting (this writes markdown AND syncs)
4. For dashboard.py: update any bmem MCP calls to memory equivalents
5. For workflows: rewrite steps that mention bmem to use new pattern
6. Test your changes make sense in context
7. Commit with message: `refactor: rewrite [filename] for memory migration`

---

## Skip (Auto-generated)

```
reference-graph.csv  # Will be regenerated
```

---

## Verification

After all files updated, run:
```bash
grep -r "bmem" $AOPS --include="*.py" --include="*.md" --include="*.sh" --include="*.yml"
```

Should return empty (except this file and any intentional historical references in LOG.md).

## Final Step

Update ROADMAP.md to move "bmem → mcp-memory migration" from "In Progress" to "Done".
