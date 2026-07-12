# Workflow-system pipeline — component, trigger & contract reference

Developer documentation for the five-stage pipeline in `aops-extras/skills/`. Covers **how each
stage is triggered**, **where each stage pulls information from**, and the **data contract at each
seam**.

## Architecture in one line

Stages **do not call each other directly**. Each reads from / writes to the **PKB graph** (a task's
frontmatter + body is the message bus); the next stage is triggered by graph state + queue position,
not by a return value.

> ### ⚠ Wiring status (read this first)
>
> The five pipeline **skills are implemented** (`aops-extras/skills/`). The **trigger layer that
> should fire them is not yet repointed** to them — it still targets the now-deleted `planner` skill
> and an absent `task-lifecycle` skill. **Today the pipeline runs only by manual `Skill()`
> invocation.** Every trigger below is marked with its real status: ✅ wired · ⚠ partial/broken · ⬚
> not wired. The blanks are shown as blanks, not glossed over.

## The pipeline, vertically — trigger (left) · stage · sources (right)

```mermaid
flowchart TB
    IN(["Intake — user prompt or inbound task-id"]):::ext

    subgraph R1[" "]
        direction LR
        T1["TRIGGER ⬚ not wired<br/>no /hydrate command; router.py hook exists<br/>but auto-invoke unconfirmed"]:::blank
        HY["hydrate<br/>context assembly"]:::agn
        S1["reads → PKB semantic search · graph neighbours ·<br/>memories · project config · workflows/INDEX.md"]:::src
        T1 --> HY
        HY -.-> S1
    end

    subgraph R2[" "]
        direction LR
        T2["TRIGGER ⚠ broken<br/>/q command exists → calls deleted planner<br/>needs repoint: /q → situate"]:::blank
        SI["situate · pauli<br/>intake + valuation"]:::pauli
        S2["reads → the context bundle · graph parents/targets ·<br/>network metrics · valuation dimensions"]:::src
        T2 --> SI
        SI -.-> S2
    end

    WAIT["⏳ task waits in the queue until it comes due"]:::wait

    subgraph R3[" "]
        direction LR
        T3["TRIGGER ⬚ not wired<br/>intended /pull or /dispatch → task-lifecycle skill<br/>(task-lifecycle SKILL.md absent in source)"]:::blank
        DE["decompose · pauli<br/>structure + review steps"]:::pauli
        S3["reads → the due task · workflows/INDEX.md<br/>(gate/process templates) · two-layer doctrine"]:::src
        T3 --> DE
        DE -.-> S3
    end

    subgraph R4[" "]
        direction LR
        T4["TRIGGER ⬚ not wired<br/>intended: task-lifecycle at subtask dispatch<br/>(same absent skill)"]:::blank
        BR["brief<br/>delegation brief"]:::agn
        S4["reads → the due subtask + parent · workflow review steps ·<br/>hydrate bundle Context (refresh if stale)"]:::src
        T4 --> BR
        BR -.-> S4
    end

    subgraph R5[" "]
        direction LR
        T5["TRIGGER ⚠ partial<br/>/dispatch command exists → background surface<br/>but delegates to absent task-lifecycle"]:::blank
        EX["execute<br/>any capable agent (out of scope)"]:::ext
        S5["reads → the brief in the task body +<br/>whatever resources the brief points to"]:::src
        T5 --> EX
        EX -.-> S5
    end

    subgraph R6[" "]
        direction LR
        T6["TRIGGER ⚠ partial<br/>/verify + /strategic-review skills exist & invokable<br/>gate-subtask auto-dispatch ⬚ (via absent task-lifecycle)"]:::blank
        EV{"evaluate — review step<br/>/verify · /strategic-review"}:::gate
        S6["reads → deliverable + brief emit-contract ·<br/>AXIOMS + local rules (rbg) · fitness rubric (marsha)"]:::src
        T6 --> EV
        EV -.-> S6
    end

    DONE(["delivered"]):::done

    IN ==> HY
    HY ==> SI
    SI ==> WAIT
    WAIT ==> DE
    DE ==> BR
    BR ==> EX
    EX ==> EV
    EV ==>|accept| DONE
    EV -. "needs work — critique folds into brief" .-> BR

    classDef pauli fill:#e7ecfb,stroke:#2b57d6,color:#17337f;
    classDef agn fill:#eef1f5,stroke:#57616c,color:#1b2027;
    classDef gate fill:#faedd8,stroke:#a86408,color:#7a4a06;
    classDef ext fill:#ffffff,stroke:#b8c0cc,color:#57616c;
    classDef done fill:#dcf0e9,stroke:#0f7a63,color:#0b5c4a;
    classDef src fill:#f3f6f4,stroke:#7fa08f,color:#33564a;
    classDef blank fill:#fbeaea,stroke:#c0392b,color:#7a241c,stroke-dasharray:4 3;
    classDef wait fill:#f5f6f8,stroke:#838d97,color:#57616c;
```

