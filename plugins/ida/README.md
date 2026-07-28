# aops-ida

The interactive face: one agent, ida, who is the only agent in the framework that talks to the user.

## How it works

Everything the user says arrives at ida. Ida either answers it, escalates one named decision, or delegates it to james — and everything that comes back is filtered before the user sees it. The filter is the point of this plugin.

Engagement after an absence starts one step earlier. Before taking new work, ida commissions a reconcile sweep — delegated to a spawned agent, since she holds no knowledge-base tools of her own — and routes whatever finished uncertified to james for certification.

```mermaid
flowchart TD
    U([user]) --> IDA["ida<br/>agents/ida.md"]
    RET(["engagement after<br/>an absence"]) --> IDA
    IDA --> Q{"can ida settle<br/>this herself?"}

    Q -->|"yes — a status check,<br/>a read, a cheap probe"| ANS["answer inline"]
    Q -->|"blocking judgment call —<br/>scope, taste, tradeoff"| ESC["AskUserQuestion:<br/>one named decision,<br/>options pre-resolved"]
    Q -->|"no — substantive work"| J["james<br/>(aops plugin)"]

    IDA -->|"before new work"| SWEEP["reconcile sweep,<br/>delegated to an agent<br/>(aops-pkb skill)"]
    SWEEP --> UNC["completed but<br/>uncertified work"]
    UNC --> J

    J --> W["review agents · agent teams ·<br/>polecat containers"]
    W --> EV["evidence bundles<br/>and verdicts"]
    SWEEP --> EV
    EV --> F{"ida filters"}

    F -->|"operational detail,<br/>per-worker outcomes,<br/>intermediate states"| DROP["dropped"]
    F -->|"correct-but-wrong,<br/>or off the user's intent"| BLOCK["blocked —<br/>back to james to replan"]
    F -->|"what happened,<br/>where it is heading,<br/>what the user must decide"| SYN["synthesis"]

    ANS --> U
    ESC --> U
    SYN --> U
    BLOCK --> J
```

<!-- NS: this needs to be reconciled with the other graphs from other plugins.
- the contract between Ida and James has to be made explicit. Ida must be prohibited from doing substantive work if she is to keep the user's context clean. Ida should strictly synthesise output from James. Presumably if Ida needs to even check on the progress of async work, it should be James who goes looking, so Ida never even touches the PKB?
- What standards does Ida use to determine whether the input from James is good enough?
- why is Ida doing a reconcile sweep and not Pauli?
- what is 'certification'? where are the diffferent places it can be done?

-->

Ida holds between steps rather than driving ahead: after each step control returns to the user, who owns the sequence. Academic integrity is carried here — research data is immutable, and research, teaching, and publication outputs reach the user with full receipts before anything is marked done. The sign-off floor itself is not ida's alone: the `one-way-door` axiom binds every agent at an irreversible, outward-facing act, and ida's charter is the stricter domain layer over it.

## What it provides

| Kind  | Name  | Purpose                                                                               |
| ----- | ----- | ------------------------------------------------------------------------------------- |
| Agent | `ida` | The interactive face. Coordinates research work, delegates to james, filters returns. |

No skills, no commands, no hooks. Ida invokes skills the other plugins ship.

## Configuration

None. This plugin reads no environment variable and declares no `userConfig` field. No endpoint, host, path, token, or credential appears in anything it ships.

## Depends on

- `lib/doctrine/` — `bar`, `launder`, `probe`, `delegation`, `epistemics`, `governing-rules`, `halt`, `memory`, inlined into `agents/ida.md` at build time.
- The `aops` plugin at runtime, for **james**. Ida delegates all substantive work to him; without him she has nowhere to send it.
- The `aops-pkb` plugin at runtime, for the **reconcile** skill her engagement sweep is delegated to run.
