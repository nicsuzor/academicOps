---
title: Debug-Headless Skill Research
type: ref
category: ref
tags: [debug-headless, cli, reference]
created: 2026-01-08
---

# Debug-Headless Skill Research (v0.2.0)

Research completed for the `debug-headless` skill implementation. This documents validated CLI behavior and implementation options for capturing Claude Code and Gemini CLI output in headless/automated contexts.

## Validated CLI Flags

### Claude Code

- `-p` / `--print`: Headless mode, prints output to stdout
- `-d`: Debug mode, logs to `~/.claude/debug/`
- `--output-format json|stream-json`: Structured output formats

### Gemini CLI

- Positional `prompt`: Required argument for query text
- `-d`: Debug mode
- `-y` / `--yolo`: Auto-approve mode (skip confirmations)
- `-o`: Output format specification

## Implementation Options

Four implementation pathways documented for the skill:

**Option A: Minimal Stdout Capture**

- Captures basic stdout/stderr
- Simplest implementation
- Limited metadata preservation

**Option B: Debug Mode with Log Copy**

- Leverages native `-d` flag
- Copies logs from `~/.claude/debug/`
- Preserves debug information

**Option C: Structured JSON Streaming**

- Uses `--output-format json` / `stream-json`
- Machine-readable output
- Real-time streaming capability

**Option D: Full Capture with Metadata Wrapper (Recommended)**

- Combines all mechanisms
- Preserves tool invocations and outputs
- Includes timing and context
- Best option for comprehensive debugging

## Open Questions

- **Storage location**: Where should captured logs be persisted? (`$ACA_DATA/debug/`? Session directory?)
- **Retention policy**: How long should debug logs be retained?
- **Compare mode priority**: Should skill support diff/comparison of successive runs?
- **Integration scope**: Which other skills should this integrate with? (logging, testing, QA?)

## Related Contexts

[[debug-headless]] skill (under development)
[[plugin-dev:skill-development]] - Framework skill creation guidelines
[[framework]] - academicOps framework architecture

_Captured 2026-01-08 during debug-headless skill research phase._
