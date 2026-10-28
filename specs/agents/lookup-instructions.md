---
title: Lookup Instructions and Direct Pauli Delegation
status: ready
---

# Lookup Instructions and Direct Pauli Delegation

Lookup instructions define the canonical protocol for how framework agents discover and disambiguate tasks, knowledge, and memory in the Personal Knowledge Base (PKB) when ambient prompt hydration has not attached context, and establishes direct, friction-free consultation between the conversational front agent (`ida`) and the PKB custodian (`pauli`). It serves front agents and executors who need contextual grounding without hunting for non-existent direct MCP tools, probing infrastructure configurations, or wondering how to query PKB state.

## User stories

### US-1 Universal lookup guidance in CORE.md

As an agent executing a turn, I want clear instructions in `CORE.md` on how to look up tasks, context, and knowledge when prompt hydration has not attached results, so that I do not hunt for direct PKB tools or investigate MCP plumbing.

- **AC-1.1** Given a session at load time before any prompt hydration has run, when the agent needs to inspect open tasks or prior context, then the agent invokes `/hydrate` to retrieve matching IDs and one-line summaries.
- **AC-1.2** Given a turn where prompt hydration attaches no context (empty results, ungrounded prompt, or skipped command), when the agent requires knowledge or task context, then the agent invokes `/hydrate` with ambiguous query terms.
- **AC-1.3** Given an agent looking for PKB information, when the agent checks available tools, then the agent never probes filesystem paths or investigates external MCP server configurations to locate PKB tools.

### US-2 Direct Pauli consultation for Ida

As Ida (the conversational front agent), I want to know that I can simply invoke Pauli as an in-session subagent and ask questions directly, so that I do not circle over tool availability or wonder how to query PKB memory and graph state.

- **AC-2.1** Given Ida needing PKB memory, task status, or graph context, when Ida formulates a query, then Ida invokes `pauli` directly as an in-session subagent with the question.
- **AC-2.2** Given Pauli receiving a direct question from Ida in session, when Pauli answers, then Pauli returns concise IDs and one-line findings directly to Ida without declining or requiring external bus routing.
- **AC-2.3** Given Ida handling a user question that requires PKB knowledge, when deciding how to proceed, then Ida never searches the filesystem, checks MCP configurations, or attempts direct PKB mutations; she asks Pauli.

### US-3 Proportionate hook boundaries without noisy spills

As an agent processing conversational turns, I want prompt hydration hooks to remain quiet when prompts do not match PKB entities, so that conversational context is not polluted with synthetic warnings or unnecessary overhead.

- **AC-3.1** Given a prompt submission where `search_the_pkb` finds no matches or returns empty content, when the hook executes, then nothing is injected into context, and the agent relies on CORE.md lookup instructions when disambiguation is needed.
- **AC-3.2** Given a hook error (such as an unreachable endpoint or missing credentials), when `search_the_pkb` fails, then the hook surfaces the single-line infrastructure failure without masking the defect or attempting silent fallback routes.

## Design

### 1. Canonical Lookup Protocol (`plugins/ida/CORE.md`)

Shared core instructions (`plugins/ida/CORE.md`, inlined into all built agent personas and referenced in repository `.agents/CORE.md`) define the unified lookup doctrine under a dedicated section `## Looking Things Up`:

1. **Ambient Hydration First**: On user prompts, incoming channel messages, and peer reports, prompt hydration automatically searches the PKB and injects relevant context before the turn begins.
2. **Explicit Lookup with `/hydrate`**:
   - At session load (before turns run or when operating without prior context).
   - On any turn where prompt hydration did not run (e.g. argument-less slash commands) or returned no hits, and the agent needs to disambiguate terms or check prior work.
   - Agents invoke `/hydrate <terms>` to receive a curated shortlist of IDs and one-line summaries.
3. **No Direct Tool Hunting**:
   - Front agents and general workers do not carry direct PKB MCP tools.
   - Agents must never search filesystem paths, query MCP server definitions (e.g., investigating `services`), or guess tool schemas to find PKB endpoints.
   - When `/hydrate` is insufficient or deep memory/graph context is needed, agents delegate to the specialized custodian (`pauli`).

