# Hook Client Translation — Spec & SSoT

> **State.** The single source of truth for how the Universal Hook Router translates
> between Claude Code, Gemini CLI, and Antigravity CLI (agy), and how the build keeps
> installed assets in sync with what the hooks expect. Per-gate forensic detail →
> [`specs/GATES.md`](../GATES.md). Enforcement currency → [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).

## Problem this solves

Per-client hook knowledge (event names, output-channel rules, field names, tool names,
config shapes) was duplicated across `router.py`, `scripts/build.py`,
`scripts/transforms/*`, and `lib/tool_categories.py` as inline prose with **no single
source of truth and no cross-client conformance test**. Each client's hook API is new,
sparsely documented, and changes upstream. Result: ~20 regressions in three weeks —
wrong wire fields, silent verdict drops, tool calls unrecognised on one surface, gate
advisories delivered to the user instead of the agent.

## Design: two SSoT tables + thin renderers + two test layers

### Table 1 — Client/event channel spec (`aops-core/hooks/client_spec.py`)

Pure-python (no heavy deps so the build can import it). One record per
`(client, internal_event)`:

| field              | meaning                                                                           |
| ------------------ | --------------------------------------------------------------------------------- |
| `wire_event`       | event name on the wire (e.g. internal `UserPromptSubmit` → agy `PreInvocation`)   |
| `config_shape`     | `wrapper` (matcher/hooks[]) · `flat` (bare handler list) · `claude`               |
| `can_block`        | does this event express a deny/block?                                             |
| `agent_channel`    | how `context_injection` reaches the AGENT (field path / injectStep kind / `None`) |
| `user_channel`     | how `system_message` reaches the USER (field / `None`)                            |
| `block`            | wire expression of deny/ask                                                       |
| `timeout_floor_ms` | per-(client,event) cold-start floor (agy PreToolUse = 15000)                      |

Drives BOTH the runtime renderers AND the build's `hooks.json` generation. The
event-name map (both directions) lives here ONCE — replacing the three divergent copies
(`router.GEMINI_EVENT_MAP`, `build.CLAUDE_TO_GEMINI_EVENTS`, `transforms/hooks.py`).

Contested cells are NOT guessed — they are filled from the **live conformance harness**
(below) and pinned in `tests/hooks/fixtures/client_capabilities.json`.

### Table 2 — Tool registry (`lib/tool_registry.py`, extends `lib/tool_categories.py`)

One record per ABSTRACT tool: `canonical`, `category`
(read/write/spawn/destructive/skill), and the per-client concrete name. Drives BOTH the
build's text/frontmatter rewriting (replacing `tool_translation.py` and the agent maps)
AND runtime recognition (`extract_subagent_type`, `SPAWN_TOOLS`, sentinel, enforcer).
Fixes the agy gap: agy's vocabulary (`view_file`, `run_command`, `invoke_subagent`, …)
is currently unknown at runtime, so sentinel/enforcer/spawn matching silently fails on agy.

### Renderers (thin, structural only)

`render_claude` / `render_gemini` / `render_agy` read Table 1 and map
`CanonicalHookOutput(verdict, system_message, context_injection)` → the wire dict. Policy
(which channel, can-block, field names) is DATA; only the structural nesting is code.

### Test layer A — unit matrix (fast, CI, deterministic)

`run_router(client, event, payload)` unified fixture + per-client **interpreter**
`interpret(client, event, output) -> Delivered(agent_sees, user_sees, blocked, accepted)`
mirroring how each real client consumes output (the agy accept-contract is the agy
interpreter). ONE parametrized `(client × event × scenario)` matrix asserts the router
conforms to Table 1 and that the core invariants hold. **No per-client test bodies.**

Core invariants:

- **A. accepted** — output validates against the client's schema / protojson accept-contract.
- **B. injection reaches agent** — `context_injection` present ⇒ `agent_sees` contains it,
  OR Table 1 says no agent channel ⇒ router blocked-to-deliver (if `can_block`) or
  dropped-with-logged-warning. _This is the property that keeps regressing._
