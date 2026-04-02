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

1. **Hydration behavior**: Did the agent invoke the hydrator when instructed?
   - Claude: `Task(subagent_type="aops-core:hydrator", ...)`
   - Gemini: `activate_skill(name="hydrator", ...)`
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

---

## Hydrator Routing Acceptance Tests

Use this workflow when running `tests/acceptance/v*.md` routing test suites. These tests evaluate **routing quality**, not just technical compliance — they require LLM supervision, not pytest.

### Why LLM Supervision (Not Pytest)

Routing tests evaluate whether the hydrator's output is _good_ — does it recommend the right skill, include the right context, avoid noise? A pytest assertion can check "does the string '/email' appear" but can't judge whether the routing plan actually helps the user. You need to evaluate that yourself.

### The Test Harness Pattern (CRITICAL)

**Always build the context file first. Never pass a raw prompt string to the hydrator.**

In production, the UserPromptSubmit hook calls `build_hydration_instruction()` which writes a context bundle (SKILLS.md, WORKFLOWS.md, AXIOMS, HEURISTICS, project workflows) to a temp file, and passes the _file path_ to the hydrator. Tests must replicate this.

```bash
# Step 1: Build context file for the test prompt
context_path=$(uv run scripts/build_hydrator_test_input.py "check my email and triage anything urgent")

# Step 2: Invoke the hydrator with the file path (not the raw prompt)
Agent(subagent_type='aops-core:hydrator', prompt='<context_path from step 1>')
```

**Anti-pattern** (causes all tests to fail — hydrator has no framework context):

```python
# WRONG — hydrator receives no SKILLS.md, no workflows, can't route anything
Agent(subagent_type='aops-core:hydrator', prompt='check my email')
```

### Running the Test Suite

1. For each test in `tests/acceptance/v0.3-release.md` (or other acceptance files):
   - Build the context file: `uv run scripts/build_hydrator_test_input.py "<user input>"`
   - Invoke the hydrator subagent with the returned file path
   - Read the hydrator's output
2. Evaluate quality (see criteria below)
3. Update the Results table in the test file with PASS/FAIL, timestamp, notes
4. After all tests complete, report: X passed, Y failed, Z errors

### Quality Evaluation Criteria

For each routing test, assess:

- **Correct skill/workflow identified** — does the hydrator name the right skill or workflow for the intent?
- **Relevant context included** — does the execution plan include meaningful steps, not generic boilerplate?
- **No noise** — does the hydrator avoid recommending irrelevant skills?
- **Actionable output** — could an agent follow this plan and do useful work?

A routing plan that names the right skill but provides no useful steps is a partial pass (routing correct, quality low). Note the distinction in results.

### Interpreting Results

- **8+ / 12 tests passing** — harness is working, routing is healthy
- **< 8 passing** — investigate whether failures are routing logic errors or harness issues first
- **All tests failing with "out of scope" or "no tools found"** — harness is broken; the hydrator is receiving raw prompts instead of context file paths

### Known Failure Patterns (from v0.3 run, 2026-03-05)

These patterns recur and should be checked when failures appear:

**Pattern 1 — MCP tools gap** (affects email-related routing)

- Symptom: Hydrator invokes P#48 halt for email requests ("no email tools available")
- Root cause: `load_mcp_tools_context()` in `builder.py` does not include Outlook MCP server tools in the context bundle — the hydrator correctly concludes no email capability exists
- Fix target: `aops-core/lib/hydration/context_loaders.py` → `load_mcp_tools_context()` must include configured MCP servers
- Test to rerun: TEST-001

**Pattern 2 — Skill recognition gap** (affects skills with weak trigger keywords)

- Symptom: Hydrator produces a correct manual plan but never mentions the dedicated skill (`/annotations`, `/hdr`)
- Root cause: SKILLS.md trigger keywords for these skills don't match natural-language phrasing well enough
- Fix target: SKILLS.md entries for `/annotations` and `/hdr` — add stronger natural-language triggers
- Example: "scan for @nic annotations" should trigger `/annotations`; "write reference letter for PhD student" should trigger `/hdr`
- Tests to rerun: TEST-009, TEST-010

**Pattern 3 — Role drift on memory/persist tasks**

- Symptom: Hydrator tries to execute the task (draft files, talk to user, ask questions) instead of routing to `Skill(skill="remember")`
- Root cause: "remember" prompts contain concrete content that tempts the hydrator to act; its tool restrictions (`read_file` only) are not strong enough to prevent it from attempting writes
- Fix target: `agents/hydrator.md` — strengthen the prohibition against execution for persist-type tasks; add explicit example: "User says 'remember X' → route to Skill(skill='remember'), do NOT draft the content yourself"
- Tests to rerun: TEST-011

### After Fixing Failures

Re-run only the failed tests (do not re-run passing tests unless the fix could regress them). Append new rows to the Results table with updated timestamps rather than overwriting old ones.

---

### Logging Issues

When you find framework problems during transcript review, log them as bug tasks:

```bash
# Via MCP tool
mcp__pkb__create_task(
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
