# Manual QA Workflow

Test that the framework works with different AI CLI tools.

## Claude Test

```bash
command claude --permission-mode bypassPermissions --output-format json --print "What time is it?"
```

## Gemini Test

```bash
command gemini --approval-mode yolo --output-format stream-json --p "What time is it?"
```

## Generate Transcripts

After both runs, create transcript files:

```bash
uv run python $AOPS/aops-core/scripts/transcript.py --recent
```

## Find New Transcripts

Find transcripts created in the last 10 minutes:

```bash
fd -l --newer 10m -e md . ~/writing/sessions/
```

Or search for specific content in recent transcripts:

```bash
fd --newer 60m -e md . ~/writing/sessions | xargs rg "what time is it"
```

## Assessment

Review the abridged transcript for each session and assess the conversation, looking for markers of features from our framework.

### Reading Transcripts

**Transcript Structure:**

- YAML frontmatter with session metadata (date, session_id, source_file)
- `Tools Used` summary - quick overview of what tools were invoked
- `Subagents` count - how many sub-agents were spawned
- Token usage breakdown (useful for cost/efficiency analysis)
- Turn-by-turn conversation with timestamps and duration

**What to Look For:**

1. **Hydration behavior**: Did the agent invoke the prompt-hydrator when instructed?
   - Claude: `Task(subagent_type="aops-core:prompt-hydrator", ...)`
   - Gemini: `activate_skill(name="prompt-hydrator", ...)`
   - **Check for "(not set)" paths**: Ensure the block message correctly resolved the `{temp_path}`. If it says `Follow instructions in (not set)`, the path resolution logic is broken.

2. **Hook compliance**: Look for `**Invoked:**` markers showing hook triggers.
   - **Pydantic Validation**: Check for `Failed with non-blocking status code` errors in stderr. This often indicates a schema mismatch (e.g., `tool_output` received a list instead of a dict).
   - **Subagent Freedom**: Inspect hook logs (`cat ~/.claude/projects/...-hooks.jsonl`) to ensure subagents aren't being blocked by gates meant for the main agent.

3. **Client-Specific Instructions**: Verify the block message provides the correct command for the current client.
   - Claude should receive `Task(...)` instructions.
   - Gemini should receive `delegate_to_agent(...)` instructions.

4. **Workflow routing**: Check if agent correctly identified the workflow type.
   - `simple-question` → should be fast, no task needed.
   - Complex tasks → should show hydration, task binding, critic review.

5. **Gate satisfaction**: Look for critic and QA invocations where required.
   - Critic: `Task(subagent_type="aops-core:critic", ...)`
   - QA: `Task(subagent_type="aops-core:qa", ...)`

6. **Turn count**: Simple questions should complete in 1-2 turns. Many turns for simple tasks indicates framework friction or recursive blocking.

### Hook Log Forensics

If things seem "sticky", inspect the raw JSONL hook log:

```bash
# Find the latest hook log
ls -t ~/.claude/projects/*-hooks.jsonl | head -n 1 | xargs cat
```

Look for:

- `verdict: deny` on tool calls that should be allowed.
- Gate names in `metadata.gate_times` to see which gates are firing.
- `WARNING: Hydration failed` messages in `system_message`.

### Example Observations

**Claude vs Gemini on "What time is it?":**

| Aspect            | Claude                    | Gemini                            |
| ----------------- | ------------------------- | --------------------------------- |
| Turns             | 6                         | 1                                 |
| Hydration         | Read file after prompting | Followed instructions immediately |
| Stop hook battles | 4+ stop hook triggers     | None                              |
| Final answer      | Correct (3:02 PM AEST)    | Correct (3:03 PM AEST)            |

**Issue identified**: Stop hook fires inappropriately for `simple-question` workflow, demanding critic/QA review for trivial queries. Bug logged as `aops-ba026b2f`.

### Logging Issues

When you find framework problems during transcript review, log them as bug tasks:

```bash
# Via MCP tool
mcp__plugin_aops-core_task_manager__create_task(
    task_title="<clear description of the bug>",
    type="bug",
    project="aops",
    priority=2,
    tags=["relevant", "tags"],
    body="## Problem\n\n<what's broken>\n\n## Evidence\n\n<transcript excerpts, comparison tables>\n\n## Expected Behavior\n\n<what should happen>\n\n## Root Cause Hypothesis\n\n<where to look>"
)
```

**Bug template checklist:**

- [ ] Clear title describing the issue
- [ ] Evidence from transcripts (turn counts, hook triggers, token usage)
- [ ] Comparison between clients if available (Claude vs Gemini)
- [ ] Expected vs actual behavior
- [ ] Hypothesis about root cause location
- [ ] Link to relevant transcript files

**Example bugs from QA sessions:**

- `aops-ba026b2f` - Stop hook triggers critic requirement for simple questions (logged by agent)
- `aops-f8759a13` - Stop hook ignores simple-question workflow routing (logged during review)
