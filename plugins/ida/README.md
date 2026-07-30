# aops-ida

The interactive face: one agent, ida, who is the only agent in the framework that talks to the user.

## How it works

Everything the user says arrives at ida. Ida either answers it, escalates one named decision, or delegates it to james — and everything that comes back is filtered before the user sees it. The filter is the point of this plugin.

Engagement after an absence starts one step earlier. Before taking new work, ida commissions a reconcile sweep from pauli, and routes whatever finished uncertified to james for certification.

```mermaid
flowchart TD
    U([user]) --> IDA["ida<br/>agents/ida.md"]
    RET(["engagement after<br/>an absence"]) --> IDA
    IDA --> Q{"can ida settle<br/>this herself?"}

    Q -->|"yes — a status check,<br/>a read, a cheap probe"| ANS["answer inline"]
    Q -->|"blocking judgment call —<br/>scope, taste, tradeoff"| ESC["AskUserQuestion:<br/>one named decision,<br/>options pre-resolved"]
    Q -->|"no — substantive work"| J["james<br/>(aops plugin)"]

    IDA -->|"before new work"| PAULI["pauli — aops-pkb<br/>runs skills/reconcile.<br/>Named, never a general-purpose spawn:<br/>the only writer to the store"]
    PAULI --> UNC["landed but uncertified"]
    UNC --> J

    J --> W["review agents · agent teams ·<br/>polecat containers"]
    W --> EV["evidence bundles<br/>and verdicts"]
    PAULI --> EV
    EV --> F{"ida's filter (synthesis)"}

    F -->|"no checkable evidence<br/>and no stated failure reason"| REJECT["returned to james —<br/>not a handback"]
    F -->|"operational detail,<br/>per-worker outcomes,<br/>intermediate states"| DROP["dropped"]
    F -->|"correct-but-wrong,<br/>or off the user's intent"| BLOCK["blocked —<br/>back to james to replan"]
    F -->|"what happened,<br/>where it is heading,<br/>what the user must decide"| SYN["synthesis"]

    ANS --> U
    ESC --> U
    SYN --> U
    BLOCK --> J
    REJECT --> J
```

Ida holds between steps rather than driving ahead: after each step control returns to the user, who owns the sequence. Academic integrity is carried here — research data is immutable, and research, teaching, and publication outputs reach the user with full receipts before anything is marked done. The sign-off floor itself is not ida's alone: the `one-way-door` axiom binds every agent at an irreversible, outward-facing act, and ida's charter is the stricter domain layer over it.

### She does not touch the knowledge base — as a rule, not as a limitation

Her frontmatter declares a narrow `tools` list and exactly two delegation targets, `aops-ida:james` and `aops-pkb:pauli`. Those are the only agents she may spawn, and a general-purpose spawn is forbidden outright for the sweep: pauli is the only writer to the store, and a spawn that lands anywhere else reads a graph it cannot correct.

The prohibition is written as a rule she keeps rather than a capability she lacks, because the capability claim is not true of the runtime. `specs/agents/agent-authority.md` records an observed spawned ida holding `Agent, Artifact, Bash, Edit, Read, Skill, ToolSearch, Write` plus the full PKB MCP namespace, against a frontmatter granting four tools and no MCP at all. A rule survives an allowlist that does not hold; "she has no tools for it" stops being a reason the moment the harness hands her some.

The sweep stays hers to commission for a reason that is not about tooling. Re-engagement after an absence is an event only she observes — she is the agent in the room when the user comes back. Commissioning is her act; the sweep, and every write it makes, is pauli's.

### The standard she applies to what comes back

Two floors, and they are different questions.

**Is this a handback at all?** Every load-bearing claim carries checkable evidence — a command and its output, a `file:line` pointer, a resolving URL, a quoted source — or a stated failure reason. There is no third option, and honest failure is always a legal exit. A return carrying neither is not a thin handback to be summarised charitably; it is noise, and it goes back to james rather than to the user (`specs/enforcement/evidence-contract.md`).

**Is this what was actually wanted?** She is the only layer holding the user's intent, and a brief carries the ask, never the ambition behind it. So she judges every delivered artifact against the intent, not against the brief it was written from — and blocks work that is correct-but-wrong, which is a planning failure and goes back to be replanned rather than into another fix loop. A worker's self-reported success is never rubber-stamped, and "fixed" means the originally-failing behaviour was observed passing, not that a diff exists.

### The contract between ida and james

Two signatures land on `done`, in this order, and neither substitutes for the other (`specs/enforcement/workflow.md`).

**Certification is james's**, at unit completion. He commissions the review the graph already carries — the review nodes `decompose` emitted as blocking dependencies — reads the verdict, and writes it onto the task record. What it certifies is mechanics, quality, and compliance with the brief. He supplies no judgment of his own there and never relays a worker's own claim of success in its place.

**Acceptance is ida's**, against the user's intent. Certification without acceptance ships work nobody weighed against what was wanted; acceptance without certification asks her to vouch for mechanics she never saw.

Ida routes but never certifies. The reconcile sweep detects uncertified work but never certifies it either. There is no status and no frontmatter field for certification: it is prose on the task record, and the four surfaces that write it are named in the aops plugin's own README.

What crosses between them is the evidence contract, defined once in `specs/enforcement/evidence-contract.md` and set out with its structured form in `plugins/aops/README.md`, which owns james. Whichever form a handback takes, two rules bind it: checkable evidence or a stated failure reason, and every claim labelled Observed or Reported. It is written to the PKB task record, which is the only message bus; a result held in a transcript or a pull-request body has not been delivered.

## What it provides

| Kind  | Name  | Purpose                                                                               |
| ----- | ----- | ------------------------------------------------------------------------------------- |
| Agent | `ida` | The interactive face. Coordinates research work, delegates to james, filters returns. |

No skills, no commands, no hooks. The skills the other plugins ship reach her only as work she delegates to james or to pauli.

## Configuration

None. This plugin reads no environment variable and declares no `userConfig` field. No endpoint, host, path, token, or credential appears in anything it ships.

## Depends on

- `lib/axioms/` — `bar`, `launder`, `probe`, `delegation`, `epistemics`, `governing-rules`, `halt`, `memory`. These are applied globally as rule context rather than inlined via `@include`.
- The `aops` plugin at runtime, for **james**. Ida delegates all substantive work to him; without him she has nowhere to send it.
- The `aops-pkb` plugin at runtime, for **pauli**, who runs the **reconcile** skill her engagement sweep commissions.
