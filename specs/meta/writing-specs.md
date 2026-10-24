---
title: Writing specs
---

# Writing specs

A spec states what one feature does and why. A person can judge the design from the spec alone, and an agent can build and test the feature from it alone.

## Template

```markdown
---
title: <feature>
status: draft | ready | in_progress | superseded
---

# <Feature>

<One paragraph: what the feature is for and who it serves.>

## User stories

### US-1 <short name>

As a <role>, I want <capability>, so that <outcome>.

- **AC-1.1** Given <state>, when <event>, then <observable result>.
- **AC-1.2** ...

## Design

<The behaviour that meets the stories: the contract, its inputs and outputs,
states and invariants, and the reason for each design choice.>

## Open questions

- <A decision the spec still needs, with the options in play.>
```

`status` is the document's lifecycle. Open questions exist only while the spec is `draft`; a spec is `ready` once every question has its answer written into the stories or the design.

## Rules

**One feature per spec.** When a spec takes on a second purpose, split it into two specs.

**Stories and acceptance criteria come first.** Every story carries criteria an observer can mark pass or fail from outside the feature, written as Given / When / Then. Every requirement in the design traces to a story; a requirement that serves no story comes out.

**Behaviour, not mechanism.** The spec states what the feature does and why. The implementer chooses how: components, files, commands, call paths, hooks, modes and steps all belong to the implementation.

**Self-contained.** A reader needs no other file to understand the spec. Where the feature needs something from its surroundings, the spec states that need as its own requirement ("each claim arrives with a pointer to its evidence") and leaves the supplier unnamed. The spec carries no links to other specs, rules, agents, harnesses or code. The test: a change to any other feature never forces an edit here.

**The contract, not its enforcement.** A spec defines what the feature promises. The checks, gates, reminders and reviews that hold parties to that promise belong in their own spec, or, when simple, in `ENFORCEMENT-MAP.md`.

**Positive and direct.** Each sentence states what is true and who does it: "the receiver checks every pointer", not "the sender is not responsible for pointers". Non-goals, exclusions and disclaimers stay out; whatever the spec leaves unstated is out of scope.

**Concise.** Say each thing once, in the fewest words that carry the design intent. Rationale earns a sentence where a choice would otherwise look arbitrary.

**No provenance.** Who decided, when, in which session or task, and what the design used to be all live in git history and the tracking task.

**The designed target.** A spec states the intended behaviour and may run ahead of the code. Where the code drifts from the spec, the code has a bug or an unfinished change. When the design itself changes, the spec changes in the same pull request.

## Review

A spec passes review when a reviewer can answer yes to each question:

1. Does it cover exactly one feature?
2. Can every acceptance criterion be marked pass or fail by observation?
3. Does every design requirement trace to a story?
4. Is it free of implementation detail, enforcement, links to other parts of the framework, and statements of what the feature does not do?
5. Would it survive unchanged if any other feature were rewritten?
