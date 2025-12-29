---
name: q
description: Quick capture - transforms idea fragment into executable prompt
allowed-tools: Task
permalink: commands/q
---

# Quick Capture to Prompt Queue

**Zero-friction idea capture. Type your fragment, press enter, alt-tab away.**

## Usage

```
/q merge those enforcement files
/q fix the dashboard session identity thing
/q we need to add validation to the prompt writer
```

## What Happens

1. You type your fragment (can be messy, shorthand, incomplete)
2. Prompt writer agent runs **async** (you don't wait)
3. Agent investigates context, formalizes into executable prompt
4. Prompt stored in `$ACA_DATA/queue/`
5. Later: `/pull` retrieves and executes

## Execution

Spawn the prompt-writer agent in the background:

```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  run_in_background=true,
  description="Queue: [first 3 words]",
  prompt="
You are the prompt-writer agent. Read your instructions at $AOPS/agents/prompt-writer.md

User fragment to process:
> [USER'S FRAGMENT HERE]

Session context: [CURRENT PROJECT IF KNOWN]

Write the executable prompt to $ACA_DATA/queue/ following the format in your instructions.
"
)
```

## Key Points

- **Async**: User doesn't wait. Agent works in background.
- **Self-contained output**: The prompt file must be executable by a fresh Claude instance.
- **Preserves fragment**: Original words kept verbatim in output.

## Output Location

`$ACA_DATA/queue/YYYYMMDD-HHMMSS-slug.md`