## Trigger status — what actually fires each stage (verified against source)

| Stage                    | Intended trigger                                                                                                 | State in source today                                                                                                                                                                                  | Status                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `hydrate`                | `router.py` (UserPromptSubmit hook) hydrates every inbound ask, or a `/hydrate` command                          | No `/hydrate` command exists. `router.sh`→`router.py` **is** registered on `UserPromptSubmit` (`aops-core/hooks/hooks.json`), but I did **not** confirm it invokes the new `hydrate` skill.            | ⬚ **not wired / unverified**                          |
| `situate`                | `/q` (capture) → `situate`                                                                                       | `aops-pkb/commands/q.md` exists but runs `Skill(skill="planner", …)` — **`planner` was deleted**.                                                                                                      | ⚠ **broken** — repoint `/q` → `situate`               |
| `decompose`              | `/pull` or `/dispatch` → `task-lifecycle` fires `decompose` when a `needs_decomposition` task comes due          | `/pull` + `/dispatch` commands exist but delegate to a **`task-lifecycle` skill with no `SKILL.md` in source** (`aops-pkb/skills/task-lifecycle/` absent).                                             | ⬚ **not wired**                                       |
| `brief`                  | `task-lifecycle` expands the due subtask into a brief just before dispatch                                       | Same absent `task-lifecycle` skill. Nothing else invokes `brief`.                                                                                                                                      | ⬚ **not wired**                                       |
| _execute_                | `/dispatch` → background surface (polecat / subagent) reads the brief by task-id                                 | `/dispatch` command exists; delegates to the absent `task-lifecycle`.                                                                                                                                  | ⚠ **partial**                                         |
| `evaluate` (review step) | a workflow's review step runs `/verify` or `/strategic-review`; the outer loop advances only once it's satisfied | `/verify` + `/strategic-review` skills **exist and are invokable**. `decompose` writes review steps into the plan, but the **outer loop that enforces them runs through the absent `task-lifecycle`**. | ⚠ **partial** — evaluators present, enforcement blank |

**To actually wire the pipeline, the remaining work is:** repoint `/q`→`situate`; create (or restore) the `task-lifecycle` skill and have it invoke `decompose` (task comes due) and `brief` (subtask dispatch); decide `hydrate`'s trigger (router hook vs. command) and wire it. None of this shipped with the skills — it's the integration layer.

## Review is a workflow step, not a blocking gate

The framework does **not** enforce quality with blocking gate nodes that intercept a running
session. Review is a **step built into the workflow**, and _strict_ enforcement lives **outside the
session** — in the supervisor's cross-session review loop and the PR/merge pipeline.

1. **Where it lives.** `decompose` selects the epic's **outer** workflow (how the epic reaches
   acceptance) and each subtask's **inner** workflow (how a task reaches done). Review steps are
   ordinary steps _inside_ those workflows, stated in plain prose — never separate DAG nodes.
