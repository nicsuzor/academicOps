---
name: debug-headless
category: instruction
description: Debug Claude Code or Gemini CLI in headless mode with full output capture.
allowed-tools: Bash, Read, Write, Glob
version: 0.4.0
permalink: skills-debug-headless
---

# /debug-headless - Headless AI CLI Debugging

Run Claude Code or Gemini CLI non-interactively with output and debug log capture.

## Quick Start

```bash
# Run headless session
cd /path/to/project && claude -p "your prompt" --output-format json --model haiku

# Find the session file (most recent)
ls -lt ~/.claude/projects/-home-<user>-<project>/*.jsonl | head -1

# Generate readable transcript
cd $AOPS && uv run python scripts/session_transcript.py /path/to/session.jsonl
```

## Workflow

### 1. Run Headless Session

```bash
claude -p "prompt" --output-format json --model haiku 2>&1 | head -200
```

**Key flags:**

- `-p "prompt"` - Non-interactive mode with prompt
- `--output-format json` - Structured output for parsing
- `--model haiku` - Faster/cheaper for testing (or `sonnet` for complex)
- `--dangerously-skip-permissions` - Skip permission prompts (use carefully)

### 2. Find Session File

Sessions are stored at: `~/.claude/projects/-<path-with-dashes>/<uuid>.jsonl`

```bash
# List recent sessions for a project
ls -lt ~/.claude/projects/-home-user-src-academicOps/*.jsonl | head -5

# Find session by prompt content
grep -l "your prompt text" ~/.claude/projects/-home-user-src-*/*.jsonl
```

### 3. Generate Transcript

```bash
cd $AOPS && uv run python scripts/session_transcript.py /path/to/session.jsonl
```

**Output**: Creates two files in `$ACA_DATA/sessions/claude/`:

- `*-full.md` - Complete transcript with all tool results
- `*-abridged.md` - Compact view without tool output details

### 4. Analyze Session

**Use the transcript** - don't grep raw JSONL. The full transcript contains:

- `### Hook: EventName: ToolName ✓` - Hook execution markers
- `### Subagent: type (description)` - Inline subagent conversations
- `## Subagent Transcripts` - Orphan/warmup agents at end
- Tool outputs in code blocks with proper formatting

**What to look for:**

| Debug Question        | Look In Transcript                                                 |
| --------------------- | ------------------------------------------------------------------ |
| Did custodiet fire?   | `### Hook: PostToolUse` entries + `Task(subagent_type="custodiet"` |
| What hooks ran?       | All `### Hook:` headings show event + tool                         |
| Where did it fail?    | Search for `ERROR`, `failed`, `exit [1-9]`                         |
| What did subagent do? | `### Subagent:` sections show full conversation                    |
| What was injected?    | SessionStart hook content at beginning                             |

## Hook Behavior in Headless Mode

**Custodiet threshold**: Fires every ~5 "action" tool calls.

**Skipped tools** (don't count toward threshold):

- `Read`, `Glob`, `Grep`, `mcp__memory__retrieve_memory`

**Parallel vs Sequential**: Tools called in parallel (same turn) may count differently than sequential calls across multiple turns.

## Hook Verification

**Use the full transcript** to verify hooks:

| Hook             | What to Check in Transcript                     |
| ---------------- | ----------------------------------------------- |
| SessionStart     | First content block has AXIOMS.md/HEURISTICS.md |
| UserPromptSubmit | `### Hook: UserPromptSubmit ✓` after user turn  |
| PostToolUse      | `### Hook: PostToolUse: ToolName ✓` entries     |
| Stop             | No `✗ (exit N)` markers on hooks                |

**Hook status indicators:**

- `✓` = exit 0 (success)
- `✗ (exit N)` = non-zero exit (error)

## Troubleshooting

**Hook not executing:**

```bash
# Check settings.json configuration
cat ~/.claude/settings.json | jq '.hooks'

# Check hook file exists
ls -la $AOPS/hooks/*.py | head -10
```

**Session exits with code 1:**

- Check Stop hooks return `sys.exit(0)` for advisory messages
- Verify no infrastructure errors in hook output

## Quick Reference

| Tool        | Headless Flag | Debug Flag | Auto-approve                     |
| ----------- | ------------- | ---------- | -------------------------------- |
| Claude Code | `-p`          | `-d`       | `--dangerously-skip-permissions` |
| Gemini CLI  | (positional)  | `-d`       | `-y` / `--yolo`                  |

## Related

- [[skills/session-insights/]] - Analyzes session transcripts
- [[transcript]] - Generates markdown from session logs
