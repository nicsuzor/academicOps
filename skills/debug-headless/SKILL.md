---
name: debug-headless
category: instruction
description: Debug Claude Code or Gemini CLI in headless mode with full output capture.
allowed-tools: Bash, Read, Write, Glob
version: 0.3.0
permalink: skills-debug-headless
---

# /debug-headless - Headless AI CLI Debugging

Run Claude Code or Gemini CLI non-interactively with output and debug log capture.

**Reference**: See [[headless-execution]] spec for CLI flags and environment variables.

## Workflow

1. **Use the wrapper** for session isolation:
   ```bash
   scripts/claude-headless.sh -p "prompt" --allowedTools "Bash,Read" ...
   ```

2. **Enable debug mode** to capture reasoning:
   ```bash
   scripts/claude-headless.sh -p "prompt" -d --output-format json 2>&1 | tee output.log
   ```

3. **Find debug logs** at `~/.claude/debug/{session-uuid}.txt`

## Quick Reference

| Tool        | Headless Flag | Debug Flag | Auto-approve                     |
| ----------- | ------------- | ---------- | -------------------------------- |
| Claude Code | `-p`          | `-d`       | `--dangerously-skip-permissions` |
| Gemini CLI  | (positional)  | `-d`       | `-y` / `--yolo`                  |

## Related

- [[session-insights]] - Analyzes session transcripts
- [[transcript]] - Generates markdown from session logs
