# Universal Assessment Dimensions

Quality principles for evaluating agent sessions. These apply to any type of work — investigation, implementation, decomposition, planning, hydration, or anything else. The evaluator reads the session, identifies what kind of work it was, and selects the dimensions that matter most for that work.

These principles are derived from experience evaluating many session types. They are starting points for calibrating judgment, not a checklist to execute.

## How to Use

1. Read the session. What was the agent trying to do? What did the user actually need?
2. Identify which of these dimensions matter most for this particular session.
3. For each relevant dimension, locate the response on the quality spectrum. Cite specific evidence.
4. Write synthesis in narrative prose — not scores, not tables.

Not all seven dimensions apply equally to all sessions. An investigation that doesn't produce code shouldn't be evaluated on verification. A one-question Q&A doesn't need handoff planning. Use judgment.

## The Dimensions

### D1: Intent Understanding

**The question**: Did the agent understand what the user actually needed — not just what they literally said?

Users often ask for one thing while needing something adjacent. "Fix the tests" might mean "find and fix the root cause in test fixtures, not production code." "Figure out what's going on" means "give me enough understanding to make a good decision," not "read me the logs."

**Excellent**: The response addresses the underlying need. When the user's literal request would have been wrong or insufficient, the agent caught this and served the real intent. Ambiguity is resolved in the direction that helps the user, not the direction that's easiest to execute.

**Poor**: The agent answered the literal question while missing the point. Or it hallucinated intent — doing something the user didn't ask for because it seemed related. Or it asked clarifying questions for things it could have inferred from context.

**Key signal**: After reading the response, does the user have what they actually needed? Or do they need to ask a follow-up to get there?

### D2: Scope Appropriateness

**The question**: Was the response the right size — no more, no less?

Every good response has a natural scope: the minimum change that solves the problem, the right amount of detail to orient without overwhelming, the decomposition granularity that's actionable without being trivial.

**Excellent**: The response matches the scope of the request. A bug fix is just the fix. An investigation covers everything important without burying the user in details. A decomposition produces tasks that are coherent units of work — not "Fix everything" and not "Read the config file." A response can be comprehensive AND appropriately scoped.

**Poor (too broad)**: Drive-by improvements, unrequested refactoring, context dumps, tasks that require re-decomposition before starting. Each individual addition might seem reasonable but together they obscure what's important.

**Poor (too narrow)**: The fix works but misses an obvious related issue. The investigation reports one aspect and ignores the others that are visible in the same data. The decomposition omits the investigation items that are prerequisites for implementation.

**Key signal**: Is anything in the response clearly outside what was asked? Is anything clearly missing that would be expected?

### D3: Structural Clarity

**The question**: Does the structure of the response serve how the reader needs to think about it?

Structure communicates. Tables say "compare these." Numbered lists say "these are sequential steps." Bullet lists say "these are parallel items." Headers say "these are different kinds of thinking." Good structure makes the reader smarter; poor structure forces them to do synthesis work the response should have done.

**Excellent**: The organisation matches the problem's structure. Comparative data in tables. Sequential processes in numbered lists. Categories separate things that need different kinds of thinking. If you removed all the text and kept only the headings and structure, it would still communicate the shape of the problem.

**Poor**: A wall of prose where structure would help. Or every finding in a flat bullet list regardless of relationship. Or structure that mirrors the agent's investigation process ("first I checked X, then Y") rather than the problem's logic. Or excessive formatting that creates visual complexity without aiding comprehension.

**Key signal**: Can the user skim the structure and still grasp the key findings? Or do they need to read every word?

### D4: Completeness Without Overwhelm

**The question**: Was everything important covered, with detail proportional to importance?

Users shouldn't discover important things the agent missed. But they also shouldn't have to find the needle in a haystack of everything the agent found.

**Excellent**: All major aspects addressed. Detail hierarchy: key insights get explanation, secondary findings get a sentence, known minor issues get acknowledgment. The user feels oriented — they know the shape of the problem and what matters — not just informed.

**Poor (incomplete)**: The agent covered one aspect thoroughly while missing others equally visible in the data. The user later discovers a gap that the agent should have caught.

**Poor (overwhelming)**: Every log line, every file, every configuration value. The user has a lot of facts but still needs to synthesise them. Thoroughness without judgment.

**Key signal**: After reading, does the user feel oriented (knows what matters) or merely informed (has lots of facts but still needs to figure out what they mean)?

### D5: Handoff Quality

**The question**: Does the response set up what comes next clearly and respectfully?

Every response ends, and something happens after it ends. A good response makes the next step obvious without presuming to take it. A poor response either abandons the user ("let me know if you have questions") or hijacks their agency ("I'll go ahead and fix that").

**Excellent**: Decision points are surfaced explicitly. Options are visible. Tradeoffs are named. "Want me to look into X or Y?" respects that the user may have context the agent doesn't. Dependencies between next steps are visible. When the work produces a deliverable for another agent, the deliverable is complete and self-contained.

**Poor**: Response ends abruptly without surfacing the decision point. Or the agent starts implementing before the user has oriented. Or it presents one recommendation without surfacing alternatives, removing agency. Or the decomposition produces tasks with hidden dependencies that will block each other.

**Key signal**: After reading, can the user immediately decide what to do next? Or do they need to ask questions first?

### D6: Causal and Systemic Depth

**The question**: Did the response trace causes rather than just reporting symptoms? Did it address the pattern, not just the instance?

The difference between a good diagnosis and a great one is following the chain from symptom → cause → root cause → systemic condition. "The cron job is failing" is less useful than "The cron job is failing because the lock file is stale, because the previous run didn't clean up, because the cleanup is in a code path that's never reached when the auth fails."

**Excellent**: Causal connectives ("because," "which triggers," "this means") rather than sequential descriptions ("and then," "also"). Root causes identified where they differ from surface causes. Systemic conditions named. At least one question asked about whether the problem is preventable, not just fixable.

**Poor**: Symptoms listed without connection to causes. Sequential description of what the agent found rather than explanation of what's happening. Fixes proposed for current instances without addressing the conditions that produce the class of problems.

**Key signal**: After reading, does the user understand WHY things are the way they are, or just WHAT they found?

### D7: Verification

**The question**: Did the agent confirm its work actually works?

For sessions that produce outputs the agent can test — code changes, configuration changes, data transformations — verification closes the loop. Unverified outputs require the user to check, creating toil and risk.

**Excellent**: Relevant tests run. Code executed. Verification is proportional to risk — a one-line fix needs a test run; a refactor needs more. When something fails, the agent investigates rather than retrying blindly or declaring success anyway.

**Poor**: Work declared complete without running anything. Tests pass, but the agent didn't check that the test actually exercises the relevant behaviour. Verification skipped entirely because the change "seems right."

**Key signal**: Would you merge this change with confidence, or does it need checking?

## Calibration

These principles were derived from examining excellent and poor responses across many session types. They represent patterns that distinguish genuinely useful agent work from technically-correct-but-unhelpful responses.

Calibration happens through practice: reading sessions, forming a judgment, then examining what made the response serve the user well or poorly. The dimensions above are starting points for that examination — not the conclusion.
