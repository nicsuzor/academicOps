---
id: enforcement-report-contracts-and-logic-syntax
title: Enforcement -- Natural-Language Output Contracts and Plain-English Logic Syntax
type: spec
status: draft
tags: [enforcement, output-contracts, argumentation, logic-syntax, premise-check, verification]
---

# Natural-Language Output Contracts and Plain-English Logic Syntax

This specification defines the architectural principles and operational syntax for unstructured and semi-structured natural-language output contracts between LLM agents, establishing a formal, plain-English logic syntax for reports, supervisor reviews, and human handovers.

## 1. Problem Space: Free Prose vs. Schema Straightjacketing

Agentic systems face a structural dilemma at module and supervisor boundaries:

1. **The Free-Prose Failure Mode:**
   Unstructured narrative prose allows inferences to pass as observed findings, conceals missing warrants, obscures unstated premises, and permits speculative extrapolation without checkable grounding. Downstream agents and human principals cannot readily verify where observation ends and deduction begins.
2. **The Schema Straightjacketing Failure Mode:**
   Enforcing strict JSON Schema, Pydantic models, or token-level constrained decoding on cognitive boundaries degrades reasoning quality. Constrained decoding forces generation into context-free grammars at the token level, suppressing intermediate chain-of-thought exploration, inflating token costs by 15–38% with escaping boilerplate, and flattening epistemic texture into brittle scalar primitives.
3. **The Inter-Agent Governance Consensus:**
   Deterministic machine interfaces (tool parameter passing, database persistence, external API calls) require strict JSON schemas. Cognitive, deliberative, and supervisory boundaries (task handbacks, peer premise checks, inter-agent debates, supervisor audits, and human handovers) require **Natural-Language Output Contracts**: human-readable, token-efficient, markdown-native semi-structured prose that enforces epistemic boundaries and logical rigor without token-level grammar straightjacketing.

## 2. 2026 Best Practices for Natural-Language Output Contracts

Modern frontier LLM agent architectures enforce output contracts through six core pillars:

### 2.1 Delimited Structural Channels and Stream Tags

Frontier models are optimized for semantic XML-style tags and markdown header delimiters:

- **Tagged Blocks:** Delimiters (`<report>`, `<claim_ledger>`, `<verdict>`) isolate communicative channels. Harnesses verify block presence via non-intrusive stream checks without semantic regex parsing.
- **Key-Value Headers:** Standardized key-value lines (`VERDICT:`, `CLAIM:`, `GATE:`, `EVIDENCE:`) allow linear scanning, zero escaping overhead, and high human readability in terminal environments.

### 2.2 Atomic Claim Decomposition

Decomposing complex paragraphs into context-independent atomic propositions:

- A report is not an essay; it is an ordered set of discrete, testable claims.
- Compound sentences combining observed events with speculative causes must be split into separate claims so each is evaluated on its own merits.

### 2.3 Epistemic Basis Tagging and Anti-Laundering

Every load-bearing claim carries an explicit basis tag declaring its epistemic warrant:

- `[observed: <pointer>]`: Directly witnessed in the current session; cites a pinpoint pointer (`file:line`, command output, URL).
- `[attempted-and-failed: <command> → <error>]`: Direct execution attempt that failed; mandatory for capability and failure claims.
- `[exhaustively-searched: <scope> → 0 matches]`: Bounded search proving absence within an explicitly declared boundary.
- `[not-observed: <scope>]`: Absence of data within an inspected subset. Explicitly prohibited from grounding assertions of non-existence or inability.
- `[inferred: warrants P_n]`: Conclusion derived from stated premises via an explicit warrant.
- `[assumed]`: Explicit working premise or operational hypothesis.
- `[reported-by-another: <source>]`: Hearsay finding; retains origin qualification.

**The Status Survival (Anti-Laundering) Invariant:** Downstream consumers, supervisors, and controllers are strictly prohibited from promoting `[inferred]`, `[assumed]`, or `[reported-by-another]` claims to established facts. The basis qualifier must survive every transit hop.

### 2.4 Bounded Search on Negative Claims

Negative claims ("X does not exist", "X is missing", "I cannot run Y") are gated hardest:

- Asserting non-existence requires either `[attempted-and-failed]` with verbatim error output or `[exhaustively-searched]` with query and boundary specified.
- Without one of these two, the claim is strictly `[not-observed]` and cannot justify halting or blocking work.

### 2.5 Popperian Falsifiability and Confound Controls

- **Falsification Criterion:** Every load-bearing finding must state what single observable check or test would falsify it.
- **Confound Check:** Blaming an external dependency or prior system state requires a clean-room or differential control run. Without a control run, the entry is `CONFOUND CHECK: NOT RUN` and cannot be asserted as established fact.

