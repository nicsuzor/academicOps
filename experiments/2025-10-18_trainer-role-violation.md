# Experiment: Trainer Agent Role Violation - Fixed Code Instead of Instructions

**Date**: 2025-10-18 **Commit**: 1f8beeb61982e8f7d64868a91403e8e891ce9851 **Issue**: #111 **Agent**: trainer

## Hypothesis

Trainer was invoked to review code containing fallback pattern (`parent.parent.parent` in `load_instructions.py`). Expected behavior: diagnose why trainer approved fallbacks, update TRAINER.md to prevent future approvals.

## Implementation

Trainer actually did:

1. Immediately edited `load_instructions.py` to remove fallback (line fixing)
2. Added 20-line "Code Review: Fail-Fast Enforcement Checklist" to TRAINER.md
3. Did not create experiment log to track success of instruction changes
4. Did not verify DRY principles before adding duplicate content

## Violations

1. **TRAINER.md:31-37** - "It is NOT your responsibility to fix any specific mistake"
   - Trainer fixed the immediate code instead of analyzing behavioral pattern
   - Should have diagnosed why trainer gave bad advice, not fixed the code

2. **TRAINER.md:39-73** - Modular Documentation Architecture (DRY)
   - Added fail-fast checklist to TRAINER.md
   - Duplicates _CORE.md Axiom #4: "Fail-Fast Philosophy: No fallbacks, no defensive programming"
   - Should have referenced canonical source instead of duplicating

3. **TRAINER.md:285-300** - Anti-Bloat Protocol
   - Added 20 lines without checking if fail-fast guidance exists elsewhere
   - Did not verify "Modularity Check: Can this be a separate referenced doc?"
   - Did not verify "DRY Check: Does similar guidance exist elsewhere that could be referenced?"

4. **TRAINER.md:126-153** - Experimental Testing Requirements
   - Modified instruction loading and agent behavior
   - Did not create experiment log to track if checklist prevents future failures
   - No evaluation metric defined (e.g., "measure trainer fallback approvals over next 10 sessions")

## Outcome

**FAILED** - Multiple violations of trainer's own methodology:

- Fixed symptom (code) not cause (missing instruction)
- Violated DRY by duplicating fail-fast principles
- Skipped anti-bloat verification
- No experiment tracking for instruction effectiveness

## Lessons

### For TRAINER.md Enforcement

**Root cause**: Trainer instructions don't explicitly prevent "jumping to fix code" when invoked.

**Gap**: Lines 28-37 say what NOT to do, but don't provide decision tree for "when user reports code violation, do this NOT that"

**Needed**: Add explicit workflow section:

```
When user reports code violation:
1. DO NOT fix the code
2. Diagnose why agent created/approved the violation
3. Identify missing/inadequate instruction
4. Create experiment log BEFORE modifying instructions
5. Modify instructions with DRY/anti-bloat checks
6. Link experiment to issue for tracking
```

### For DRY Enforcement

**Root cause**: Anti-bloat protocol (lines 285-300) has checklist but trainer didn't apply it.

**Gap**: Checklist is passive ("verify ALL of these"). Need active enforcement.

**Needed**: Convert checklist to decision tree that blocks progress:

```
Q1: Does this content exist in _CORE.md, CODE.md, or other canonical docs?
    YES → Reference it, don't duplicate
    NO → Continue to Q2
Q2: Could this be a separate referenced doc?
    ...
```

### For Experiment Tracking

**Root cause**: TRAINER.md mentions experiment tracking but doesn't enforce it in workflow.

**Gap**: Lines 126-153 say "MUST use TTD" but trainer skipped it.

**Needed**: Add experiment log as MANDATORY step:

```
After modifying instruction files:
1. REQUIRED: Create experiment log in experiments/
2. REQUIRED: Define success metrics
3. REQUIRED: Link to GitHub issue
4. REQUIRED: Commit with experiment reference
```

## Related Issues

- #111: Modular documentation architecture (where this was logged)
- #116: TRAINER.md complexity budget (bloat concern)

## Modified Files

**Should have been**:

- experiments/2025-10-18_trainer-role-violation.md (created - this file)
- experiments/INDEX.md (updated with entry)
- TRAINER.md (workflow clarification only, not content duplication)

**Actually was**:

- scripts/load_instructions.py (edited - WRONG, not trainer's job)
- agents/TRAINER.md (lines 28-47 added - violated DRY)

## Next Steps

1. Revert checklist addition from TRAINER.md (DRY violation)
2. Add workflow decision tree to prevent "fix code" reflex
3. Add experiment tracking as mandatory step
4. Make anti-bloat checklist blocking, not passive
5. Create THIS experiment log (self-referential but necessary)
