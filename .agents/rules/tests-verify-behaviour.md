---
trigger: always_on
description: A test earns its place by catching a plausible defect in code that executes; change-detector, mirror and tautological tests are defects.
---

## Tests verify behaviour, not our own code

A test exercises behaviour of code that executes, through its public interface, and fails when that behaviour breaks. Before writing one, name the defect it catches: a plausible bug in logic someone could get wrong. Mutation check: if you introduced that bug, the test must fail; if the test still passes, or it passes against the code before your change, it guards nothing and is not written.

These are defects, not tests:

- **Change-detector (mirror) tests** -- assert that a file, config, mapping or directory holds what it holds today: a string an agent, skill or instruction file contains, an entry the same PR added, the globs a checker was configured with, a source-to-dist file inventory. They fail on every legitimate edit and never on a real bug.
- **Tautological tests** -- the expected value is produced by the code under test, copied from its output, or restated from its implementation; or the assertion can fail only if a library or language primitive (a copy, a glob, a parse) breaks.
- **Implementation-coupled tests** -- assert private helpers, internal state, call order or a mock's call log instead of the output or observable effect.
- **Acceptance checks committed as tests** -- a one-off check that the change worked (a listing diff, a command's output, a fresh agent's run) is evidence for the PR and task report. It joins the suite only if it also guards code that executes against a plausible regression.

A change to agent-facing instruction text -- an agent definition, skill, workflow template, rule, axiom, AGENTS.md or CLAUDE.md, or slash command (markdown, unlike an executable CLI or script) -- owes no test. Prove it by a fresh agent's run that follows it, judged against the acceptance criteria; where test-first is asked for, the failing baseline is a run without the change. A change that modifies no code that executes adds no test. A spec is checked by review.

A test that earns its place is:

- one behaviour in arrange-act-assert form, named for the behaviour and the condition;
- hermetic and deterministic: no network, live services, wall clock, sleeps, unseeded randomness or state shared between tests; temp directories and fixtures instead;
- built on real collaborators where they are cheap, with test doubles only at process boundaries (network, model calls, clock) and never on the unit under test;
- checked against an expected value derived independently of the code (a worked example, a known-good fixture);
- covering boundary and error cases, not only the happy path;
- fast, with a failure message that says what broke.

A bug fix carries a regression test that reproduces the reported failure, red before the fix. An existing test that fails only on legitimate edits is deleted or rewritten to test behaviour.