2. **The two near-mandatory reviews** (stated once, at epic level, on every epic):
   - **Independent review before acceptance** — a reviewer identity distinct from the author
     (`/strategic-review`: rbg axioms · pauli premise/strategy · marsha QA → james). The author
     never reviews their own work.
   - **Human sign-off before anything externally-visible ships** — send / publish / prod / spend /
     delete / merge to a protected branch. The one hard line; carried whenever a subtask is one-way.
     Beyond these, match review to stakes — reversible, read-only work needs none.
3. **The review's "work"** = running an evaluator: **`/verify`** (marsha — assume-broken runtime QA;
   quality + claim-reliability) or **`/strategic-review`** (rbg axioms + pauli premise + james).
4. **Enforcement is external.** `decompose` writes the review step into the plan; making it _stick_
   is the outer loop's job — the supervisor advances a subtask only once its inner-workflow review
   step is satisfied, and the PR/merge pipeline holds the human sign-off. No node blocks a running
   worker mid-flight.
5. **What's wired vs. blank.** The evaluator skills (`/verify`, `/strategic-review`) exist and run
   ✅; `decompose` is authored to write review steps into the plan ✅. The **blank ⬚** is the outer
   loop that enforces them across sessions — the supervisor's review-advance depends on the absent
   `task-lifecycle` skill. You can run `/verify` or `/strategic-review` on an artifact manually today.

## Surfaces & sessions — who runs each stage, in which session

The stages don't all run in one place. **Three session types coordinate only through the PKB graph**
— no direct calls across sessions — the same message-bus principle as the in-session seams, now
across process/host boundaries.

```mermaid
flowchart TB
    subgraph HEAD["Head session — ida (interactive, one working dir)"]
        direction TB
        IK["intake — user ask"]:::ext
        HYq["hydrate ⬚ owner unresolved<br/>head-inline? router hook? pauli subagent?"]:::blank
        SIp["situate → pauli subagent (graph write)"]:::pauli
        AMB["reads evidence bundles · ambition/intent check"]:::agn
    end

    subgraph SUP["Supervisor session — headless, cheap model, /loop timer"]
        direction TB
        PULL["pull epic from queue<br/>Select→Gates spine ⬚ (absent task-lifecycle)"]:::blank
        DEs["decompose ⚠ owner forked — here, or upstream in Head?"]:::blank
        BRs["brief · briefer ≠ executor"]:::agn
        DIS["dispatch worker by task-id"]:::agn
        EVAL{"evaluate loop — /verify + /strategic-review"}:::gate
        TERM["terminal? → reconcile → one-epic-one-PR"]:::done
    end

    subgraph WORK["Worker session(s) — polecat / agy / claude code (anywhere)"]
        direction TB
        CLAIM["claim ready task by id"]:::ext
        EXE["execute against the brief"]:::ext
        HAND["update task — canonical handback<br/>(finishing contract, front-loaded in brief)"]:::ext
    end

    PKB[("PKB graph — cross-session bus<br/>tasks · claims · briefs · handbacks · ledger")]:::bus

    IK --> HYq --> SIp --> PKB
    PKB -. "reads bundle" .-> AMB
    PKB -. "epic comes due" .-> PULL
    PULL --> DEs --> BRs --> DIS
    DIS -->|"task-id + brief in body"| PKB
    PKB -. "ready task" .-> CLAIM
    CLAIM --> EXE --> HAND --> PKB
    PKB -->|"handback evidence"| EVAL
    EVAL -->|"fail: critique → brief"| BRs
    EVAL -->|"accept"| TERM
    TERM --> PKB
    PKB -. "PR + evidence bundle" .-> AMB

    classDef pauli fill:#e7ecfb,stroke:#2b57d6,color:#17337f;
    classDef agn fill:#eef1f5,stroke:#57616c,color:#1b2027;
    classDef gate fill:#faedd8,stroke:#a86408,color:#7a4a06;
    classDef ext fill:#ffffff,stroke:#b8c0cc,color:#57616c;
    classDef done fill:#dcf0e9,stroke:#0f7a63,color:#0b5c4a;
    classDef blank fill:#fbeaea,stroke:#c0392b,color:#7a241c,stroke-dasharray:4 3;
    classDef bus fill:#f5f6f8,stroke:#838d97,color:#57616c;
```