- **C. verdict fidelity** — deny ⇒ blocked; allow ⇒ not blocked (agy: allow ≠ `{}`).
- **D. no leak** — `system_message` only on user channels; advisory never on a user-only field.

### Test layer B — live conformance harness (opt-in / scheduled)

`scripts/verify_hook_formats.py` + `tests/hooks/test_live_conformance.py`
(`@live @slow`, skip-if-client-unavailable). Parametrized over
`(client × event × candidate_shape × scenario)`. Per cell: install a probe hook emitting
the candidate shape with a unique sentinel in the agent channel; run the client headless;
ask the model to echo any system/context instruction it received. Records three signals:
**ACCEPTED** (no client error), **AGENT_SAW** (model echoed the sentinel — delivery proven
by MODEL ECHO, never transcript grep), **BLOCKED** (deny actually blocked / stop re-entered).
Output is committed as `client_capabilities.json` — the empirical SSoT. When a client
changes upstream, a signal flips and this test goes red. **This is what ends the guessing.**

## Authoritative channel matrix (live docs + to be confirmed by harness, 2026-06-25)

See `client_spec.py` for the machine-readable form. Key facts:

- **agy has NO hidden agent-only channel** — injected steps are user-visible; only knob is
  `userMessage` (persistent) vs `ephemeralMessage` (transient) + `<details>` collapse.
- **agy PreToolUse** docs = `decision`/`reason`/`permissionOverrides`; verified-live =
  top-level `allowTool`/`denyReason`. Binary descriptor has BOTH. Harness decides; until
  then emit both consistent (belt-and-suspenders) — `{}` is NEVER allow (omitted bool=false).
- **agy Stop** = `{decision:"continue", reason}`; **PostInvocation** =
  `{injectSteps, terminationBehavior:"force_continue"|"terminate"}`. Enables the agy hard
  stop-block (handover) that is a silent no-op today.
- **Claude Stop** (2.1.191) docs = accepts `hookSpecificOutput.additionalContext` without
  blocking. If the harness confirms, the qa/handover/ida force-block-on-first workaround
  retires by flipping ONE table cell.

## Message audience / persistence / template matrix — per client

> **Anti-flip-flop SSoT.** For every hook event × message kind × client: WHICH wire
> channel carries it, whether the USER (human) sees it, whether it is injected into
> MODEL/agent CONTEXT, whether it PERSISTS beyond the current turn, and the TEMPLATE it
> renders from. Every non-in-flux cell is derived from authoritative code
> (`aops-core/hooks/router.py` renderers + docstrings, `aops-core/hooks/client_spec.py`,
> `aops-core/lib/gates/definitions.py`, `aops-core/lib/template_registry.py`). Do not edit
> a cell without re-deriving from those sources.

### The two internal message kinds (`CanonicalHookOutput`)

The gate engine produces exactly two text payloads per fired policy
(`aops-core/lib/gate_model.py` → `CanonicalHookOutput`, `aops-core/hooks/schemas.py:125`):

| canonical field     | gate config key                                                         | template category   | wrapped in markers?                                       | intended audience                             |
| ------------------- | ----------------------------------------------------------------------- | ------------------- | --------------------------------------------------------- | --------------------------------------------- |
| `system_message`    | `message_key` (`.policy_*` / countdown)                                 | `USER_MESSAGE`      | NO                                                        | USER — short reason / banner / deny reason    |
| `context_injection` | `context_key` (`.policy_context` / `.reminder` / `stop.handover_block`) | `CONTEXT_INJECTION` | YES — `<SYSTEM HOOK INSTRUCTION>…</…>` at `engine.py:472` | MODEL/agent — advisory / recovery instruction |

