---
name: headless-execution
title: Headless AI CLI Execution
type: spec
category: spec
description: Reference documentation for running Claude Code and Gemini CLI in non-interactive mode
permalink: headless-execution
tags: [infrastructure, cli, automation]
---

# Headless AI CLI Execution

Reference for running Claude Code and Gemini CLI non-interactively (cron jobs, scripts, automation).

## Session Log Isolation

**Problem**: Headless runs from the project directory pollute interactive session logs in `~/.claude/projects/`.

**Solution**: Use the wrapper script to run from a temp directory:

```bash
scripts/claude-headless.sh -p "prompt" --allowedTools "Bash,Read" ...
```

The wrapper:

1. Creates `/tmp/claude-headless-{pid}-{timestamp}/`
2. Adds `--add-dir` for original cwd and `$AOPS`
3. Runs claude from temp directory
4. Cleans up on exit

**Environment variables:**

- `CLAUDE_HEADLESS_ADD_DIRS` - Additional directories (colon-separated)
- `CLAUDE_HEADLESS_KEEP_TMP=1` - Preserve temp dir for debugging

## Claude Code Flags

| Flag                             | Purpose                                                               |
| -------------------------------- | --------------------------------------------------------------------- |
| `-p, --print`                    | Non-interactive mode - print response and exit                        |
| `-d, --debug [filter]`           | Debug with category filtering (e.g., `api,hooks` or `!statsig,!file`) |
| `--output-format <format>`       | Output: `text` (default), `json`, `stream-json`                       |
| `--verbose`                      | Override verbose mode                                                 |
| `--model <model>`                | Specify model (`sonnet`, `opus`)                                      |
| `--permission-mode <mode>`       | `default`, `acceptEdits`, `bypassPermissions`, `plan`                 |
| `--dangerously-skip-permissions` | Skip all permission prompts (unattended)                              |
| `--allowedTools <list>`          | Comma-separated tool whitelist                                        |
| `--add-dir <path>`               | Grant access to additional directory                                  |

**Debug log location**: `~/.claude/debug/{session-uuid}.txt`

**Environment variables**:

- `CLAUDE_CODE_ENABLE_TELEMETRY=1`
- `CLAUDECODE=1` (indicates running in Claude Code)

## Gemini CLI Flags

| Flag                           | Purpose                               |
| ------------------------------ | ------------------------------------- |
| `<query>` (positional)         | Non-interactive prompt                |
| `-d, --debug`                  | Enable debug mode                     |
| `-y, --yolo`                   | Auto-approve all tool actions         |
| `--approval-mode <mode>`       | `default`, `auto_edit`, `yolo`        |
| `-o, --output-format <format>` | Output: `text`, `json`, `stream-json` |
| `-m, --model <model>`          | Specify model                         |

**Session history**: `~/.gemini/history/` (per-project subdirs)

## Output Capture Patterns

### Minimal (stdout/stderr only)

```bash
scripts/claude-headless.sh -p "prompt" --output-format json 2>&1 | tee output.log
```

### With debug logs

```bash
scripts/claude-headless.sh -p "prompt" -d --output-format json 2>&1 | tee output.log
# Debug logs written to ~/.claude/debug/{session-uuid}.txt
```

### Streaming JSON

```bash
scripts/claude-headless.sh -p "prompt" --output-format stream-json 2>&1 | tee stream.jsonl
```

## Artifact Structure

For debugging runs that need artifact capture:

```
/tmp/debug-headless/
└── YYYYMMDD-HHMMSS-{tool}/
    ├── metadata.json      # prompt, flags, timing, exit code
    ├── output.log         # combined stdout/stderr
    ├── output.json        # structured response
    └── debug.log          # tool-specific debug output
```
