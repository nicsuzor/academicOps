---
name: debug-headless
category: instruction
description: Run claude-code and gemini-cli in headless mode, capturing all output and debug logs for framework debugging.
allowed-tools: Bash, Read, Write, Glob
version: 0.1.0
status: stub
permalink: skills-debug-headless
review: this should be a spec, not a skill. skills come after. -- NS.
---

# /debug-headless - Headless AI CLI Debugging

Run Claude Code and Gemini CLI in headless/non-interactive mode with full output and debug log capture.

## Purpose

Framework self-reflexivity requires debugging agent behavior. This skill provides infrastructure to:

1. Execute claude-code or gemini-cli non-interactively
2. Capture stdout, stderr, and debug logs
3. Store artifacts for analysis

## Status: STUB

This is a Phase 1 stub spec. Implementation pending validation of:

- [ ] Claude Code headless execution flags (`--print`, `-p`, `--output-format`)
- [ ] Gemini CLI headless execution (`--non-interactive`, debug verbosity)
- [ ] Debug log locations and capture mechanisms
- [ ] Output artifact storage conventions

## Usage (Planned)

```
/debug-headless claude "your prompt here"    # Run claude-code headless
/debug-headless gemini "your prompt here"    # Run gemini-cli headless
/debug-headless --compare "prompt"           # Run both and compare outputs
```

## Infrastructure Requirements

### Claude Code

```bash
# Headless execution (to be validated)
claude --print "prompt" 2>&1 | tee output.log

# With debug logging
CLAUDE_DEBUG=1 claude --print "prompt" 2>&1 | tee output.log
```

### Gemini CLI

```bash
# Headless execution (to be validated)
gemini --non-interactive "prompt" 2>&1 | tee output.log

# With verbose/debug output
gemini --verbose --non-interactive "prompt" 2>&1 | tee output.log
```

## Output Artifacts

Captured to `$ACA_DATA/debug/headless/YYYYMMDD-HHMMSS-{tool}/`:

- `stdout.log` - Standard output
- `stderr.log` - Standard error
- `debug.log` - Debug/verbose output (if available)
- `metadata.json` - Execution context (prompt, flags, timing, exit code)

## Next Steps

1. Research exact CLI flags for both tools
2. Test headless execution in isolated environment
3. Define output parsing for structured analysis
4. Integrate with session-insights for pattern detection

## Related

- [[session-insights]] - Analyzes session transcripts
- [[transcript]] - Generates markdown from session logs
- [[learning-log]] - Routes observations to GitHub Issues
