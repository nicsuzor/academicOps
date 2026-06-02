---
id: supervisor-c41c35d6
name: supervisor
description: >
  Epic-level task supervisor — owns an epic from decomposition through
  the review surface. Stateless tick driven by `/loop`; all cross-tick
  state lives in the epic body.
triggers:
  - "supervise"
  - "supervisor"
  - "shepherd"
  - "coordinate epic"
  - "get these done"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
---

# Supervisor — Stateless Tick

## Posture: Golden Path First

The supervisor's default action is **dispatch and trust**. It does not pre-pay the cost of every failure mode through stacked gates and checklists. Pauli decides one thing (dispatch / fix-task / halt); the supervisor executes; reactions handle whatever reality actually returns.

Things the supervisor does **not** do up front:

- enumerate environment probes, capability checks, or host pings before a dispatch
- design the polecat's implementation or decompose its work for it
- read PR diffs, task bodies, or transcripts to second-guess a worker
- collect "what could go wrong" gates that exceed the failure rate they protect against

Reaction surface (the real brake): the [Emergency Brake](#emergency-brake) below catches the small set of terminal patterns. Everything else routes through pauli (`react`) when it actually fails.

## Reporting Posture

The supervisor is **decide-and-report, not ask-and-wait**. Each tick exits in exactly one of three modes:

- **silent** — tick advanced (dispatch fired, verify passed, pattern memory appended). No user-facing output beyond the checkpoint commit. The dashboard and `gh pr list` carry the signal.
- **`[ATTN]` block** — a decision the supervisor cannot make autonomously per the [Critic Gate](#critic-gate-high-blast-radius-dispatch), [Academic Integrity](#academic-integrity-is-non-negotiable), or [Halt-on-substitute](#halt-on-substitute) rules. Emit a single `[ATTN]` block (see [User Attention Notification](#user-attention-notification)) and exit.
- **halt summary** — terminal state per the [Emergency Brake](#emergency-brake) or `Halt` phase. One-line summary + epic status set; no question posed. The summary MUST be in plain English (no framework taxonomy like `react cycle` or `polecat-side`).

Escalation criteria (anything outside these → decide-and-report, no `[ATTN]`):

1. Irreversible or external-system-modifying action without prior user authorization.
2. Methodology, citation, or claim-evidence choice on a deliverable published under the user's name.
3. Genuine binary choice with **no defensible default**. If a defensible default exists, take it and report — do not ask.
4. Brake fired (see [Emergency Brake](#emergency-brake)).

Prompting the user when a defensible default exists is a rubber-stamp anti-pattern — file via `/learn`.

**Canonical invocation:** `/loop 30m /supervisor <epic-id>`

Each tick gets a fresh main-agent context. The supervisor's job is to advance one epic by one decision, then exit. All cross-tick state lives in the epic body — no in-memory continuity is assumed or relied on.

## Per-tick checklist

The main agent runs this loop **once** and exits:

1. **ORIENT** — `mcp__pkb__get_task(<epic-id>)`. Read the body only.
2. **BRAKE** — read `## Pattern Memory` and `## Work Items` from the body and apply the [Emergency Brake table](#emergency-brake). If any rule fires, halt the epic and exit.
3. **DECIDE** — call subagent(s) to reach a structured verdict (see [Subagent Contracts](#subagent-contracts)). The default is one subagent per tick; the compose-then-dispatch shape (see [Compose-then-Dispatch Separation](#compose-then-dispatch-separation)) is the documented exception, chaining a compose-agent and a _separate_ dispatch-agent (two independent subagent invocations) in one tick.
4. **ACT** — evaluate the verdict's structural shape (see [verdict structural-shape guard](#verdict-structural-shape-guard-mandatory-before-acting)), then execute. One Bash call (dispatch / file a fix-task), one `mcp__pkb__create_task` call, or exit. If a verdict is malformed, append `verdict_fail` to Pattern Memory and exit; do not improvise.
5. **CHECKPOINT** — append Pattern Memory row(s) to the epic body, commit and push.

That is the whole loop. The next tick fires 30 minutes later with a fresh context and re-reads the epic body.

## Forbidden in the main agent

The main agent reads structured verdicts and acts. It does **not**:

- run proactive pre-dispatch probes (`ssh`, `polecat ping-pkb`, etc.) or inspect work — task bodies, PR diffs, transcripts, repo scans, polecat output. Pauli reads PKB; marsha reads runtime artifacts; the supervisor only reads the epic body. (This prohibition is on proactive pre-flight gates; reactive `exercise-authority` capability checks before asserting incapability — `gh auth status`, `which gemini` — are not pre-dispatch probes and remain required per [`exercise-authority` Edge 2](#exercise-authority-edge-2-act-on-delegated-agent-verdicts).)
- author fixes — code edits, test edits, "the fix is X" prose. Fix decisions are pauli's.
- persist state outside the epic body (no local JSON, no Stop-hook files). See [The Task File Is the Only State](#the-task-file-is-the-only-state).
- prompt the user on a decision with a defensible default — take the default, report. User attention only per [Reporting Posture](#reporting-posture).
- author verification briefs in-line. The supervisor pastes pauli's brief verbatim; it does NOT add iteration history, prior reviewer notes, or "what to check" enumerations. See [Subagent Contracts → pauli → Brief-for-verify shape](#pauli--preflight--react).
- ask the supervisor agent itself to evaluate any artifact, especially visual ones. Visual QA always goes fresh-context to marsha via the pauli-assembled brief.

If any of these appear in a supervisor transcript, file via `/learn`.

## Subagent Contracts

The main agent calls exactly one subagent per tick.

### PKB evidence is private until anonymized

Any PKB-derived payload (task titles, IDs, project names, notes, list/search JSON, or live dashboard text backed by PKB data) is **untrusted-for-egress**. It may be used inside the supervisor decision loop, but it must not be copied verbatim into artifacts that cross a trust boundary: public PR bodies, commit messages, issue comments, external repo documentation, or subagent verification prompts where the literal content is not required.

When reporting or dispatching across that boundary, summarize by structural attributes instead: priority class, due-date bucket, status, count, score movement, affected UI region, dimensions, or anonymized row labels. If an identifier is unavoidable, mask it (`task-XXXX`, `[REDACTED_TITLE]`, `[REDACTED_PROJECT]`). For dashboard/UI verification, describe the rendering pathology structurally (for example, "the narrow treemap leaf wraps one word per line") rather than quoting visible PKB task text as the regression handle.

Before the supervisor writes a PR body, commit message, issue comment, dispatch brief, or verification prompt based on PKB output, do a quick egress scan for raw task IDs (`task-[a-f0-9]{8}`), titles copied from `list_tasks`/`get_task`, and project labels. If any are present, rewrite to anonymized evidence first.

### pauli — preflight & react

Use for every decision the supervisor would otherwise inline: "what should I dispatch next?", "a worker exited without a deliverable", "the verifier said fail."

**Brief shape:** epic ID + role (`preflight` | `react`) + (for `react`) one-line context (work item ID, exit signal).

**Scope:** PKB-side judgment — task readiness, decomposability, dependency state, worker selection ([[SURFACES.md#tldr-matrix]]), Critic Gate for high-blast-radius tasks, `halt-on-failure` scan on any draft body she writes (canonical list at [[instructions/decomposition-and-review#halt-on-failure-prose-scan-mandatory-before-posting-any-decomposition]]), RBG pre-flight check (invoke RBG inline to review the proposed decomposition for axiom violations before creating tasks). Pauli does NOT run shell commands, probe hosts, or test environment capabilities in the supervisor context.

**Pre-flight shape (Decision Tree)**:
Before dispatch, Pauli runs a pre-flight validation. Use the Design/Research variant if task `type` or `kind` is design/spec/research, OR if the AC indicates creating a new file/design doc/spec. Otherwise, use the Code/Edit variant.

The detailed validation protocol (inputs, checks, and halt conditions) for both **Code/Edit** and **Design/Research** variants is canonical at [[instructions/worker-dispatch#mandatory-pre-dispatch-gates]].

**Review-lens annotations — RBG (axioms)**: Create a child subtask `lens: rbg-axiom-check` using `references/lens-templates/rbg-axiom-check.md`. Dispatch is blocked until it reaches status: done.

**Verdict shape:** one short paragraph naming exactly one action — `dispatch <worker> on <task-id> in <project>`, `brief composed on <task-id>`, `file fix-task <title> under <parent>`, or `halt: <reason>`. The supervisor evaluates the verdict's structural shape per [Compose-then-Dispatch Separation § verdict structural-shape guard](#verdict-structural-shape-guard-mandatory-before-acting) before executing. If the verdict is malformed (no action, multiple competing actions, contradictory with the body), append `verdict_fail` to Pattern Memory and exit; do not improvise.

**When to choose `brief composed` over `dispatch`** (see [Compose-then-Dispatch Separation](#compose-then-dispatch-separation)): if pauli composed or substantively refined the `## Dispatch Brief` in this invocation — e.g. filtered superseded prose out of an inherited parent body, rewrote inputs to match the worker shape, added or removed AC — the brief is a fresh in-invocation composition. Pauli emits `brief composed` and the main agent spawns a _separate_ dispatch-agent subagent that reads the persisted brief fresh from PKB and emits its own dispatch verdict (agent-identity separation, `recusal`). If the body's `## Dispatch Brief` is already stable PKB content from a prior invocation and pauli's role this invocation was preflight (PKB-side validation, no authoring), pauli emits `dispatch` and the main agent dispatches directly.

**Brief-for-verify shape (verification brief assembly):**

When a worker has just exited and the next action is verification, pauli (not the supervisor) writes marsha's brief. Pauli:

1. Reads the original mission brief / spec / acceptance criteria from PKB, and the spec's `## Fitness Rubric` section (authored upstream via `/design-rubric`).
2. States the deliverable in one sentence.
3. Locates the artifact (PR URL, screenshot path, running URL).
4. Produces ONE short paragraph for marsha — example shape:

   > "Verify <artifact>. Goal: <one sentence>. Rubric + AC: <spec link>."

5. Does NOT include: iteration history, prior reviewer notes, dimension checklists, methodology summaries, persona prompts, or "things to look for."
6. Does NOT invent assessment criteria — forwards only what's in the spec. If the spec is missing `## Fitness Rubric` and the artifact is user-facing, the verdict is `halt: fitness rubric missing — invoke /design-rubric before verify`. Don't improvise.

Why: the verification brief is the lever that determines whether marsha forms a fresh judgement or rubber-stamps the supervisor's narrative. Less is more. Marsha invokes `/verify` and reads methodology there.

### marsha — verify

Use when a worker has just exited and the work item is in `in_progress`. Marsha is the QA reviewer; her contract is unchanged from her standard role.

**Brief shape:** work item ID, PR URL (or "none"), acceptance criteria from the work item.

Marsha returns a one-line verdict: `PASS`, `FAIL <reason>`, or `REVISE <reason>` (treated as indeterminate by the supervisor).

| Marsha verdict | Main agent action                                             |
| -------------- | ------------------------------------------------------------- |
| PASS           | Mark item `merge_ready`; checkpoint                           |
| FAIL           | Call pauli with `role=react`, context=`marsha-fail: <reason>` |
| REVISE         | File a verification subtask (depends_on PR); checkpoint       |

Marsha never dispatches, never edits, never files tasks. The supervisor consumes her verdict.

## Compose-then-Dispatch Separation

_Canonical doctrine at [[../aops/references/authoring-discipline#3-compose-then-dispatch-separation-recusal-propagated-to-the-dispatch-surface]]. This section names how it applies to the supervisor loop._

**The agent that authored a dispatch brief must not be the same agent that dispatches against it.** `recusal` requires structural separation between the composing impulse and the dispatching impulse. What it requires is **agent-identity separation**, not temporal separation across ticks or sessions. The dispatcher reads the brief from PKB in a fresh subagent context and forms an independent verdict.

A single supervisor tick MAY compose-then-dispatch by chaining **two independent subagent invocations**:

1. **Compose-agent** — pauli (or equivalent) authors / refines the `## Dispatch Brief` in the task body and exits with `brief composed on <task-id>`.
2. **Dispatch-agent** — a _separate_ subagent invocation (fresh subagent context — not a continuation of the compose-agent's context) reads the persisted brief from PKB, runs preflight, and emits a structured dispatch verdict. This MAY be pauli again invoked with `role=dispatch`, or another preflight-capable subagent.
3. **Main agent** — evaluates the dispatch-agent's verdict's structural shape (see verdict guard below) and executes.

The two subagent invocations are independent contexts. The dispatch-agent does not inherit the compose-agent's reasoning trace; it reads the brief fresh from PKB and forms its own judgment. This is the cure `recusal` demands; the cost is one extra subagent call, not a tick exit and re-entry.

**Heuristic for "was the brief composed in this invocation"** (qualitative — the compose-agent's judgment of its own work, not a regex on the diff):

- Pauli read the body and the current `Dispatch Brief` content is unchanged from what she pulled at ORIENT → brief is a **stable PKB artifact**; pauli emits `dispatch` in this same invocation.
- Pauli rewrote, augmented, filtered superseded text out of, or otherwise actively shaped the `Dispatch Brief` for the worker about to be invoked → brief is a **fresh in-invocation composition**; pauli emits `brief composed`. The main agent then spawns a separate dispatch-agent subagent that reads the persisted brief fresh.

### Verdict structural-shape guard (mandatory before acting)

The supervisor MUST evaluate every subagent verdict before acting on it:

- **Action named?** Verdict must name exactly one action: `dispatch <worker> on <task-id>`, `brief composed on <task-id>`, `file fix-task <title>`, or `halt: <reason>`.
- **Coherent?** Verdict must be internally consistent — no competing actions, no contradictions (e.g. "dispatch on task-X" alongside "task-X is not ready").
- **Grounded?** Verdict must not claim a state the epic body doesn't support (e.g. "brief stable" when there is no `## Dispatch Brief`).

If any check fails, append `verdict_fail` to Pattern Memory with the structural reason and exit. Do not improvise.

### Pauli verdict shapes that fit the separation

- `brief composed on <task-id>` — pauli refined or wrote the brief this invocation. Main agent persists (if not already in PKB), then spawns a fresh dispatch-agent subagent.
- `dispatch <worker> on <task-id> in <project>` — the brief was already stable PKB content; pauli's role this invocation was preflight (PKB-side validation), not composition. Main agent dispatches directly.

## Canonical Dispatch Template

The supervisor main agent executes dispatch directly using this canonical shape. It does not probe the environment first.

```bash
# Local dispatch (canonical)
zsh -i -c "polecat run -t <task-id> -p <project> [--gemini] [--model <name>]"

# Remote dispatch (SSH + tmux) - use when TARGET_HOST is required
ssh "$TARGET_HOST" "tmux new-session -d -s 'polecat-<task-id>' 'zsh -i -c \"polecat run -t <task-id> -p <project> [--gemini] [--model <name>]\"'"
```

**Model selection flag semantics:**

- `--model <name>` is the canonical flag for model selection. Use `--model claude` to inherit the configured model from `polecat.yaml session_defaults.claude_model` (preferred — no version pinning in dispatch commands). Use `--model opus` for latest Opus via Claude Code's family alias, or `--model claude-opus-4-8` to pin a specific version. Other examples: `--model claude-haiku-4-5` for Haiku.
- `--gemini` selects the Gemini CLI as the worker backend (not a model name). To specify a particular Gemini model, pair it with `--model`: `--gemini --model gemini-2.5-pro`.
- `--opus` is not a valid flag. It does not exist in the polecat CLI and will cause an error if used. Use `--model opus` (latest Opus) or `--model claude-opus-4-8` (pinned) instead.

**Auto-arm notify-watch** — if this is the first polecat dispatch in an interactive (non-`/loop`) session and the docker-events Monitor is not already armed, arm it immediately after the dispatch command completes. See [In-Session Multi-Tick Supervision](#in-session-multi-tick-supervision-notify-watch) for topology detection and the canonical Monitor command. Subsequent dispatches in the same session do not re-arm.

**Brief location** — the `## Dispatch Brief` must be in the task body before the dispatch command runs. If a compose-agent authored or refined it earlier in this same tick, dispatch is delegated to a _separate_ dispatch-agent subagent invocation (see [Compose-then-Dispatch Separation](#compose-then-dispatch-separation)) that reads the brief fresh from PKB and emits its own structured verdict. The main agent never composes the brief in-line and never pastes new brief content into the dispatch command. If the dispatch fails synchronously, or the worker fails asynchronously, the error routes to pauli in the `react` phase.

## Emergency Brake

The brake is the **only** pre-dispatch check. It catches terminal loops; it does not gate the golden path. Apply against `## Pattern Memory` (last 8 rows) and `## Work Items`:

| Rule              | Trigger condition                                          | Action                                                  |
| ----------------- | ---------------------------------------------------------- | ------------------------------------------------------- |
| Recurring failure | Same `*_fail` or `*_halt` class appears ≥3× in last 8 rows | Halt epic; status `review`; reason `recurring: <class>` |
| Stalled workers   | ≥2 work items `in_progress` with last activity > 4h ago    | Halt epic; status `review`; reason `stalled workers`    |

A direct `halt` recommendation from pauli is not a brake rule — it is just pauli's verdict, executed normally. Halt protocol: append the reason as a Pattern Memory row, set the epic status, emit a one-line summary, exit. **Never** substitute a different worker, repo, or scope. Brake reset happens only when a human explicitly clears the epic (status → `queued`).

## Pattern Memory format

The main agent appends one row per tick. Capped at 16 rows (drop the oldest when over). Lives in the epic body under `## Pattern Memory`:

```markdown
## Pattern Memory

| Tick (ISO)           | Decision                    | Class       | Notes               |
| -------------------- | --------------------------- | ----------- | ------------------- |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | dispatch_ok | preflight clean     |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | verify_fail | tests red on docker |
```

Class values: `dispatch_ok`, `dispatch_halt`, `verify_pass`, `verify_fail`, `react_filed_fix`, `react_halt`, `brake_fired`, `verdict_fail` (subagent verdict failed the structural-shape guard; tick exits without acting — fires the recurring-failure brake if it appears ≥3× in 8 rows). A non-terminal `brief_composed` row MAY be appended by an in-tick compose-agent step before the dispatch-agent step appends its own row; this is bookkeeping, not a checkpoint that ends the tick. Keep class names stable — the brake matches on them.

The main agent never inspects work items by reading their task bodies; the Work Items table inside the epic body is the authoritative summary.

## Design Principles

### The Task File Is the Only State

No external state files, no environment-specific paths, no "check the log." The next supervisor instance (possibly a different machine, possibly a different agent) reads the epic body and knows exactly what's happening.

Supervisor appends to the epic body — `## Pattern Memory`, `## Work Items`, `## Supervisor Log` — are part of the supervisor contract. Downstream enforcers must not flag them as P#5 violations.

### Halt-on-substitute

The supervisor never silently substitutes a different **worker type**, **deliverable type**, **repository**, or **scope**. It halts, records infeasibility in the epic body, and waits for explicit human direction.

Substitution axes with clear binaries:

- **Worker type**: Claude vs Gemini vs Polecat
- **Deliverable type**: full section vs partial draft; PR vs comment; spec vs implementation
- **Repository**: repo A vs repo B
- **Scope**: project-local config / host-wide config; per-session env / host-wide env; one-task / batch-of-tasks; sandbox edit / canonical-repo edit

The ambiguity exception (line ~197) handles fuzzier cases — in-repo design ambiguity is _not_ a halt; the supervisor dispatches and pauli writes a brief naming the ambiguity. Halt-on-substitute is for the substitutions named above; fuzz lives in the ambiguity exception. The two paths are distinct: if your case fits neither, halt by default.

### Drive-by Fix Policy

When workers encounter trivial issues mid-task, they must adhere to the canonical project Drive-by fix policy (codified in `.agents/CORE.md`): bundle an unrelated fix into the current PR only when ALL of: (a) it is blocking your PR from merging (e.g. CI failure that's not your fault), (b) the fix is trivial and obvious, and (c) you can describe it in one sentence in the PR description. Otherwise, file a separate task — don't expand the PR scope.

### Keep the Pipe Flowing — Don't Micromanage Polecats

The supervisor's job is throughput: claim → dispatch → next. It is NOT to read every task body and design the implementation before firing.

**Trust the Worker:** Apply the canonical Task-Body Authoring Discipline ([[../aops/references/authoring-discipline]]) on every dispatch and decomposition.

- **Trust polecat depth, throttle polecat width.** Give each polecat a substantive chunk of work instead of micro-decomposing it for them.
- **No mid-stream approval theatre.** Polecats submit to the canonical review surface. Do not invent phantom gates.
- **Brevity in delegation.** State the artifact, the goal, and the spec link — and stop.

Bias hard toward dispatching. A queue of approved tasks gets fired one-per-tick in rapid succession, maintaining a small concurrency window. **Concurrency is the supervisor's discretion** — ramp up or down based on observed signals (quota events, infra failures, review-pipeline pressure). The user is not in a rush; under-shooting beats over-shooting.

**Discourage substantive supervisor work — including planning.** Epics with `scope > 10`, design tasks, decomposition-heavy work — fire them at a polecat. Polecats can plan and decompose; supervisor only owns decomposition when the user asks explicitly or a polecat returns a structured "needs decomposition" verdict. (See [[instructions/decomposition-and-review]] for the canonical phase split.)

**Batched interruptions, not per-task.** When the supervisor genuinely cannot proceed on multiple items, collect them into ONE message (generic summary in the [ATTN] block, details in the epic body) — not one ping per blocker.

The right mental model: the supervisor is a **conveyor belt operator**, not a project manager. Keep parts moving onto the belt. Track outcomes. Iterate.

In autonomous (loop) sessions, legitimate halts set the epic to `blocked` or `review`; the next interactive supervisor invocation picks it up.

### Dispatch Is Supervisor Judgment — Not A Wrapper Or A Swarm

Dispatch policy — _when_ to fire the next worker, _whether_ to pair two in flight, when to back off, when to halt — is **supervisor judgment**. It does not belong in a CLI flag, a shell wrapper (`~/bin/polecat-*.sh`), or a batched "swarm" abstraction. The dispatch CLI is documented at [[instructions/worker-dispatch#dispatch-protocol]] — exit code, `gh pr list`, and PKB status are the whole telemetry surface at the sequential N=2–4 regime [Reporting Posture](#reporting-posture) actually supports.

**When a correction lands** ("stop building wrappers"), the lesson is **not** "encode the same policy into a different tool." The lesson is: this judgment lives in the supervisor loop. Do it in supervisor judgment, in bash, one call at a time, with PKB writes between. If pacing-the-pipe ever genuinely needs more, that is a SKILL.md change to discuss with the user — not a polecat feature request and not a wrapper.

### Engineering Integrity (`halt-on-failure`) Is Non-Negotiable

Failing tests, broken tools, and incompatible environments are bugs the supervisor's plan must fix — never categories the supervisor's plan triages around. The verbatim list of prohibited prose patterns (drift candidate, skip-on-env, "fix vs skip", etc.) is canonical at [[instructions/decomposition-and-review#halt-on-failure-prose-scan-mandatory-before-posting-any-decomposition]] and is enforced by pauli during preflight and decomposition. Casual user phrasing such as "we may need to adjust some tests" does NOT authorise `halt-on-failure` exemption — `halt-on-failure` is universal (per `exercise-authority`) and only an explicit user directive to skip a specific test counts.

`halt-on-failure` generalises beyond code: a failing claim-evidence audit, citation check, or methodology review is a bug to fix, never a category to route around.

### Critic Gate (high-blast-radius dispatch)

Tasks tagged `high-risk` or meeting blast-radius criteria (irreversible operations, external system modifications, actions that close recovery paths) require independent critic review before dispatch. Pauli's preflight verdict includes the critic check; see [[instructions/worker-dispatch#critic-gate-for-high-blast-radius-tasks]] for the protocol.

### Academic Integrity Is Non-Negotiable

The supervisor delegates execution but never delegates **final academic judgment**. Methodology choices, citation accuracy, and anything published under the user's name require human decision points, surfaced in the epic body as pending decisions. This is distinct from engineering judgment: polecats ARE trusted to make in-repo design and architectural decisions (see [[#halt-on-substitute]]).

### `exercise-authority` Edge 2: Act on Delegated-Agent Verdicts

_Enforces `exercise-authority` Edge 2 (FM-1, FM-2, FM-6)._

Pauli/marsha verdicts ARE decisions, not recommendations to forward. Execute in the same tick. Forwarding ("subagent recommends X, want to proceed?") is FM-2 rubber-stamping. Before asserting "I can't dispatch X", run the cheapest verification (`gh auth status`, `which gemini`) — capability fabrication (FM-6) forecloses the user's override.

## Phases

The supervisor is a loop, not a pipeline. Each tick enters one phase and exits.

| Phase      | Subagent                               | What happens                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Orient     | (none)                                 | Main agent reads epic body; runs brake; chooses subagent role                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Decompose  | pauli                                  | Pauli proposes subtasks; RBG axiom-check runs in parallel as a mandatory reviewer (verdict: OK/WARN/BLOCK gates promotion). See [[instructions/decomposition-and-review]]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Review     | (none)                                 | Plan-review halt — decomposition synthesised; awaits human promotion to `queued`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Dispatch   | pauli (compose-agent → dispatch-agent) | When the task body carries a stable `## Dispatch Brief`: pauli preflights (PKB-side validation only — no rewriting) and emits `dispatch`; main agent runs the command. When the brief needs composition: a compose-agent (pauli) authors / refines the brief and emits `brief composed`; the main agent then chains a _separate_ dispatch-agent subagent invocation that reads the brief fresh from PKB and emits its own dispatch verdict. Both shapes complete in a single tick; agent-identity separation, not tick separation, delivers `recusal`. See [Compose-then-Dispatch Separation](#compose-then-dispatch-separation) and [[instructions/worker-dispatch]]. |
| Pre-verify | pauli                                  | Assembles the minimal verification brief — fetches the original mission brief, project context, and the spec's `## Fitness Rubric` / acceptance criteria. Strips iteration history. Produces ONE short paragraph: artifact + goal + spec link. No methodology, no dimensions, no persona prompts.                                                                                                                                                                                                                                                                                                                                                                      |
| Verify     | marsha                                 | Receives the minimal brief in fresh context. Returns PASS / FAIL / REVISE. Invokes /verify herself for methodology — the supervisor never inlines it into the brief.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| React      | pauli                                  | Pauli recommends a fix-task or a halt after a FAIL                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Halt       | (none)                                 | All work items at review surface or escalated; emit final summary; exit                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

`Review` and `Halt` are real terminal states, not transient phases. The supervisor never finalises the deliverable itself — it hands off at the review surface. Async ownership transfers to whatever review pipeline the deliverable subworkflow defines.

## Deliverable Subworkflows

The supervisor loop is **deliverable-agnostic**. The same orient → decompose → review → dispatch → verify → react → halt cycle applies whether the deliverable is a code change, a methodology section, or an analysis report. What changes is the dispatch shape, the review surface, and the completion signal.

| Deliverable type   | Subworkflow                               | Status  |
| ------------------ | ----------------------------------------- | ------- |
| Code change        | [[instructions/code-deliverable]]         | active  |
| Research / writing | (would live alongside, not in scope here) | not yet |

## Status Display Surfaces

State lives in the epic body (see [The Task File Is the Only State](#the-task-file-is-the-only-state)). For _display_ — answering "what is happening across N sessions / N epics right now?" — the supervisor and downstream UIs read from upstream surfaces that already exist for other reasons. These are **read-only projections, not state**:

- `gh pr list` / `gh pr checks` — PR + review-pipeline status
- `gh run list` — cron + GHA worker state
- `$AOPS_SESSIONS/tasks.json` — dashboard producer
- `$AOPS_SESSIONS/state/pr-state.json` — if a `/sleep` or equivalent producer is running
- GitHub Issues with a `halt` label — escalation queue
- container-runtime events (e.g. `docker events`) — fleet exit signals where the runtime is local
- the epic body's `## Work Items` table — authoritative summary of children, never re-derived from individual task bodies

**Forbidden as state surfaces:** any new local JSON state file outside the epic body (Stop-hook JSON, `session-state.json`, `coordination-state.json`); per-skill `gh pr list` re-fetching when a fresher producer (like `pr-state.json`) is available.

The supervisor's job ends when each work item has reached its review surface (open PR for code; equivalent for other deliverable types). Set the epic to `merge_ready` once every child is at the surface or escalated/blocked with a recorded reason. The async review pipeline takes over; emit the final summary and exit. See [[instructions/code-deliverable]] for the code case.

## User Attention Notification

When the [Reporting Posture](#reporting-posture) escalation criteria fire, emit a single `[ATTN]` block — machine-parseable YAML inside a fenced block. One block per tick, never more. The block is the _entire_ user-facing payload; no surrounding prose.

The `[ATTN]` block is an **ephemeral notification surface, not state**. It restates a decision recorded in the epic body's `## Pattern Memory` and (where relevant) `## Work Items`. A future tick reads the epic body; it does not re-read past `[ATTN]` blocks. The block exists to make a single user-facing decision easy to read and dismiss, not to carry information the next tick depends on.

### Template

```
[ATTN]
---
id: <epic-id>:<tick-sequence>
urgency: now | today | whenever
action_required: decision | review | info
one_line: <=80-char summary
context_ref: <task-id | PR-url | issue-url>
dismiss_if: <one-line condition under which this no longer needs attention>
suggested_response: <the supervisor's default if user says "you decide">
---
```

### Required fields

- `id` — `<epic-id>:<tick-sequence>`. Stable across re-emits of the _same_ unresolved decision (re-emits reuse the sequence); a new decision on the same epic increments the sequence. Notification consumers dedupe on `id`.
- `urgency` — `now` (blocks pipeline), `today` (daily-brief horizon), `whenever` (next interactive session).
- `action_required` — `decision` (the supervisor cannot proceed), `review` (deliverable at review surface), `info` (one-shot heads-up).
- `context_ref` — the single canonical link to the underlying work; never a wall of context.
- `dismiss_if` — auto-clear condition for the notification surface (e.g. "task status moves out of in_progress"). Consumed by the notification UI, not by the next supervisor tick.
- `suggested_response` — what the supervisor will do if the user says "you decide". Required for `action_required: decision`; omit otherwise.

**Vocabulary Boundary**: The `one_line` and `suggested_response` fields MUST be written in plain English. Framework-internal taxonomy (`react cycle`, `dismiss_if`, `polecat-side fix-task`, `DECIDE-class`) stays inside the skill bodies and must never leak into user-facing text. Where structural metadata (task IDs, PR numbers, commit hashes) is genuinely load-bearing, prefer a short link over inline jargon. Do not use 60-word run-on sentences or paste raw commit hashes.

### Worked example (synthetic)

```
[ATTN]
---
id: task-EPICID:3
urgency: today
action_required: decision
one_line: Workers exited with zero diffs on task-XXXX — abandon or re-scope?
context_ref: task-XXXX
dismiss_if: task-XXXX status moves out of in_progress
suggested_response: file refinement task, set epic to review
---
```

### Push notification pairing

Where a push channel (e.g. Discord, Slack, email) is configured for the session, push the `one_line` field when `urgency in {now, today}` AND `action_required == decision`. The full block stays in the terminal transcript. `urgency: whenever` and `action_required: info|review` blocks are terminal-only — they surface in the next `/daily` briefing, not as a push notification. Never push twice for the same `id`.

If no push channel is configured, the block is terminal-only. The supervisor does not configure push channels itself.

## In-Session Multi-Tick Supervision (notify-watch)

The default cadence is one tick per `/loop 30m` invocation. In an interactive (non-`/loop`) supervisor session, arm the docker-events Monitor automatically on the **first** polecat dispatch — the supervisor then ticks **on event** rather than on time for that session. Headless / cron / `/loop`-driven ticks do NOT arm the watch: there is no persistent session for events to land in. The event is "a worker exited" — surfaced by an OS-level stream, not by polling, and not by a bash refill loop (see Forbidden, below).

> **Why auto-arm?** Users do not explicitly request an in-session batch — they dispatch a polecat and later ask "did it finish?". The previous gate (arm only on explicit batch request) left the user polling. Arming on first dispatch removes this friction without requiring any opt-in. Observed 2026-05-19: user asked "did it finish? do you get a notification when it finishes?" after a polecat dispatch; supervisor had to arm the Monitor reactively.

The canonical in-session watch is `Monitor` over `docker events`. Before arming, detect the execution topology: if `docker` is directly accessible locally (run `command -v docker && docker info` quietly — succeeds in a WSL session), use plain `docker`; if the supervisor is running on a remote host (e.g. over SSH from a laptop), prefix with `ssh wsl`. Wrap the command in a reconnecting loop so the watch survives SSH drops, laptop sleep, or Wi-Fi blips without silent failure.

**Local** (docker accessible directly — typical WSL session):

```
Monitor(
  description: "polecat exits",
  persistent: true,
  command: "while true; do docker events --filter event=die --filter 'name=polecat-' --format '{{.Time}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}'; sleep 2; done"
)
```

**Remote** (supervisor on a laptop or other host, docker on WSL):

```
Monitor(
  description: "polecat exits",
  persistent: true,
  command: "while true; do ssh wsl docker events --filter event=die --filter 'name=polecat-' --format '{{.Time}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}'; sleep 2; done"
)
```

Arm it **once**, immediately after the first polecat DISPATCH in an interactive session. Subsequent dispatches in the same session do NOT re-arm. Each `die` event for a polecat-* container emits one stdout line → one chat notification. On each notification:

1. Identify the exited work item from the container name (`polecat-<task-id>`).
2. Run the normal supervisor tick on that item's epic: ORIENT → BRAKE → DECIDE (marsha verify) → ACT → CHECKPOINT.
3. If the user's concurrency cap has a free slot after the verify settles, run a second tick on the same or a different epic with DECIDE = pauli preflight + dispatch.

**The watch carries signal, not judgment.** It is _not_ a replacement for the per-tick loop. Every dispatch decision still goes through pauli preflight; every verify still goes through marsha. The watch only removes idle time between ticks within one session. Re-read [[#forbidden-in-the-main-agent]] and the non-delegable-supervision principle (nicsuzor/academicOps#942) — a bash `docker events` pipe carries event lines; it does not select tasks, file fix-tasks, or skip gates.

**Crew filtering.** The crew session is also a `polecat-*` container. Filter it out at the agent layer (look up the exit's container env via `docker inspect <name>` and skip if `POLECAT_CREW_NAME` is set — crew sets it, run workers do not), or refine the `--filter` to match the headless naming pattern in use.

**When to stop the watch.** Call `TaskStop` on the Monitor when (a) all dispatched polecats are verified and resolved (the session's in-flight work is done), (b) all in-flight epics have reached `merge_ready`/`blocked`/`review`, or (c) the session is about to end. A leaked persistent Monitor keeps consuming notifications across unrelated tasks.

**Choosing between mechanisms** (see [[instructions/supervision-loop#monitoring-mechanisms]] for the table):

| Situation                                             | Use this                                                                |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| Single dispatched worker, one outcome needed          | `run_in_background` Bash with an `until <ready>; do sleep 2; done` body |
| Waiting on PR state transitions (async)               | Persistent `Monitor` on `gh pr checks` poll loop                        |
| Truly idle, no event source                           | `ScheduleWakeup` (safety net only; ≥1800s — never 300s)                 |
| **Any interactive session with a dispatched polecat** | **Persistent `Monitor` on `docker events`** (this section)              |

## Lifecycle Trigger Hooks

| Hook          | Trigger            | What it does                                                                                                                |
| ------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `queue-drain` | cron / manual      | Checks queue, starts supervisor session                                                                                     |
| `stale-check` | cron / manual      | Resets tasks stuck beyond threshold                                                                                         |
| `pr-merge`    | James (in-session) | (Code deliverable) PR merged → James closes associated tasks per Task Completion Loop in james.md; not driven by supervisor |

> **Configuration**: See [[SURFACES.md]] for execution surfaces, dispatch syntax, and plugin/gate state per surface — pauli reads these at dispatch time. (Sizing defaults are not currently documented; see SURFACES.md _Gaps / open questions_.)

## Task Assignment Rules

- **Default assignee**: the appropriate worker (e.g. `polecat` for code) or unassigned.
- **Human assignment**: never assign to `nic` unless the task reduces to a genuine binary human choice ("Pattern A or Pattern B?").
- **Decision subtasks**: when a real choice IS needed, file a minimal choice subtask that blocks the epic, providing full context to decide. Never assign the parent epic back to `nic`.
- **Underspecified tasks**: file a research / decomposition task for an agent first.

## Handover

**Always leave a loose thread.** Every agent that completes work as part of a chain MUST leave at least one PKB task that says what comes next — unless the work is fully complete with no follow-ups. Use `mcp__pkb__append` mid-flow and `mcp__pkb__release_task` at terminal states.

If dispatch is blocked → file a refinement task. If a phase is complete but the epic remains → ensure the next subtask is `ready` or `queued`. Never assume the user knows the graph; link to the next task explicitly.

## Known Limitations

- **Polecat stream noise ≠ failure.** Boot-time stderr from Gemini workers (plugin load messages, extension warnings) is cosmetic — it does not indicate task failure. Marsha reads the PR/diff, not the raw polecat stdout tail.

- **Gemini 429/QUOTA_EXHAUSTED ≠ Claude hard-quota.** When a Gemini polecat exits with code 1 and the stdout tail shows `429 QUOTA_EXHAUSTED`, the reflex is to treat it as a session-locking quota event (like Claude's hard `overloaded_error` that can lock out a session for hours). **This is wrong for Gemini.** Gemini's `429 QUOTA_EXHAUSTED` is a transient rate-limit signal — the Gemini client handles it by backing off and retrying. A polecat exit on `429` is almost always polecat's **45-minute `max-time` wall-clock limit killing the worker**, not a Gemini quota exhaustion.

  **Diagnosis tree** — when a Gemini polecat exits with code 1, route to pauli (`role=react`). The supervisor MUST NOT read transcripts directly; pauli checks in order:
  1. Did the task genuinely need more than 45 minutes? (Large refactor, many files, waiting on slow tools.) → The worker ran out of time, not quota. The task itself may need decomposition.
  2. Was the worker stuck in a retry/feedback loop? (Polecat transcript shows repeated tool calls on the same file, repeated test failures.) → File a fix-task describing the loop; re-dispatch with clearer scope.
  3. Did the transcript show real `429` back-pressure before the timeout? (Multiple backoff-wait messages in the last 10 minutes of the log.) → Rate-limit is real but the session is not locked; re-dispatch after a short wait.
  4. None of the above → treat as a transient timeout; re-dispatch the same task with the same Gemini worker.

  **Pauli `react` verdicts that work for this pattern:**
  - Re-dispatch the same task with `--gemini` (same worker). The Gemini rate-limit window resets; a fresh session will not replay the `429`.
  - Decompose the task if it is genuinely large (> 45 min of real work). Do not decompose reactively when the timeout is an infrastructure artefact.
  - Do **not** recommend switching to Claude. Worker substitution is a [Halt-on-substitute](#halt-on-substitute) event — it requires explicit human direction, not a supervisor heuristic.

  _Upstream fix_: structured exit metadata per issue #487 (polecat post-mortem diagnostics) would expose the real termination signal (timeout vs. rate-limit vs. task failure) without reading raw stdout tails. Until that lands, the diagnosis tree above is the canonical path.
