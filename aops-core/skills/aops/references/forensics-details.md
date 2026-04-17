---
title: Session Hook Forensics — Detailed Procedures
type: reference
category: ref
permalink: ref-forensics-details
description: How to read hook JSONL logs, diagnose gate failures, trace session events, and correlate artifacts across the polecat system
---

# Session Hook Forensics — Detailed Procedures

This reference provides the specific knowledge needed to diagnose hook and gate behavior from raw session artifacts. For hook architecture and I/O schemas, see [[hooks]]. For general framework debugging, see [[debug-details]].

## Hook JSONL Schema

Hook events are logged to `$AOPS_SESSIONS/hooks/<YYYYMMDD>-<session-short-hash>-hooks.jsonl` by `unified_logger.py`. Each line is a JSON object.

### Key Fields

| Field                | Type        | Description                                                                                                                                          |
| -------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `session_id`         | string      | Full UUID                                                                                                                                            |
| `session_short_hash` | string      | First 8 chars of UUID                                                                                                                                |
| `hook_event`         | string      | `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionEnd`, `PreCompact`, `Notification` |
| `logged_at`          | string      | ISO 8601 timestamp                                                                                                                                   |
| `exit_code`          | int         | 0=allow, 1=warn, 2=block                                                                                                                             |
| `cwd`                | string      | Working directory at time of event                                                                                                                   |
| `tool_name`          | string/null | Tool that triggered this event (PreToolUse/PostToolUse)                                                                                              |
| `subagent_type`      | string/null | Agent type (SubagentStart/SubagentStop)                                                                                                              |
| `output`             | object/null | **The gate verdict and messages** — see below                                                                                                        |

### The `output` Field (CanonicalHookOutput)

This is the most important field for forensics. Written by `unified_logger.py:69` as `output.model_dump()`.

```json
{
  "verdict": "allow" | "deny" | null,
  "system_message": "Text shown to agent or logged (may be null)",
  "context_injection": "Text injected into agent context (may be null)",
  "updated_input": null,
  "metadata": { "source": "...", ... }
}
```

- **`verdict`**: `"allow"` = gate passed, `"deny"` = gate blocked. On PreToolUse, deny means the tool call was rejected.
- **`system_message`**: Human-readable message about gate state. Contains countdown markers (`◇ N`), gate status icons (`💧 ≡`), and blocking reasons.
- **`context_injection`**: Instructions injected into the agent's context. Contains compliance check demands, skill routing tables, etc.

### Known Transcript Gap

**IMPORTANT**: The transcript parser (`transcript_parser.py:1764`) reads `data.get("hookSpecificOutput")` — a field from the Claude Code protocol that does NOT exist in hook JSONL. All `output` fields (verdicts, system_messages, context_injections) are silently dropped from generated transcripts. Until this parser bug is fixed, you **must read raw hook JSONL** for gate forensics. Do not trust transcripts for hook behavior.

## File Locations & Cross-Referencing

### Finding Files for a Session

| Artifact              | Location                              | Pattern                                                   |
| --------------------- | ------------------------------------- | --------------------------------------------------------- |
| Hook JSONL            | `$AOPS_SESSIONS/hooks/`               | `<YYYYMMDD>-<session-short-hash>-hooks.jsonl`             |
| Custodiet audit       | `$AOPS_SESSIONS/hooks/`               | `<YYYYMMDD>-<session-short-hash>-custodiet.md`            |
| Session state         | `$AOPS_SESSION_STATE_DIR/`            | `<YYYYMMDD>-<HH>-<session-short-hash>.json`               |
| Transcript (full)     | `$POLECAT_HOME/sessions/transcripts/` | `<YYYYMMDD>-<HH>-<worktree-name>-<session>-*-full.md`     |
| Transcript (abridged) | `$POLECAT_HOME/sessions/transcripts/` | `<YYYYMMDD>-<HH>-<worktree-name>-<session>-*-abridged.md` |
| CC session JSONL      | `~/.claude/projects/<project-dir>/`   | `<session-uuid>.jsonl`                                    |

### Example Local Paths

- `$AOPS_SESSIONS` = `$HOME/.aops/sessions`
- `$POLECAT_HOME` = `$HOME/.aops`
- `$AOPS_SESSION_STATE_DIR` = `$HOME/.claude/projects/<project-dir>/`

### Correlating Task → Session → Artifacts

1. **Task → Session**: Polecat branches use `polecat/<task-id>` naming. Check `git log --all --oneline | grep <task-id>` to find the worktree.
2. **Session → Hook JSONL**: Read the first line of the hook JSONL for `session_short_hash`, or match by date and session hash in the filename.
3. **Session → Transcript**: Transcripts include the session short hash in the filename. Search: `ls $POLECAT_HOME/sessions/transcripts/ | grep <session-short-hash>`.

## Gate Forensics

### Custodiet / RBG Gate

The compliance gate periodically requires the agent to invoke the rbg (formerly custodiet) subagent.

**Configuration**:

