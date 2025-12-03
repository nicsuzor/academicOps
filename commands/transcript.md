---
name: transcript
description: Generate markdown transcript of a Claude Code session (user)
permalink: commands/transcript
---

**IMMEDIATELY** invoke the `transcript` skill to generate session transcripts.

The skill wraps `scripts/claude_transcript.py` and provides:
- Standard output naming: `YYYYMMDD-<project>-<slug>-{full,abridged}.md`
- Output location: `$ACA_DATA/sessions/claude/`
- Two versions: full (with tool results) and abridged (compact)

See skills/transcript/SKILL.md for complete workflow specification.
