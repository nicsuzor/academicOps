---
title: Session Insights Generation Prompt
type: prompt-template
status: draft
tier: observability
tags: [prompt-template, observability, session-insights]
---

# Session Insights Generation Prompt

**Unbuilt.** Nothing invokes this template. No `session-insights` skill or
command exists in this repository, and the `transcript_parser.py` that earlier
drafts credited with pre-computing `user_prompt_count` and `timeline_events`
does not exist either. The design is a Claude subagent launched with this
template plus a session transcript, emitting the JSON directly — no Python glue.
The consuming design is [sleep-cycle.md](sleep-cycle.md), whose first phase
backfills one insight object per session; the pipeline metrics contract is
[session-insights-metrics-schema.md](session-insights-metrics-schema.md).

Two references in this contract do not resolve, and both must be settled before
it ships:

- `learning_observations[].heuristic` keys on heuristic identifiers (`H2`, `H3`,
  `H4`, `H22`). No register defining them exists in this repository, so the
  field is undecidable as written.
- The prompt collects both `## Framework Reflection` and `### Session Handover`
  blocks into one array, but the two carry different fields and only the first
  has a stated mapping.

`current_bead_id` names an issue in a task system this repository no longer
uses; it survives because the schema is a contract with stored data, not because
anything writes it.

The prompt below is agent-facing instruction text. Session metadata sits at the
tail so the static body stays cacheable across every session it runs on.

## The prompt

Extract structured insights from the session transcript provided with this
message. Output one JSON object and nothing else — no prose, no code fences.

## Output

Emit exactly these keys, in this shape:

```json
{
  "session_id": "string",
  "date": "string",
  "project": "string",
  "summary": "one sentence on what was worked on",
  "outcome": "success | partial | failure",
  "accomplishments": ["concrete deliverable"],
  "friction_points": ["what was harder than expected"],
  "proposed_changes": ["framework improvement identified"],
  "current_bead_id": "issue id active at session end, or null",
  "worker_name": "agent or human who did the work, or null",
  "workflows_used": ["workflow name"],
  "subagents_invoked": ["subagent name"],
  "subagent_count": 0,
  "enforcer_blocks": 0,
  "stop_reason": "how the session ended",
  "critic_verdict": "PROCEED | REVISE | HALT | null",
  "acceptance_criteria_count": 0,
  "user_prompt_count": 0,
  "learning_observations": [
    {
      "category": "Process Adherence | Verification | Context Gap | Axiom Violation | Skill Usage | Error Handling | ...",
      "evidence": "what was observed, quoted from the transcript where possible",
      "context": "where in the session it occurred",
      "heuristic": "heuristic id, or null",
      "suggested_evidence": "what should have happened instead"
    }
  ],
  "skill_compliance": {
    "suggested": ["skill name"],
    "invoked": ["skill name"],
    "compliance_rate": 0.0
  },
  "context_gaps": ["knowledge needed but not surfaced in time"],
  "user_mood": 0.0,
  "conversation_flow": [["ISO 8601 timestamp", "user | agent", "content"]],
  "user_prompts": [["ISO 8601 timestamp", "user | agent", "content"]],
  "workflow_improvements": ["actionable change that would ease a similar task"],
  "jit_context_needed": ["context missing at session start but needed later"],
  "context_distractions": ["context supplied that added noise without value"],
  "framework_reflections": [
    {
      "prompts": "the user request that triggered the session",
      "guidance_received": "hydrator or system guidance, or null",
      "followed": true,
      "outcome": "success | partial | failure",
      "accomplishments": ["item"],
      "friction_points": ["item"],
      "root_cause": "failure category, or null",
      "proposed_changes": ["item"],
      "next_step": "follow-up action, or null"
    }
  ],
  "timeline_events": [
    {
      "timestamp": "ISO 8601",
      "type": "user_prompt",
      "description": "full prompt text"
    },
    {
      "timestamp": "ISO 8601",
      "type": "task_create",
      "task_id": "",
      "task_title": "",
      "project": ""
    },
    { "timestamp": "ISO 8601", "type": "task_complete", "task_id": "" },
    {
      "timestamp": "ISO 8601",
      "type": "task_update",
      "task_id": "",
      "new_status": ""
    },
    {
      "timestamp": "ISO 8601",
      "type": "task_release",
      "task_id": "",
      "status": "done | merge_ready | review | partial | cancelled",
      "summary": ""
    }
  ],
  "token_metrics": {
    "totals": {
      "input_tokens": 0,
      "output_tokens": 0,
      "cache_read_tokens": 0,
      "cache_create_tokens": 0
    },
    "by_model": { "<model id>": { "input": 0, "output": 0 } },
    "by_agent": { "main": { "input": 0, "output": 0 } },
    "efficiency": {
      "cache_hit_rate": 0.0,
      "tokens_per_minute": 0,
      "session_duration_minutes": 0
    }
  }
}
```

`session_id`, `date`, `project`, `summary`, `outcome`, and `accomplishments` are
always present. Every other key is present too: use `[]` for an unknown array,
`null` for an unknown object, string, or number. Timestamps are ISO 8601 with a
timezone.

## Judgment calls the shape does not carry

**`outcome`** — `success` when every goal was met with nothing blocking;
`partial` when some were met, or met with unresolved issues; `failure` when
blockers prevented completion. A user who had to correct the work rates
`partial` at best. Explicit "done" or "working" from the user rates `success`.

**`user_mood`** — user satisfaction inferred from tone, `-1.0` to `1.0`.
`1.0` effusive praise; `0.5` satisfied, task closed without friction; `0.0`
neutral, task-focused exchanges only — this is the default; `-0.5` corrections
and mild frustration; `-1.0` explicit anger or repeated failure. Read
corrections, repeat requests, and sarcasm as negative; thanks, praise, and
collaborative tone as positive.

**`skill_compliance`** — `suggested` is every skill the session was told to use,
`invoked` is every skill actually run, and `compliance_rate` is
`len(invoked) / len(suggested)`, or `1.0` when nothing was suggested. The
transcript markers:

| Field       | Marker                                        |
| ----------- | --------------------------------------------- |
| `suggested` | a hydrator line of the form `**Skill(s)**: X` |
| `suggested` | a router suggestion in a system message       |
| `suggested` | an explicit user request, `/skillname`        |
| `invoked`   | 🔧 Skill invoked: followed by the skill name  |
| `invoked`   | Launching skill: followed by the skill name   |
| `invoked`   | a Skill tool call                             |

**`conversation_flow`** — quote user prompts verbatim; summarise agent turns in
one or two sentences.

**`user_prompts`** — for each user prompt, the agent message immediately
preceding it, then the prompt itself verbatim. The preceding turn is what makes
the prompt interpretable later.

**`framework_reflections`** — collect every `## Framework Reflection` and
`### Session Handover` block in the transcript, in both main-agent and subagent
entries; a session may hold several. From a Framework Reflection, map its
labelled fields onto the object keys of the same name, reading `Followed: Yes`
as `true`. From a Session Handover, map the fields that correspond and leave the
rest `null`. A reflection reading `Answered user's question: "<summary>"` emits
`{"prompts": "<summary>", "outcome": "success", "quick_exit": true}`.

## Session

Use these values verbatim:

- session_id: {session_id}
- date: {date}
- project: {project}
