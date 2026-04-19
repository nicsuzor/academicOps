---
title: Debug Framework Issue
type: automation
category: instruction
permalink: workflow-debug-framework-issue
description: Process for diagnosing and fixing framework component failures and integration issues
---

# Workflow 2: Debug Framework Issue

**When**: Framework component failing, unexpected behavior, integration broken.

**Key principle**: Use **controlled tests in /tmp** to run experiments and validate hypotheses. Read **Claude session logs** to understand agent behavior.

**CRITICAL**: If you need to read session JSONL files, invoke `Skill(skill='transcript')` FIRST to convert to markdown. Raw JSONL wastes 10-70K tokens; transcripts are 90% smaller and human-readable.

**Steps**:

1. **Reproduce the issue with controlled test**
   - Run test with `--debug` flag (fixture does this automatically)
   - Test runs in `/tmp/claude-test-*` directory (controlled environment)
   - Required env vars (`AOPS`, `ACA_DATA`) must be set (fail-fast if missing)
   - Document exact steps to trigger issue
   - Verify issue exists (not user error)

2. **Read Claude session logs to understand behavior**
   - Session logs stored in `~/.claude/projects/-tmp-claude-test-*/`
   - Use ripgrep to search logs: `rg "pattern" ~/.claude/projects/-tmp-claude-test-*/`
   - Check JSONL files for:
     - User prompts sent to agent
     - Tool calls made by agent
     - Agent's reasoning and decisions
     - Error messages or failures
   - Look for: Did agent read the right files? Follow instructions? Use correct tools?

3. **Form hypothesis about root cause**
   - Verify component follows single source of truth
   - Look for duplication or conflicts
   - **Agent behavior analysis**: Did agent receive correct context? Interpret instructions correctly?

4. **Test hypothesis with controlled experiment**
   - Modify one variable at a time
   - Run test in `/tmp` with `--debug` flag
   - Read session logs to confirm behavior change
   - Iterate until hypothesis confirmed
   - **Pattern**: Change → Test → Read logs → Refine hypothesis

5. **Design minimal fix**
   - Minimal change to address root cause
   - Avoid workarounds
   - Maintain documentation integrity
   - **Fail-fast enforcement**: Add validation that fails immediately on misconfiguration

6. **Create/update integration test**
   - Test must fail with current broken state
   - Test must pass with fix applied
   - Cover regression cases
   - **E2E test**: Agent must actually read and follow instructions (not just file existence)

7. **Validate fix with full test suite**
   - Run all integration tests with `--debug` enabled
   - Verify no new conflicts introduced
   - Confirm documentation consistency
   - Check session logs if tests fail

8. **Log in experiment if significant**
   - Document issue, root cause, fix
   - Note lessons learned from session log analysis
   - Document debugging pattern used
   - Update tests to prevent recurrence

## Debugging Tools

**Session log analysis**:

```bash
# Find test project directories
ls ~/.claude/projects/-tmp-*

# Search for specific prompt
rg "pattern" ~/.claude/projects/-tmp-claude-test-*/

# Check agent tool usage
rg "type.*tool" ~/.claude/projects/-tmp-claude-test-*/
```

**Session transcript generation** (human-readable format):

```bash
# List recent sessions for current project
ls -lt ~/.claude/projects/-home-nic-src-aOps/*.jsonl | head -5

# Generate markdown transcript from JSONL
mkdir -p ~/.cache/aops/transcripts
uv run $AOPS/scripts/session_transcript.py \
  ~/.claude/projects/{project-path}/{session-id}.jsonl \
  -o ~/.cache/aops/transcripts/{session-id}_transcript.md

# Read transcript (much easier than raw JSONL)
cat ~/.cache/aops/transcripts/{session-id}_transcript.md
```

Use transcripts when:

- Raw JSONL search results are hard to interpret
- Need to understand full conversation flow
- Sharing session details for debugging

**Note**: Transcripts don't show hook-injected `<system-reminder>` tags. To verify hook behavior, grep raw JSONL.

