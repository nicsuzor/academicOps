---
id: base-review-checkpoint
category: base
---

# Base: Review Checkpoint

**Composable base pattern.** Forces iterative quality loops via human review gates. Essential for research/academic work where methodology correctness matters beyond technical correctness.

## Pattern

1. BEFORE marking work complete, create a **review checkpoint task**:
   - `type: task` with `status: blocked`
   - `depends_on: [work-task-id]` (blocks completion)
   - `assignee: nic` (human reviewer)
   - Body documents what to verify (methodology, quality criteria)

2. Work task goes to `status: review` (not done)

3. Human reviews and either:
   - **Approves** → Both tasks marked done
   - **Rejects with feedback** → Work task back to `in_progress`, iterate

4. Loop until approved

## When to Use

- Research benchmarking (methodology must match research questions)
- Academic outputs (papers, data, analyses)
- Any work where "technically correct" ≠ "actually correct"
- Complex multi-step work where goalposts may shift

## Skip When

- Pure technical implementation with clear acceptance criteria
- Tasks where [[base-verification]] suffices
- Trivial changes

## Why This Exists

Technical verification (tests pass, code runs) is necessary but not sufficient for research work. A prompt template may render correctly while completely missing the research hypothesis. This pattern catches methodology drift by requiring explicit human sign-off.

## Escalation

If review reveals fundamental methodology issues:
- Document in task body (preserves reasoning)
- May need to return to [[decompose]] workflow
- Consider `/learn` if pattern failure recurs
