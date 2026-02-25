---
name: scripts
title: Scripts Index
type: index
category: framework
description: |
    Quick reference for utility scripts in scripts/ directory.
    These are NOT user-invocable skills - they're developer tools
    that may be relevant when user requests involve their functionality.
    Hydrator uses this to surface relevant scripts without memory search.
permalink: scripts
tags: [framework, scripts, index, utilities]
---

# Scripts Index

Utility scripts for framework development and maintenance. These are NOT user-invocable skills - invoke via `uv run python scripts/<name>.py` when relevant.

## Utility Scripts

| Script                      | Purpose                                                   | Invocation                                                                           |
| --------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `session_transcript.py`     | Save/export session transcript to markdown                | `uv run python $AOPS/scripts/session_transcript.py <session.jsonl> -o output.md`     |
| `scan_session_summaries.py` | Scan session summaries for daily note/overwhelm dashboard | `uv run python $AOPS/scripts/scan_session_summaries.py [--days N] [--format FORMAT]` |
| `task_graph.py`             | Generate styled DOT/SVG graph from task JSON              | `uv run python $AOPS/scripts/task_graph.py INPUT.json [-o OUTPUT]`                   |
| `audit_framework_health.py` | Collect framework health metrics (orphans, broken links)  | `uv run python $AOPS/scripts/audit_framework_health.py`                              |
| `generate_context_index.py` | Scan docs and generate project-context.md                 | `uv run python $AOPS/scripts/generate_context_index.py`                              |
| `refinery.py`               | Run polecat refinery scan and merge                       | `uv run python $AOPS/scripts/refinery.py`                                            |
| `bump_version.py`           | Bump package version                                      | `uv run python $AOPS/scripts/bump_version.py`                                        |
| `build.py`                  | Build/package the framework                               | `uv run python $AOPS/scripts/build.py`                                               |
| `install.py`                | Install framework dependencies                            | `uv run python $AOPS/scripts/install.py`                                             |

## Development/Maintenance Scripts

| Script                        | Purpose                                   | Invocation                                                |
| ----------------------------- | ----------------------------------------- | --------------------------------------------------------- |
| `check_orphan_files.py`       | Find files not referenced anywhere        | `uv run python $AOPS/scripts/check_orphan_files.py`       |
| `check_skill_line_count.py`   | Check SKILL.md files for excessive length | `uv run python $AOPS/scripts/check_skill_line_count.py`   |
| `check_no_fallbacks.py`       | Verify no fallback patterns in codebase   | `uv run python $AOPS/scripts/check_no_fallbacks.py`       |
| `fix_agent_definitions.py`    | Fix agent definition formatting           | `uv run python $AOPS/scripts/fix_agent_definitions.py`    |
| `convert_commands_to_toml.py` | Convert command definitions to TOML       | `uv run python $AOPS/scripts/convert_commands_to_toml.py` |
| `convert_mcp_to_gemini.py`    | Convert MCP format to Gemini format       | `uv run python $AOPS/scripts/convert_mcp_to_gemini.py`    |
| `automated_test_harness.py`   | Run automated test harness                | `uv run python $AOPS/scripts/automated_test_harness.py`   |

## External Tools

| Script               | Purpose                     | Invocation                                       |
| -------------------- | --------------------------- | ------------------------------------------------ |
| `dropbox_monitor.py` | Monitor Dropbox for changes | `uv run python $AOPS/scripts/dropbox_monitor.py` |

## When to Surface Scripts

- **Token/session analysis**: Surface `session_transcript.py`, `scan_session_summaries.py`
- **Task visualization**: Surface `task_graph.py`
- **Framework health**: Surface `audit_framework_health.py`, `check_orphan_files.py`
- **Build/release**: Surface `build.py`, `bump_version.py`, `install.py`