### Session roles (grounded in `agents/ida.md` + `aops-core/skills/supervisor/SKILL.md`)

- **Head session — `ida`** (interactive, one working dir): talks to the user; runs intake → hydrate
  → situate, delegating graph writes to a **pauli** subagent _in the same harness session_; reads
  finished **evidence bundles** (never logs); applies the ambition/intent check and blocks
  correct-but-wrong epics. **Never** dispatches or supervises. (ida §Delegation Rule, §Supervision
  Boundary.)
- **Supervisor session** — headless, cheap-model, `/loop`-timer background process; unit of work =
  one **epic**; stateless tick, cross-tick state in the epic body. Reuses the task-lifecycle
  Select→Gates spine, then owns brief composition, worker dispatch, the evaluate/review loop, the
  ledger, terminal detection, and hand-back (one-epic-one-PR). Nic never meets it.
- **Worker session(s)** — polecat / agy / claude-code / any capable agent, **running anywhere**:
  claim a ready task by id, execute against the brief, save the work (PR / evidence), return the
  **canonical structured handback** — the finishing contract the supervisor front-loads into every
  brief (supervisor §5/§7; format in `specs/enforcement/evidence-contract.md`).
- **pauli** — not a session, a **subagent** invoked for graph mutation (sole graph-shaper) inside
  whichever session needs a write (situate / decompose / graph-maintenance).

### Stage → session map

| Stage            | Session / agent               | Invocation                                                                                                          | Status                                                        |
| ---------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| intake           | head (`ida`)                  | user types                                                                                                          | ✅                                                            |
| hydrate          | ⬚ **unresolved**              | head-inline vs router hook vs pauli/hydrate subagent — not decided                                                  | ⬚ open                                                        |
| situate          | head → pauli subagent         | ida delegates the graph write to pauli                                                                              | ⚠ skill exists; `/q` trigger broken                           |
| decompose        | ⚠ **forked**                  | ida: supervisor gets an _already-decomposed_ epic (⇒ decompose upstream); your model: supervisor decomposes on pull | ⚠ open                                                        |
| brief            | supervisor                    | supervisor composes per subtask at dispatch                                                                         | ⚠ supervisor exists but not yet calling the new `brief` skill |
| execute          | worker (anywhere)             | claims ready task by id                                                                                             | ✅ polecat system                                             |
| evaluate         | supervisor spawns reviewers   | `/verify` + `/strategic-review` as review subtasks                                                                  | ⚠ evaluators exist; auto-dispatch via absent task-lifecycle   |
| reconcile / done | **supervisor** (same session) | terminal detection → one-epic-one-PR                                                                                | ⚠ logic exists; depends on task-lifecycle spine               |

### The unifying principle

Three session types, three hosts, one coordination surface: **the PKB graph is the message bus
across sessions exactly as task bodies are across pipeline stages.** No session calls another
directly — they hand off through task state (`claim_task` / `update_task` / `append` /
`release_task`) and queue position. That is what lets a worker run literally anywhere.

## Component contract table