Each renderer (`output_for_claude` / `output_for_gemini` / `output_for_agy`) decides which
WIRE field carries each, per the `client_spec.channel_spec(client, event)` capability cell.
For agy these markers are STRIPPED before delivery (`router.py:1038-1039`); for Claude
`additionalContext` they are KEPT, and on the user-visible Stop `reason` they are stripped
(`router.py:923`, `_strip_hook_markers`).

### ⚠ DISAMBIGUATION — `systemMessage` means THREE different things

The token `systemMessage` collides across three layers; this collision is itself a
documented source of confusion. The reader must NEVER conflate them:

| # | identity                                                                    | layer / type                                                                                                        | where                                                                                                | audience                                                                                                                                                                                   |
| - | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | **Claude top-level `systemMessage`** (wire output field)                    | Claude wire schema (`ClaudeGeneralHookOutput`/`ClaudeStopHookOutput`)                                               | `router.py:860,952,958`; `schemas.py:50,73`                                                          | **USER-only** banner; agent does NOT see it (C✗).                                                                                                                                          |
| 2 | **internal `CanonicalHookOutput.system_message`** = the gate "short_reason" | our canonical model                                                                                                 | `schemas.py:131`; gate `message_key`                                                                 | a payload, NOT a channel — its DESTINATION is per-client: Claude→`systemMessage` (#1, USER), Gemini→`reason`/`systemMessage` (USER), agy→`denyReason`/`reason`/`ephemeralMessage` (MODEL). |
| 3 | **agy injectSteps `systemMessage` member** (member 4 of the step union)     | agy `exa.hooks_pb` injectStep — structured `HookSystemMessage`, nested `{"systemMessage": {"systemMessage": text}}` | NOT emitted by `output_for_agy` today (only `ephemeralMessage` is — `router.py:1072,1075,1081,1083`) | **‹being measured› — see note below**; distinct from agy's top-level `systemMessage`, which agy REJECTS as an unknown protojson field (`router.py:1006`, invariant #1).                    |

So: internal `system_message` (#2) is a _payload that routes to different channels per
client_; Claude's top-level `systemMessage` (#1) is one such USER-only destination; agy's
injectSteps `systemMessage` member (#3) is a SEPARATE, structured, model-side step variant
that the router does not currently emit.

### LEGEND — channel audience + persistence (cite once; cells reference by name)

**The USER-vs-AGENT distinction is the load-bearing column** — read it on every cell:
**U** = USER-visible (the HUMAN sees it in terminal/chat UI). **C** = injected into
MODEL/agent CONTEXT (the MODEL reads it; the human does not). A channel can be U-only,
C-only, or BOTH. **P** = PERSISTS (survives beyond the current turn / stays in conversation
history). `✓` yes · `✗` no · `—` channel not used for that cell · `‹being measured›` =
audience/persistence not yet derivable from code, live measurement in progress.

**Claude Code** (2.1.191; `output_for_claude` + `schemas.py` docstrings):

| channel (wire field)                                    | U | C | P | basis                                                                                                                                                                  |
| ------------------------------------------------------- | - | - | - | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hookSpecificOutput.additionalContext` (Pre/UPS/Post)   | ✗ | ✓ | ✓ | agent-only context, delivered without block; persists as injected context. `schemas.py:22-30`, `router.py:991`                                                         |
| `hookSpecificOutput.permissionDecisionReason` (deny)    | ✓ | ✓ | ✓ | deny reason shown to user AND fed to agent on the blocked tool call. `router.py:976-983`                                                                               |
| `hookSpecificOutput.additionalContext` (Stop, no-block) | ✗ | ✓ | ✓ | Stop warn-deliver: reaches agent next turn WITHOUT blocking; CONFIRMED 2.1.191 mem-4ab6cc0b. `router.py:930-938`, `schemas.py:37-48`                                   |
| `decision="block"` + `reason` (Stop enforcement)        | ✓ | ✓ | ✓ | block-to-halt: Claude renders `reason` to user AS A NOTICE **and** feeds it to the agent (markers stripped for the user view). `router.py:925-929`, `schemas.py:44-48` |
| `systemMessage` / `stopReason`                          | ✓ | ✗ | ✗ | USER-only banner; agent does NOT see it next turn. `schemas.py:50-52`, `router.py:950-952`, `957`                                                                      |

**Gemini CLI** (`output_for_gemini` + `schemas.py:84-119`):

| channel (wire field)                   | U | C | P | basis                                                                                                                                |
| -------------------------------------- | - | - | - | ------------------------------------------------------------------------------------------------------------------------------------ |
| `hookSpecificOutput.additionalContext` | ✗ | ✓ | ✓ | injected into agent prompt (BeforeAgent/AfterTool); agent-only. `router.py:869-879`, `schemas.py:89-91`                              |
| `reason` (decision="deny")             | ✓ | ✗ | ✗ | USER-visible denial explanation; the model never sees it (recovery payload goes to `additionalContext` instead). `router.py:865-873` |
| `systemMessage`                        | ✓ | ✗ | ✗ | USER-only banner. `router.py:859-860`                                                                                                |

**Antigravity (agy)** (`output_for_agy` docstring `router.py:1000-1101`; `client_spec.py:217-228`):

agy `injectSteps` are **MODEL-facing, NOT human-terminal** — there is NO hidden agent-only
channel and NO separate user banner; delivery is observable only by MODEL ECHO, not transcript
(invariant #14, `CLIENT-TRANSLATION.md` invariant list). The two `injectSteps` member variants:

| channel (wire field)                                                                                                         | U                | C                | P                | basis                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `injectSteps[].ephemeralMessage`                                                                                             | ✗                | ✓                | ✗                | rendered into model context ONCE then DISCARDED — transient; does NOT persist as a turn. `router.py:1072,1075,1081,1083`; invariant #5                                                                                                                                                                                                                |
| `injectSteps[].userMessage`                                                                                                  | ✗                | ✓                | ✓                | rendered into model context and PERSISTS as a user turn in history. (defined member; not currently emitted by the renderer) `client_spec.py:90-91`, invariant #5                                                                                                                                                                                      |
| `injectSteps[].systemMessage` (member 4 — structured `HookSystemMessage`, nested `{"systemMessage":{"systemMessage":text}}`) | ‹being measured› | ‹being measured› | ‹being measured› | distinct from agy top-level `systemMessage` (which agy REJECTS, `router.py:1006`). NOT emitted by the renderer today. Audience (USER-facing vs agent-context) + persistence are the open question at `client_spec.py:186` ("Is there a USER-facing message channel for system_message?") — a live measurement is in progress. Do NOT guess; see note. |
| `denyReason` (PreToolUse, `allowTool=false`)                                                                                 | ✗                | ✓                | ✓                | top-level deny reason fed to the model on the blocked call; structural block. `router.py:1054-1057`, `client_spec.py:220`                                                                                                                                                                                                                             |
| `reason` (Stop)                                                                                                              | ✗                | ✓                | ✓                | StopHookResult reason fed to the model. `router.py:1087-1095`                                                                                                                                                                                                                                                                                         |

> agy has no TOP-LEVEL `systemMessage`/user-banner field that the router emits — the
> `output_for_agy` formatter emits ONLY the fields each `*Result` protojson message defines
> and NEVER top-level `metadata`/`systemMessage` (invariant #1; `router.py:1009-1011`,
> `1006`). So agy `system_message` (short_reason) is today delivered through the SAME
> model-facing `injectSteps`/`denyReason`/`reason` channel as advisory — there is no
> user-only split in the EMITTED output.
>
> **agy injectSteps `systemMessage` member (member 4) — BEING MEASURED:** `‹being
> measured›`. This structured `HookSystemMessage` step variant (nested
> `{"systemMessage":{"systemMessage":text}}`) is a _defined_ injectStep member that the
> renderer does NOT currently emit. Whether it is USER-facing (a real human-visible channel,
> which would give agy its first user-only split) or agent-context, and whether it persists,
> is the open question recorded at `client_spec.py:186`. A live measurement is in progress;
> the supervisor will finalize these cells. Do NOT guess — a wrong agy field is silently
> discarded (invariant #1), so an unverified audience claim here would be worse than the
> honest `‹being measured›` marker.

### TABLE — event × message-kind × client

Rows are the events the router handles (`router.py:_call_gate_method`) × the message kinds a
gate can emit on that event (from `definitions.py` policies). Each cell shows the **wire
channel** and its **U/C/P** flags (per the legend) and the **template** (filename in
`aops-core/hooks/templates/`, key in `template_registry.py:TEMPLATE_SPECS`). `n/a` = the
client does not register / support that event-kind.

#### PreToolUse — `sentinel` (block) and `enforcer` (block) gates

| message kind                   | Claude                                 | Gemini                                    | agy                                                                                                                                                                   | template (source)                                                                                                   |
| ------------------------------ | -------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| deny-reason (`system_message`) | `permissionDecisionReason` — U✓ C✓ P✓  | `reason` — U✓ C✗ P✗ (+`systemMessage` U✓) | `denyReason` (`allowTool=false`) — U✗ C✓ P✓                                                                                                                           | `sentinel-policy-message.md` (`sentinel.policy_message`) / `enforcer-policy-message.md` (`enforcer.policy_message`) |
| advisory (`context_injection`) | `additionalContext` — U✗ C✓ P✓         | `additionalContext` — U✗ C✓ P✓            | **n/a** — agy PreToolUse has NO inject channel; renderer RAISES if advisory present (`router.py:1058-1061`, `client_spec.py:220` `agent_context_without_block=False`) | `sentinel-policy-context.md` (`sentinel.policy_context`) / `enforcer-policy-context.md` (`enforcer.policy_context`) |
| allow (no block)               | `permissionDecision="allow"` (no text) | `decision="allow"`                        | `{"allowTool": true}` (explicit; `{}` = deny, invariant #2) — `router.py:1062`                                                                                        | —                                                                                                                   |

#### PostToolUse — `enforcer`/`qa`/`handover` triggers (state only; no policy emits here)

| message kind | Claude                                                         | Gemini              | agy                                                                                | template                                                                                               |
| ------------ | -------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| any text     | `additionalContext` supported but no gate emits on PostToolUse | `additionalContext` | **`{}` only** — renderer RAISES on any field (`router.py:1064-1067`, invariant #4) | — (triggers update gate state via `system_message_key` on transitions, not delivered as policy output) |

#### UserPromptSubmit (agy: PreInvocation) — `pkb.nudge` (T0) + `hydration.warn` (main session) injection

| message kind                    | Claude                         | Gemini                         | agy (PreInvocation)                                                                                                                                                | template (source)                                                                                                                                                  |
| ------------------------------- | ------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| advisory (`context_injection`)  | `additionalContext` — U✗ C✓ P✓ | `additionalContext` — U✗ C✓ P✓ | `injectSteps[].ephemeralMessage`, advisory wrapped in `<details><summary>System Advisory (Agent Context)</summary>` — U✗ C✓ **P‹in-flux›** (`router.py:1069-1076`) | `pkb-nudge.md` (`pkb.nudge`, CONTEXT_INJECTION) + `hydration-gate-warn.md` (`hydration.warn`, USER_MESSAGE — routing hint, main session only; `router.py:561-578`) |
| short-reason (`system_message`) | `systemMessage` — U✓ C✗ P✗     | `systemMessage` — U✓ C✗ P✗     | `injectSteps[].ephemeralMessage` (bare) — U✗ C✓ **P‹in-flux›** (`router.py:1071-1072`)                                                                             | gate `message_key` (none fire on UPS by default; hydration hint via `hydration.warn`)                                                                              |

> **agy PreInvocation advisory persistence — IN FLUX:** `‹PENDING FINAL DECISION — ephemeralMessage(transient, P✗) vs userMessage(persistent, P✓); see live measurement, epic aops-aa512c33›`. **Current emitted code = `ephemeralMessage` (transient)** (`router.py:1072,1075`). Both members are fully defined in the legend above; the active choice is being decided by a live measurement and the supervisor will finalize this cell.

#### Stop (Claude/Gemini) · PostInvocation + native Stop (agy) — `qa`, `handover`, `ida` gates

| message kind                                                   | Claude (Stop)                                                                                           | Gemini (AfterAgent/SessionEnd)                                                                                 | agy (PostInvocation)                                                                                                                      | agy (native Stop, provisional)                                    | template (source)                                                                                                                         |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| advisory / recovery (`context_injection`) — WARN mode          | `hookSpecificOutput.additionalContext`, NO block — U✗ C✓ P✓ (2.1.191 mem-4ab6cc0b; `router.py:930-938`) | `reason` via block (`agent_context_without_block=False`, `client_spec.py:213`) — agent sees on retry; U✓ C✓ P✓ | `injectSteps[].ephemeralMessage` wrapped in `<details>` — U✗ C✓ **P‹in-flux›** (`router.py:1078-1085`)                                    | **n/a** — agy Stop RAISES on advisory (`router.py:1089-1092`)     | `qa-policy-context.md` (`qa.policy_context`) · `stop-gate-handover-block.md` (`stop.handover_block`) · `ida-reminder.md` (`ida.reminder`) |
| advisory / enforcement (`context_injection`) — DENY/block mode | `decision="block"` + `reason` (markers stripped for user) — U✓ C✓ P✓ (`router.py:925-929`)              | `reason` (decision="deny") — U✓ C✗ P✗; recovery → `additionalContext` U✗ C✓ P✓ (`router.py:865-879`)           | `injectSteps[].ephemeralMessage` (terminationBehavior hard-block PROVISIONAL, not emitted — `router.py:1029-1032`) — U✗ C✓ **P‹in-flux›** | `reason` only (`router.py:1087-1095`; advisory RAISES) — U✗ C✓ P✓ | same as above                                                                                                                             |
| short-reason / banner (`system_message`)                       | `stopReason` + `systemMessage` — U✓ C✗ P✗ (`router.py:950-952`)                                         | `systemMessage` (+`reason` on deny) — U✓                                                                       | `injectSteps[].ephemeralMessage` (bare) — U✗ C✓ **P‹in-flux›** (`router.py:1081-1082`)                                                    | `reason` — U✗ C✓ P✓ (`router.py:1095`)                            | `qa-policy-message.md` · `handover-policy-message.md` · `ida-policy-message.md`                                                           |

#### SessionStart / SessionEnd / Notification / SubagentStart / SubagentStop

| event              | Claude                                                                                            | Gemini                                                 | agy                                                                     | notes                                          |
| ------------------ | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------- |
| SessionStart       | `additionalContext` (env setup) — U✗ C✓ P✓; no block (`client_spec.py:199`)                       | `additionalContext` — U✗ C✓ P✓                         | **not registered** (agy `_OUTBOUND` drops it, `client_spec.py:126-135`) | `session_env_setup` (not a gate template)      |
| SessionEnd         | same channels as Stop (`output_for_claude` Stop branch)                                           | fan-out of internal Stop (`client_spec.py:118`)        | n/a                                                                     | —                                              |
| Notification       | `systemMessage` only — U✓ C✗ P✗ (no `hookSpecificOutput`, `router.py:962-970` raises if advisory) | maps to `BeforeAgent` (`client_spec.py:124`)           | not registered                                                          | —                                              |
| SubagentStart/Stop | `systemMessage` only (no HSO events) — U✓ C✗ P✗                                                   | map to BeforeTool/AfterTool (`client_spec.py:121-122`) | not registered                                                          | gates evaluate but tool-event renderer applies |

### Client differences that jump out

1. **agy injectSteps are model-facing, never a user banner** — Claude/Gemini split USER
   (`systemMessage`/`reason`) from AGENT (`additionalContext`); agy has ONE model-facing
   channel and NO user-only split. (`router.py:1009-1011`, invariant #1, #14.)
2. **agy PreToolUse cannot carry advisory at all** — Claude/Gemini ride `additionalContext`
   on an allow; agy PreToolHookResult has only `allowTool`/`denyReason`, so a warn-mode gate
   carrying advisory on PreToolUse is impossible on agy (renderer raises). (`router.py:1041-1062`.)
3. **Stop advisory persistence differs three ways** — Claude delivers WITHOUT a block
   (additionalContext, persists); Gemini must BLOCK to deliver (reason→retry); agy uses
   `ephemeralMessage` (transient ‹in-flux›) and its hard stop-block enum is provisional /
   not emitted. (`client_spec.py:204,213,226`.)
4. **Only Claude renders a blocking Stop `reason` to BOTH user and agent** — Gemini `reason`
   is user-only on deny; agy `reason` is model-only. (`router.py:925-929,865-873,1095`.)
5. **`systemMessage` is three different things** (see disambiguation table) — Claude's
   top-level `systemMessage` is a USER-only banner; our internal `system_message` is a
   payload that routes to USER channels on Claude/Gemini but a MODEL channel on agy; agy's
   injectSteps `systemMessage` member is a separate structured step (audience ‹being
   measured›) that the router does not currently emit. Same name, three audiences.

## Regression-avoidance invariants (24) — encoded as permanent test anchors

The hard-won invariants from three weeks of agy fixes. Full list with WHY in the PR / git
history; the load-bearing ones:

1. agy rejects unknown protojson fields → only documented fields; never `metadata`.
2. agy PreToolUse allow = explicit `{"allowTool":true}`; `{}` = deny.
3. `allowTool`/`denyReason` top-level, never nested in `permissionOverrides` (repeated list).
4. agy PostToolUse / unmapped event = `{}` only.
5. injectSteps `userMessage`/`ephemeralMessage` are SCALAR strings; prefer `ephemeralMessage`.
6. PreInvocation/PostInvocation tolerate `short_reason` — never raise.
7. Claude `hookSpecificOutput` only for {PreToolUse, UserPromptSubmit, PostToolUse, PostToolBatch} (+Stop iff harness-verified).
8. agy `toolCall`/`error` at ROOT of stdin; root-first extraction.
9. agy flat handler list for PreInvocation/PostInvocation/Stop; wrapper only for Pre/PostToolUse.
10. agy PreToolUse timeout floor ≥ 15000ms.
11. substitute `${CLAUDE_PLUGIN_ROOT}` for agy; agy agent bodies use Claude tool names.
12. never `--dangerously-skip-permissions` on agy; `AOPS_AGY_CLIENT` worker posture; Stop never worker-skipped.
13. plugin dir FRONT of sys.path; provider from `--client`; prebake venv (staging + runtime registry).
14. verify agy injection by MODEL ECHO not transcript grep; test SEMANTIC verdict not literal dict.
15. cowork ships NO hooks.

## Phasing (regression-safe)

- **P0** unit-matrix safety net (router vs table, current behavior) + live conformance harness.
- **P1** SSoT tables (`client_spec.py`, `tool_registry.py`); router reads them; output byte-identical.
- **P2** renderers become thin table-driven functions.
- **P3** build imports the SSoT; delete orphaned `transforms/` duplicates; regen dist.
- **P4** corrections (each = one table-cell flip, harness-driven): agy PreToolUse format,
  agy hard stop-block, Claude Stop inject retirement.
- **P5** ENFORCEMENT-MAP row; update `specs/GATES.md` + `aops-core/skills/aops/references/hooks.md`; cleanup; PR.
