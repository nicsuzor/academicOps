---
trigger: always_on
description: Direct all session, prompt, and execution trace inspection exclusively to Arize Phoenix; prohibit reading local JSONL transcript or debug files, and mandate Turn-1 REVISE returns on missing inputs.
---

## Session traces through Phoenix, never local JSONL logs

Direct all session, prompt, and execution trace lookups exclusively to Arize Phoenix via `ida:session-trace`. Agents are strictly prohibited from reading or scraping raw local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files.

- **Trace inspection belongs in Phoenix**: Never open, grep, or read local transcript files (`transcript.jsonl`, `transcript_full.jsonl`) or debug hook log files (`aops_debug_hooks_*.jsonl`). Query OpenTelemetry spans and session transcripts through `ida:session-trace`.
- **Subagent brief verification on Turn 1**: When a subagent receives a brief with missing inputs, task parameters, or target artifacts, it must verify on Turn 1 and immediately return `REVISE` via `send_message` to the caller rather than scraping local transcripts or debug files. Do not invoke `verdict.py` on direction briefs.
- **Fail fast on missing traces**: If Phoenix spans are absent or unavailable, halt immediately and report that traces are unavailable. Never introduce silent fallback branches to local disk logs.
