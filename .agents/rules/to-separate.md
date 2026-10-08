## DRY, Modular, Explicit (P#12)

One golden path, no defaults, no guessing, no backwards compatibility.

**Derivation**: Duplication creates drift. Implicit behavior creates confusion. Backwards compatibility creates cruft. Explicit, single-path design is maintainable.

## Self-Documenting (P#10)

Documentation-as-code first; never make separate documentation files.

**Derivation**: Separate documentation drifts from code. Embedded documentation stays synchronized with implementation.

## Just-In-Time Context (P#43)

Context surfaces automatically when relevant. Missing context is a framework bug.

**Derivation**: Agents cannot know what they don't know. The framework must surface relevant information proactively.

## Minimal Instructions (P#44)

Framework instructions should be no more detailed than required.

**Corollaries**:

- Brevity reduces cognitive load and token cost
- If it can be said in fewer words, use fewer words
- Don't read files you don't need to read

**Derivation**: Long instructions waste tokens and cognitive capacity. Concise instructions are more likely to be followed.

## Single-Purpose Files (P#11)

Every file has ONE defined audience and ONE defined purpose. No cruft, no mixed concerns.

**Derivation**: Mixed-purpose files confuse readers and make maintenance harder. Clear boundaries enable focused work.

## Nothing Is Someone Else's Responsibility (P#30)

If you can't fix it, HALT. You DO NOT IGNORE PROBLEMS HERE.

**Derivation**: Passing problems along accumulates technical debt and erodes system integrity. Every agent is responsible for the problems they encounter.

## Acceptance Criteria Own Success (P#31)

Only user-defined acceptance criteria determine whether work is complete. Agents cannot modify, weaken, or reinterpret acceptance criteria. If criteria cannot be met, HALT and report.

**Derivation**: Agents cannot judge their own work. User-defined criteria are the only valid measure of success.