- Threshold: `CUSTODIET_TOOL_CALL_THRESHOLD` env var (default: **50 operations**)
- Countdown starts: 7 operations before threshold (`start_before=7`)
- Counter: tracks `ops_since_open` (incremented on PostToolUse for non-subagent calls)
- Resets: when custodiet/rbg subagent completes (SubagentStop event)

**IMPORTANT**: The gate counts **operations** (tool calls), NOT turns (user prompts). A single turn may produce 5-10 tool calls. "11 turns" ≈ 50 operations.

**Diagnostic commands**:

```bash
# Count total operations in a session
grep -c '"hook_event":"PostToolUse"' <hooks.jsonl>

# Check if custodiet was dispatched (and how many times)
grep -E '"hook_event":"SubagentSt' <hooks.jsonl> | \
  python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line.strip())
    st = d.get('subagent_type', '')
    if 'custodiet' in st or 'rbg' in st:
        evt = d.get('hook_event')
        v = d.get('output', {}).get('verdict')
        print(f'{evt}: type={st}, verdict={v}')
"

# Check if custodiet blocked (verdict=deny on PreToolUse after threshold)
grep '"hook_event":"PreToolUse"' <hooks.jsonl> | \
  python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line.strip())
    out = d.get('output', {})
    if out.get('verdict') == 'deny':
        tool = d.get('tool_name', '?')
        msg = str(out.get('system_message', ''))[:100]
        print(f'BLOCKED: {tool} — {msg}')
"
```

**What to look for**:

- `SubagentStart` with `subagent_type` containing `custodiet` or `rbg` = gate check started
- `SubagentStop` with same type + `verdict=allow` = gate cleared, counter reset
- PreToolUse with `verdict=deny` and system_message mentioning "Compliance check" = gate blocking tools
- Multiple SubagentStart/Stop pairs = gate firing repeatedly (normal in long sessions)

### Stop / Handover Gate

The Stop hook enforces session completion requirements (commit, handover, etc.).

**Configuration**:

- Handover gate: starts CLOSED when task bound, opens when `/dump` skill completes
- Safety override: after **4 consecutive denies within 2 minutes**, auto-approves to prevent deadlock

**Diagnostic commands**:

```bash
# Find all Stop events and their verdicts
grep '"hook_event":"Stop"' <hooks.jsonl> | \
  python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line.strip())
    out = d.get('output', {})
    v = out.get('verdict', '?')
    msg = str(out.get('system_message', ''))[:100]
    ts = d.get('logged_at', '?')
    print(f'{ts} verdict={v} msg={msg}')
"
```

**What to look for**:

- `verdict=deny` with `system_message` containing "Uncommitted changes" = handover gate blocking
- 4 consecutive denies followed by `verdict=allow` = safety override fired (common pattern)
- `verdict=allow` with no denies = session ended cleanly

**The 4-deny pattern**: Many sessions show exactly 4 Stop denies before auto-approval. This is the safety override, not agent compliance. It means the agent either ignored or could not comply with the stop advice. Investigate the CC session JSONL to understand what the agent did between denies.

## Identifying Polecat Sessions

### By Working Directory

Polecat worktree sessions have `cwd` containing `.claude/worktrees/`:

```bash
for f in $AOPS_SESSIONS/hooks/*.jsonl; do
    head -1 "$f" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    cwd = d.get('cwd', '')
    if 'worktree' in cwd:
        print(f'{d.get(\"session_short_hash\")} | {d.get(\"logged_at\",\"?\")[:10]} | {cwd}')
except: pass
" 2>/dev/null
done
```

### Claude vs Gemini

- **Claude sessions**: Standard UUID session IDs (e.g., `fafa268a-7570-4284-...`)
- **Gemini sessions**: Prefixed with `gemini-` (e.g., `gemini-20260405-abc12345`)
- **Known gap**: The `model` and `client` fields in hook JSONL are currently `unknown` for all polecat sessions. The only reliable identifier is the session ID format.

## Common Patterns

### Pattern: Custodiet firing repeatedly in long sessions

**Sessions**: `fafa268a` (193 ops, 10+ dispatches), `c7909ba1` (211 ops), `ac37cbc3` (268 ops)
**Meaning**: Normal. Long sessions accumulate many operations. The gate fires every ~50 ops, custodiet evaluates, returns OK, counter resets, work continues.

### Pattern: 4 Stop denies then auto-approve

**Sessions**: `00d1f873`, `08a89782`, `0adf0325`, and many others
**Meaning**: Agent tried to stop but had uncommitted changes. Ignored 3 denies. Safety override on 4th. Investigate whether the agent attempted to commit between denies or just retried Stop.

### Pattern: Zero Gemini hook JSONL

**As of 2026-04-09**: No Gemini-prefixed sessions exist in hook JSONL. Either Gemini polecats haven't been run with the current hook system, or the integration is broken. This is an open question.

### Pattern: Operations vs turns confusion

The gate threshold is 50 operations (tool calls), not 50 turns. A single user prompt can trigger 5-10+ tool calls. When someone says "the gate fired at 11 turns," it means ~50 operations happened across 11 prompts.