## Controlled test environment

- Tests run in `/tmp/claude-test-*` (consistent location)
- `--debug` flag automatically enabled (full logging)
- Env vars validated fail-fast (`AOPS`, `ACA_DATA` required)
- Session logs persist for post-mortem analysis

**Hypothesis testing pattern**:

1. State hypothesis about root cause
2. Design test that would confirm/refute hypothesis
3. Run test with `--debug` in `/tmp`
4. Read session logs for evidence
5. Refine hypothesis based on evidence
6. Repeat until root cause identified

## Deep Root Cause Analysis (MANDATORY for "why didn't X work?")

When investigating why something didn't work as expected, **surface explanations are insufficient**. Use these techniques:

### 1. Never Accept Surface Explanations

| Surface answer           | Required follow-up                            |
| ------------------------ | --------------------------------------------- |
| "It wasn't run"          | WHY wasn't it run? Was it invoked but failed? |
| "The file doesn't exist" | WAS it created? Check git history             |
| "The skill didn't work"  | Find the EXACT error message in transcripts   |

### 2. Git Forensics (REQUIRED)

```bash
# What commits touched this file?
git log --oneline --all -- "path/to/file"

# What was the content at a specific commit?
git show <commit>:<path/to/file>

# Full diff history for a file
git log -p --follow -- "path/to/file"

# What else was in a commit?
git show <commit> --stat

# All commits in a time range
git log --oneline --since="YYYY-MM-DD HH:MM"
```

### 3. Production Transcript Analysis

Search transcripts for skill invocations and errors:

```bash
# Find skill invocations
grep -l "Skill.*skillname\|/skillname" $ACA_DATA/../sessions/claude/*.md

# Find errors in a transcript
grep -B5 -A15 "❌ ERROR\|Traceback\|AttributeError" <transcript>

# See context around skill invocation
grep -B2 -A15 "Skill invoked.*skillname" <transcript>
```

### 4. Verify Claims By Running Code

Don't trust documentation - verify actual state:

```bash
# Check what attributes an object actually has
uv run python -c "
from lib.module import SomeClass
from dataclasses import fields
for f in fields(SomeClass):
    print(f'{f.name}: {f.type}')
"

# Check if file/function exists
uv run python -c "from lib.module import function_name; print('exists')"
```

### 5. Identify Axiom Violations

Common failure patterns map to axiom violations:

| Symptom                              | Likely violation                                                   |
| ------------------------------------ | ------------------------------------------------------------------ |
| Workflow started but didn't complete | AXIOM #8 (Fail-Fast): Agent worked around error instead of halting |
| Wrong data written                   | AXIOM #7 (Fail-Fast): Silent failure, no validation                |
| Skill docs don't match code          | H9: Skills contain no dynamic content                              |
| Agent promised to improve            | H11: No promises without instructions                              |

### Example: Full Investigation

"Why didn't session-insights produce a daily summary?"

