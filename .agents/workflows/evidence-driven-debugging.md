# Evidence-Driven Debugging Workflow

Move from ad hoc debugging (read code, patch, move on) to institutionalised debugging where
investigation artifacts become durable infrastructure.

## Core Principle

**Investigation artifacts are infrastructure, not throwaway work.**

Build the tool because you need it right now to investigate. Build it properly because you'll need
it again. By the end of a debugging session you must have: a tool that makes the bug visible, a fix
validated by that tool, and a test that uses the tool to prevent regression.

## The Antipattern to Avoid

Separating investigation (ad hoc) from infrastructure (speculative, built after). This fails
because investigation produces no durable artifacts and infrastructure gets built for a problem
that no longer matches what you found. **Collapse both tracks into one.**

## Phase 1: Instrument Before You Diagnose

Before reading source code, ask: _what tool would let me see what's actually happening?_

1. Build minimal logging at the decision point you care about:
   - What was the input? What was the output? Why?
   - Structured format (JSON lines preferred — machine-readable)
   - Commit it immediately
2. Use the instrument to produce an evidence-based diagnosis
   - Cite log output or tool output, not code reading
   - Code reading is for explaining the evidence, not forming the hypothesis

**Phase closes when:** instrument committed AND diagnosis written with evidence.

## Phase 2: Build a Reproducer, Then Fix

Build a CLI tool that reproduces the bug without a live session:

1. Takes state as input (e.g. `--tool Edit --state hydration_pending`)
2. Uses the real implementation — not a stub or reimplementation
3. Exit code encodes the result (0=allow, 1=block) so it's scriptable
4. Reproduce the bug first — confirm you can trigger it on demand
5. Fix the root cause
6. Confirm the fix with the same tool

**Phase closes when:** reproducer committed AND fix validated by the reproducer.

## Phase 3: Formalise Into Tests

Do not write tests from scratch. The instrumentation (Phase 1) and reproducer (Phase 2) contain
everything:

1. Tests call the reproducer as a subprocess — they test real logic, not stubs
2. Test cases are scenarios already explored: the bug case (fixed), happy path, edge cases
3. Generate a coverage matrix by running the reproducer across all known inputs — not by hand
4. Wire into CI

**Phase closes when:** test suite green in CI AND coverage matrix committed.

## Phase 4: Operationalise

Wrap investigation artifacts into permanent operational tooling:

1. **Health check command** — shows current system state and recent log tail; first thing to run
   when something seems wrong
2. **CI contract** — path-filtered, runs on PRs touching the relevant code, diffs coverage matrix,
   fails on regressions
3. **Contract document** — what the system does, what a maintainer must preserve, where the tools
   are

**Phase closes when:** a maintainer who didn't write any of this can understand the system from the
document alone.

## Decision Rules

- Reading source code without any tool output → stop, build the instrument first
- Built a throwaway script → commit it; throwaway scripts are undocumented tools
- "Infra work" is a separate track from "investigation" → collapse them
- A phase has no committed artifact → it is not done

## Task Title Template

```
Phase N: [Build X] to [observe/reproduce/validate Y]
```

Title encodes both the tool being built and the investigation it enables. If the tool doesn't
enable the stated investigation, the phase is not complete.

## See Also

- Full spec: `specs/evidence-driven-debugging.md`
- Example epic applying this workflow: `aops-fa32b8ad` (hook gate reliability)