### 2. Ida-Pauli Direct Consultation (`plugins/ida/agents/ida.md` & `pauli.md`)

To eliminate deliberation circling:

- **Ida Persona (`plugins/ida/agents/ida.md`)**:
  - Clarifies that Ida never performs direct PKB mutations or investigates MCP tools.
  - Under `Ask routing` and `In-session peers`, explicitly instructs: "For any question about the PKB, task status, memory, or knowledge graph context, you can simply call Pauli and ask her questions."
  - Prohibits circling over whether Pauli can be invoked: Pauli is an in-session subagent available for direct queries.
- **Pauli Persona (`plugins/ida/agents/pauli.md`)**:
  - Affirms that Pauli answers direct queries from Ida in session as well as peer requests on the bus.
  - Answers direct inquiries with matching node IDs and concise findings (one-line summaries), preserving full body reads only for the primary target artifact under review.

### 3. Proportional Intervention Options Pass & Enforcement Map Extract

Before establishing this enforcement mechanism, the options were evaluated against the enforcement pyramid (`specs/enforcement/enforcement.md`):

| Level | Mechanism Category | Evaluation & Decision |
| :- | :- | :- |
| 1 | `doctrine only` | **Rejected.** General architecture principles existed but failed to prevent runtime circling in real sessions (AGY trace). |
| 2 | `instructions` (`imperative`) | **Adopted.** Adding explicit imperative instructions in `CORE.md` and persona definitions directly guides model deliberation at zero token overhead for unaffected turns. |
| 3 | `JIT injection` | **Evaluated.** `SessionStart` already injects minimal session metadata and premise-check pointer; adding a concise session-load pointer is supported. However, injecting JIT reminders on every unhydrated prompt submit is rejected as invasive noise that pollutes regular conversational banter. |
| 4 | `structural` | **Rejected.** Gating or blocking tool use is disproportionate for query guidance. |
| 5 | `process` | **Rejected.** Post-turn review cannot prevent in-turn circling. |

#### Enforcement Map Extract

The following row is added to [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md):

| Rule / nudge | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Lookup Guidance: /hydrate & Calling Pauli](../plugins/ida/CORE.md) -- Look up tasks/knowledge via `/hydrate` when unhydrated at session load or prompt submit; Ida calls Pauli directly for PKB questions without tool hunting. | instructions | imperative | `plugins/ida/CORE.md:68-80`, `plugins/ida/agents/ida.md:28-32`, `plugins/ida/agents/pauli.md:19-25`: Instructs agents to use `/hydrate` at session load or on unhydrated turns rather than hunting for direct PKB tools; explicitly authorizes Ida to call Pauli directly for memory, task, and knowledge questions. Observation: Telegram msg 678 trace demonstrated Ida circling over missing PKB tools and hesitating to invoke Pauli. |

### 4. Outcome-Level Build Criteria (for `aops_da5ad152`)

The implementation task (`aops_da5ad152`) must satisfy the following verifiable criteria:

- [ ] **BC-1 (Universal CORE.md)**: `plugins/ida/CORE.md` contains a canonical `## Looking Things Up` section instructing agents to use `/hydrate` at session load and on unhydrated turns, and explicitly prohibiting searching the filesystem or probing MCP configurations for PKB tools.
- [ ] **BC-2 (Ida Instruction)**: `plugins/ida/agents/ida.md` explicitly states under `Ask routing` and governing rules that Ida can simply call Pauli as an in-session subagent and ask her questions for any PKB memory, task, or graph query.
- [ ] **BC-3 (Pauli Instruction)**: `plugins/ida/agents/pauli.md` explicitly accommodates direct in-session questions from Ida, responding with concise IDs and one-line summaries.
- [ ] **BC-4 (Enforcement Register)**: `specs/ENFORCEMENT-MAP.md` carries the `[Lookup Guidance: /hydrate & Calling Pauli]` row with exact line pinpoints and empirical evidence.
- [ ] **BC-5 (Repository Hygiene & Tests)**: All documented paths validate via `scripts/check_refs.py`, formatting conforms via `dprint` and `ruff`, and all existing unit tests in `tests/test_ida_hooks.py` and `tests/test_pkb_handlers.py` pass without regression.