1. **Surface**: "It wasn't run" → **Push deeper**
2. **Git forensics**: `git log -- sessions/YYYYMMDD-daily.md` - found commits exist
3. **Transcript search**: `grep "session-insights" transcripts/*.md` - found invocation
4. **Error extraction**: Found `AttributeError: 'SessionInfo' has no 'start_time'`
5. **Verification**: Ran code to confirm `start_time` doesn't exist on `SessionInfo`
6. **Axiom violation**: Agent worked around error (AXIOM #8 violation) instead of halting
7. **Root cause**: Skill docs referenced non-existent attribute + agent didn't halt on error

## Debugging Headless/Subagent Sessions

When a test spawns a headless Claude session (via `claude -p` or Task tool) and it fails or times out, use this workflow to investigate what the subagent actually did.

### 1. Find the Subagent Session File

The test output usually includes the session ID. Search for it:

```bash
# Search by session ID (from test output)
grep -rl "SESSION_ID_HERE" ~/.claude/projects/

# Search by unique prompt content
grep -rl "add_numbers\|unique_prompt_text" ~/.claude/projects/ | head -10

# Find test project sessions (tests run from academicOps)
ls -lt ~/.claude/projects/-home-nic-src-academicOps/*.jsonl | head -10
```

**Tip**: Tests running headless sessions create JSONL in `~/.claude/projects/-home-nic-src-academicOps/` (the project where pytest runs), not in the test temp directory.

### 2. Generate Readable Transcript

Raw JSONL is unreadable. Always convert first:

```bash
# Generate transcript (saves to $ACA_DATA/../sessions/claude/)
cd $AOPS && uv run python scripts/session_transcript.py \
  ~/.claude/projects/-home-nic-src-academicOps/SESSION_ID.jsonl

# Output shows paths to full and abridged versions
# Abridged is usually sufficient (excludes tool results)
```

### 3. Analyze the Transcript

Look for these patterns:

| Pattern             | Location in Transcript                     | What It Reveals                    |
| ------------------- | ------------------------------------------ | ---------------------------------- |
| **Subagent spawns** | `### Subagent: TYPE (description)`         | What subagents were invoked        |
| **Tool errors**     | `**❌ ERROR:**`                            | Failed tool calls with exact error |
| **Turn timing**     | `## User (Turn N (HH:MM, took X seconds))` | Where time was spent               |
| **Hook injections** | `Hook(SessionStart)` at top                | What context was loaded            |
| **TodoWrite items** | `▶ □ ✓` markers                            | Planned vs executed work           |

### 4. Common Failure Patterns

| Symptom                          | Likely Cause                      | Fix                                             |
| -------------------------------- | --------------------------------- | ----------------------------------------------- |
| **Timeout with few tool calls**  | Stuck in loop                     | Check for recursive spawns                      |
| **Timeout with many tool calls** | Over-engineered workflow          | Prescribed overkill; add "trivial task" bypass  |
| **Tool error cascade**           | First error caused confusion      | Fix the first error; later ones are symptoms    |
| **Enforcer CANNOT_ASSESS**       | Audit file has incomplete context | Expected for short sessions; not a real failure |
| **Write "file not read" error**  | Tried to create new file          | Use Bash heredoc or fix Write tool handling     |

### 5. Example: Demo Test Timeout Investigation

**Problem**: `test_core_pipeline.py` timed out after 180s on a trivial "write add_numbers function" task.

**Investigation**:

```bash
# Find session from test output (session ID: c64de01b-...)
grep -rl "c64de01b" ~/.claude/projects/
# Found: ~/.claude/projects/-home-nic-src-academicOps/c64de01b-....jsonl

# Generate transcript
cd $AOPS && uv run python scripts/session_transcript.py \
  ~/.claude/projects/-home-nic-src-academicOps/c64de01b-....jsonl
```

**Transcript revealed**:

1. Turn 1 took **2 minutes 34 seconds** (way too long)
2. Prescribed full **TDD workflow with 5 todo items**
3. Enforcer spawned but returned `CANNOT_ASSESS` (incomplete context)
4. Write tool failed ("file not read"), Bash heredoc also failed ("file exists")
5. Session timed out before completing

**Root cause**: Framework overhead (TDD prescription + enforcer) consumed all time on a trivial task.

**Axiom violations identified**:

- TDD overkill: Full test cycle for trivial utility function
- Tool friction: Write tool requires pre-read even for new files

## Debugging Gemini CLI / Crew Sessions

When debugging Gemini-based crew or polecat sessions (as opposed to Claude Code sessions), different tools and log locations apply.

### 1. Check MCP Server Status

```bash
# List all configured MCP servers and their connection state
gemini mcp list

# Expected output for healthy PKB:
# ✓ pkb (from aops-core): pkb mcp (stdio) - Connected

# If pkb shows "disconnected" or is missing, the server binary failed to start.
```

### 2. Get Debug Logs from Gemini CLI

```bash
# Run with --debug flag (opens debug console, shows verbose extension/MCP loading)
gemini --debug

# Extension loading errors appear on stderr:
# [ExtensionManager] Error loading agent from aops-core: ...

# Capture stderr to a file for analysis:
gemini --sandbox 2>gemini-debug.log
```

### 3. Enable Verbose PKB Server Logging

The PKB MCP server respects `RUST_LOG` env var. Change from `warn` to `debug` in the extension config:

```json
"env": {
  "ACA_DATA": "${ACA_DATA}",
  "RUST_LOG": "debug"
}
```

Config locations:

- **Gemini extension**: `~/.gemini/extensions/aops-core/gemini-extension.json`
- **Claude plugin**: `~/.claude/plugins/cache/aops/aops-core/<version>/.mcp.json`
- **Source template**: `aops-core/mcp.json.template`

### 4. Crew Session Transcripts

| Session Type          | Transcript Location                                     |
| --------------------- | ------------------------------------------------------- |
| Claude crew           | `$AOPS_SESSIONS/crew/<crew-name>/claude-sessions/`      |
| Polecat task (Claude) | `$AOPS_SESSIONS/polecats/<task-id>.jsonl`               |
| Gemini crew           | `$GEMINI_CLI_HOME/.gemini/` (temp dir, cleaned on exit) |
| Polecat task (Gemini) | stdout/stderr captured in polecat transcript JSONL      |

### 5. Diagnose MCP Server Startup Failures

```bash
# Step 1: Verify pkb binary exists and is the right version
which pkb
pkb --version

# Step 2: Verify the MCP subcommand works
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test"}},"id":1}' | pkb mcp
# Should return JSON-RPC response. If pkb exits with task list output,
# the "mcp" subcommand arg is missing from the config.

# Step 3: Check ACA_DATA is set and valid
echo "ACA_DATA=$ACA_DATA"
ls "$ACA_DATA" | head -5

# Step 4: Check the extension config has correct args
cat ~/.gemini/extensions/aops-core/gemini-extension.json | python3 -m json.tool
# Verify: "args": ["mcp"] must be present in the pkb server config.
# Without it, Gemini runs bare "pkb" which outputs a task list and exits.
```

### 6. Gemini Sandbox Environment Variables

In sandbox mode (`gemini --sandbox`), env vars are forwarded via special mechanisms:

| Mechanism              | Purpose                                  | Limitation                          |
| ---------------------- | ---------------------------------------- | ----------------------------------- |
| `SANDBOX_FLAGS`        | Extra `-e KEY=VAL` Docker flags          | Shell-quote mangles shell functions |
| `SANDBOX_MOUNTS`       | Extra volume mounts (`from:to:opts`)     | Must be comma-separated             |
| `GEMINI_SANDBOX_IMAGE` | Docker image name (default: `aops-crew`) | Must have pkb on PATH               |

```bash
# Check what env vars are forwarded to sandbox
# (set by polecat/cli.py _make_worker_env)
echo "SANDBOX_FLAGS: $SANDBOX_FLAGS"
echo "SANDBOX_MOUNTS: $SANDBOX_MOUNTS"
echo "GEMINI_SANDBOX_IMAGE: $GEMINI_SANDBOX_IMAGE"
echo "GEMINI_CLI_HOME: $GEMINI_CLI_HOME"
```

### 7. Common Gemini MCP Failure Patterns

| Symptom                                 | Likely Cause                                   | Fix                                                    |
| --------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| PKB server "disconnected"               | Missing `"args": ["mcp"]` in extension config  | Add `"args": ["mcp"]` to gemini-extension.json         |
| `${ACA_DATA}` unresolved                | Env var not forwarded into sandbox             | Check `SANDBOX_FLAGS` includes `-e ACA_DATA=...`       |
| `pkb` not found                         | Binary not in container PATH                   | Rebuild Docker image (`make build-docker`)             |
| Agent load errors (`Invalid tool name`) | Claude-specific tool names in Gemini agent def | Fix build script tool name mapping                     |
| Extension not loaded                    | `GEMINI_CLI_HOME` temp dir missing extensions  | Check `_replicate_gemini_auth()` copied extension dirs |