| # | Component           | Consumes                          | Produces (→ where)                                                                                                | Identity                                           | Tool surface (from frontmatter)                                                                                                 |
| - | ------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `hydrate`           | raw prompt **or** task-id         | **context bundle** → task body (`append`) or handed forward in-turn                                               | agnostic                                           | `search, task_search, get_task, get_semantic_neighbors, retrieve_memory, get_dependency_tree, append` — **≤6 calls, read-only** |
| 2 | `situate`           | context bundle                    | **one task node**: parent, `contributes_to` (weight+justification), 6 valuation dims, `needs_decomposition: true` | **pauli**                                          | `create_task, update_task, append, search, task_search, get_network_metrics, get_dependency_tree, AskUserQuestion`              |
| 3 | `decompose`         | due task + `workflows/INDEX.md`   | **unexploded subtask DAG** + chosen **workflow** with **review steps** built in (no blocking gate nodes)          | **pauli**                                          | `get_task, decompose_task, append, search, get_dependency_tree`                                                                 |
| 4 | `brief`             | one due subtask + regime          | **seven-element brief** → subtask body; dispatch by task-id                                                       | agnostic — **briefer ≠ executor**                  | `get_task, append, update_task, get_dependency_tree, Skill, Task`                                                               |
| — | _execute_           | task-id                           | deliverable + emitted evidence                                                                                    | any capable agent                                  | _(out of scope)_                                                                                                                |
| 5 | `/verify`           | deliverable + brief emit-contract | verdict: accept / critique-to-brief / escalate                                                                    | marsha (quality + claim-reliability)               | `Task, Read, Glob, Grep`                                                                                                        |
| 5 | `/strategic-review` | deliverable + emit-contract       | verdict (compliance lens)                                                                                         | rbg (axioms) + pauli (premise) + james (synthesis) | `Agent, Bash, Read, Glob, Grep, AskUserQuestion`                                                                                |

**Loop:** on FAIL the critique is addressed to the _brief_ → `brief` updates → re-dispatch. **Thin or
missing emitted evidence is itself a FAIL** — not a licence to re-investigate from scratch.

## Seam contracts (the exact records passed)

**hydrate → situate — the context bundle** (four named sections, written to the task body):

```markdown
## Intent — one-sentence restatement of the ask

## Context — prior knowledge/attempts/decisions, each with a spot-checkable node id

## Standards — applicable obligations, from workflows/INDEX.md + project config

## Dependencies — known blocking/related task ids
```

**decompose → brief — DAG row + regime record:**

```
DAG row:  | id | one-line scope | door-type (two-way|one-way) | depends_on |
Regime:   Process: <template…> · Gates: <template…> · Standing: <template…>   (by name, from workflows/INDEX.md)
```

**brief → execute — the seven-element brief** (prose, in the subtask body, never a step-script):
Intent (+why) · Scoped context (incl. the hydrate bundle's `## Context`) · Constraints · Autonomy +
non-goals · Done + observable AC · Emit-for-evaluation contract (rubric · claim-provenance ·
procedural record) · Effort budget + door-type.

**execute → evaluate — the emit-for-evaluation contract:** element 6 of the brief _is_ the
evaluator's evidence spec; the evaluator judges emitted evidence against the pre-agreed rubric, it
does not re-run the work.

## Intended fire order (⚠ several triggers not yet wired — see status table)

```mermaid
sequenceDiagram
    autonumber
    actor U as Ask
    participant H as hydrate
    participant S as situate (pauli)
    participant G as PKB graph
    participant D as decompose (pauli)
    participant B as brief
    participant X as execute
    participant E as evaluate

    Note over U,S: same conversational turn (fast)
    U->>H: raw prompt / task-id
    H->>S: context bundle
    S->>G: create task node · needs_decomposition=true
    Note over G,D: time passes — task rises in the queue
    G->>D: task comes due
    D->>G: subtask DAG + chosen workflow with review steps built in
    Note over B,E: per subtask, at dispatch (rolling-wave)
    G->>B: subtask due next
    B->>X: dispatch by task-id (brief in body)
    X->>E: deliverable + emitted evidence
    alt accept
        E-->>G: mark done · unblock downstream
    else needs work
        E-->>B: critique addressed to the brief
        B->>X: re-dispatch (bounded retries)
    end
```

## Invariants

- **pauli owns graph mutation** — only `situate`, `decompose`, `graph-maintenance` write graph
  structure (single authoritative writer for edges/scores).
- **briefer ≠ executor** — the identity that writes a brief never executes it; enforced structurally
  (`brief` dispatches by task-id, never inlines the brief text).
- **Rolling-wave** — `decompose` leaves subtasks coarse; `brief` pays the detail cost only for the
  subtask dispatching now.
- **Templates are composed, not invented** — `decompose` selects from `workflows/INDEX.md`; a missing
  template is a flagged library gap, never freelanced.
