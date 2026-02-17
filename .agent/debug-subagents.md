# Debugging Subagents

Quick reference for testing and debugging framework subagents.

## The QA Tool

Use `subagent_qa.py` to inspect what context a subagent receives and optionally run it:

```bash
uv run python aops-core/scripts/subagent_qa.py --help
```

## Common Workflows

### Test Hydrator Context

See what the hydrator would receive for a given prompt:

```bash
# Show context only
uv run python aops-core/scripts/subagent_qa.py "fix the bug in auth"

# Show context + run Haiku
uv run python aops-core/scripts/subagent_qa.py "fix the bug" --run

# Save to file for review
uv run python aops-core/scripts/subagent_qa.py "my prompt" --save /tmp/qa-output.md
```

### Test Critic

```bash
# Pass a plan directly
uv run python aops-core/scripts/subagent_qa.py \
  --subagent critic \
  --context "Review this plan: Add JWT auth to the API..."

# Or from a file
uv run python aops-core/scripts/subagent_qa.py \
  --subagent critic \
  --context-file /tmp/my-plan.md
```

### Test Custodiet

```bash
# Pass an audit file
uv run python aops-core/scripts/subagent_qa.py \
  --subagent custodiet \
  --context-file ~/.claude/projects/.../audit.md
```

### List Available Agents

```bash
uv run python aops-core/scripts/subagent_qa.py --list
```

## Extracting Samples from Transcripts

Find subagent responses in session transcripts:

```bash
# Find transcripts with hydrator responses
grep -l "hydration_result" ~/.aops/transcripts/*-full.md

# Extract a specific response
grep -A100 "<hydration_result>" ~/.aops/transcripts/YYYYMMDD-*.md | head -80
```

## Key Context Sections

When reviewing hydrator context, check these sections:

| Section | What to look for |
|---------|------------------|
| **User Prompt** | Is the prompt captured correctly? |
| **Session Context** | Does it include recent work? |
| **Task State** | Are active tasks visible? |
| **Workflow Index** | Is the right workflow being suggested? |
| **Relevant Files** | Are keyword matches sensible? |

## Troubleshooting

**Hydrator returns wrong workflow:**
- Check if prompt keywords match workflow routing rules
- Review `WORKFLOWS.md` decision tree

**Context is too large:**
- Check `load_*` functions in `lib/hydration/context_loaders.py`
- Look for unnecessary sections being included

**Subagent not found:**
- Verify agent file exists in `aops-core/agents/`
- Check spelling matches filename (e.g., `prompt-hydrator.md`)

## Adding New Subagents

To support a new subagent in the QA tool:

1. Add agent file to `aops-core/agents/<name>.md`
2. Add model mapping in `subagent_qa.py`:
   ```python
   AGENT_MODELS = {
       ...
       "new-agent": "claude-3-5-haiku-latest",
   }
   ```
3. If it needs special context building, add a handler in `build_context()`