### 2.6 Self-Contained Asymmetric Verification

Verification must be structurally cheaper than generation:

- The reviewer must be able to verify claims by checking cited pointers (`file:line`, command output, URL) without reading the generator's entire session trajectory.

## 3. Survey of Logic Syntaxes and Controlled Natural Languages

To structure inferences between atomic premises without resorting to inaccessible formalisms, several foundational frameworks provide guidance:

| Framework                             | Core Strengths                                                                                                                | Failure Modes for Runtime LLMs                                                         | Key Takeaway for aops                                                                            |
| :------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------- |
| **Argdown** (Voigt / Argunauts)       | Premise-conclusion syllogisms `(1)`, `(2)`, `----`, `(3)`; explicit support (`+>`), attack (`->`), and undercut (`_>`) edges. | Pure graph syntax can become verbose; requires compiler for visualization.             | The premise-separator-conclusion block structure and explicit line references.                   |
| **Toulmin Model**                     | 6-part argumentation: Claim, Grounds, Warrant, Backing, Qualifier, Rebuttal.                                                  | Slots can tempt models to hallucinate backing when unneeded.                           | Mandatory **Warrants** (linking grounds to claim) and **Rebuttals** (defeaters).                 |
| **Attempto Controlled English (ACE)** | Unambiguous English subset compiling directly to First-Order Logic (FOL/DRS).                                                 | Grammatical rigidity leads to out-of-grammar hallucinations under zero-shot prompting. | Strict quantifier scoping (`every`, `at least one`, `no`) and elimination of ambiguous pronouns. |
| **Catala** (Merigoux et al.)          | Executable default logic; general rules hold _unless_ an explicit exception applies.                                          | Designed for statutory legal code, not dynamic inter-agent reports.                    | **Default logic semantics:** explicit `UNLESS` clauses for exception handling.                   |
| **SBVR** (OMG Standard)               | Separates structural concepts (nouns), empirical facts (verbs), and deontic/alethic rules.                                    | Heavyweight enterprise ontology specification.                                         | Strict separation of terms, facts, and deontic constraints (`obligatory`, `prohibited`).         |
| **FActScore / Claimify**              | Decomposes text into verifiable, context-independent atomic factual claims.                                                   | Evaluative pipeline rather than an agent-facing reasoning syntax.                      | Pre-processing discipline: decompose and disambiguate before asserting.                          |
| **Chain-of-Verification (CoVe)**      | Independent factored verification questions to prevent confirmation bias.                                                     | Multi-call latency cost if applied naively to every sentence.                          | Supervisor premise checks must be executed independently of the report's framing.                |

## 4. The Proposed Plain-English Logic Syntax: Argdown-Lite Claim Ledger

The framework adopts **Argdown-Lite**: a simplified, plain-English claim ledger combining Argdown's premise-conclusion structure, Toulmin's explicit warrants, and Catala's defeasible exception handling.

### 4.1 Syntax Specification

A reasoning block consists of four sections:

```
[Pn] <Grounds / Empirical Premise> [basis-tag: pinpoint-pointer]
[Wn] WARRANT: <General structural invariant, domain rule, or operational mechanism>
[Dn] UNLESS: <Tested defeater, alternative explanation, or exception condition>
--------------------------------------------------------------------------------
THEREFORE [Cn] <Derived Claim> [inferred: basis; spine: Pn + Wn - Dn -> Cn]
```

1. **Empirical Premises (`[P1]`, `[P2]`, ...):** Atomic propositions of observed facts, failed executions, or bounded searches. Each line MUST carry an explicit basis tag and pinpoint citation.
2. **Warrant (`[W1]`, ...):** The explicit rule, invariant, or causal bridge explaining _why_ the premises necessitate or justify the conclusion.
3. **Defeater / Exception (`[D1]`, ...):** The alternative hypothesis, confound, or exception condition that was evaluated and ruled out (`[evaluated: <result>]`).
4. **Deduction Line (`----`):** Visual and structural boundary separating grounds from conclusions.
5. **Conclusion (`THEREFORE [C1]`):** The resulting claim, carrying an explicit **Spine** declaring the premises and warrants on which it rests.

### 4.2 Mapping to the Six Logic-Check Questions

The Argdown-Lite syntax maps directly to the six audit criteria in `hearsay.md`:

| Logic-Check Question (`hearsay.md`)                                             | Syntax Mechanism in Argdown-Lite                                                     |
| :------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------- |
| **1. Independent Subject:** What is the subject independent of what is told?    | Grounded exclusively in `[observed: <pointer>]` empirical premises (`[P]`).          |
| **2. Alternative Explanations:** Does evidence admit more than one explanation? | Evaluated in the `[D] UNLESS` defeater line with control results.                    |
| **3. Sufficiency & Warrant:** Is evidence sufficient and inferences warranted?  | Tested by the explicit `[W] WARRANT` line; invalid jumps lack a viable warrant.      |
| **4. Fact vs. Inference:** Is an inference masquerading as observed fact?       | Enforced by basis tag partitioning (`[observed]` on `[P]` vs `[inferred]` on `[C]`). |
| **5. Generalisation:** Does the conclusion generalize beyond the sample?        | Scope bounds must be stated explicitly in the conclusion line.                       |
| **6. Unstated Dependencies:** What does conclusion depend on that is unstated?  | Spine tracing exposes missing premises; unlinked dependencies fail audit.            |

## 5. Concrete Examples: Before and After

### Example 1: Reporting an Execution Blocker

#### Before (Free Prose -- Failing Audit)

> "I ran the test suite and it failed because the polecat container environment lacks the necessary network credentials to reach the server. We need to mount the credentials."

_Defects:_ Conflates observed test failure with an assumed cause (network credentials). Asserts an environmental capability limit without a failed command or bounded search. Lacks verifiable pointers.

#### After (Argdown-Lite Claim Ledger -- Passing Audit)

```text
[P1] Command `pytest tests/test_network.py` failed with exit code 1. [observed: run_command exit 1]
[P2] Test stderr output was: `ConnectionRefusedError: [Errno 111] Connection refused at localhost:8080`. [observed: step-12:line-4]
[P3] Service check `curl -s http://localhost:8080/health` returned connection refused. [attempted-and-failed: `curl -s http://localhost:8080/health` -> exit 7]
[W1] WARRANT: A connection refused on localhost:8080 indicates the target daemon is not listening on that port, not an external network authentication failure. [warrant: TCP transport layer semantics]
[D1] UNLESS: A firewall rule explicitly rejects localhost packets. Evaluated: `iptables -L` showed default ACCEPT policy with 0 reject rules. [observed: iptables-check]
--------------------------------------------------------------------------------
THEREFORE [C1] The failure is caused by the local server process being stopped, not missing credentials. [inferred; spine: P1 + P2 + P3 via W1; falsified by: server running on 8080]
```

### Example 2: Verifying a Code Implementation

#### Before (Free Prose -- Form-Only Compliance)

> "VERDICT: PASS
> CLAIM: Added the required validation to the task parser.
> GATE: Acceptance criteria met.
> EVIDENCE: Checked the code.
> CONFIDENCE: high"

_Defects:_ Form-only recitation. No pinpoint pointers. No indication of what was actually tested.

#### After (Argdown-Lite Claim Ledger -- Passing Audit)

```text
VERDICT: PASS
CLAIM: Task parser rejects parent/child cycles at write time with cycle error.
GATE: AC 2: "Cycles between parent and child tasks must raise InvalidCycleError".
EVIDENCE:
[P1] Unit test `test_task_cycle_rejected` added in `tests/test_tasks.py:45-62`. [observed: tests/test_tasks.py:45]
[P2] Execution `pytest tests/test_tasks.py -k test_task_cycle_rejected` passed with 1 passed in 0.12s. [observed: pytest output]
[P3] Code path in `lib/tasks/parser.py:112-124` raises `InvalidCycleError` when ancestor ID matches candidate ID. [observed: lib/tasks/parser.py:118]
[W1] WARRANT: Execution of a targeted unit test verifying the specific exception on cyclical input proves the gate condition is met. [warrant: testing doctrine]
--------------------------------------------------------------------------------
THEREFORE [C1] Acceptance Criterion 2 is satisfied on commit `a1b2c3d`. [inferred; spine: P1 + P2 + P3 via W1]
CONFIDENCE: high (falsified if `parser.create_task(id="A", parent="A")` does not raise `InvalidCycleError`)
CONFOUND CHECK: Clean control run verified on clean worktree.
```

## 6. Implementation and Boundary Enactments

1. **Inter-Agent Handbacks:**
   - Every supervisor report, handback, and release claim instantiates the six-field structured header with embedded Argdown-Lite claim ledgers for all load-bearing deductions.
2. **Supervisor Premise Checking:**
   - When a supervisor (Ida) audits an incoming report, it checks the Argdown-Lite block against the six questions in `hearsay.md`.
   - Any report that asserts an inference as an empirical premise (`[observed]`) without a primary source pointer is rejected with a `RETURN` verdict back to the author.
3. **Observability and Telemetry:**
   - Spans emitted by `premise_check_verdict.py` capture the spine lineage, premise count, and basis tags in span attributes (`premise_check.premises`, `premise_check.spine`), enabling automated audit sweeps of epistemic health across agent runs.
